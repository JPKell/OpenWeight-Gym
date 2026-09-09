#!/usr/bin/env bash
# Apply MEMORY_SAFETY.md §2 to this host: cap and re-default the Ollama daemon, pin FreeWeight's
# context, and (with --fire) prove the guard once by driving Ollama past the cap on purpose.
#
#   docs/scripts/apply_memory_safety.sh            # apply + verify
#   docs/scripts/apply_memory_safety.sh --fire     # also fire the guard (§2.3), ~1 min
#
# Idempotent: re-running rewrites the same override and leaves an existing context_size alone.
# Sizes default to the reference machine (30 GB RAM); pass MEMORY_MAX_G / MEMORY_HIGH_G /
# CONTEXT_TOKENS in the environment to change them.
set -euo pipefail

MEMORY_MAX_G="${MEMORY_MAX_G:-24}"
MEMORY_HIGH_G="${MEMORY_HIGH_G:-22}"
CONTEXT_TOKENS="${CONTEXT_TOKENS:-8192}"
OVERRIDE=/etc/systemd/system/ollama.service.d/override.conf
FW_CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/freeweight/config.toml"
FIRE=0; [[ "${1:-}" == "--fire" ]] && FIRE=1

say() { printf '\n== %s\n' "$*"; }
fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }

# ---- 0. preconditions --------------------------------------------------------------------------
command -v systemctl >/dev/null || fail "systemd required"
systemctl cat ollama >/dev/null 2>&1 || fail "no ollama.service on this host"
total_kb=$(awk '/MemTotal/ {print $2}' /proc/meminfo)
total_g=$(( total_kb / 1024 / 1024 ))
(( MEMORY_MAX_G < total_g )) || fail "MEMORY_MAX_G=${MEMORY_MAX_G} is not below RAM (${total_g} G)"
(( MEMORY_HIGH_G < MEMORY_MAX_G )) || fail "MEMORY_HIGH_G must be below MEMORY_MAX_G"

# ---- 1. Ollama unit override (§2.1) ------------------------------------------------------------
say "Ollama override -> $OVERRIDE  (MemoryHigh=${MEMORY_HIGH_G}G MemoryMax=${MEMORY_MAX_G}G ctx=${CONTEXT_TOKENS})"
if [[ -f "$OVERRIDE" ]]; then
    sudo cp -n "$OVERRIDE" "${OVERRIDE}.bak.$(date +%Y%m%d)" && echo "backup: ${OVERRIDE}.bak.$(date +%Y%m%d)"
fi
sudo mkdir -p "$(dirname "$OVERRIDE")"
sudo tee "$OVERRIDE" >/dev/null <<EOF
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
# Daemon default for requests that set no num_ctx. Applications set it per run.
Environment="OLLAMA_CONTEXT_LENGTH=${CONTEXT_TOKENS}"
# ADR-0038: one model per GPU.
Environment="OLLAMA_MAX_LOADED_MODELS=1"
# ADR-0119: cgroup cap, swap denied so a kill is fast, oomd on the unit as well as the session.
MemoryHigh=${MEMORY_HIGH_G}G
MemoryMax=${MEMORY_MAX_G}G
MemorySwapMax=0
ManagedOOMMemoryPressure=kill
ManagedOOMMemoryPressureLimit=50%
EOF
sudo systemctl daemon-reload
sudo systemctl restart ollama

say "verify unit"
systemctl show ollama -p MemoryHigh -p MemoryMax -p MemorySwapMax -p ManagedOOMMemoryPressure \
    -p ManagedOOMMemoryPressureLimit
for _ in $(seq 1 20); do curl -fs http://127.0.0.1:11434/api/version >/dev/null && break; sleep 1; done
curl -fs http://127.0.0.1:11434/api/version >/dev/null || fail "ollama did not come back"
grep -q "OLLAMA_CONTEXT_LENGTH=${CONTEXT_TOKENS}" <(systemctl show ollama -p Environment) \
    || fail "OLLAMA_CONTEXT_LENGTH not applied"
oomctl | grep -q ollama.service && echo "oomd: ollama.service monitored" \
    || echo "oomd: not yet listed (pressure monitoring registers on first sample; re-run oomctl in a minute)"

# ---- 2. FreeWeight: pin the context (§6 checklist) --------------------------------------------
say "FreeWeight -> $FW_CONFIG"
mkdir -p "$(dirname "$FW_CONFIG")"
touch "$FW_CONFIG"
if grep -qE '^\s*context_size\s*=' "$FW_CONFIG"; then
    echo "context_size already set: $(grep -E '^\s*context_size\s*=' "$FW_CONFIG" | head -1 | xargs)"
elif grep -qE '^\s*\[runtime\]' "$FW_CONFIG"; then
    sed -i "/^\s*\[runtime\]/a context_size = ${CONTEXT_TOKENS}   # MEMORY_SAFETY.md: never unset" "$FW_CONFIG"
    echo "added context_size = ${CONTEXT_TOKENS} under existing [runtime]"
else
    printf '\n[runtime]\ncontext_size = %s   # MEMORY_SAFETY.md: never unset\n' "$CONTEXT_TOKENS" >> "$FW_CONFIG"
    echo "appended [runtime] context_size = ${CONTEXT_TOKENS}"
fi

# ---- 3. fire the guard on purpose (§2.3) ------------------------------------------------------
if (( FIRE )); then
    model=$(ollama list 2>/dev/null | awk 'NR>1 {print $1, $3, $4}' | sort -k2 -n -r | head -1 | cut -d' ' -f1)
    [[ -n "$model" ]] || fail "no model pulled; cannot fire the guard"
    say "firing guard with $model at num_ctx=262144 (expect: runner dies, daemon restarts, desktop stays)"
    before=$(systemctl show ollama -p MainPID --value)
    curl -s --max-time 180 http://127.0.0.1:11434/api/generate \
        -d "{\"model\":\"$model\",\"prompt\":\"hi\",\"stream\":false,\"options\":{\"num_ctx\":262144}}" \
        | head -c 400; echo
    sleep 5
    say "journal"
    journalctl -u ollama --since "-4m" --no-pager | grep -iE 'oom|killed|memory|exit|error' | tail -8 || true
    journalctl -k --since "-4m" --no-pager | grep -iE 'oom|killed process' | tail -4 || true
    after=$(systemctl show ollama -p MainPID --value)
    echo "MainPID before=$before after=$after  ($( [[ "$before" != "$after" ]] && echo 'daemon restarted' || echo 'daemon survived; runner was the victim or the request was refused'))"
    ollama ps
fi

say "done — remaining manual steps"
cat <<'EOF'
* Launch long runs and live tests in a capped scope until rows N4–N6 ship:
    systemd-run --user --scope -p MemoryHigh=22G -p MemoryMax=24G -p MemorySwapMax=0 freeweight run start ...
    systemd-run --user --scope -p MemoryHigh=22G -p MemoryMax=24G -p MemorySwapMax=0 loadcoach serve
* On an Ollama install set  [benchmarks] max_fit_context_tokens  (row N5) once it exists.
EOF
