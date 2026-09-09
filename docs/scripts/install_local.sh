#!/usr/bin/env bash
# Install every suite component from this workspace, editable, into one venv (.venv-suite).
# Local __about__ versions win over PyPI: all fourteen are passed to one pip call, so pip resolves
# the apps' suite-package ranges against the local checkouts, never the index.
#
#   ./install_local.sh            # runtime only
#   ./install_local.sh --dev      # plus each component's [dev] extras (pytest, ruff, mypy …)
#   PYTHON=python3.13 ./install_local.sh
set -euo pipefail
cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"
VENV=".venv-suite"
EXTRA=""; [[ "${1:-}" == "--dev" ]] && EXTRA="[dev]"

# Dependency order (layer 1 → apps); pip does not need it, but the printout does.
COMPONENTS=(
  py/BaseAiCore py/SetSpec
  py/ModelRack py/SweatMeter py/WeightsDB py/MirrorWall py/LoadLedger py/CutCtx py/ToolYard py/Commissioner
  FreeWeight LoadCoach IdeaPress PromptCadence
)

[[ -x "$VENV/bin/python" ]] || "$PYTHON" -m venv "$VENV"
"$VENV/bin/python" -m pip install --quiet --upgrade pip

args=()
for c in "${COMPONENTS[@]}"; do args+=(-e "./$c$EXTRA"); done
"$VENV/bin/python" -m pip install --quiet "${args[@]}"

echo "installed into $VENV ($("$VENV/bin/python" --version)):"
for c in "${COMPONENTS[@]}"; do
  name=$(basename "$c" | tr '[:upper:]' '[:lower:]')
  printf '  %-14s %s\n' "$name" "$("$VENV/bin/python" -c "import importlib.metadata as m; print(m.version('$name'))")"
done
echo
echo "activate:  source $VENV/bin/activate"
echo "servers:   ./launch.sh start"
