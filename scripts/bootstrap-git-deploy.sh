#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
  echo "Run this as your normal user, not root. It will ask for sudo once." >&2
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_USER="$(id -un)"

if [[ ! -d "$REPO_ROOT/.git" ]]; then
  echo "Run this from the Heimdall git checkout." >&2
  exit 1
fi

echo "Configuring Heimdall Git deploy for:"
echo "  repo: $REPO_ROOT"
echo "  user: $DEPLOY_USER"

sudo mkdir -p /etc/heimdall
printf 'REPO_ROOT=%q\nDEPLOY_USER=%q\n' "$REPO_ROOT" "$DEPLOY_USER" | \
  sudo tee /etc/heimdall/deploy.conf >/dev/null
sudo chown root:root /etc/heimdall/deploy.conf
sudo chmod 0644 /etc/heimdall/deploy.conf

sudo install -o root -g root -m 0755 \
  "$REPO_ROOT/ops/heimdall-deploy-root" \
  /usr/local/sbin/heimdall-deploy

sudo tee /etc/sudoers.d/heimdall-deploy >/dev/null <<EOF
$DEPLOY_USER ALL=(root) NOPASSWD: /usr/local/sbin/heimdall-deploy
EOF
sudo chmod 0440 /etc/sudoers.d/heimdall-deploy
sudo visudo -cf /etc/sudoers.d/heimdall-deploy >/dev/null

git -C "$REPO_ROOT" config core.hooksPath .githooks
chmod +x "$REPO_ROOT/.githooks/post-merge"

# Convenience command that can also be run manually without a password.
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/heimdall-deploy" <<'EOF'
#!/usr/bin/env bash
exec sudo -n /usr/local/sbin/heimdall-deploy
EOF
chmod +x "$HOME/.local/bin/heimdall-deploy"

sudo /usr/local/sbin/heimdall-deploy

cat <<EOF

Heimdall Git deploy is ready.

Normal update workflow:
  cd $REPO_ROOT
  git pull

The post-merge hook will deploy/restart Heimdall automatically without asking
for a sudo password. You can also run:
  $HOME/.local/bin/heimdall-deploy

Only the fixed root-owned /usr/local/sbin/heimdall-deploy helper is allowed
passwordless sudo; general sudo access is unchanged.
EOF
