#!/usr/bin/env bash
set -euo pipefail

BASE="/home/nabzaf/Heimdall/project_heimdall"
NODE_USER="nabzaf"
NODE_GROUP="nabzaf"

if [ ! -x "$BASE/.venv/bin/python" ]; then
  echo "ERROR: Heimdall virtual environment not found at $BASE/.venv"
  echo "Run ./install.sh first."
  exit 1
fi

required=(
  "$BASE/ui_control_v2.py"
  "$BASE/ui_control_v2_launcher.py"
  "$BASE/maintenance_auth_v2.py"
  "$BASE/radio_mode_manager.py"
  "$BASE/maintenance_helper.sh"
  "$BASE/setup_maintenance_password.py"
  "$BASE/systemd/heimdall.service"
  "$BASE/systemd/heimdall-maintenance.service"
  "$BASE/systemd/heimdall-ui.service"
  "$BASE/systemd/heimdall-radio.service"
)
for f in "${required[@]}"; do
  [ -f "$f" ] || { echo "ERROR: required file missing: $f"; exit 2; }
done

"$BASE/.venv/bin/python" -m py_compile \
  "$BASE/ui_control_v2_launcher.py" \
  "$BASE/maintenance_auth_v2.py" \
  "$BASE/radio_mode_manager.py" \
  "$BASE/setup_maintenance_password.py"

install -m 0644 "$BASE/systemd/heimdall.service" /etc/systemd/system/heimdall.service
install -m 0644 "$BASE/systemd/heimdall-maintenance.service" /etc/systemd/system/heimdall-maintenance.service
install -m 0644 "$BASE/systemd/heimdall-ui.service" /etc/systemd/system/heimdall-ui.service
install -m 0644 "$BASE/systemd/heimdall-radio.service" /etc/systemd/system/heimdall-radio.service
install -m 0755 "$BASE/maintenance_helper.sh" /usr/local/sbin/heimdall-maintenance

echo 'nabzaf ALL=(root) NOPASSWD: /usr/local/sbin/heimdall-maintenance *' > /etc/sudoers.d/heimdall-maintenance
chmod 0440 /etc/sudoers.d/heimdall-maintenance
visudo -cf /etc/sudoers.d/heimdall-maintenance

if [ ! -f "$BASE/maintenance_auth.json" ]; then
  echo
  echo "Create the local Heimdall maintenance password."
  echo "This password/hash stays on Josh and is not committed to Git."
  sudo -u "$NODE_USER" "$BASE/.venv/bin/python" "$BASE/setup_maintenance_password.py"
fi
chown "$NODE_USER:$NODE_GROUP" "$BASE/maintenance_auth.json"
chmod 600 "$BASE/maintenance_auth.json"

systemctl daemon-reload
systemctl enable heimdall.service heimdall-maintenance.service heimdall-ui.service heimdall-radio.service
systemctl restart heimdall.service
sleep 2
systemctl restart heimdall-maintenance.service
sleep 1
systemctl restart heimdall-ui.service
systemctl restart heimdall-radio.service

echo
echo "Heimdall appliance services installed."
echo "Backend:     http://$(hostname -I | awk '{print $1}'):8080"
echo "Control UI:  http://$(hostname -I | awk '{print $1}'):8081"
echo "Maintenance: localhost only on 127.0.0.1:8090"
echo
echo "Status:"
for svc in heimdall.service heimdall-maintenance.service heimdall-ui.service heimdall-radio.service; do
  printf '%-30s %s\n' "$svc" "$(systemctl is-active "$svc" 2>/dev/null || true)"
done
