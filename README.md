# Heimdall

**Guardian of the Bifrost**

Heimdall is the wireless-intelligence node of the Odin ecosystem.

- **System:** Heimdall
- **Persona:** Josh
- **Default node:** `heimdall-01`
- **Role:** Wireless intelligence
- **Current release target:** `v0.1.0-alpha`

Heimdall is built from the Pwnagotchi codebase and retains its GPL-3.0 licensing and upstream attribution. Heimdall keeps the original Pwnagotchi-style active capabilities and adds Odin integration, runtime modes, telemetry, health monitoring, a custom interface, and remote-control support.

## Runtime modes

Heimdall can change behavior live without rebooting:

- `pwn` — original Pwnagotchi-style active behavior for authorized environments
- `sentinel` — passive wireless observation
- `recon` — observation plus peer advertising, without client disruption
- `maintenance` — management and maintenance mode

The default mode is `pwn` so an existing Pwnagotchi user does not lose the original behavior when converting the device to Heimdall. Active wireless behavior must only be used where the operator has authorization.

## Geri / Odin control path

The intended control architecture is:

```text
Geri web UI
    ↓
Odin / Bifrost authenticated control API
    ↓
Heimdall (Josh)
```

Geri should never need direct public access to Heimdall. Heimdall polls an authenticated Odin control endpoint for its desired mode and can switch modes live. The current mode is also included in Heimdall's heartbeat back to Odin.

## v0.1 Alpha goals

Heimdall v0.1 provides:

- Raspberry Pi Zero W / Zero 2 W compatible base
- e-ink interface with Heimdall/Josh personality
- original active Pwnagotchi-style operation retained
- additional Sentinel, Recon, and Maintenance modes
- local health telemetry
- heartbeat reporting to Odin
- offline heartbeat queue when Odin is unavailable
- optional Odin/Geri-directed runtime mode control
- USB gadget management connectivity
- reproducible configuration and installation

## Repository layout

```text
Heimdall/
├── config/             Example Heimdall configuration
├── custom_plugins/     Heimdall-specific plugins
├── docs/               Installation and release documentation
├── pwnagotchi/         Upstream engine with Heimdall UI/voice changes
├── scripts/            Installation and validation helpers
├── PROJECT_ODIN.md     Odin ecosystem integration notes
├── VERSION             Heimdall release version
└── README.md
```

## Quick install on an existing compatible Pwnagotchi base

```bash
git clone -b heimdall-dev https://github.com/djwildbill/Heimdall.git
cd Heimdall
sudo bash scripts/install-heimdall.sh
```

The installer backs up the current Pwnagotchi configuration and UI files before installing Heimdall components.

After installation, review `/etc/pwnagotchi/config.toml`, reboot, and validate with:

```bash
sudo bash scripts/validate-heimdall.sh
```

## Identity

```text
System:  Heimdall
Node:    heimdall-01
Persona: Josh
Role:    Wireless Intelligence
```

Odin should display the node as **Heimdall-01 (Josh)**.

## Odin communication

Heartbeat reports are designed for:

```text
/api/v1/heimdall/heartbeat
```

Mode control is designed for an authenticated endpoint that returns JSON such as:

```json
{"mode":"sentinel"}
```

The exact Odin/Bifrost endpoint will be finalized in the shared API specification.

## Upstream attribution

Heimdall is derived from [evilsocket/pwnagotchi](https://github.com/evilsocket/pwnagotchi) and includes software originally created by Simone Margaritelli (`@evilsocket`) and Pwnagotchi contributors. Upstream work remains subject to its GPL-3.0 license and copyright notices.

## Status

**Alpha software.** Do not treat v0.1 as production-ready until it has been tested on the target Raspberry Pi hardware and display.
