#!/usr/bin/env python3
"""Project Odin styled UI for Heimdall/Josh.

This UI intentionally runs separately from the working Heimdall observer so the
presentation can evolve without destabilizing the field scanner. It proxies the
privacy-filtered local Heimdall APIs from 127.0.0.1:8080 and serves the new UI on
port 8081.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from flask import Flask, jsonify, render_template_string

BACKEND = "http://127.0.0.1:8080"
app = Flask(__name__)


def backend_json(path: str):
    try:
        with urllib.request.urlopen(BACKEND + path, timeout=3) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as exc:
        return {"_error": str(exc)}


@app.get("/api/status")
def api_status():
    return jsonify(backend_json("/api/status"))


@app.get("/api/networks")
def api_networks():
    data = backend_json("/api/networks")
    return jsonify([] if isinstance(data, dict) and data.get("_error") else data)


@app.get("/api/activity")
def api_activity():
    data = backend_json("/api/activity")
    return jsonify([] if isinstance(data, dict) and data.get("_error") else data)


HTML = r'''<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Project Odin — Heimdall / Josh</title>
<style>
:root{
 --bg:#020814;--bg2:#07142a;--panel:#07182fdd;--panel2:#0a2142;
 --line:#164f88;--line2:#0a8fff;--cyan:#38d5ff;--blue:#168cff;
 --green:#1cff86;--text:#eaf5ff;--muted:#82a8c8;--warn:#ffb342;--bad:#ff556f;
}
*{box-sizing:border-box}body{margin:0;color:var(--text);font-family:Inter,Segoe UI,Arial,sans-serif;background:
radial-gradient(circle at 50% -10%,#123b71 0,#06152e 28%,#020814 65%);min-height:100vh}
body:before{content:"";position:fixed;inset:0;pointer-events:none;opacity:.18;background-image:linear-gradient(#0e3d69 1px,transparent 1px),linear-gradient(90deg,#0e3d69 1px,transparent 1px);background-size:42px 42px;mask-image:linear-gradient(to bottom,#000,transparent 70%)}
.shell{max-width:1500px;margin:auto;padding:20px 22px 36px;position:relative}
.top{display:grid;grid-template-columns:1fr auto;gap:20px;align-items:center;margin-bottom:14px}
.brand{display:flex;gap:18px;align-items:center}.sigil{width:70px;height:70px;border:2px solid #2eaaff;border-radius:50%;display:grid;place-items:center;box-shadow:0 0 30px #168cff55 inset,0 0 18px #168cff44;font-size:31px;font-weight:900;color:var(--cyan)}
.brand h1{font-size:34px;letter-spacing:4px;margin:0;text-transform:uppercase}.brand h2{font-size:14px;letter-spacing:5px;color:#b9d7ef;margin:4px 0}.motto{color:#61c9ff;letter-spacing:3px;font-size:11px}
.identity{display:flex;gap:20px;align-items:center}.nodeid{font-family:Consolas,monospace}.nodeid b{font-size:25px;letter-spacing:2px}.nodeid small{display:block;color:#9ac1df;line-height:1.5}.online{border:1px solid #16df7f;border-radius:16px;padding:14px 20px;color:var(--green);font-weight:800;letter-spacing:1px;box-shadow:inset 0 0 20px #00ff7720}.dot{display:inline-block;width:12px;height:12px;border-radius:50%;background:var(--green);box-shadow:0 0 13px var(--green);margin-right:10px}
.nav{display:grid;grid-template-columns:repeat(6,1fr);border:1px solid #164a80;border-radius:14px;overflow:hidden;background:#07172b99;margin-bottom:18px}.nav div{padding:14px;text-align:center;border-right:1px solid #123c69;color:#b9d3e8;font-weight:700}.nav div:last-child{border:0}.nav .active{background:linear-gradient(#0a4f91,#073061);box-shadow:inset 0 0 0 1px #27baff;color:#fff}
.metrics{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:14px}.metric,.panel{background:linear-gradient(145deg,#081a33dd,#061126e8);border:1px solid #1f5f9b;border-radius:13px;box-shadow:inset 0 0 25px #0c315533,0 8px 30px #0005}.metric{padding:16px}.metric .label{font-size:11px;color:#9ec2dd;letter-spacing:1px;text-transform:uppercase}.metric .value{font-size:27px;font-weight:800;margin-top:6px}.metric .sub{font-size:11px;color:var(--muted);margin-top:3px}.ok{color:var(--green)}.cyan{color:var(--cyan)}.warn{color:var(--warn)}
.layout{display:grid;grid-template-columns:minmax(0,2.15fr) minmax(300px,.95fr);gap:14px}.panel{padding:16px}.title{font-size:17px;font-weight:800;letter-spacing:.8px;margin:0 0 12px;display:flex;align-items:center;justify-content:space-between}.title span{color:#b9d5ec}.pill{font-size:10px;padding:5px 9px;border:1px solid #245b8d;border-radius:999px;color:#86caff}
.statusbox{display:flex;align-items:center;gap:18px;padding:18px;margin-bottom:14px;background:linear-gradient(90deg,#082142,#06152d);border:1px solid #1b68aa;border-radius:13px}.rune{font-size:42px;color:var(--cyan);text-shadow:0 0 16px #17aaff}.statusbox h3{margin:0 0 5px;font-size:19px}.statusline{color:var(--green);font-weight:700}.pulse{height:44px;flex:1;min-width:120px;background:linear-gradient(90deg,transparent 0 12%,#16baff 12% 13%,transparent 13% 28%,#16baff 28% 29%,transparent 29% 42%,#16baff 42% 43%,transparent 43%);opacity:.6;filter:drop-shadow(0 0 6px #16aaff)}
.twocol{display:grid;grid-template-columns:1.2fr .8fr;gap:14px}.tablewrap{overflow:auto;max-height:520px}table{width:100%;border-collapse:collapse}th{font-size:10px;color:#87b4d6;text-transform:uppercase;letter-spacing:.8px;text-align:left;padding:10px;border-bottom:1px solid #1b527f}td{padding:10px;border-bottom:1px solid #102f50;font-size:12px}.sigbar{height:6px;border-radius:4px;background:#0d3153;overflow:hidden;margin-top:4px}.sigbar i{display:block;height:100%;background:linear-gradient(90deg,#0d7cff,#3eeaff);box-shadow:0 0 8px #18aaff}
.activity{max-height:540px;overflow:auto}.event{padding:10px 11px;margin:7px 0;border-left:3px solid #25d4ff;background:#071a31;border-radius:5px}.event b{color:#61dcff}.event small{color:#6f99b9;display:block;margin-top:4px}.event.PRIVACY{border-color:#a56cff}.event.CHANGE{border-color:#ffbd42}.event.ERROR{border-color:#ff516e}.event.SAVE{border-color:#1cff86}
.sidegrid{display:grid;gap:14px}.sysrow{display:grid;grid-template-columns:110px 1fr;gap:8px;padding:6px 0;border-bottom:1px solid #102f50;font-size:12px}.sysrow span:first-child{color:#86aeca}.actions{display:grid;grid-template-columns:1fr 1fr;gap:10px}.action{border:1px solid #1c73ba;background:#08264c;border-radius:11px;padding:15px 8px;text-align:center;color:#dff4ff}.action strong{display:block;font-size:12px;margin-top:5px}.action.disabled{opacity:.42}.quicknote{font-size:10px;color:#719abb;margin-top:8px}.footer{margin-top:14px;text-align:center;border-top:1px solid #16487c;padding:18px;color:#4fa8e3;letter-spacing:8px;font-size:11px}
@media(max-width:980px){.top{grid-template-columns:1fr}.identity{justify-content:space-between}.metrics{grid-template-columns:repeat(2,1fr)}.layout,.twocol{grid-template-columns:1fr}.nav{grid-template-columns:repeat(3,1fr)}}
@media(max-width:560px){.shell{padding:12px}.brand h1{font-size:23px}.sigil{width:52px;height:52px}.identity{display:block}.online{margin-top:10px;display:inline-block}.metrics{grid-template-columns:1fr}.nav{grid-template-columns:repeat(2,1fr)}}
</style>
</head>
<body><div class="shell">
<div class="top"><div class="brand"><div class="sigil">ᛟ</div><div><h1>Project Odin</h1><h2>HEIMDALL NODE CONTROL CENTER</h2><div class="motto">INFORMATION IS POWER // KNOWLEDGE IS DEFENSE</div></div></div><div class="identity"><div class="nodeid"><b id="nodeName">OVN-002</b><small>CODENAME: JOSH<br>WIRELESS OBSERVATION NODE</small></div><div class="online"><span class="dot"></span>ONLINE</div></div></div>
<div class="nav"><div class="active">⌂ OVERVIEW</div><div>⚡ ACTIVITY</div><div>◉ WIRELESS</div><div>▣ SYSTEM</div><div>≡ LOGS</div><div>⚙ SETTINGS</div></div>
<div class="metrics">
<div class="metric"><div class="label">Visible Networks</div><div class="value cyan" id="visible">—</div><div class="sub">Current observation</div></div>
<div class="metric"><div class="label">Known Networks</div><div class="value" id="known">—</div><div class="sub">Local memory</div></div>
<div class="metric"><div class="label">Protected</div><div class="value ok" id="protected">—</div><div class="sub">Excluded by privacy guard</div></div>
<div class="metric"><div class="label">Scan Cycle</div><div class="value" id="scan">#—</div><div class="sub" id="lastScan">Waiting for observation</div></div>
<div class="metric"><div class="label">Next Cycle</div><div class="value cyan" id="next">10s</div><div class="sub">Automatic refresh</div></div>
</div>
<div class="statusbox"><div class="rune">ᚺ</div><div><h3>NODE STATUS</h3><div class="statusline" id="statusLine">Josh is online and standing watch.</div></div><div class="pulse"></div></div>
<div class="layout">
<div>
<div class="twocol">
<div class="panel"><div class="title"><span>WIRELESS INVENTORY</span><div class="pill">PRIVACY FILTERED</div></div><div class="tablewrap"><table><thead><tr><th>SSID</th><th>CH</th><th>Signal</th><th>Security</th></tr></thead><tbody id="nets"><tr><td colspan="4">Waiting for scan...</td></tr></tbody></table></div></div>
<div class="panel"><div class="title"><span>JOSH ACTIVITY</span><div class="pill">LIVE</div></div><div class="activity" id="activity"><div class="event"><b>START</b> Waiting for Josh...</div></div></div>
</div>
</div>
<div class="sidegrid">
<div class="panel"><div class="title"><span>SYSTEM INFO</span></div><div class="sysrow"><span>Node</span><b id="sysNode">—</b></div><div class="sysrow"><span>Role</span><span>Wireless Observation</span></div><div class="sysrow"><span>Mode</span><span id="mode">—</span></div><div class="sysrow"><span>Uptime</span><span id="uptime">—</span></div><div class="sysrow"><span>Memory</span><span id="memory">—</span></div><div class="sysrow"><span>Storage</span><span id="disk">—</span></div><div class="sysrow"><span>Load</span><span id="load">—</span></div><div class="sysrow"><span>Backend</span><span class="ok" id="backend">ONLINE</span></div></div>
<div class="panel"><div class="title"><span>QUICK ACTIONS</span></div><div class="actions"><div class="action" onclick="refreshNow()">↻<strong>Refresh</strong></div><div class="action" onclick="location.href='/api/status'">⌁<strong>Raw Status</strong></div><div class="action" onclick="location.href='/api/activity'">≡<strong>Activity JSON</strong></div><div class="action" onclick="location.href='/api/networks'">◉<strong>Network JSON</strong></div><div class="action disabled">⚕<strong>Run Doctor</strong></div><div class="action disabled">⬆<strong>Check Update</strong></div></div><div class="quicknote">Maintenance actions will be enabled after authentication/control backend is added.</div></div>
<div class="panel"><div class="title"><span>NODE ROLE</span></div><div style="display:flex;gap:14px;align-items:center"><div class="sigil" style="width:50px;height:50px;font-size:22px">ᛉ</div><div><b>Heimdall / Josh</b><div style="color:#85aac8;font-size:12px;margin-top:4px">Passive wireless situational awareness, privacy-safe observation and reporting.</div></div></div></div>
</div>
</div>
<div class="footer">DEFEND • INVESTIGATE • ANALYZE • DOCUMENT</div>
</div>
<script>
let countdown=10,lastScanKey=null;
function duration(s){s=Number(s||0);let d=Math.floor(s/86400),h=Math.floor((s%86400)/3600),m=Math.floor((s%3600)/60);return `${d}d ${h}h ${m}m`}
function esc(v){return String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
async function refreshNow(){
 try{
  const [sr,nr,ar]=await Promise.all([fetch('/api/status'),fetch('/api/networks'),fetch('/api/activity')]);
  const s=await sr.json(),ns=await nr.json(),a=await ar.json();
  if(s._error){backend.textContent='OFFLINE';backend.className='warn';statusLine.textContent='Backend unavailable: '+s._error;return}
  backend.textContent='ONLINE';backend.className='ok';nodeName.textContent=s.node_name||'OVN-002';sysNode.textContent=s.node_name||'—';
  visible.textContent=s.observed_networks??0;known.textContent=s.known_networks??0;protected.textContent=s.protected_filtered??0;scan.textContent='#'+(s.scan_number??0);
  lastScan.textContent=s.last_inventory_at?'Last '+new Date(s.last_inventory_at).toLocaleTimeString():'Waiting for observation';mode.textContent=(s.mode||'live').toUpperCase();uptime.textContent=duration(s.uptime_seconds);memory.textContent=(s.memory_percent??0)+'%';disk.textContent=(s.disk_percent??0)+'%';load.textContent=s.load_1m??'—';
  countdown=Number(s.scan_interval_seconds||10);next.textContent=countdown+'s';statusLine.textContent=s.last_inventory_error?('Observation warning: '+s.last_inventory_error):'Josh is online and standing watch.';
  nets.innerHTML=(ns||[]).map(x=>`<tr><td><b>${esc(x.ssid)}</b></td><td>${esc(x.channel)}</td><td>${esc(x.signal)}%<div class="sigbar"><i style="width:${Math.max(0,Math.min(100,Number(x.signal||0)))}%"></i></div></td><td>${esc(x.security)}</td></tr>`).join('')||'<tr><td colspan="4">No visible unprotected networks.</td></tr>';
  activity.innerHTML=(a||[]).slice(0,20).map(x=>`<div class="event ${esc(x.kind)}"><b>${esc(x.kind)}</b> ${esc(x.message)}<small>${esc(x.detail||'')} ${x.time?'• '+new Date(x.time).toLocaleTimeString():''}</small></div>`).join('')||'<div class="event"><b>IDLE</b> Waiting for activity...</div>';
 }catch(e){backend.textContent='OFFLINE';backend.className='warn';statusLine.textContent='UI refresh error: '+e}
}
refreshNow();setInterval(refreshNow,2000);setInterval(()=>{countdown=Math.max(0,countdown-1);next.textContent=countdown+'s'},1000);
</script></body></html>'''


@app.get("/")
def home():
    return render_template_string(HTML)


if __name__ == "__main__":
    print("Heimdall Project Odin UI starting on http://0.0.0.0:8081", flush=True)
    print("Backend expected at http://127.0.0.1:8080", flush=True)
    app.run(host="0.0.0.0", port=8081, debug=False, use_reloader=False)
