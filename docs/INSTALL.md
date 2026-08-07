# Heimdall v0.1 Alpha Installation

This guide converts a compatible working Pwnagotchi installation into Heimdall.

## Before you begin

1. Make a full image backup of the SD card.
2. Confirm the Pi, display, and wireless interface already work with the underlying engine.
3. Use the `heimdall-dev` branch for v0.1 testing.

## Install

```bash
cd ~
git clone -b heimdall-dev https://github.com/djwildbill/Heimdall.git
cd Heimdall
sudo bash scripts/install-heimdall.sh
```

The installer will:

- back up `/etc/pwnagotchi/config.toml`
- back up the current voice, face, and view files
- install Heimdall UI and Josh personality files
- install the heartbeat and health plugins
- configure passive defensive defaults
- disable PwnGrid reporting
- set the hostname to `heimdall`
- write `/etc/heimdall-release`

## Defensive defaults

Heimdall v0.1 installs with active wireless interactions disabled:

```toml
personality.deauth = false
personality.associate = false
personality.advertise = false
```

Only enable active testing functions when the operator has explicit authorization for the target environment.

## Display

The example configuration uses:

```toml
ui.display.type = "waveshare_2"
```

If Josh uses another display, preserve the known-working display settings from the existing installation.

## Odin heartbeat

The heartbeat plugin is enabled but does not transmit until an endpoint is configured.

```toml
main.plugins.heimdall-heartbeat.endpoint = "http://ODIN-IP:PORT/api/v1/heimdall/heartbeat"
main.plugins.heimdall-heartbeat.token = "YOUR_TOKEN"
```

Keep the endpoint empty while testing Heimdall independently.

## Reboot

```bash
sudo reboot
```

Expected identity after reboot:

```text
System: Heimdall
Persona: Josh
Hostname: heimdall
Mode label: SENT / WISE / CMD
```

## Validate

```bash
cd ~/Heimdall
sudo bash scripts/validate-heimdall.sh
```

## Restore

The installer prints the backup directory it created under:

```text
/var/backups/heimdall/
```

A full SD-card image backup remains the preferred rollback method during alpha testing.
