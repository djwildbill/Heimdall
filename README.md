# Heimdall

**Guardian of the Bifrost**

Heimdall is the wireless-intelligence node of the Odin ecosystem.

- **System:** Heimdall
- **Persona:** Josh
- **Default node:** `heimdall-01`
- **Role:** Wireless intelligence
- **Current release target:** `v0.1.0-alpha`

Heimdall is built from the Pwnagotchi codebase and retains its GPL-3.0 licensing and upstream attribution. Heimdall keeps the original Pwnagotchi-style active capabilities and adds Odin integration, runtime modes, telemetry, health monitoring, a custom interface, standalone web/SSH control, and future remote-control support.

## Runtime modes

Heimdall can change behavior live without rebooting:

- `pwn` — original Pwnagotchi-style active behavior for authorized environments
- `sentinel` — passive wireless observation
- `recon` — observation plus peer advertising, without client disruption
- `maintenance` — management and maintenance mode

The default mode is `pwn` so an existing Pwnagotchi user does not lose the original behavior when converting the device to Heimdall. Active wireless behavior must only be used where the operator has authorization.

## Standalone control

Heimdall does not require Odin, Bifrost, or Geri to operate.

From SSH or the local console:

```bash
sudo heimdall-mode status
sudo heimdall-mode pwn
sudo heimdall-mode sentinel
sudo heimdall-mode recon
sudo heimdall-mode maintenance
```

The authenticated local web UI exposes the mode controller at:

```text
/plugins/heimdall_mode
```

## Geri / Odin control path

When the rest of the ecosystem is available, the intended control architecture is:

```text
Geri web UI
    ↓
Odin / Bifrost authenticated control API
    ↓
Heimdall (Josh)
```

Geri should never need direct public access to Heimdall. Heimdall can poll an authenticated Odin control endpoint for its desired mode and can switch modes live. The current mode is also included in Heimdall's heartbeat back to Odin.

## Native Heimdall image

The image builder now produces:

```text
Heimdall-v0.1.0-alpha.img
Heimdall-v0.1.0-alpha.sha256
Heimdall-v0.1.0-alpha.zip
```

On a supported GNU/Linux build host:

```bash
make clean
make install
make heimdall
```

A GitHub Actions workflow is also included at `.github/workflows/build-heimdall-image.yml` to build the image bundle as an artifact.

### First boot

The image creates a dedicated console account:

```text
username: heimdall
temporary password: heimdall
```

The temporary password is expired in the image. The first successful interactive login requires a new password and then launches the Heimdall setup wizard. The wizard asks for:

- node name
- local Heimdall web password
- starting mode

It then reboots Josh with the final configuration.

## v0.1 Alpha features

- Raspberry Pi Zero W / Zero 2 W compatible upstream foundation
- e-ink interface with Heimdall/Josh personality
- original active Pwnagotchi-style operation retained
- additional Sentinel, Recon, and Maintenance modes
- local SSH/console mode command
- authenticated local web mode controls
- first-boot credential/setup wizard
- local health telemetry
- heartbeat reporting to Odin
- offline heartbeat queue when Odin is unavailable
- optional Odin/Geri-directed runtime mode control
- USB gadget management connectivity
- native image build target and checksum bundle

## Repository layout

```text
Heimdall/
├── .github/workflows/  Automated image build
├── builder/            ARM image provisioning and Heimdall finalization
├── config/             Example Heimdall configuration
├── custom_plugins/     Heimdall-specific plugins
├── docs/               Installation and release documentation
├── pwnagotchi/         Upstream engine with Heimdall UI/voice changes
├── scripts/            Installation, first-boot, control, validation helpers
├── PROJECT_ODIN.md     Odin ecosystem integration notes
├── VERSION             Heimdall release version
└── README.md
```

## Conversion install on an existing compatible base

For development or recovery, an existing compatible Pwnagotchi installation can still be converted:

```bash
git clone -b heimdall-dev https://github.com/djwildbill/Heimdall.git
cd Heimdall
sudo bash scripts/install-heimdall.sh
```

The installer backs up the current Pwnagotchi configuration and UI files before installing Heimdall components.

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

**Alpha software.** The source and image build pipeline are ready for the first hardware validation on Josh. Do not treat v0.1 as production-ready until that test passes.
