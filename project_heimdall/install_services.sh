#!/usr/bin/env bash
set -euo pipefail

BASE="/home/nabzaf/Heimdall/project_heimdall"

if [ ! -x "$BASE/.venv/bin/python" ]; then
  echo "ERROR: Heimdall virtual environment not found at $BASE/.venv"
  echo "Run ./install.sh first."
  exit 1
fi

# Validate the polished UI source through its compatibility launcher before
# replacing the running service definition.
"$BASE/.venv/bin/python" -m py_compile "$BASE/ui_control_v2_launcher.py" "$BASE/maintenance_auth_v2.py"

sudo install -m 0644 "$BASE/systemd/heimdall.service" /etc/systemd/system/heimdall.service
sudo install -m 0644 "$BASE/systemd/heimdall-maintenance.service" /etc/systemd/system/heimdall-maintenance.service
sudo install -m 0644 "$BASE/systemd/heimdall-ui.service" /etc/systemd/system/heimdall-ui.service

sudo install -m 0755 "$BASE/maintenance_helper.sh" /usr/local/sbin/heimdall-maintenance

# The maintenance web service runs as nabzaf but can only invoke this single
# root-owned allowlisted helper. The helper itself rejects unknown actions.
echo 'nabzaf ALL=(root) NOPASSWD: /usr/local/sbin/heimdall-maintenance *' | sudo tee /etc/sudoers.d/heimdall-maintenance >/dev/null
sudo chmod 0440 /etc/sudoers.d/heimdall-maintenance
sudo visudo -cf /etc/sudoers.d/heimdall-maintenance

if [ ! -f "$BASE/maintenance_auth.json" ]; then
  echo
  echo "Create the local Heimdall maintenance password."
  echo "This password/hash stays on Josh and is not committed to Git."
  "$BASE/.venv/bin/python" "$BASE/setup_maintenance_password.py"
fi
chmod 600 "$BASE/maintenance_auth.json" || true

sudo systemctl daemon-reload
sudo systemctl enable heimdall.service heimdall-maintenance.service heimdall-ui.service
sudo systemctl restart heimdall.service
sleep 2
sudo systemctl restart heimdall-maintenance.service
sleep 1
sudo systemctl restart heimdall-ui.service

echo
echo "Heimdall appliance services installed."
echo "Backend:     http://$(hostname -I | awk '{print $1}'):8080"
echo "Control UI:  http://$(hostname -I | awk '{print $1}'):8081"
echo "Maintenance: localhost only on 127.0.0.1:8090"
echo
echo "Status:"
for svc in heimdall.service heimdall-maintenance.service heimdall-ui.service; do
  printf '%-30s %s\n' "$svc" "$(systemctl is-active "$svc" 2>/dev/null || true)"
done
