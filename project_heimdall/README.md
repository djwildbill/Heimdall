# Heimdall — Wireless Situational Awareness

**Project Odin subsystem**  
**Version:** 0.1.0  
**Mission:** Observe. Correlate. Detect. Document.

Heimdall is a passive wireless situational-awareness and asset-observation node for authorized environments. It inventories locally visible Wi-Fi network metadata through the host operating system, maintains observation history, raises simple defensive alerts, records session evidence, and exposes a local dashboard/API.

Heimdall v0.1 does **not** perform packet injection, wireless disruption, credential collection, exploitation, handshake harvesting, password cracking, or automatic interaction with discovered third-party systems.

## Fast bench test

```bash
cd ~/Heimdall/project_heimdall
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp -n config.example.json config.json
python heimdall.py --demo
```

Open `http://<PI-IP>:8080` from a device on the same network.

## Live authorized observation

NetworkManager and `nmcli` are required.

```bash
python heimdall.py
```

Heimdall uses the host OS Wi-Fi inventory and records SSID, BSSID, channel, frequency, signal percentage, security label, and observation time. No monitor-mode interface is required by this v0.1 build.

## Raspberry Pi service install

```bash
cd ~/Heimdall/project_heimdall
chmod +x install.sh
./install.sh
nano config.json
sudo systemctl restart heimdall
sudo systemctl status heimdall --no-pager
```

Follow logs:

```bash
journalctl -u heimdall -f
```

## Dashboard/API

- `/` — dashboard
- `/api/status` — node heartbeat and system health
- `/api/heartbeat` — heartbeat-compatible status endpoint
- `/api/networks` — current wireless inventory
- `/api/known-networks` — historical wireless inventory
- `/api/alerts` — session alerts
- `POST /api/session/export` — force a JSON session snapshot

## Local data

Runtime data is written under `project_heimdall/data/`:

```text
data/
├── heimdall.db
├── heimdall.log
└── sessions/
    └── <session-uuid>.json
```

The SQLite database stores first seen, last seen, times seen, signal history summary, individual observations, and alerts.

## Configuration

Copy `config.example.json` to `config.json` and set the node/site values. `authorized_scope` must remain `true` for an authorized test site or Heimdall will refuse to start.

## Field test checklist

1. Start in `--demo` mode and confirm the dashboard loads.
2. Confirm `/api/status` returns `ONLINE`.
3. Stop demo mode and start live mode.
4. Confirm visible networks appear in Wireless Inventory.
5. Leave it running for several inventory cycles.
6. Confirm known-network counts persist after restart.
7. Confirm `data/sessions/` contains a JSON session snapshot.
8. Check `data/heimdall.log` or the systemd journal for errors.

## Current v0.1 boundaries

Included now: heartbeat/system telemetry, live Wi-Fi metadata inventory, demo mode, SQLite history, new-network alerts, large-signal-change alerts, JSON session evidence, local dashboard, REST endpoints, and systemd installation.

Next modules: Bluetooth observation, GPS integration, Odin/Bifrost upstream heartbeat, richer anomaly correlation, and report generation.
