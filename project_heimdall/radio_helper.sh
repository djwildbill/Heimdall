#!/usr/bin/env bash
set -euo pipefail
BASE="/home/nabzaf/Heimdall/project_heimdall"
PY="$BASE/.venv/bin/python"
ACTION="${1:-}"
case "$ACTION" in
  status) exec "$PY" "$BASE/radio_mode_manager.py" --status ;;
  connected|survey|field) exec "$PY" "$BASE/radio_mode_manager.py" "$ACTION" ;;
  *) echo "Allowed: status connected survey field" >&2; exit 2 ;;
esac
