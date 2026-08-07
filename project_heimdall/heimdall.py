#!/usr/bin/env python3
"""Project Odin - Heimdall
Passive wireless situational-awareness and asset observation node.

Heimdall observes locally visible Wi-Fi network metadata through the host OS,
maintains local history, raises simple defensive alerts, records sessions, and
serves a local dashboard/API. It does not perform packet injection, disruption,
credential collection, exploitation, or automatic interaction with discovered
systems.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import signal
import sqlite3
import subprocess
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psutil
from flask import Flask, jsonify, render_template_string

VERSION = "0.1.0"
APP_NAME = "Heimdall"
MISSION = "Observe. Correlate. Detect. Document."
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SESSION_DIR = DATA_DIR / "sessions"
DB_PATH = DATA_DIR / "heimdall.db"
LOG_PATH = DATA_DIR / "heimdall.log"
CONFIG_PATH = BASE_DIR / "config.json"

DEFAULT_CONFIG = {
    "node_name": "Heimdall-001",
    "site_name": "Authorized Test Site",
    "authorized_scope": True,
    "scan_interval_seconds": 30,
    "dashboard_host": "0.0.0.0",
    "dashboard_port": 8080,
    "new_network_alerts": True,
    "signal_change_alert_db": 25,
    "session_export_interval_seconds": 60,
}

app = Flask(__name__)
lock = threading.RLock()
stop_event = threading.Event()
started_monotonic = time.monotonic()
started_at = datetime.now(timezone.utc)
current_session_id = str(uuid.uuid4())

runtime: dict[str, Any] = {
    "last_inventory_at": None,
    "last_inventory_error": None,
    "last_session_export_at": None,
    "inventory_count": 0,
    "known_count": 0,
    "alert_count": 0,
    "networks": [],
    "alerts": [],
    "mode": "live",
}


@dataclass
class NetworkObservation:
    ssid: str
    bssid: str
    channel: str
    frequency_mhz: str
    signal_percent: int
    security: str
    observed_at: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SESSION_DIR.mkdir(parents=True, exist_ok=True)


def log(message: str, level: str = "INFO") -> None:
    ensure_dirs()
    line = f"[{utc_now()}] {level:<5} {message}"
    print(line, flush=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
        return dict(DEFAULT_CONFIG)
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        log(f"Config unreadable; using defaults: {exc}", "WARN")
        return dict(DEFAULT_CONFIG)
    merged = dict(DEFAULT_CONFIG)
    merged.update(data)
    return merged


CONFIG = load_config()


def db_connect() -> sqlite3.Connection:
    ensure_dirs()
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with db_connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS networks (
                bssid TEXT PRIMARY KEY,
                ssid TEXT NOT NULL DEFAULT '',
                channel TEXT,
                frequency_mhz TEXT,
                security TEXT,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                times_seen INTEGER NOT NULL DEFAULT 1,
                last_signal INTEGER,
                average_signal REAL,
                notes TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                ssid TEXT,
                bssid TEXT NOT NULL,
                channel TEXT,
                frequency_mhz TEXT,
                signal_percent INTEGER,
                security TEXT
            );
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                severity TEXT NOT NULL,
                category TEXT NOT NULL,
                bssid TEXT,
                ssid TEXT,
                message TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_obs_bssid ON observations(bssid);
            CREATE INDEX IF NOT EXISTS idx_obs_time ON observations(observed_at);
            CREATE INDEX IF NOT EXISTS idx_alert_time ON alerts(created_at);
            """
        )


def escape_nmcli(value: str) -> str:
    return value.replace("\\:", "__COLON__")


def parse_nmcli_line(line: str) -> list[str]:
    fields: list[str] = []
    buf: list[str] = []
    escaped = False
    for char in line.rstrip("\n"):
        if escaped:
            buf.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == ":":
            fields.append("".join(buf))
            buf = []
        else:
            buf.append(char)
    fields.append("".join(buf))
    return fields


def live_wifi_inventory() -> list[NetworkObservation]:
    if not shutil.which("nmcli"):
        raise RuntimeError("nmcli not found. Install NetworkManager or use --demo.")
    cmd = [
        "nmcli", "-t", "--escape", "yes",
        "-f", "SSID,BSSID,CHAN,FREQ,SIGNAL,SECURITY",
        "device", "wifi", "list", "--rescan", "yes",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20, check=False)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "nmcli inventory failed").strip()
        raise RuntimeError(err)
    now = utc_now()
    observations: list[NetworkObservation] = []
    seen: set[str] = set()
    for raw in proc.stdout.splitlines():
        if not raw.strip():
            continue
        parts = parse_nmcli_line(raw)
        if len(parts) < 6:
            continue
        ssid, bssid, channel, freq, signal_pct, security = parts[:6]
        bssid = bssid.upper()
        if not bssid or bssid in seen:
            continue
        seen.add(bssid)
        try:
            sig = max(0, min(100, int(signal_pct or 0)))
        except ValueError:
            sig = 0
        observations.append(NetworkObservation(
            ssid=ssid or "(hidden)",
            bssid=bssid,
            channel=channel,
            frequency_mhz=freq,
            signal_percent=sig,
            security=security or "Unknown",
            observed_at=now,
        ))
    observations.sort(key=lambda x: x.signal_percent, reverse=True)
    return observations


def demo_wifi_inventory() -> list[NetworkObservation]:
    now = utc_now()
    base = [
        ("ASGARD-LAB", "02:11:22:33:44:55", "6", "2437", 82, "WPA2"),
        ("Authorized-Guest", "02:AA:BB:CC:DD:01", "11", "2462", 63, "WPA2"),
        ("Venue-IoT", "02:AA:BB:CC:DD:02", "44", "5220", 46, "WPA2"),
    ]
    return [NetworkObservation(*row, now) for row in base]


def add_alert(conn: sqlite3.Connection, severity: str, category: str,
              obs: NetworkObservation | None, message: str) -> None:
    created = utc_now()
    bssid = obs.bssid if obs else None
    ssid = obs.ssid if obs else None
    conn.execute(
        "INSERT INTO alerts(session_id,created_at,severity,category,bssid,ssid,message) VALUES(?,?,?,?,?,?,?)",
        (current_session_id, created, severity, category, bssid, ssid, message),
    )
    item = {
        "created_at": created,
        "severity": severity,
        "category": category,
        "bssid": bssid,
        "ssid": ssid,
        "message": message,
    }
    with lock:
        runtime["alerts"].insert(0, item)
        runtime["alerts"] = runtime["alerts"][:100]
        runtime["alert_count"] += 1
    log(f"ALERT {severity} {category}: {message}")


def process_inventory(observations: list[NetworkObservation]) -> None:
    with db_connect() as conn:
        for obs in observations:
            existing = conn.execute(
                "SELECT * FROM networks WHERE bssid = ?", (obs.bssid,)
            ).fetchone()
            if existing is None:
                conn.execute(
                    """INSERT INTO networks
                    (bssid,ssid,channel,frequency_mhz,security,first_seen,last_seen,times_seen,last_signal,average_signal)
                    VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (obs.bssid, obs.ssid, obs.channel, obs.frequency_mhz, obs.security,
                     obs.observed_at, obs.observed_at, 1, obs.signal_percent, float(obs.signal_percent)),
                )
                if CONFIG.get("new_network_alerts", True):
                    add_alert(conn, "INFO", "NEW_NETWORK", obs,
                              f"New wireless network observed: {obs.ssid} ({obs.bssid})")
            else:
                old_avg = float(existing["average_signal"] or obs.signal_percent)
                old_times = int(existing["times_seen"] or 1)
                new_avg = ((old_avg * old_times) + obs.signal_percent) / (old_times + 1)
                old_signal = int(existing["last_signal"] or obs.signal_percent)
                threshold = int(CONFIG.get("signal_change_alert_db", 25))
                if abs(obs.signal_percent - old_signal) >= threshold:
                    add_alert(conn, "NOTICE", "SIGNAL_CHANGE", obs,
                              f"Large signal change for {obs.ssid}: {old_signal}% -> {obs.signal_percent}%")
                conn.execute(
                    """UPDATE networks SET ssid=?,channel=?,frequency_mhz=?,security=?,last_seen=?,
                    times_seen=times_seen+1,last_signal=?,average_signal=? WHERE bssid=?""",
                    (obs.ssid, obs.channel, obs.frequency_mhz, obs.security, obs.observed_at,
                     obs.signal_percent, new_avg, obs.bssid),
                )
            conn.execute(
                """INSERT INTO observations
                (session_id,observed_at,ssid,bssid,channel,frequency_mhz,signal_percent,security)
                VALUES(?,?,?,?,?,?,?,?)""",
                (current_session_id, obs.observed_at, obs.ssid, obs.bssid, obs.channel,
                 obs.frequency_mhz, obs.signal_percent, obs.security),
            )
        known_count = conn.execute("SELECT COUNT(*) FROM networks").fetchone()[0]
        alert_count = conn.execute("SELECT COUNT(*) FROM alerts WHERE session_id=?", (current_session_id,)).fetchone()[0]
    with lock:
        runtime["networks"] = [asdict(x) for x in observations]
        runtime["inventory_count"] = len(observations)
        runtime["known_count"] = known_count
        runtime["alert_count"] = alert_count
        runtime["last_inventory_at"] = utc_now()
        runtime["last_inventory_error"] = None


def system_status() -> dict[str, Any]:
    disk = psutil.disk_usage(str(BASE_DIR))
    vm = psutil.virtual_memory()
    uptime = int(time.monotonic() - started_monotonic)
    temp = None
    try:
        temps = psutil.sensors_temperatures()
        for key in ("cpu_thermal", "coretemp"):
            if key in temps and temps[key]:
                temp = round(float(temps[key][0].current), 1)
                break
    except Exception:
        pass
    return {
        "app": APP_NAME,
        "version": VERSION,
        "mission": MISSION,
        "node_name": CONFIG["node_name"],
        "site_name": CONFIG["site_name"],
        "authorized_scope": bool(CONFIG.get("authorized_scope")),
        "status": "ONLINE",
        "mode": runtime["mode"],
        "started_at": started_at.isoformat(timespec="seconds"),
        "uptime_seconds": uptime,
        "cpu_percent": psutil.cpu_percent(interval=None),
        "cpu_temperature_c": temp,
        "memory_percent": round(vm.percent, 1),
        "memory_used_mb": round((vm.total - vm.available) / 1024 / 1024, 1),
        "memory_total_mb": round(vm.total / 1024 / 1024, 1),
        "disk_percent": round(disk.percent, 1),
        "disk_used_gb": round(disk.used / 1024 / 1024 / 1024, 2),
        "disk_total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
        "architecture": platform.machine(),
        "hostname": platform.node(),
        "session_id": current_session_id,
        "last_inventory_at": runtime["last_inventory_at"],
        "last_inventory_error": runtime["last_inventory_error"],
        "observed_networks": runtime["inventory_count"],
        "known_networks": runtime["known_count"],
        "session_alerts": runtime["alert_count"],
        "timestamp": utc_now(),
    }


def export_session() -> Path:
    status = system_status()
    with db_connect() as conn:
        rows = conn.execute(
            "SELECT * FROM observations WHERE session_id=? ORDER BY observed_at DESC LIMIT 5000",
            (current_session_id,),
        ).fetchall()
        alerts = conn.execute(
            "SELECT * FROM alerts WHERE session_id=? ORDER BY created_at DESC",
            (current_session_id,),
        ).fetchall()
    doc = {
        "classification": "Authorized defensive wireless observation",
        "scope_statement": "Metadata-only local wireless inventory; no disruption, credential collection, exploitation, or automated interaction.",
        "node": status,
        "observations": [dict(x) for x in rows],
        "alerts": [dict(x) for x in alerts],
    }
    path = SESSION_DIR / f"{current_session_id}.json"
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    with lock:
        runtime["last_session_export_at"] = utc_now()
    return path


def worker(demo: bool) -> None:
    runtime["mode"] = "demo" if demo else "live"
    interval = max(10, int(CONFIG.get("scan_interval_seconds", 30)))
    export_interval = max(30, int(CONFIG.get("session_export_interval_seconds", 60)))
    last_export = 0.0
    while not stop_event.is_set():
        try:
            observations = demo_wifi_inventory() if demo else live_wifi_inventory()
            process_inventory(observations)
            log(f"Inventory complete: {len(observations)} networks observed")
        except Exception as exc:
            with lock:
                runtime["last_inventory_error"] = str(exc)
            log(f"Wireless inventory error: {exc}", "WARN")
        if time.monotonic() - last_export >= export_interval:
            try:
                path = export_session()
                log(f"Session snapshot exported: {path.name}")
            except Exception as exc:
                log(f"Session export error: {exc}", "WARN")
            last_export = time.monotonic()
        stop_event.wait(interval)


DASHBOARD_HTML = r"""
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Heimdall | Wireless Situational Awareness</title>
<style>
:root{color-scheme:dark;background:#07110d;color:#dbe7df;font-family:Inter,system-ui,Segoe UI,Arial,sans-serif}
body{margin:0;background:linear-gradient(135deg,#06100c,#0a1712 55%,#07100e);min-height:100vh}.wrap{max-width:1250px;margin:auto;padding:24px}
header{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #1d3c2d;padding-bottom:18px}.brand h1{margin:0;font-size:30px;letter-spacing:2px}.brand small{color:#7fae91}.online{border:1px solid #2d9c5b;padding:8px 14px;border-radius:999px;color:#71e39c;background:#0a2115}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0}.card,.panel{background:#0b1813;border:1px solid #183628;border-radius:14px;padding:16px;box-shadow:0 8px 25px #0005}.card .v{font-size:25px;font-weight:700;color:#7ce3a2}.label{color:#7f9d8b;font-size:12px;text-transform:uppercase;letter-spacing:1px}.panel{margin-top:14px}.panel h2{font-size:15px;letter-spacing:1.5px;color:#78dc9c;margin:0 0 12px}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:10px;border-bottom:1px solid #173126;font-size:13px}th{color:#729780}.signal{font-weight:700}.notice{padding:10px;border-left:3px solid #d6a84b;background:#1d190d;margin:7px 0;border-radius:6px}.info{padding:10px;border-left:3px solid #3fc379;background:#0d2015;margin:7px 0;border-radius:6px}.muted{color:#799083}.scope{font-size:12px;color:#8db39a}.err{color:#ff9b8f}.two{display:grid;grid-template-columns:2fr 1fr;gap:14px}@media(max-width:850px){.grid{grid-template-columns:repeat(2,1fr)}.two{grid-template-columns:1fr}}@media(max-width:520px){.grid{grid-template-columns:1fr}}
</style></head><body><div class="wrap">
<header><div class="brand"><h1>HEIMDALL</h1><small>Wireless Situational Awareness & Asset Observation</small></div><div class="online">● ONLINE</div></header>
<div class="scope">Observe • Correlate • Detect • Document &nbsp; | &nbsp; Authorized defensive observation only</div>
<div id="error" class="err"></div>
<div class="grid">
<div class="card"><div class="label">Observed Networks</div><div class="v" id="observed">—</div></div>
<div class="card"><div class="label">Known Networks</div><div class="v" id="known">—</div></div>
<div class="card"><div class="label">Session Alerts</div><div class="v" id="alertsCount">—</div></div>
<div class="card"><div class="label">CPU / Memory</div><div class="v"><span id="cpu">—</span>% / <span id="mem">—</span>%</div></div>
</div>
<div class="two"><div class="panel"><h2>WIRELESS INVENTORY</h2><div style="overflow:auto"><table><thead><tr><th>SSID</th><th>BSSID</th><th>CH</th><th>SIGNAL</th><th>SECURITY</th><th>OBSERVED</th></tr></thead><tbody id="networks"></tbody></table></div></div>
<div class="panel"><h2>NODE STATUS</h2><p><b id="node">—</b><br><span class="muted" id="site">—</span></p><p>Mode: <b id="mode">—</b><br>Architecture: <span id="arch">—</span><br>Uptime: <span id="uptime">—</span></p><p>Last inventory:<br><span id="last">—</span></p></div></div>
<div class="panel"><h2>RECENT ALERTS</h2><div id="alerts"></div></div>
</div><script>
function dur(s){s=Number(s||0);let d=Math.floor(s/86400),h=Math.floor((s%86400)/3600),m=Math.floor((s%3600)/60);return `${d}d ${h}h ${m}m`}
async function refresh(){try{let [sr,nr,ar]=await Promise.all([fetch('/api/status'),fetch('/api/networks'),fetch('/api/alerts')]);let s=await sr.json(),ns=await nr.json(),as=await ar.json();
document.getElementById('observed').textContent=s.observed_networks;document.getElementById('known').textContent=s.known_networks;document.getElementById('alertsCount').textContent=s.session_alerts;document.getElementById('cpu').textContent=s.cpu_percent;document.getElementById('mem').textContent=s.memory_percent;document.getElementById('node').textContent=s.node_name;document.getElementById('site').textContent=s.site_name;document.getElementById('mode').textContent=s.mode;document.getElementById('arch').textContent=s.architecture;document.getElementById('uptime').textContent=dur(s.uptime_seconds);document.getElementById('last').textContent=s.last_inventory_at||'Waiting...';document.getElementById('error').textContent=s.last_inventory_error||'';
document.getElementById('networks').innerHTML=ns.map(n=>`<tr><td>${n.ssid}</td><td>${n.bssid}</td><td>${n.channel}</td><td class="signal">${n.signal_percent}%</td><td>${n.security}</td><td>${n.observed_at}</td></tr>`).join('')||'<tr><td colspan="6" class="muted">Waiting for observation...</td></tr>';
document.getElementById('alerts').innerHTML=as.slice(0,15).map(a=>`<div class="${a.severity==='INFO'?'info':'notice'}"><b>${a.category}</b> — ${a.message}<br><span class="muted">${a.created_at}</span></div>`).join('')||'<span class="muted">No alerts this session.</span>';}catch(e){document.getElementById('error').textContent=e}}
refresh();setInterval(refresh,5000);
</script></body></html>
"""


@app.get("/")
def dashboard():
    return render_template_string(DASHBOARD_HTML)


@app.get("/api/status")
def api_status():
    return jsonify(system_status())


@app.get("/api/heartbeat")
def api_heartbeat():
    return jsonify(system_status())


@app.get("/api/networks")
def api_networks():
    with lock:
        return jsonify(runtime["networks"])


@app.get("/api/alerts")
def api_alerts():
    with lock:
        return jsonify(runtime["alerts"])


@app.get("/api/known-networks")
def api_known_networks():
    with db_connect() as conn:
        rows = conn.execute("SELECT * FROM networks ORDER BY last_seen DESC LIMIT 1000").fetchall()
    return jsonify([dict(x) for x in rows])


@app.post("/api/session/export")
def api_export():
    return jsonify({"ok": True, "file": str(export_session())})


def shutdown_handler(signum=None, frame=None):
    log("Shutdown requested")
    stop_event.set()
    try:
        export_session()
    except Exception:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Heimdall wireless situational-awareness node")
    parser.add_argument("--demo", action="store_true", help="Use safe synthetic observations for bench testing")
    parser.add_argument("--port", type=int, help="Override dashboard port")
    parser.add_argument("--host", help="Override dashboard bind address")
    args = parser.parse_args()

    ensure_dirs()
    init_db()
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    if not CONFIG.get("authorized_scope", False):
        raise SystemExit("Heimdall is disabled: set authorized_scope=true in config.json for an authorized environment.")

    log(f"{APP_NAME} v{VERSION} starting | {MISSION}")
    log(f"Node={CONFIG['node_name']} Site={CONFIG['site_name']} Session={current_session_id}")
    worker_thread = threading.Thread(target=worker, args=(args.demo,), daemon=True)
    worker_thread.start()

    host = args.host or CONFIG.get("dashboard_host", "0.0.0.0")
    port = args.port or int(CONFIG.get("dashboard_port", 8080))
    log(f"Dashboard listening on http://{host}:{port}")
    app.run(host=host, port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
