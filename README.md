# Heimdall

**Project Odin — Wireless Situational Awareness & Asset Observation**

> **Mission:** Observe. Correlate. Detect. Document.

Heimdall is Project Odin's wireless situational-awareness node. It is designed for authorized defensive environments where an operator needs to inventory locally visible wireless assets, maintain observation history, identify unusual changes, preserve session telemetry, and report node health to the wider Odin ecosystem.

## Current Project Odin build

The active rebuild lives in [`project_heimdall/`](project_heimdall/).

Heimdall v0.1 includes:

- node heartbeat and system telemetry
- local Wi-Fi metadata inventory
- persistent SQLite asset history
- first-seen network alerts
- large signal-change alerts
- JSON session evidence exports
- browser dashboard
- REST status/inventory endpoints
- Raspberry Pi systemd installer
- safe synthetic `--demo` mode for bench testing

### Defensive operating boundary

The Project Odin Heimdall build is intended for authorized observation and defensive analysis. The v0.1 application does **not** perform packet injection, wireless disruption, credential collection, exploitation, handshake harvesting, password cracking, or automatic interaction with discovered third-party systems.

The application uses normal host operating-system network inventory interfaces and records wireless metadata such as SSID, BSSID, channel, frequency, signal level, security label, and observation time.

## Start here

```bash
cd project_heimdall
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp -n config.example.json config.json
python heimdall.py --demo
```

Then open:

```text
http://<PI-IP>:8080
```

For the Raspberry Pi service installation and live authorized-observation procedure, see [`project_heimdall/README.md`](project_heimdall/README.md).

## Architecture role

```text
Project Odin
    |
    +-- Heimdall
         +-- Wireless Inventory
         +-- Observation History
         +-- Defensive Alerts
         +-- Session Evidence
         +-- Node Heartbeat
         +-- Dashboard / API
         +-- Future: Bluetooth
         +-- Future: GPS
         +-- Future: Bifrost -> Odin reporting
```

## Legacy code notice

This repository contains historical code inherited from the Pwnagotchi project. That legacy material predates the Project Odin Heimdall rebuild and is not the operating definition of the current Heimdall node. Project Odin's active implementation is the `project_heimdall/` application described above.

Historical upstream material remains subject to its original GPLv3 licensing and attribution requirements. Project Odin will progressively isolate, replace, or adapt only the components appropriate for Heimdall's defensive mission while preserving required attribution and license notices.

## Project principle

**Knowledge is Defense.**

Observations should be documented as observations, analytical assessments should be identified as assessments, and conclusions should be limited to what the available evidence supports.
