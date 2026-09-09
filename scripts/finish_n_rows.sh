#!/usr/bin/env bash
# Finish rows N1–N6 (docs/history/N*_HANDOFF.md): everything the model session was not allowed to
# do — push, tag, publish, relock — in the order the dependencies force.
#
#   docs/scripts/finish_n_rows.sh                # run every step from the start
#   docs/scripts/finish_n_rows.sh --from locks   # resume at a step (see STEPS below)
#   docs/scripts/finish_n_rows.sh --host         # also apply MEMORY_SAFETY.md §2 first (sudo)
#   docs/scripts/finish_n_rows.sh --ideapress-release 1.5.0   # also cut IdeaPress (row N2)
#
# STEPS, in order:
#   host            apply_memory_safety.sh (only with --host)
#   push-modelrack  push py/ModelRack main, tag v0.8.0, push the tag, wait for PyPI to serve it
#   locks           regenerate ci.lock in FreeWeight, LoadCoach, IdeaPress on python3.13 against
#                   the published modelrack 0.8.0 (IdeaPress's pin widened to >=0.7,<0.9 first),
#                   commit
#   push-apps       push main in docs, ToolYard, FreeWeight, LoadCoach, IdeaPress, PromptCadence;
#                   wait for each CI run
#   tag-apps        tag freeweight v1.2.0, loadcoach v1.3.0 (and IdeaPress if asked); push tags;
#                   wait for PyPI
#   verify          pip index versions for every published package
#
# Idempotent: a tag that exists is not re-made, a lock that did not change is not committed, a
# push with nothing to push is a no-op. Every wait polls; the PyPI `environment: pypi` approval is
# a click in GitHub Actions the script cannot make — it tells you where and keeps polling.
set -euo pipefail

SUITE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STEPS=(host push-modelrack locks push-apps tag-apps verify)
FROM=""; HOST=0; IDEAPRESS_VERSION=""
while (($#)); do
    case "$1" in
        --from) FROM="$2"; shift 2 ;;
        --host) HOST=1; shift ;;
        --ideapress-release) IDEAPRESS_VERSION="$2"; shift 2 ;;
        *) echo "unknown argument: $1" >&2; exit 2 ;;
    esac
done

say()  { printf '\n\033[1m== %s\033[0m\n' "$*"; }
fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
need() { command -v "$1" >/dev/null || fail "$1 not on PATH"; }
need git; need gh; need python3.13; need curl

# ---- helpers ------------------------------------------------------------------------------------
clean_or_fail() {  # a dirty tree is somebody else's work in progress; never push over it
    local dirty; dirty="$(git -C "$1" status --short | wc -l)"
    (( dirty == 0 )) || fail "$1 has $dirty uncommitted change(s); commit or stash before pushing"
}
push_main() {
    clean_or_fail "$1"
    local ahead; ahead="$(git -C "$1" rev-list --count '@{u}..HEAD')"
    if (( ahead == 0 )); then echo "$1: nothing to push"; return; fi
    echo "$1: pushing $ahead commit(s)"; git -C "$1" push
}
tag_and_push() {  # repo tag
    if git -C "$1" rev-parse -q --verify "refs/tags/$2" >/dev/null; then
        echo "$1: tag $2 exists"
    else
        git -C "$1" tag -a "$2" -m "$2"; echo "$1: tagged $2"
    fi
    git -C "$1" push origin "refs/tags/$2"
}
wait_ci() {  # repo — wait for the newest CI run on main to finish, fail if it failed
    local run
    for _ in $(seq 1 12); do
        run="$(gh run list -R "$(repo_slug "$1")" --workflow CI --branch main --limit 1 --json databaseId --jq '.[0].databaseId' 2>/dev/null || true)"
        [[ -n "$run" ]] && break; sleep 10
    done
    [[ -n "$run" ]] || fail "$1: no CI run appeared"
    echo "$1: watching CI run $run"; gh run watch -R "$(repo_slug "$1")" "$run" --exit-status
}
repo_slug() { git -C "$1" remote get-url origin | sed -E 's#.*github.com[:/]##; s#\.git$##'; }
pypi_serves() {  # package version — true when PyPI's JSON lists the version
    curl -fs "https://pypi.org/pypi/$1/json" | python3 -c 'import json,sys; print(sys.argv[1] in json.load(sys.stdin)["releases"])' "$2" 2>/dev/null | grep -q True
}
wait_pypi() {  # package version repo — poll up to 60 min; the release job needs the pypi environment approved
    if pypi_serves "$1" "$2"; then echo "PyPI already serves $1 $2"; return; fi
    echo "Waiting for PyPI to serve $1 $2."
    echo "  If the release job is pending approval: https://github.com/$(repo_slug "$3")/actions  (environment: pypi)"
    for _ in $(seq 1 120); do
        sleep 30; if pypi_serves "$1" "$2"; then echo "PyPI serves $1 $2"; return; fi
    done
    fail "$1 $2 not on PyPI after 60 min"
}
version_of() { python3 - "$1" <<'EOF'
import re, sys, pathlib
print(re.search(r'__version__ = "([^"]+)"', pathlib.Path(sys.argv[1]).read_text()).group(1))
EOF
}
step_enabled() {  # step — true once we have reached --from
    if [[ -z "$FROM" ]]; then return 0; fi
    local seen=0; for s in "${STEPS[@]}"; do [[ "$s" == "$FROM" ]] && seen=1; [[ "$s" == "$1" ]] && { (( seen )) && return 0 || return 1; }; done
    fail "unknown --from step: $FROM (one of: ${STEPS[*]})"
}
relock() {  # repo extras... — cut ci.lock on python3.13 with pip-tools 7.6.1, moving modelrack only
    local repo="$1"; shift
    ( cd "$repo" && "$LOCKENV/bin/pip-compile" --strip-extras --generate-hashes --no-emit-index-url \
        "$@" --upgrade-package modelrack --output-file requirements/ci.lock pyproject.toml >/dev/null )
    if git -C "$repo" diff --quiet -- requirements/ci.lock; then echo "$repo: ci.lock unchanged"; return; fi
    grep -qE '^modelrack==0\.8\.' "$repo/requirements/ci.lock" || fail "$repo: ci.lock does not pin modelrack 0.8.x"
    git -C "$repo" add requirements/ci.lock
}

MR_VERSION="$(version_of "$SUITE/py/ModelRack/src/modelrack/__about__.py")"
FW_VERSION="$(version_of "$SUITE/FreeWeight/src/freeweight/__about__.py")"
LC_VERSION="$(version_of "$SUITE/LoadCoach/src/loadcoach/__about__.py")"
[[ "$MR_VERSION" == 0.8.* ]] || fail "py/ModelRack is at $MR_VERSION, expected 0.8.x (row N4)"

# ---- host --------------------------------------------------------------------------------------
if step_enabled host && (( HOST )); then
    say "host: MEMORY_SAFETY.md §2"
    "$SUITE/docs/scripts/apply_memory_safety.sh"
fi

# ---- push-modelrack ----------------------------------------------------------------------------
if step_enabled push-modelrack; then
    say "push-modelrack: modelrack $MR_VERSION"
    push_main "$SUITE/py/ModelRack"
    wait_ci "$SUITE/py/ModelRack"
    tag_and_push "$SUITE/py/ModelRack" "v$MR_VERSION"
    wait_pypi modelrack "$MR_VERSION" "$SUITE/py/ModelRack"
fi

# ---- locks -------------------------------------------------------------------------------------
if step_enabled locks; then
    say "locks: ci.lock against modelrack $MR_VERSION (python3.13, pip-tools 7.6.1)"
    pypi_serves modelrack "$MR_VERSION" || fail "PyPI does not serve modelrack $MR_VERSION yet; run --from push-modelrack"
    LOCKENV="${TMPDIR:-/tmp}/finish-n-rows-lockenv"
    [[ -x "$LOCKENV/bin/pip-compile" ]] || { python3.13 -m venv "$LOCKENV"; "$LOCKENV/bin/pip" install -q "pip-tools==7.6.1"; }
    # IdeaPress uses modelrack's Ollama/OpenAI adapters only; 0.8 is additive, and a pin below 0.8
    # would stop the four applications co-installing once FreeWeight and LoadCoach require it.
    sed -i 's/"modelrack>=0.7,<0.8"/"modelrack>=0.7,<0.9"/' "$SUITE/IdeaPress/pyproject.toml"
    sed -i 's/| `modelrack` | `>=0.7,<0.8` |/| `modelrack` | `>=0.7,<0.9` |/' "$SUITE/IdeaPress/README.md"
    git -C "$SUITE/IdeaPress" add pyproject.toml README.md
    relock "$SUITE/FreeWeight" --extra dev --extra postgresql --unsafe-package freeweight
    relock "$SUITE/LoadCoach"  --extra dev --extra postgres
    relock "$SUITE/IdeaPress"  --extra dev --extra postgres --pip-args='--no-cache-dir'
    for repo in FreeWeight LoadCoach IdeaPress; do
        if git -C "$SUITE/$repo" diff --cached --quiet; then echo "$repo: nothing to commit"; continue; fi
        git -C "$SUITE/$repo" commit -q -m "chore(deps): ci.lock resolves modelrack $MR_VERSION

Rows N4–N6: the launcher memory cap lives in modelrack 0.8.0.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
        echo "$repo: committed $(git -C "$SUITE/$repo" rev-parse --short HEAD)"
    done
fi

# ---- push-apps ---------------------------------------------------------------------------------
if step_enabled push-apps; then
    say "push-apps"
    push_main "$SUITE/docs"
    push_main "$SUITE/py/ToolYard"
    push_main "$SUITE/PromptCadence"
    for repo in FreeWeight LoadCoach IdeaPress; do push_main "$SUITE/$repo"; done
    for repo in py/ToolYard FreeWeight LoadCoach IdeaPress; do wait_ci "$SUITE/$repo"; done
fi

# ---- tag-apps ----------------------------------------------------------------------------------
if step_enabled tag-apps; then
    say "tag-apps: freeweight $FW_VERSION, loadcoach $LC_VERSION${IDEAPRESS_VERSION:+, ideapress $IDEAPRESS_VERSION}"
    tag_and_push "$SUITE/FreeWeight" "v$FW_VERSION"
    tag_and_push "$SUITE/LoadCoach"  "v$LC_VERSION"
    if [[ -n "$IDEAPRESS_VERSION" ]]; then
        IP="$SUITE/IdeaPress"; current="$(version_of "$IP/src/ideapress/__about__.py")"
        if [[ "$current" != "$IDEAPRESS_VERSION" ]]; then
            clean_or_fail "$IP"
            sed -i "s/__version__ = \"$current\"/__version__ = \"$IDEAPRESS_VERSION\"/" "$IP/src/ideapress/__about__.py"
            sed -i "0,/^## \[Unreleased\]$/s//## [Unreleased]\n\n## [$IDEAPRESS_VERSION] - $(date +%F)/" "$IP/CHANGELOG.md"
            sed -i "s/\*\*Status:\*\* \`$current\`/**Status:** \`$IDEAPRESS_VERSION\`/" "$IP/README.md"
            ( cd "$IP" && .venv/bin/python -m pytest tests/unit/test_readme_version.py -q >/dev/null ) || fail "IdeaPress README version guard failed"
            git -C "$IP" add src/ideapress/__about__.py CHANGELOG.md README.md
            git -C "$IP" commit -q -m "chore(release): ideapress $IDEAPRESS_VERSION

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
            push_main "$IP"; wait_ci "$IP"
        fi
        tag_and_push "$IP" "v$IDEAPRESS_VERSION"
    fi
    wait_pypi freeweight "$FW_VERSION" "$SUITE/FreeWeight"
    wait_pypi loadcoach  "$LC_VERSION" "$SUITE/LoadCoach"
    [[ -z "$IDEAPRESS_VERSION" ]] || wait_pypi ideapress "$IDEAPRESS_VERSION" "$SUITE/IdeaPress"
fi

# ---- verify ------------------------------------------------------------------------------------
if step_enabled verify; then
    say "verify"
    for pkg in modelrack freeweight loadcoach ideapress toolyard; do
        printf '%-11s %s\n' "$pkg" "$(python3 -m pip index versions "$pkg" 2>/dev/null | head -1 || echo '?')"
    done
    echo
    echo "Left for a person: (1) run 'apply_memory_safety.sh --fire' once if --host was not used;"
    echo "(2) one live 'freeweight run start --suite native.memory_kv' on llama.cpp with"
    echo "    max_fit_context_tokens = 32768 (N5 handoff); (3) the follow-ups in N1/N5/N6 handoffs."
fi
