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
  SNAP="$(mktemp -d /tmp/heimdall-backup.XXXXXX)"
  trap 'rm -rf "$SNAP"' RETURN

  # Snapshot node-local state before tar so live files cannot change underneath
  # the archiver. SQLite gets its own consistent online backup.
  [ -f "$BASE/config.json" ] && cp -a "$BASE/config.json" "$SNAP/config.json"
  [ -f "$BASE/maintenance_auth.json" ] && cp -a "$BASE/maintenance_auth.json" "$SNAP/maintenance_auth.json"
  [ -f "$BASE/radio_mode.json" ] && cp -a "$BASE/radio_mode.json" "$SNAP/radio_mode.json"
  [ -f "$BASE/recovery_ap.json" ] && cp -a "$BASE/recovery_ap.json" "$SNAP/recovery_ap.json"

  if [ -d "$BASE/data" ]; then
    mkdir -p "$SNAP/data"
    if [ -f "$BASE/data/heimdall.db" ]; then
      run_as_node "$BASE/.venv/bin/python" - "$BASE/data/heimdall.db" "$SNAP/data/heimdall.db" <<'PY'
import sqlite3, sys
src, dst = sys.argv[1], sys.argv[2]
with sqlite3.connect(src) as s, sqlite3.connect(dst) as d:
    s.backup(d)
PY
    fi
    while IFS= read -r -d '' f; do
      rel="${f#$BASE/data/}"
      [ "$rel" = "heimdall.db" ] && continue
      mkdir -p "$SNAP/data/$(dirname "$rel")"
      cp -a "$f" "$SNAP/data/$rel" 2>/dev/null || true
    done < <(find "$BASE/data" -type f -print0)
  fi

  if [ -z "$(find "$SNAP" -mindepth 1 -print -quit)" ]; then
    echo "Nothing to back up."
    return 1
  fi

  tar -C "$SNAP" -czf "$OUT" .
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
    # Restart both the web control UI and the native Pwnagotchi display runtime.
    # This is the phone/Bluetooth-safe way to force Josh's e-paper plugin to reload.
    systemctl restart heimdall-ui.service
    if systemctl list-unit-files pwnagotchi.service >/dev/null 2>&1; then
      systemctl restart pwnagotchi.service || true
    fi
    echo "ui=restarted"
    echo "pwnagotchi=$(systemctl is-active pwnagotchi.service 2>/dev/null || echo unavailable)" ;;
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

    # Deploy repo-level Heimdall/Pwnagotchi presentation assets and plugins.
    if [ -x "$REPO/ops/heimdall-deploy-root" ]; then
      "$REPO/ops/heimdall-deploy-root"
    fi

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
