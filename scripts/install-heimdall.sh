#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  echo "Run this installer with sudo: sudo bash scripts/install-heimdall.sh" >&2
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

for path in "$PKG_DIR/voice.py" "$PKG_DIR/ui/faces.py" "$PKG_DIR/ui/view.py"; do
  if [[ -f "$path" ]]; then
    cp -a "$path" "$BACKUP_DIR/$(basename "$path")"
  fi
done

install -m 0644 "$REPO_ROOT/pwnagotchi/voice.py" "$PKG_DIR/voice.py"
install -m 0644 "$REPO_ROOT/pwnagotchi/ui/faces.py" "$PKG_DIR/ui/faces.py"
install -m 0644 "$REPO_ROOT/pwnagotchi/ui/view.py" "$PKG_DIR/ui/view.py"
install -m 0644 "$REPO_ROOT/custom_plugins/heimdall_heartbeat.py" "$PLUGIN_DIR/heimdall_heartbeat.py"
install -m 0644 "$REPO_ROOT/custom_plugins/heimdall_health.py" "$PLUGIN_DIR/heimdall_health.py"

if [[ ! -f "$CONFIG_FILE" ]]; then
  install -m 0600 "$REPO_ROOT/config/heimdall.example.toml" "$CONFIG_FILE"
  echo "Created $CONFIG_FILE from the Heimdall template."
else
  python3 "$REPO_ROOT/scripts/configure-heimdall.py"
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

cat <<EOF

Heimdall v0.1 Alpha installed.
Persona: Josh
Backup: $BACKUP_DIR

Defensive defaults are enabled:
  personality.deauth = false
  personality.associate = false
  personality.advertise = false
  PwnGrid reporting = disabled

Review $CONFIG_FILE, especially display settings and the optional Odin endpoint/token.
Then run:
  sudo reboot

After reboot validate with:
  sudo bash $REPO_ROOT/scripts/validate-heimdall.sh
EOF
