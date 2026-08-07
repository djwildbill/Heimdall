#!/usr/bin/env bash
set -u

failures=0

ok() { printf '[OK] %s\n' "$1"; }
warn() { printf '[WARN] %s\n' "$1"; }
fail() { printf '[FAIL] %s\n' "$1"; failures=$((failures+1)); }

if [[ -f /etc/heimdall-release ]]; then
  ok "/etc/heimdall-release present"
else
  fail "/etc/heimdall-release missing"
fi

if [[ "$(hostname 2>/dev/null)" == "heimdall" ]]; then
  ok "hostname is heimdall"
else
  warn "hostname is $(hostname 2>/dev/null || echo unknown), expected heimdall"
fi

if [[ -f /etc/pwnagotchi/config.toml ]]; then
  ok "config.toml present"
  if grep -Eq '^personality\.deauth\s*=\s*false' /etc/pwnagotchi/config.toml; then
    ok "deauthentication disabled by default"
  else
    warn "personality.deauth=false not found"
  fi
  if grep -Eq '^personality\.associate\s*=\s*false' /etc/pwnagotchi/config.toml; then
    ok "association disabled by default"
  else
    warn "personality.associate=false not found"
  fi
else
  fail "/etc/pwnagotchi/config.toml missing"
fi

for plugin in heimdall_heartbeat.py heimdall_health.py; do
  if [[ -f "/usr/local/share/pwnagotchi/custom-plugins/$plugin" ]]; then
    ok "$plugin installed"
  else
    fail "$plugin missing"
  fi
done

if [[ -f /var/lib/heimdall/health.json ]]; then
  ok "health telemetry generated"
else
  warn "health telemetry not generated yet; plugin may need a restart"
fi

if systemctl is-active --quiet pwnagotchi 2>/dev/null; then
  ok "pwnagotchi engine service active"
else
  warn "pwnagotchi engine service is not active"
fi

if ip link show usb0 >/dev/null 2>&1; then
  ok "USB gadget interface usb0 present"
else
  warn "usb0 not currently present"
fi

if [[ $failures -eq 0 ]]; then
  echo
  echo "Heimdall validation completed with no hard failures."
  exit 0
else
  echo
  echo "Heimdall validation found $failures hard failure(s)."
  exit 1
fi
