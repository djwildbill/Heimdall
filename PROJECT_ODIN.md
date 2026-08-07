# Heimdall — Project Odin Wireless Intelligence Node

## Project Identity

**Heimdall** is the wireless intelligence and observation node within **Project Odin**, a distributed defensive-security platform built around modular Raspberry Pi systems.

Heimdall is derived from the Pwnagotchi project by evilsocket and retains that project's upstream history and applicable licensing requirements. Project Odin extends the platform with its own identity, user interface, reporting model, sensor integrations, node communications, and defensive operating philosophy.

## Role

Like the mythological Heimdall watching the Bifrost, this node watches the wireless environment and reports findings to Odin.

Primary responsibilities:

- Passive Wi-Fi environment monitoring
- Authorized wireless reconnaissance
- GPS-aware logging when supported
- Bluetooth and BLE discovery
- Node health and battery telemetry
- Local evidence and event logging
- Secure reporting to the Odin command node
- Offline queueing when Odin is unavailable

## Operating Philosophy

Heimdall is designed for authorized defensive-security work, lab environments, education, network inventory, and incident-response support.

Passive observation is the default operating posture. Active wireless testing features must be used only on networks and systems the operator owns or has explicit authorization to assess.

## Initial Operating States

The Heimdall interface will evolve away from the stock Pwnagotchi personality model toward mission-oriented states:

- **Sleeping** — low-power or inactive state
- **Awakening** — startup and service initialization
- **Watching** — passive observation
- **Scanning** — active inventory of the authorized environment
- **Learning** — adapting to environmental patterns
- **Reporting** — preparing or transmitting telemetry
- **Connected** — authenticated connection to Odin is available
- **Synchronizing** — queued data is being reconciled with Odin
- **Alert** — a configured condition or meaningful environmental change was detected
- **Debugging** — maintenance or fault-diagnostic state

## Project Odin Integration

Heimdall is a sensor node. Odin is the coordinator.

```text
                 Project Odin
                      |
                +-----+-----+
                |   Odin    |
                | Command   |
                +-----+-----+
                      ^
                      |
              telemetry / status
                      |
                +-----+-----+
                | Heimdall  |
                | Wireless  |
                | Watcher   |
                +-----------+
```

Heimdall should report operational metadata such as:

- Node identifier
- Timestamp
- Current operating state
- Visible access-point count
- Bluetooth/BLE discovery count
- GPS status
- Battery level
- CPU temperature
- Uptime
- Odin connection state
- Locally queued report count

Raw capture material should remain local by default until secure transport, authentication, storage, retention, and authorization controls are in place.

## Development Strategy

Heimdall development should preserve upstream compatibility wherever practical.

Preferred approach:

1. Keep `master` as the upstream-compatible baseline.
2. Perform Project Odin development on `heimdall-dev` and feature branches.
3. Extend behavior through plugins before modifying core Pwnagotchi logic.
4. Keep Heimdall-specific code isolated and documented.
5. Preserve upstream copyright notices, licensing, and attribution.
6. Make passive and defensive behavior the default configuration.
7. Add active assessment functionality only behind explicit configuration and authorization controls.

## Initial Milestones

### v0.1 — Identity and Heartbeat

- Heimdall branding
- Heimdall hostname defaults
- Project Odin documentation
- Custom state/face definitions
- Node health collection
- Authenticated heartbeat to Odin
- Local telemetry queue

### v0.2 — Sensors

- GPS integration
- Bluetooth/BLE observation
- Battery HAT support
- Improved health telemetry

### v0.3 — Odin Integration

- Secure node registration
- Signed node identity
- Odin dashboard integration
- Alert reporting
- Configuration synchronization

## Repository Structure Goal

```text
Heimdall/
├── PROJECT_ODIN.md
├── README.md
├── config/
├── docs/
├── plugins/
├── display/
├── services/
├── scripts/
└── tests/
```

## Attribution

Heimdall is based on the Pwnagotchi project by evilsocket and contributors. Upstream project history, licensing, and copyright obligations must remain intact as Project Odin evolves the codebase.

---

**Project Odin**  
**Heimdall — Guardian of the Bifrost**
