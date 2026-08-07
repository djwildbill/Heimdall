#!/usr/bin/env python3
from __future__ import annotations
import json, os, shutil, subprocess, time, urllib.request
from pathlib import Path
from flask import Flask, jsonify, render_template_string

BASE=Path(__file__).resolve().parent
BACKEND='http://127.0.0.1:8080'
CONFIG=BASE/'config.json'
app=Flask(__name__)

def backend(path):
    try:
        with urllib.request.urlopen(BACKEND+path,timeout=3) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {'_error':str(e)}

def cmd(args):
    try:return subprocess.run(args,capture_output=True,text=True,timeout=4).stdout.strip()
    except Exception as e:return str(e)

def service(name):
    return cmd(['systemctl','is-active',name]) or 'unknown'

@app.get('/api/status')
def status(): return jsonify(backend('/api/status'))
@app.get('/api/networks')
def networks():
    d=backend('/api/networks'); return jsonify([] if isinstance(d,dict) and d.get('_error') else d)
@app.get('/api/activity')
def activity():
    d=backend('/api/activity'); return jsonify([] if isinstance(d,dict) and d.get('_error') else d)
@app.get('/api/system')
def system():
    total,used,_=shutil.disk_usage(BASE)
    mem={}
    try:
        for line in Path('/proc/meminfo').read_text().splitlines():
            k,v=line.split(':',1); mem[k]=int(v.strip().split()[0])
        mp=round((1-mem.get('MemAvailable',0)/mem['MemTotal'])*100,1)
    except Exception: mp=0
    return jsonify({'hostname':os.uname().nodename,'kernel':os.uname().release,'arch':os.uname().machine,'load_1m':round(os.getloadavg()[0],2),'memory_percent':mp,'storage_percent':round(used/total*100,1),'backend_service':service('heimdall.service'),'ui_service':service('heimdall-ui.service'),'ssh_service':service('ssh.service')})
@app.get('/api/logs')
def logs():
    a=cmd(['journalctl','-u','heimdall.service','-n','60','--no-pager','-o','short-iso'])
    b=cmd(['journalctl','-u','heimdall-ui.service','-n','40','--no-pager','-o','short-iso'])
    return jsonify({'heimdall':a.splitlines(),'ui':b.splitlines()})
@app.get('/api/settings')
def settings():
    try:d=json.loads(CONFIG.read_text())
    except Exception:d={}
    safe={k:v for k,v in d.items() if k not in {'protected_networks','protected_bssids'}}
    safe['protected_networks_count']=len(d.get('protected_networks',[])); safe['protected_bssids_count']=len(d.get('protected_bssids',[]))
    return jsonify(safe)

HTML=r'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Project Odin — Heimdall</title><style>
:root{--bg:#020814;--p:#07182f;--p2:#0a2142;--line:#1765aa;--cyan:#36d8ff;--blue:#178fff;--green:#20f18a;--text:#ecf7ff;--muted:#86accb;--warn:#ffb947;--bad:#ff5873}*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 50% -10%,#123c72,#06152c 30%,#020814 70%);color:var(--text);font-family:Segoe UI,Arial,sans-serif;min-height:100vh}.wrap{max-width:1500px;margin:auto;padding:18px}.top{display:flex;justify-content:space-between;gap:20px;align-items:center}.brand{display:flex;gap:14px;align-items:center}.seal{width:58px;height:58px;border:2px solid var(--blue);border-radius:50%;display:grid;place-items:center;color:var(--cyan);font-size:28px;box-shadow:0 0 20px #178fff55}.brand h1{margin:0;letter-spacing:4px}.brand small{color:#7fcfff;letter-spacing:2px}.id b{font:700 22px Consolas}.online{border:1px solid var(--green);color:var(--green);padding:10px 16px;border-radius:14px;margin-left:15px}.nav{display:grid;grid-template-columns:repeat(6,1fr);margin:16px 0;border:1px solid var(--line);border-radius:12px;overflow:hidden}.nav button{border:0;border-right:1px solid #15436f;background:#07172b;color:#b9d5ea;padding:14px;font-weight:700;cursor:pointer}.nav button.active{background:linear-gradient(#0a559d,#07315f);color:#fff;box-shadow:inset 0 0 0 1px #2ebcff}.metrics{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}.card,.panel{background:linear-gradient(145deg,#081b35ee,#061126ee);border:1px solid #1f619e;border-radius:12px;box-shadow:inset 0 0 24px #0d315533}.card{padding:14px}.lab{font-size:10px;color:#93b7d2;text-transform:uppercase}.val{font-size:25px;font-weight:800;color:var(--cyan);margin-top:5px}.sub{font-size:10px;color:var(--muted)}.view{display:none;margin-top:12px}.view.active{display:block}.grid{display:grid;grid-template-columns:2fr 1fr;gap:12px}.panel{padding:15px}.title{font-weight:800;letter-spacing:1px;margin-bottom:10px}.activity{max-height:560px;overflow:auto}.event{padding:9px;margin:6px 0;background:#071a31;border-left:3px solid var(--cyan);border-radius:4px}.event small{display:block;color:var(--muted);margin-top:3px}.event.ERROR{border-color:var(--bad)}.event.PRIVACY{border-color:#a86cff}.event.CHANGE{border-color:var(--warn)}table{width:100%;border-collapse:collapse}th,td{padding:9px;border-bottom:1px solid #123452;text-align:left;font-size:12px}th{color:#8fb9d6;text-transform:uppercase;font-size:10px}.rows{display:grid;grid-template-columns:160px 1fr;gap:8px}.rows div{padding:7px;border-bottom:1px solid #123452;font-size:12px}.rows div:nth-child(odd){color:#88aec9}.log{font:12px Consolas,monospace;white-space:pre-wrap;background:#020914;padding:12px;border-radius:8px;max-height:520px;overflow:auto;color:#bfe8ff}.settings{font:13px Consolas,monospace;white-space:pre-wrap}.statusbox{margin-top:12px;padding:14px;border:1px solid #1b68aa;border-radius:12px;background:linear-gradient(90deg,#082142,#06152d);color:var(--green);font-weight:700}.actions{display:flex;gap:8px;flex-wrap:wrap}.actions button{background:#08264c;border:1px solid #1c73ba;border-radius:9px;color:#e6f7ff;padding:10px 14px;cursor:pointer}@media(max-width:900px){.metrics{grid-template-columns:repeat(2,1fr)}.grid{grid-template-columns:1fr}.nav{grid-template-columns:repeat(3,1fr)}}@media(max-width:550px){.metrics{grid-template-columns:1fr}.top{display:block}.nav{grid-template-columns:repeat(2,1fr)}}
</style></head><body><div class="wrap"><div class="top"><div class="brand"><div class="seal">ᛟ</div><div><h1>PROJECT ODIN</h1><small>HEIMDALL NODE CONTROL CENTER</small></div></div><div class="id"><b id="node">OVN-002</b><span class="online">● ONLINE</span></div></div>
<div class="nav"><button class="active" data-v="overview">⌂ OVERVIEW</button><button data-v="activity">⚡ ACTIVITY</button><button data-v="wireless">◉ WIRELESS</button><button data-v="system">▣ SYSTEM</button><button data-v="logs">≡ LOGS</button><button data-v="settings">⚙ SETTINGS</button></div>
<div class="metrics"><div class="card"><div class="lab">Visible Networks</div><div class="val" id="visible">—</div><div class="sub">Current observation</div></div><div class="card"><div class="lab">Known Networks</div><div class="val" id="known">—</div><div class="sub">Local memory</div></div><div class="card"><div class="lab">Protected</div><div class="val" id="protected">—</div><div class="sub">Privacy filtered</div></div><div class="card"><div class="lab">Scan Cycle</div><div class="val" id="scan">#—</div><div class="sub" id="last">Waiting</div></div><div class="card"><div class="lab">Next Cycle</div><div class="val" id="next">10s</div><div class="sub">Automatic observation</div></div></div>
<div class="statusbox" id="statusline">Josh is online and standing watch.</div>
<section id="overview" class="view active"><div class="grid"><div class="panel"><div class="title">WIRELESS INVENTORY</div><table><thead><tr><th>SSID</th><th>CH</th><th>Signal</th><th>Security</th></tr></thead><tbody id="overviewNets"></tbody></table></div><div class="panel"><div class="title">JOSH ACTIVITY</div><div id="overviewAct" class="activity"></div></div></div></section>
<section id="activity" class="view"><div class="panel"><div class="title">LIVE ACTIVITY STREAM</div><div id="fullAct" class="activity"></div></div></section>
<section id="wireless" class="view"><div class="panel"><div class="title">WIRELESS OBSERVATION</div><table><thead><tr><th>SSID</th><th>BSSID</th><th>Channel</th><th>Frequency</th><th>Signal</th><th>Security</th><th>Observed</th></tr></thead><tbody id="fullNets"></tbody></table></div></section>
<section id="system" class="view"><div class="grid"><div class="panel"><div class="title">SYSTEM INFORMATION</div><div class="rows" id="sysrows"></div></div><div class="panel"><div class="title">SERVICE HEALTH</div><div class="rows" id="services"></div></div></div></section>
<section id="logs" class="view"><div class="grid"><div class="panel"><div class="title">HEIMDALL SERVICE LOG</div><div class="log" id="hlog"></div></div><div class="panel"><div class="title">UI SERVICE LOG</div><div class="log" id="ulog"></div></div></div></section>
<section id="settings" class="view"><div class="grid"><div class="panel"><div class="title">PRIVACY-SAFE SETTINGS</div><div class="settings" id="settingsText"></div></div><div class="panel"><div class="title">QUICK ACTIONS</div><div class="actions"><button onclick="refreshAll()">↻ Refresh</button><button onclick="window.open('/api/status','_blank')">Raw Status</button><button onclick="window.open('/api/activity','_blank')">Activity JSON</button><button onclick="window.open('/api/networks','_blank')">Network JSON</button></div><p class="sub">Protected SSID/BSSID values are never displayed here.</p></div></div></section>
</div><script>
const qs=s=>document.querySelector(s),qsa=s=>[...document.querySelectorAll(s)];function esc(v){return String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}function evt(a){return a.map(x=>`<div class="event ${esc(x.kind)}"><b>${esc(x.kind)}</b> ${esc(x.message)}<small>${esc(x.detail||'')} • ${esc(x.time)}</small></div>`).join('')||'<div class="sub">No activity yet.</div>'}function nets(ns,full=false){return ns.map(n=>full?`<tr><td>${esc(n.ssid)}</td><td>${esc(n.bssid)}</td><td>${esc(n.channel)}</td><td>${esc(n.frequency)}</td><td>${esc(n.signal)}%</td><td>${esc(n.security)}</td><td>${esc(n.observed_at)}</td></tr>`:`<tr><td>${esc(n.ssid)}</td><td>${esc(n.channel)}</td><td>${esc(n.signal)}%</td><td>${esc(n.security)}</td></tr>`).join('')||'<tr><td colspan="7">No visible networks.</td></tr>'}
qsa('.nav button').forEach(b=>b.onclick=()=>{qsa('.nav button').forEach(x=>x.classList.remove('active'));qsa('.view').forEach(x=>x.classList.remove('active'));b.classList.add('active');qs('#'+b.dataset.v).classList.add('active');if(b.dataset.v==='logs')loadLogs();if(b.dataset.v==='system')loadSystem();if(b.dataset.v==='settings')loadSettings()});
async function loadSystem(){let s=await (await fetch('/api/system')).json();sysrows.innerHTML=Object.entries(s).filter(([k])=>!k.endsWith('_service')).map(([k,v])=>`<div>${esc(k.replaceAll('_',' '))}</div><div>${esc(v)}</div>`).join('');services.innerHTML=['backend_service','ui_service','ssh_service'].map(k=>`<div>${esc(k.replace('_service',''))}</div><div>${esc(s[k])}</div>`).join('')}
async function loadLogs(){let l=await(await fetch('/api/logs')).json();hlog.textContent=(l.heimdall||[]).join('\n');ulog.textContent=(l.ui||[]).join('\n')}
async function loadSettings(){let s=await(await fetch('/api/settings')).json();settingsText.textContent=JSON.stringify(s,null,2)}
async function refreshAll(){try{let [s,ns,a]=await Promise.all([fetch('/api/status').then(r=>r.json()),fetch('/api/networks').then(r=>r.json()),fetch('/api/activity').then(r=>r.json())]);if(s._error){statusline.textContent='Backend unavailable: '+s._error;return}node.textContent=s.node_name||'OVN-002';visible.textContent=s.observed_networks??0;known.textContent=s.known_networks??0;protected.textContent=s.protected_filtered??0;scan.textContent='#'+(s.scan_number??0);next.textContent=(s.scan_interval_seconds??10)+'s';last.textContent=s.last_inventory_at?new Date(s.last_inventory_at).toLocaleTimeString():'Waiting';statusline.textContent=s.last_inventory_error?'Observation warning: '+s.last_inventory_error:'Josh is online and standing watch.';overviewNets.innerHTML=nets(ns);fullNets.innerHTML=nets(ns,true);overviewAct.innerHTML=evt(a.slice(0,14));fullAct.innerHTML=evt(a)}catch(e){statusline.textContent='UI refresh error: '+e}}
refreshAll();setInterval(refreshAll,2000);
</script></body></html>'''

@app.get('/')
def home(): return render_template_string(HTML)

if __name__=='__main__': app.run(host='0.0.0.0',port=8081,debug=False,use_reloader=False)
