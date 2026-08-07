# Heimdall

**Guardian of the Bifrost**

Heimdall is the wireless-intelligence node of the Odin ecosystem.

- **System:** Heimdall
- **Persona:** Josh
- **Default node:** `heimdall-01`
- **Role:** Wireless intelligence
- **Current release target:** `v0.1.0-alpha`

Heimdall is built from the Pwnagotchi codebase and retains its GPL-3.0 licensing and upstream attribution. Heimdall changes the operational identity, interface, defaults, telemetry, and integration model so the node can operate as a defensive wireless sensor reporting to Odin.

## v0.1 Alpha goals

Heimdall v0.1 is intended to provide:

- Raspberry Pi Zero W / Zero 2 W compatible base
- e-ink interface with Heimdall/Josh personality
- passive wireless observation by default
- optional authorized testing features inherited from the upstream engine
- local health telemetry
- heartbeat reporting to Odin
- offline heartbeat queue when Odin is unavailable
- USB gadget management connectivity
- reproducible configuration and installation

## Safety and scope

Heimdall is designed for defensive monitoring, education, lab use, and explicitly authorized security testing. The default Heimdall configuration disables active deauthentication and association behavior. Active wireless testing must only be enabled where the operator has authorization.

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
sudo ./scripts/install-heimdall.sh
```

The installer backs up the current Pwnagotchi configuration and UI files before installing Heimdall components.

After installation, review:

```text
/etc/pwnagotchi/config.toml
```

Then reboot:

```bash
sudo reboot
```

## Identity

A node has both a technical identity and a persona:

```text
System:  Heimdall
Node:    heimdall-01
Persona: Josh
Role:    Wireless Intelligence
```

Odin should display the node as **Heimdall-01 (Josh)**.

## Odin communication

The heartbeat plugin can send authenticated JSON status reports to:

```text
/api/v1/heimdall/heartbeat
```

The endpoint and token are configured locally. Heimdall continues operating when Odin is offline and queues failed heartbeat reports locally.

## Upstream attribution

Heimdall is derived from [evilsocket/pwnagotchi](https://github.com/evilsocket/pwnagotchi) and includes software originally created by Simone Margaritelli (`@evilsocket`) and Pwnagotchi contributors. Upstream work remains subject to its GPL-3.0 license and copyright notices.

Heimdall-specific additions include Odin integration, Heimdall/Josh identity and voice, defensive defaults, telemetry plugins, configuration, installer, and ecosystem documentation.

## Status

**Alpha software.** Do not treat v0.1 as production-ready until it has been tested on the target Raspberry Pi hardware and display.
