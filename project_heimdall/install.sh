#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
echo "== Heimdall field installer =="
sudo apt update
sudo apt install -y network-manager python3-venv
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if [ ! -f config.json ]; then cp config.example.json config.json; fi
mkdir -p data/sessions
chmod 700 data || true
chmod 600 config.json || true
echo
echo "Install complete."
echo "Demo:   source .venv/bin/activate && python heimdall.py --demo"
echo "Live:   source .venv/bin/activate && python heimdall.py"
echo "Web:    http://$(hostname -I | awk '{print $1}'):8080"
