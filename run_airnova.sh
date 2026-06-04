#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_DIR="$ROOT_DIR/.airnova-runtime"
BACKEND_PID_FILE="$RUNTIME_DIR/backend.pid"
FRONTEND_PID_FILE="$RUNTIME_DIR/frontend.pid"
BACKEND_LOG="$RUNTIME_DIR/backend.log"
FRONTEND_LOG="$RUNTIME_DIR/frontend.log"
ACTIVE_BACKEND_PORT_FILE="$RUNTIME_DIR/backend.port"
ACTIVE_FRONTEND_PORT_FILE="$RUNTIME_DIR/frontend.port"
BACKEND_PORT="${BACKEND_PORT:-5000}"
FRONTEND_PORT="${FRONTEND_PORT:-8080}"

mkdir -p "$RUNTIME_DIR"

is_running() {
  local pid="$1"
  kill -0 "$pid" 2>/dev/null
}

port_open() {
  local port="$1"
  lsof -iTCP:"$port" -sTCP:LISTEN -t >/dev/null 2>&1
}

backend_healthy() {
  local port="$1"
  python3 - "$port" <<'PY'
import json, sys, urllib.request
port = int(sys.argv[1])
url = f"http://127.0.0.1:{port}/health"
try:
    with urllib.request.urlopen(url, timeout=1.5) as resp:
        if resp.status != 200:
            raise RuntimeError("bad status")
        data = json.loads(resp.read().decode("utf-8"))
        ok = data.get("status") == "ok"
        print("ok" if ok else "bad")
except Exception:
    print("bad")
PY
}

pid_from_file() {
  local file="$1"
  [[ -f "$file" ]] || return 1
  local pid
  pid="$(<"$file")"
  [[ -n "$pid" ]] || return 1
  if is_running "$pid"; then
    echo "$pid"
    return 0
  fi
  rm -f "$file"
  return 1
}

start_backend() {
  if pid_from_file "$BACKEND_PID_FILE" >/dev/null; then
    echo "Backend already running (pid $(<"$BACKEND_PID_FILE"))."
    return
  fi

  local selected_port="$BACKEND_PORT"
  if port_open "$selected_port"; then
    if [[ "$(backend_healthy "$selected_port")" == "ok" ]]; then
      echo "$selected_port" >"$ACTIVE_BACKEND_PORT_FILE"
      echo "AIRNOVA backend already available on :$selected_port."
      return
    fi
    echo "Port $selected_port is occupied by another service. Trying :5001 for AIRNOVA backend."
    selected_port=5001
    if port_open "$selected_port" && [[ "$(backend_healthy "$selected_port")" == "ok" ]]; then
      echo "$selected_port" >"$ACTIVE_BACKEND_PORT_FILE"
      echo "AIRNOVA backend already available on :$selected_port."
      return
    fi
    if port_open "$selected_port"; then
      echo "Port :5001 is also in use by another service. Set BACKEND_PORT manually."
      return
    fi
  fi

  : >"$BACKEND_LOG"
  (
    cd "$ROOT_DIR"
    PORT="$selected_port" python3 backend/app.py
  ) >>"$BACKEND_LOG" 2>&1 &
  echo $! >"$BACKEND_PID_FILE"
  echo "$selected_port" >"$ACTIVE_BACKEND_PORT_FILE"
  echo "Started backend on http://127.0.0.1:$selected_port (pid $!)."
}

start_frontend() {
  if pid_from_file "$FRONTEND_PID_FILE" >/dev/null; then
    echo "Frontend already running (pid $(<"$FRONTEND_PID_FILE"))."
    return
  fi

  local selected_port="$FRONTEND_PORT"
  if port_open "$selected_port"; then
    echo "Frontend port $selected_port already in use. Trying :8081 for AIRNOVA frontend."
    selected_port=8081
    if port_open "$selected_port"; then
      echo "Frontend port :8081 is also in use. Set FRONTEND_PORT manually."
      return
    fi
  fi

  : >"$FRONTEND_LOG"
  (
    cd "$ROOT_DIR/frontend"
    python3 -m http.server "$selected_port"
  ) >>"$FRONTEND_LOG" 2>&1 &
  echo $! >"$FRONTEND_PID_FILE"
  echo "$selected_port" >"$ACTIVE_FRONTEND_PORT_FILE"
  echo "Started frontend on http://127.0.0.1:$selected_port (pid $!)."
}

show_status() {
  local active_backend_port="${BACKEND_PORT}"
  local active_frontend_port="${FRONTEND_PORT}"
  if [[ -f "$ACTIVE_BACKEND_PORT_FILE" ]]; then
    active_backend_port="$(<"$ACTIVE_BACKEND_PORT_FILE")"
  fi
  if [[ -f "$ACTIVE_FRONTEND_PORT_FILE" ]]; then
    active_frontend_port="$(<"$ACTIVE_FRONTEND_PORT_FILE")"
  fi

  if pid_from_file "$BACKEND_PID_FILE" >/dev/null; then
    echo "Backend: running (pid $(<"$BACKEND_PID_FILE")) on :$active_backend_port"
  elif port_open "$active_backend_port"; then
    if [[ "$(backend_healthy "$active_backend_port")" == "ok" ]]; then
      echo "Backend: AIRNOVA available on :$active_backend_port (external process)"
    else
      echo "Backend: port :$active_backend_port is in use (non-AIRNOVA service)"
    fi
  else
    echo "Backend: stopped"
  fi

  if pid_from_file "$FRONTEND_PID_FILE" >/dev/null; then
    echo "Frontend: running (pid $(<"$FRONTEND_PID_FILE")) on :$active_frontend_port"
  elif port_open "$active_frontend_port"; then
    echo "Frontend: port :$active_frontend_port is in use (external process)"
  else
    echo "Frontend: stopped"
  fi

  echo "Open: http://127.0.0.1:$active_frontend_port/index.html"
}

stop_one() {
  local name="$1"
  local file="$2"
  if pid_from_file "$file" >/dev/null; then
    local pid
    pid="$(<"$file")"
    kill "$pid" 2>/dev/null || true
    rm -f "$file"
    if [[ "$name" == "Backend" ]]; then
      rm -f "$ACTIVE_BACKEND_PORT_FILE"
    elif [[ "$name" == "Frontend" ]]; then
      rm -f "$ACTIVE_FRONTEND_PORT_FILE"
    fi
    echo "$name stopped (pid $pid)."
  else
    echo "$name not managed by launcher (or already stopped)."
  fi
}

start_all() {
  start_backend
  start_frontend
  echo
  show_status
  echo
  echo "Logs:"
  echo "  Backend : $BACKEND_LOG"
  echo "  Frontend: $FRONTEND_LOG"
}

usage() {
  cat <<EOF
AIRNOVA launcher

Usage:
  ./run_airnova.sh start     Start backend + frontend
  ./run_airnova.sh stop      Stop only launcher-managed processes
  ./run_airnova.sh status    Show current status

Optional env vars:
  BACKEND_PORT (default: 5000)
  FRONTEND_PORT (default: 8080)
EOF
}

cmd="${1:-start}"
case "$cmd" in
  start)
    start_all
    ;;
  stop)
    stop_one "Backend" "$BACKEND_PID_FILE"
    stop_one "Frontend" "$FRONTEND_PID_FILE"
    ;;
  status)
    show_status
    ;;
  *)
    usage
    exit 1
    ;;
esac
