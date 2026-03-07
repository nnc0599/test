#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$ROOT_DIR/.tmp/codespaces-gui"
LOG_DIR="$STATE_DIR/logs"
DISPLAY_NUM="${DISPLAY_NUM:-:1}"
VNC_PORT="${VNC_PORT:-5901}"
WEB_PORT="${WEB_PORT:-6080}"
SCREEN_SIZE="${SCREEN_SIZE:-1440x900x24}"
PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
APP_ENTRY="$ROOT_DIR/run.py"
NO_VNC_PROXY="/usr/share/novnc/utils/novnc_proxy"

mkdir -p "$LOG_DIR"

if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$(command -v python3)"
fi

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing command: $1"
    exit 1
  fi
}

write_pid() {
  local name="$1"
  local pid="$2"
  echo "$pid" > "$STATE_DIR/$name.pid"
}

read_pid() {
  local name="$1"
  local file="$STATE_DIR/$name.pid"
  if [[ -f "$file" ]]; then
    cat "$file"
  fi
}

is_running() {
  local pid="$1"
  [[ -n "$pid" ]] && kill -0 "$pid" >/dev/null 2>&1
}

stop_if_running() {
  local name="$1"
  local pid
  pid="$(read_pid "$name")"

  if is_running "$pid"; then
    kill "$pid" >/dev/null 2>&1 || true
    sleep 1
  fi

  pid="$(read_pid "$name")"
  if is_running "$pid"; then
    kill -9 "$pid" >/dev/null 2>&1 || true
  fi

  rm -f "$STATE_DIR/$name.pid"
}

codespaces_url() {
  if [[ -n "${CODESPACE_NAME:-}" && -n "${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-}" ]]; then
    printf 'https://%s-%s.%s/vnc.html?autoconnect=1&resize=scale\n' \
      "$CODESPACE_NAME" "$WEB_PORT" "$GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN"
  else
    printf 'http://127.0.0.1:%s/vnc.html?autoconnect=1&resize=scale\n' "$WEB_PORT"
  fi
}

status() {
  local xvfb_pid x11vnc_pid novnc_pid app_pid
  xvfb_pid="$(read_pid xvfb)"
  x11vnc_pid="$(read_pid x11vnc)"
  novnc_pid="$(read_pid novnc)"
  app_pid="$(read_pid app)"

  printf 'DISPLAY=%s\n' "$DISPLAY_NUM"
  printf 'VNC=%s WEB=%s\n' "$VNC_PORT" "$WEB_PORT"
  printf 'xvfb=%s\n' "$(is_running "$xvfb_pid" && echo running || echo stopped)"
  printf 'x11vnc=%s\n' "$(is_running "$x11vnc_pid" && echo running || echo stopped)"
  printf 'novnc=%s\n' "$(is_running "$novnc_pid" && echo running || echo stopped)"
  printf 'app=%s\n' "$(is_running "$app_pid" && echo running || echo stopped)"
  printf 'url=%s' "$(codespaces_url)"
}

start() {
  require_cmd Xvfb
  require_cmd x11vnc
  require_cmd "$PYTHON_BIN"

  if [[ ! -x "$NO_VNC_PROXY" ]]; then
    echo "Missing noVNC proxy at $NO_VNC_PROXY"
    exit 1
  fi

  stop >/dev/null 2>&1 || true

  nohup Xvfb "$DISPLAY_NUM" -screen 0 "$SCREEN_SIZE" > "$LOG_DIR/xvfb.log" 2>&1 &
  write_pid xvfb "$!"
  sleep 1

  nohup x11vnc -display "$DISPLAY_NUM" -forever -shared -nopw -rfbport "$VNC_PORT" > "$LOG_DIR/x11vnc.log" 2>&1 &
  write_pid x11vnc "$!"
  sleep 1

  nohup "$NO_VNC_PROXY" --listen "$WEB_PORT" --vnc "127.0.0.1:$VNC_PORT" > "$LOG_DIR/novnc.log" 2>&1 &
  write_pid novnc "$!"
  sleep 1

  nohup env DISPLAY="$DISPLAY_NUM" QT_X11_NO_MITSHM=1 "$PYTHON_BIN" "$APP_ENTRY" > "$LOG_DIR/app.log" 2>&1 &
  write_pid app "$!"
  sleep 2

  status
}

stop() {
  stop_if_running app
  stop_if_running novnc
  stop_if_running x11vnc
  stop_if_running xvfb
}

case "${1:-start}" in
  start)
    start
    ;;
  stop)
    stop
    ;;
  restart)
    stop
    start
    ;;
  status)
    status
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status}"
    exit 1
    ;;
esac