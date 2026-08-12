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
  STAGE="$(mktemp -d /tmp/heimdall-backup.XXXXXX)"
  trap 'rm -rf "$STAGE"' RETURN

  # Build a stable staging snapshot first. Archiving the live data directory
  # directly caused tar to abort whenever heimdall.db changed during a phone
  # initiated update.
  for file in config.json maintenance_auth.json radio_mode.json recovery_ap.json; do
    if [ -f "$BASE/$file" ]; then
      cp -a "$BASE/$file" "$STAGE/$file"
    fi
  done

  if [ -d "$BASE/data" ]; then
    mkdir -p "$STAGE/data"
    cp -a "$BASE/data/." "$STAGE/data/"

    # Replace the possibly-racy copied SQLite database with a consistent SQLite
    # backup made through Python's stdlib backup API. Josh can remain online.
    if [ -f "$BASE/data/heimdall.db" ]; then
      SRC_DB="$BASE/data/heimdall.db" DST_DB="$STAGE/data/heimdall.db.snapshot" \
      run_as_node "$BASE/.venv/bin/python" - <<'PY'
import os, sqlite3
src = os.environ['SRC_DB']
dst = os.environ['DST_DB']
source = sqlite3.connect(f'file:{src}?mode=ro', uri=True, timeout=10)
target = sqlite3.connect(dst)
try:
    source.backup(target)
finally:
    target.close()
    source.close()
PY
      mv -f "$STAGE/data/heimdall.db.snapshot" "$STAGE/data/heimdall.db"
    fi
  fi

  if [ -z "$(find "$STAGE" -mindepth 1 -print -quit)" ]; then
    echo "Nothing to back up."
    return 1
  fi

  run_as_node tar -C "$STAGE" -czf "$OUT" .
  chmod 600 "$OUT"
  chown nabzaf:nabzaf "$OUT"
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
    bluetoothctl system-alias HEIMDALL >/dev/null 2>&1 || true
    bluetoothctl pairable on >/dev/null 2>&1 || true
    bluetoothctl discoverable on >/dev/null 2>&1 || true
    if command -v sdptool >/dev/null 2>&1; then sdptool add --channel=22 SP >/dev/null 2>&1 || true; fi

    # Deploy repo-level Heimdall/Pwnagotchi changes too. The old phone updater
    # only refreshed project_heimdall services, so e-paper/plugin changes were
    # pulled into Git but never installed into the running Pwnagotchi runtime.
    if [ -f "$REPO/ops/heimdall-deploy-root" ] && [ -r /etc/heimdall/deploy.conf ]; then
      bash "$REPO/ops/heimdall-deploy-root"
    fi

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
