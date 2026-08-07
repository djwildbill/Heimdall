#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  echo "Run this installer with sudo: sudo ./scripts/install-heimdall.sh" >&2
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="/var/backups/heimdall/$(date +%Y%m%d-%H%M%S)"
PLUGIN_DIR="/usr/local/share/pwnagotchi/custom-plugins"
CONFIG_FILE="/etc/pwnagotchi/config.toml"

mkdir -p "$BACKUP_DIR" "$PLUGIN_DIR" /var/lib/heimdall

if [[ -f "$CONFIG_FILE" ]]; then
  cp -a "$CONFIG_FILE" "$BACKUP_DIR/config.toml"
fi

PKG_DIR="$(python3 - <<'PY'
import os
import pwnagotchi
print(os.path.dirname(os.path.abspath(pwnagotchi.__file__)))
PY
)"

if [[ -z "$PKG_DIR" || ! -d "$PKG_DIR" ]]; then
  echo "Could not locate the installed pwnagotchi Python package." >&2
  exit 1
fi

echo "Installed engine found at: $PKG_DIR"

for path in "$PKG_DIR/voice.py" "$PKG_DIR/ui/faces.py"; do
  if [[ -f "$path" ]]; then
    cp -a "$path" "$BACKUP_DIR/$(basename "$path")"
  fi
done

install -m 0644 "$REPO_ROOT/pwnagotchi/voice.py" "$PKG_DIR/voice.py"
install -m 0644 "$REPO_ROOT/pwnagotchi/ui/faces.py" "$PKG_DIR/ui/faces.py"
install -m 0644 "$REPO_ROOT/custom_plugins/heimdall_heartbeat.py" "$PLUGIN_DIR/heimdall_heartbeat.py"
install -m 0644 "$REPO_ROOT/custom_plugins/heimdall_health.py" "$PLUGIN_DIR/heimdall_health.py"

if [[ ! -f "$CONFIG_FILE" ]]; then
  install -m 0600 "$REPO_ROOT/config/heimdall.example.toml" "$CONFIG_FILE"
  echo "Created $CONFIG_FILE from the Heimdall template."
else
  cat <<'EOF'

Existing config.toml was preserved.
Review config/heimdall.example.toml and merge the Heimdall settings into:
  /etc/pwnagotchi/config.toml

Important v0.1 defensive defaults:
  personality.deauth = false
  personality.associate = false
  main.plugins.grid.enabled = false
  main.plugins.grid.report = false
EOF
fi

if command -v hostnamectl >/dev/null 2>&1; then
  hostnamectl set-hostname heimdall || true
else
  echo heimdall > /etc/hostname
fi

cat > /etc/heimdall-release <<'EOF'
NAME=Heimdall
VERSION=0.1.0-alpha
PERSONA=Josh
ROLE=Wireless Intelligence
EOF

chmod 0755 "$REPO_ROOT/scripts/install-heimdall.sh"

echo
echo "Heimdall v0.1 Alpha installed."
echo "Persona: Josh"
echo "Backup: $BACKUP_DIR"
echo
echo "Before rebooting, review /etc/pwnagotchi/config.toml."
echo "Then run: sudo reboot"
