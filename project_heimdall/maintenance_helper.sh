#!/usr/bin/env bash
set -euo pipefail

BASE="/home/nabzaf/Heimdall/project_heimdall"
REPO="/home/nabzaf/Heimdall"
BACKUPS="$BASE/backups"
ACTION="${1:-}"

run_as_node() { sudo -u nabzaf "$@"; }
make_backup() {
  mkdir -p "$BACKUPS"
  chown nabzaf:nabzaf "$BACKUPS"
  chmod 700 "$BACKUPS"
  STAMP="$(date +%Y%m%d-%H%M%S)"
  OUT="$BACKUPS/heimdall-backup-$STAMP.tar.gz"
  ITEMS=()
  [ -f "$BASE/config.json" ] && ITEMS+=("config.json")
  [ -d "$BASE/data" ] && ITEMS+=("data")
  [ -f "$BASE/maintenance_auth.json" ] && ITEMS+=("maintenance_auth.json")
  [ -f "$BASE/radio_mode.json" ] && ITEMS+=("radio_mode.json")
  [ -f "$BASE/recovery_ap.json" ] && ITEMS+=("recovery_ap.json")
  [ ${#ITEMS[@]} -gt 0 ] || { echo "Nothing to back up."; return 1; }
  cd "$BASE"
  run_as_node tar -czf "$OUT" "${ITEMS[@]}"
  chmod 600 "$OUT"; chown nabzaf:nabzaf "$OUT"
  echo "$OUT"
}

case "$ACTION" in
  doctor)
    cd "$BASE"; run_as_node "$BASE/.venv/bin/python" "$BASE/doctor.py" ;;
  restart-backend)
    systemctl restart heimdall.service
    systemctl --no-pager --full status heimdall.service | sed -n '1,10p' ;;
  restart-ui)
    systemctl restart heimdall-ui.service ;;
  repair-db)
    systemctl stop heimdall.service || true
    cd "$BASE"; run_as_node "$BASE/.venv/bin/python" "$BASE/repair_database.py"
    systemctl start heimdall.service
    systemctl is-active heimdall.service ;;
  check-update)
    run_as_node git -C "$REPO" fetch origin heimdall-dev
    LOCAL="$(run_as_node git -C "$REPO" rev-parse HEAD)"
    REMOTE="$(run_as_node git -C "$REPO" rev-parse origin/heimdall-dev)"
    echo "local=$LOCAL"; echo "remote=$REMOTE"
    if [ "$LOCAL" = "$REMOTE" ]; then echo "status=up-to-date"; else
      echo "status=update-available"
      echo "behind=$(run_as_node git -C "$REPO" rev-list --count HEAD..origin/heimdall-dev)"
      echo "ahead=$(run_as_node git -C "$REPO" rev-list --count origin/heimdall-dev..HEAD)"
    fi ;;
  apply-update)
    make_backup
    run_as_node git -C "$REPO" fetch origin heimdall-dev
    if [ -n "$(run_as_node git -C "$REPO" status --porcelain --untracked-files=no)" ]; then
      echo "Tracked local changes detected; refusing automatic update." >&2; exit 3
    fi
    run_as_node git -C "$REPO" merge --ff-only origin/heimdall-dev
    install -m 0644 "$BASE/systemd/heimdall.service" /etc/systemd/system/heimdall.service
    install -m 0644 "$BASE/systemd/heimdall-maintenance.service" /etc/systemd/system/heimdall-maintenance.service
    install -m 0644 "$BASE/systemd/heimdall-ui.service" /etc/systemd/system/heimdall-ui.service
    install -m 0644 "$BASE/systemd/heimdall-radio.service" /etc/systemd/system/heimdall-radio.service
    install -m 0644 "$BASE/systemd/heimdall-recovery.service" /etc/systemd/system/heimdall-recovery.service
    install -m 0644 "$BASE/systemd/heimdall-bluetooth.service" /etc/systemd/system/heimdall-bluetooth.service
    install -m 0755 "$BASE/maintenance_helper.sh" /usr/local/sbin/heimdall-maintenance
    install -m 0755 "$BASE/recovery_helper.sh" /usr/local/sbin/heimdall-recovery
    install -m 0755 "$BASE/radio_helper.sh" /usr/local/sbin/heimdall-radio-control
    echo 'nabzaf ALL=(root) NOPASSWD: /usr/local/sbin/heimdall-recovery *' > /etc/sudoers.d/heimdall-recovery
    echo 'nabzaf ALL=(root) NOPASSWD: /usr/local/sbin/heimdall-radio-control *' > /etc/sudoers.d/heimdall-radio
    chmod 0440 /etc/sudoers.d/heimdall-recovery /etc/sudoers.d/heimdall-radio
    systemctl enable --now bluetooth.service >/dev/null 2>&1 || true
    bluetoothctl power on >/dev/null 2>&1 || true
    bluetoothctl system-alias JOSH-OVN-002 >/dev/null 2>&1 || true
    bluetoothctl pairable on >/dev/null 2>&1 || true
    bluetoothctl discoverable on >/dev/null 2>&1 || true
    if command -v sdptool >/dev/null 2>&1; then sdptool add --channel=22 SP >/dev/null 2>&1 || true; fi
    systemctl daemon-reload
    systemctl enable heimdall-radio.service heimdall-recovery.service heimdall-bluetooth.service >/dev/null 2>&1 || true
    systemctl restart heimdall.service
    systemctl restart heimdall-maintenance.service
    systemctl restart heimdall-radio.service
    systemctl restart heimdall-recovery.service
    systemctl restart heimdall-bluetooth.service
    systemctl restart heimdall-ui.service ;;
  backup)
    make_backup ;;
  reboot)
    echo "Rebooting OVN-002..."; systemctl reboot ;;
  shutdown)
    echo "Shutting down OVN-002..."; systemctl poweroff ;;
  *)
    echo "Allowed actions: doctor restart-backend restart-ui repair-db check-update apply-update backup reboot shutdown" >&2
    exit 2 ;;
esac
