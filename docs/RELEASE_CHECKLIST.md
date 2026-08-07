# Heimdall v0.1 Alpha Release Checklist

## Identity

- [x] Repository named Heimdall
- [x] Persona defined as Josh
- [x] Default node defined as `heimdall-01`
- [x] Heimdall README and upstream attribution present
- [x] Version marker present

## UI

- [x] Heimdall/Josh face set
- [x] Heimdall voice/status messages
- [x] Screen name changed to Josh
- [x] `APS` label changed to `NET`
- [x] `PWND` label changed to `CAP`
- [x] Heimdall mode labels defined (`SENT`, `WISE`, `CMD`)
- [ ] Verify layout physically on Josh's e-ink display

## Defensive defaults

- [x] Deauthentication disabled by default
- [x] Association disabled by default
- [x] Peer advertising disabled by default
- [x] PwnGrid reporting disabled by default
- [ ] Verify effective runtime configuration on Josh

## Plugins

- [x] Odin heartbeat plugin
- [x] Offline heartbeat queue
- [x] Local health plugin
- [ ] Test heartbeat against Odin endpoint
- [ ] Test recovery after Odin disconnect/reconnect

## Installation

- [x] Existing config/UI backup
- [x] Automatic installed-package discovery
- [x] Heimdall configuration helper
- [x] Hostname conversion
- [x] `/etc/heimdall-release`
- [x] Validation script
- [ ] Run installer on Josh
- [ ] Cold-boot test
- [ ] USB gadget connectivity test

## Hardware

- [ ] Confirm Josh model (Pi Zero W vs Zero 2 W)
- [ ] Confirm display model/revision
- [ ] Confirm battery/UPS hardware if present
- [ ] Confirm temperature remains acceptable during extended run

## Release gate

`v0.1.0-alpha` can be tagged after Josh successfully boots, displays the Heimdall UI, stays stable for an extended test, and passes the validation script without hard failures.

A flashable standalone Heimdall image is a later packaging milestone; v0.1 Alpha currently installs as a reproducible overlay on a compatible working Pwnagotchi base.
