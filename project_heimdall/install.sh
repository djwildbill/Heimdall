#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$HERE/.venv"
SERVICE_NAME="heimdall.service"

printf '\n== Project Odin: Heimdall installer ==\n'

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required."
  exit 1
fi

if command -v apt-get >/dev/null 2>&1; then
  echo "Installing OS requirements (NetworkManager, Python venv)..."
  sudo apt-get update
  sudo apt-get install -y network-manager python3-venv
fi

if [ ! -d "$VENV" ]; then
  python3 -m venv "$VENV"
fi

"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/pip" install -r "$HERE/requirements.txt"

if [ ! -f "$HERE/config.json" ]; then
  cp "$HERE/config.example.json" "$HERE/config.json"
  echo "Created config.json from example."
fi

cat > /tmp/heimdall.service <<EOF
[Unit]
Description=Project Odin Heimdall Wireless Situational Awareness Node
After=network-online.target NetworkManager.service
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HERE
ExecStart=$VENV/bin/python $HERE/heimdall.py
Restart=on-failure
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

sudo cp /tmp/heimdall.service "/etc/systemd/system/$SERVICE_NAME"
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"

echo
echo "Install complete."
echo "Edit: $HERE/config.json"
echo "Bench test: $VENV/bin/python $HERE/heimdall.py --demo"
echo "Live start: sudo systemctl restart $SERVICE_NAME"
echo "Status: sudo systemctl status $SERVICE_NAME --no-pager"
echo "Dashboard: http://<PI-IP>:8080"
