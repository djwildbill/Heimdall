#!/usr/bin/env bash
set -euo pipefail

BASE="/home/nabzaf/Heimdall/project_heimdall"

if [ ! -x "$BASE/.venv/bin/python" ]; then
  echo "ERROR: Heimdall virtual environment not found at $BASE/.venv"
  echo "Run ./install.sh first."
  exit 1
fi

sudo install -m 0644 "$BASE/systemd/heimdall.service" /etc/systemd/system/heimdall.service
sudo install -m 0644 "$BASE/systemd/heimdall-ui.service" /etc/systemd/system/heimdall-ui.service

sudo systemctl daemon-reload
sudo systemctl enable heimdall.service heimdall-ui.service
sudo systemctl restart heimdall.service
sleep 2
sudo systemctl restart heimdall-ui.service

echo
echo "Heimdall appliance services installed."
echo "Backend: http://$(hostname -I | awk '{print $1}'):8080"
echo "UI:      http://$(hostname -I | awk '{print $1}'):8081"
echo
echo "Status:"
systemctl --no-pager --full status heimdall.service | sed -n '1,8p' || true
systemctl --no-pager --full status heimdall-ui.service | sed -n '1,8p' || true
