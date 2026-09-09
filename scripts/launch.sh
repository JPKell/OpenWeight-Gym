#!/usr/bin/env bash
# Start, stop and inspect the four application servers from .venv-suite (see install_local.sh).
# Pids and logs live in .run/. Each app binds loopback on its documented port.
#
#   ./launch.sh start [app …]     # default: all four, in dependency order
#   ./launch.sh stop  [app …]
#   ./launch.sh status
#   ./launch.sh logs <app>        # tail -f
#   SUITE_XDG=/tmp/suite ./launch.sh start   # isolated config/data roots
set -euo pipefail
cd "$(dirname "$0")"
VENV=".venv-suite"; RUN=".run"; mkdir -p "$RUN"
# SUITE_XDG=<dir> keeps every app's config/data/state under one directory instead of ~/.config,
# ~/.local/share and ~/.local/state — a scratch suite that never touches your real databases.
if [[ -n "${SUITE_XDG:-}" ]]; then
  export XDG_CONFIG_HOME="$SUITE_XDG/config" XDG_DATA_HOME="$SUITE_XDG/data" XDG_STATE_HOME="$SUITE_XDG/state"
  mkdir -p "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$XDG_STATE_HOME"
fi
[[ -x "$VENV/bin/freeweight" ]] || { echo "run ./install_local.sh first" >&2; exit 1; }

APPS=(freeweight loadcoach ideapress promptcadence)
declare -A PORT=([freeweight]=8765 [loadcoach]=8766 [ideapress]=8767 [promptcadence]=8768)

alive() { [[ -f "$RUN/$1.pid" ]] && kill -0 "$(cat "$RUN/$1.pid")" 2>/dev/null; }
port_owner() { ss -ltnpH "sport = :$1" 2>/dev/null | sed -n 's/.*pid=\([0-9]*\).*/\1/p' | head -1; }

start() {
  local app=$1
  if alive "$app"; then echo "$app already running (pid $(cat "$RUN/$app.pid"))"; return; fi
  local owner; owner=$(port_owner "${PORT[$app]}")
  if [[ -n "$owner" ]]; then
    echo "$app: port ${PORT[$app]} is held by pid $owner ($(ps -o args= -p "$owner" | cut -c1-80)) — not started" >&2
    return 1
  fi
  nohup "$VENV/bin/$app" serve >"$RUN/$app.log" 2>&1 &
  echo $! >"$RUN/$app.pid"
  for _ in $(seq 1 60); do
    if curl -fs -o /dev/null "http://127.0.0.1:${PORT[$app]}/"; then
      echo "$app up on http://127.0.0.1:${PORT[$app]} (pid $!)"; return
    fi
    alive "$app" || { echo "$app exited — see $RUN/$app.log" >&2; tail -20 "$RUN/$app.log" >&2; return 1; }
    sleep 0.5
  done
  echo "$app started (pid $!) but port ${PORT[$app]} not answering yet — see $RUN/$app.log"
}

stop() {
  local app=$1
  alive "$app" || { echo "$app not running"; rm -f "$RUN/$app.pid"; return; }
  kill "$(cat "$RUN/$app.pid")"                       # SIGTERM: apps close providers/servers cleanly
  for _ in $(seq 1 40); do alive "$app" || break; sleep 0.5; done
  alive "$app" && kill -9 "$(cat "$RUN/$app.pid")" && echo "$app killed"
  rm -f "$RUN/$app.pid"; echo "$app stopped"
}

status() {
  for app in "${APPS[@]}"; do
    if alive "$app"; then
      code=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${PORT[$app]}/" || true)
      printf '%-14s running  pid %-7s port %s  http %s\n' "$app" "$(cat "$RUN/$app.pid")" "${PORT[$app]}" "$code"
    else
      local owner; owner=$(port_owner "${PORT[$app]}")
      if [[ -n "$owner" ]]; then
        printf '%-14s stopped  port %s  HELD by pid %s (%s)\n' "$app" "${PORT[$app]}" "$owner" "$(ps -o args= -p "$owner" | cut -c1-60)"
      else
        printf '%-14s stopped  port %s\n' "$app" "${PORT[$app]}"
      fi
    fi
  done
}

cmd=${1:-status}; shift || true
targets=("${@:-${APPS[@]}}")
case "$cmd" in
  start)  rc=0; for a in "${targets[@]}"; do start "$a" || rc=1; done; exit $rc ;;
  stop)   for ((i=${#targets[@]}-1; i>=0; i--)); do stop "${targets[$i]}"; done ;;   # reverse order
  restart) "$0" stop "${targets[@]}"; "$0" start "${targets[@]}" ;;
  status) status ;;
  logs)   tail -f "$RUN/${1:?app}.log" ;;
  *) echo "usage: $0 start|stop|restart|status|logs [app …]  (apps: ${APPS[*]})" >&2; exit 2 ;;
esac
