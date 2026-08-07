#!/usr/bin/env python3
"""Heimdall field observer: passive Wi-Fi metadata, privacy filtering, local history and dashboard."""
from __future__ import annotations

import argparse, hashlib, json, os, shutil, sqlite3, subprocess, threading, time, uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template_string

VERSION = "0.2.0-field"
BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
SESSIONS = DATA / "sessions"
DB = DATA / "heimdall.db"
CONFIG_FILE = BASE / "config.json"

DEFAULT = {
    "node_name": "OVN-002",
    "site_name": "Authorized Test Site",
    "authorized_scope": True,
    "scan_interval_seconds": 10,
    "dashboard_host": "0.0.0.0",
    "dashboard_port": 8080,
    "privacy_mode": True,
    "protected_networks": [],
    "protected_bssids": [],
    "protected_action": "exclude",
    "export_raw_identifiers": False,
    "new_network_alerts": True,
    "signal_change_alert_percent": 20,
    "session_export_interval_seconds": 60,
}

DATA.mkdir(exist_ok=True); SESSIONS.mkdir(exist_ok=True)
if not CONFIG_FILE.exists():
    CONFIG_FILE.write_text(json.dumps(DEFAULT, indent=2), encoding="utf-8")
try:
    CONFIG = DEFAULT | json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
except Exception:
    CONFIG = dict(DEFAULT)

if not CONFIG.get("authorized_scope", False):
    raise SystemExit("Heimdall refused to start: authorized_scope is false")

app = Flask(__name__)
lock = threading.RLock()
stop = threading.Event()
session_id = str(uuid.uuid4())
started = time.monotonic()
state: dict[str, Any] = {
    "mode": "live", "networks": [], "activities": [], "alerts": [],
    "visible": 0, "known": 0, "last_scan": None, "last_error": None,
    "scan_number": 0, "protected_filtered": 0,
}

@dataclass
class Network:
    ssid: str; bssid: str; channel: str; frequency: str; signal: int; security: str; observed_at: str

def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def activity(kind: str, message: str, detail: str = "") -> None:
    item = {"time": now(), "kind": kind, "message": message, "detail": detail}
    with lock:
        state["activities"].insert(0, item); state["activities"] = state["activities"][:80]
    print(f"[{item['time']}] {kind}: {message} {detail}", flush=True)

def norm(s: Any) -> str:
    return str(s or "").strip().lower()

def is_protected(n: Network) -> bool:
    if not CONFIG.get("privacy_mode", True): return False
    ssids = {norm(x) for x in CONFIG.get("protected_networks", [])}
    bssids = {norm(x) for x in CONFIG.get("protected_bssids", [])}
    return norm(n.ssid) in ssids or norm(n.bssid) in bssids

def parse_nmcli(line: str) -> list[str]:
    out, buf, esc = [], [], False
    for c in line.rstrip("\n"):
        if esc: buf.append(c); esc = False
        elif c == "\\": esc = True
        elif c == ":": out.append("".join(buf)); buf = []
        else: buf.append(c)
    out.append("".join(buf)); return out

def scan_live() -> list[Network]:
    if not shutil.which("nmcli"): raise RuntimeError("nmcli not found")
    p = subprocess.run(["nmcli","-t","--escape","yes","-f","SSID,BSSID,CHAN,FREQ,SIGNAL,SECURITY","device","wifi","list","--rescan","yes"], capture_output=True, text=True, timeout=20)
    if p.returncode: raise RuntimeError((p.stderr or p.stdout).strip())
    ts, found, seen = now(), [], set()
    for line in p.stdout.splitlines():
        parts = parse_nmcli(line)
        if len(parts) < 6: continue
        ssid,bssid,ch,freq,sig,sec = parts[:6]; bssid = bssid.upper()
        if not bssid or bssid in seen: continue
        seen.add(bssid)
        try: signal = max(0,min(100,int(sig)))
        except ValueError: signal = 0
        found.append(Network(ssid or "(hidden)",bssid,ch,freq,signal,sec or "Unknown",ts))
    return sorted(found, key=lambda x:x.signal, reverse=True)

def scan_demo() -> list[Network]:
    ts=now(); return [Network("ASGARD-LAB","02:11:22:33:44:55","6","2437",82,"WPA2",ts), Network("Venue-Guest","02:AA:BB:CC:DD:01","11","2462",63,"WPA2",ts), Network("Venue-IoT","02:AA:BB:CC:DD:02","44","5220",46,"WPA2",ts)]

def db() -> sqlite3.Connection:
    c=sqlite3.connect(DB,timeout=10); c.row_factory=sqlite3.Row; return c

def init_db() -> None:
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS networks(bssid TEXT PRIMARY KEY,ssid TEXT,channel TEXT,frequency TEXT,security TEXT,first_seen TEXT,last_seen TEXT,times_seen INTEGER,last_signal INTEGER,average_signal REAL);
        CREATE TABLE IF NOT EXISTS observations(id INTEGER PRIMARY KEY AUTOINCREMENT,session_id TEXT,observed_at TEXT,ssid TEXT,bssid TEXT,channel TEXT,frequency TEXT,signal INTEGER,security TEXT);
        """)

def process(found: list[Network]) -> None:
    protected=[n for n in found if is_protected(n)]
    visible=[n for n in found if not is_protected(n)]
    previous={n["bssid"]:n for n in state.get("networks",[])}
    if protected:
        activity("PRIVACY", f"Filtered {len(protected)} protected network(s)", "identifiers not stored")
    new_count=0; changed=0
    with db() as c:
        for n in visible:
            old=c.execute("SELECT * FROM networks WHERE bssid=?",(n.bssid,)).fetchone()
            if old is None:
                c.execute("INSERT INTO networks VALUES(?,?,?,?,?,?,?,?,?,?)",(n.bssid,n.ssid,n.channel,n.frequency,n.security,n.observed_at,n.observed_at,1,n.signal,float(n.signal)))
                new_count += 1
                if CONFIG.get("new_network_alerts",True): activity("NEW",f"New network: {n.ssid}",f"CH {n.channel} • {n.signal}%")
            else:
                last=int(old["last_signal"] or n.signal); times=int(old["times_seen"] or 1); avg=float(old["average_signal"] or n.signal); newavg=(avg*times+n.signal)/(times+1)
                if abs(n.signal-last)>=int(CONFIG.get("signal_change_alert_percent",20)):
                    changed += 1; activity("CHANGE",f"Signal change: {n.ssid}",f"{last}% → {n.signal}%")
                c.execute("UPDATE networks SET ssid=?,channel=?,frequency=?,security=?,last_seen=?,times_seen=times_seen+1,last_signal=?,average_signal=? WHERE bssid=?",(n.ssid,n.channel,n.frequency,n.security,n.observed_at,n.signal,newavg,n.bssid))
            c.execute("INSERT INTO observations(session_id,observed_at,ssid,bssid,channel,frequency,signal,security) VALUES(?,?,?,?,?,?,?,?)",(session_id,n.observed_at,n.ssid,n.bssid,n.channel,n.frequency,n.signal,n.security))
        known=c.execute("SELECT COUNT(*) FROM networks").fetchone()[0]
    current={n.bssid:n for n in visible}
    gone=[v for k,v in previous.items() if k not in current]
    appeared=[n for k,n in current.items() if k in previous and previous[k].get("signal") is None]
    if gone: activity("CHANGE",f"{len(gone)} network(s) no longer visible")
    with lock:
        state["networks"]=[asdict(n) for n in visible]; state["visible"]=len(visible); state["known"]=known
        state["protected_filtered"]=len(protected); state["last_scan"]=now(); state["last_error"]=None; state["scan_number"]+=1
    activity("SCAN",f"Observation #{state['scan_number']} complete",f"{len(visible)} visible • {new_count} new • {changed} changed")

def export_session() -> Path:
    raw=bool(CONFIG.get("export_raw_identifiers",False))
    with db() as c: rows=[dict(r) for r in c.execute("SELECT * FROM observations WHERE session_id=? ORDER BY id DESC LIMIT 5000",(session_id,))]
    if not raw:
        for r in rows:
            r["ssid"]="[REDACTED]"; r["bssid"]="id-"+hashlib.sha256(r["bssid"].encode()).hexdigest()[:12]
    doc={"classification":"Authorized defensive wireless observation","privacy":{"protected_identifiers_excluded":True,"raw_identifiers_exported":raw},"session_id":session_id,"node":CONFIG.get("node_name"),"observations":rows}
    path=SESSIONS/f"{session_id}.json"; path.write_text(json.dumps(doc,indent=2),encoding="utf-8"); return path

def mem_percent() -> float:
    try:
        vals={}
        for line in Path('/proc/meminfo').read_text().splitlines():
            k,v=line.split(':',1); vals[k]=int(v.strip().split()[0])
        return round((1-vals.get('MemAvailable',0)/vals['MemTotal'])*100,1)
    except Exception:return 0.0

def status() -> dict[str,Any]:
    total,used,free=shutil.disk_usage(BASE)
    return {"app":"Heimdall","version":VERSION,"node_name":CONFIG.get("node_name"),"site_name":CONFIG.get("site_name"),"status":"ONLINE","mode":state["mode"],"uptime_seconds":int(time.monotonic()-started),"load_1m":round(os.getloadavg()[0],2),"memory_percent":mem_percent(),"disk_percent":round(used/total*100,1),"observed_networks":state["visible"],"known_networks":state["known"],"protected_filtered":state["protected_filtered"],"last_inventory_at":state["last_scan"],"last_inventory_error":state["last_error"],"scan_number":state["scan_number"],"scan_interval_seconds":int(CONFIG.get("scan_interval_seconds",10)),"timestamp":now()}

def worker(demo: bool) -> None:
    state["mode"]="demo" if demo else "live"; interval=max(10,int(CONFIG.get("scan_interval_seconds",10))); last_export=0.0
    activity("START",f"Josh is watching",f"{interval}s observation interval")
    while not stop.is_set():
        try: process(scan_demo() if demo else scan_live())
        except Exception as e:
            state["last_error"]=str(e); activity("ERROR","Wireless observation failed",str(e))
        if time.monotonic()-last_export>=max(30,int(CONFIG.get("session_export_interval_seconds",60))):
            try: export_session(); activity("SAVE","Privacy-safe session snapshot saved")
            except Exception as e: activity("ERROR","Session export failed",str(e))
            last_export=time.monotonic()
        stop.wait(interval)

HTML='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Heimdall</title><style>body{font-family:system-ui;background:#07110d;color:#dce8df;margin:0}.w{max-width:1150px;margin:auto;padding:22px}h1{letter-spacing:3px}.g{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}.c,.p{background:#0c1914;border:1px solid #1a392a;border-radius:12px;padding:14px}.v{font-size:25px;color:#76e39d;font-weight:700}.l{font-size:11px;color:#83a48f;text-transform:uppercase}.two{display:grid;grid-template-columns:2fr 1fr;gap:12px;margin-top:12px}table{width:100%;border-collapse:collapse}td,th{padding:8px;border-bottom:1px solid #183126;text-align:left;font-size:12px}.ev{padding:8px;border-left:3px solid #4ad17e;margin:6px 0;background:#0c2115}.PRIVACY{border-color:#65a7ff}.CHANGE{border-color:#e9b94f}.ERROR{border-color:#ff776b}@media(max-width:800px){.g{grid-template-columns:repeat(2,1fr)}.two{grid-template-columns:1fr}}</style></head><body><div class=w><h1>HEIMDALL / JOSH</h1><p>Observe • Correlate • Detect • Document</p><div class=g><div class=c><div class=l>Visible</div><div id=v class=v>—</div></div><div class=c><div class=l>Known</div><div id=k class=v>—</div></div><div class=c><div class=l>Protected</div><div id=p class=v>—</div></div><div class=c><div class=l>Scan</div><div id=n class=v>—</div></div><div class=c><div class=l>Next cycle</div><div id=i class=v>10s</div></div></div><div class=two><div class=p><h3>WIRELESS INVENTORY</h3><table><thead><tr><th>SSID</th><th>CH</th><th>Signal</th><th>Security</th></tr></thead><tbody id=nets></tbody></table></div><div class=p><h3>JOSH ACTIVITY</h3><div id=act></div></div></div></div><script>async function r(){let s=await(await fetch('/api/status')).json(),ns=await(await fetch('/api/networks')).json(),a=await(await fetch('/api/activity')).json();v.textContent=s.observed_networks;k.textContent=s.known_networks;p.textContent=s.protected_filtered;n.textContent='#'+s.scan_number;i.textContent=s.scan_interval_seconds+'s';nets.innerHTML=ns.map(x=>`<tr><td>${x.ssid}</td><td>${x.channel}</td><td>${x.signal}%</td><td>${x.security}</td></tr>`).join('');act.innerHTML=a.slice(0,18).map(x=>`<div class="ev ${x.kind}"><b>${x.kind}</b> ${x.message}<br><small>${x.detail} • ${x.time}</small></div>`).join('')}r();setInterval(r,2000)</script></body></html>'''

@app.get('/')
def home(): return render_template_string(HTML)
@app.get('/api/status')
def api_status(): return jsonify(status())
@app.get('/api/networks')
def api_networks(): return jsonify(state['networks'])
@app.get('/api/activity')
def api_activity(): return jsonify(state['activities'])
@app.get('/api/heartbeat')
def heartbeat(): return jsonify(status())

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--demo',action='store_true'); args=ap.parse_args(); init_db(); threading.Thread(target=worker,args=(args.demo,),daemon=True).start(); app.run(host=CONFIG.get('dashboard_host','0.0.0.0'),port=int(CONFIG.get('dashboard_port',8080)),debug=False,use_reloader=False)
