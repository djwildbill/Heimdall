#!/usr/bin/env bash
set -euo pipefail

BASE="/home/nabzaf/Heimdall/project_heimdall"
REPO="/home/nabzaf/Heimdall"
BACKUPS="$BASE/backups"
ACTION="${1:-}"

run_as_node() {
  sudo -u nabzaf "$@"
}

case "$ACTION" in
  doctor)
    cd "$BASE"
    run_as_node "$BASE/.venv/bin/python" "$BASE/doctor.py"
    ;;

  restart-backend)
    systemctl restart heimdall.service
    systemctl --no-pager --full status heimdall.service | sed -n '1,10p'
    ;;

  restart-ui)
    # UI may disconnect while this command completes; systemd will bring it back.
    systemctl restart heimdall-ui.service
    systemctl --no-pager --full status heimdall-ui.service | sed -n '1,10p'
    ;;

  repair-db)
    systemctl stop heimdall.service || true
    cd "$BASE"
    run_as_node "$BASE/.venv/bin/python" "$BASE/repair_database.py"
    systemctl start heimdall.service
    systemctl is-active heimdall.service
    ;;

  check-update)
    run_as_node git -C "$REPO" fetch origin heimdall-dev
    LOCAL="$(run_as_node git -C "$REPO" rev-parse HEAD)"
    REMOTE="$(run_as_node git -C "$REPO" rev-parse origin/heimdall-dev)"
    echo "local=$LOCAL"
    echo "remote=$REMOTE"
    if [ "$LOCAL" = "$REMOTE" ]; then
      echo "status=up-to-date"
    else
      BEHIND="$(run_as_node git -C "$REPO" rev-list --count HEAD..origin/heimdall-dev)"
      AHEAD="$(run_as_node git -C "$REPO" rev-list --count origin/heimdall-dev..HEAD)"
      echo "status=update-available"
      echo "behind=$BEHIND"
      echo "ahead=$AHEAD"
    fi
    ;;

  backup)
    mkdir -p "$BACKUPS"
    chown nabzaf:nabzaf "$BACKUPS"
    chmod 700 "$BACKUPS"
    STAMP="$(date +%Y%m%d-%H%M%S)"
    OUT="$BACKUPS/heimdall-backup-$STAMP.tar.gz"
    ITEMS=()
    [ -f "$BASE/config.json" ] && ITEMS+=("config.json")
    [ -d "$BASE/data" ] && ITEMS+=("data")
    [ -f "$BASE/maintenance.token" ] && ITEMS+=("maintenance.token")
    if [ ${#ITEMS[@]} -eq 0 ]; then
      echo "Nothing to back up."
      exit 1
    fi
    cd "$BASE"
    run_as_node tar -czf "$OUT" "${ITEMS[@]}"
    chmod 600 "$OUT"
    chown nabzaf:nabzaf "$OUT"
    echo "$OUT"
    ;;

  reboot)
    echo "Rebooting OVN-002..."
    systemctl reboot
    ;;

  shutdown)
    echo "Shutting down OVN-002..."
    systemctl poweroff
    ;;

  *)
    echo "Allowed actions: doctor restart-backend restart-ui repair-db check-update backup reboot shutdown" >&2
    exit 2
    ;;
esac
