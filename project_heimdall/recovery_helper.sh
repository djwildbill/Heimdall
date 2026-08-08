#!/usr/bin/env bash
set -euo pipefail
BASE="/home/nabzaf/Heimdall/project_heimdall"
PY="$BASE/.venv/bin/python"
ACTION="${1:-}"
case "$ACTION" in
  prepare) exec "$PY" "$BASE/recovery_ap_manager.py" prepare ;;
  start) exec "$PY" "$BASE/recovery_ap_manager.py" start ;;
  stop) exec "$PY" "$BASE/recovery_ap_manager.py" stop ;;
  status) exec "$PY" "$BASE/recovery_ap_manager.py" status ;;
  show-key) exec "$PY" "$BASE/recovery_ap_manager.py" status --show-key ;;
  connect-saved)
    [ $# -eq 2 ] || { echo "profile required" >&2; exit 2; }
    exec "$PY" "$BASE/recovery_ap_manager.py" connect-saved "$2" ;;
  connect-new)
    [ $# -eq 2 ] || { echo "SSID required" >&2; exit 2; }
    exec "$PY" "$BASE/recovery_ap_manager.py" connect-new "$2" --password-stdin ;;
  *) echo "Allowed: prepare start stop status show-key connect-saved connect-new" >&2; exit 2 ;;
esac
