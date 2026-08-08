#!/usr/bin/env python3
from __future__ import annotations
import html, json, subprocess, urllib.request, urllib.error
from flask import Flask, jsonify, request, render_template_string

MAINT='http://127.0.0.1:8090'
HELPER='/usr/local/sbin/heimdall-recovery'
app=Flask(__name__)

PAGE='''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Josh Recovery</title><style>body{margin:0;background:#020915;color:#eef8ff;font-family:Segoe UI,Arial}.w{max-width:760px;margin:auto;padding:22px}.p{background:#07162b;border:1px solid #185b9c;border-radius:14px;padding:18px;margin:14px 0}h1{letter-spacing:3px}.muted{color:#89abc5}.good{color:#20ef88}.btn{background:#09264b;color:#fff;border:1px solid #1d72b8;border-radius:9px;padding:11px 14px;margin:5px;cursor:pointer}input,select{width:100%;padding:12px;margin:7px 0;background:#020914;color:#fff;border:1px solid #245c8b;border-radius:8px;box-sizing:border-box}.danger{border-color:#c73b52}.out{white-space:pre-wrap;font-family:Consolas,monospace;background:#020812;padding:12px;border-radius:8px;min-height:40px}</style></head><body><div class="w"><h1>PROJECT ODIN</h1><div class="muted">HEIMDALL / JOSH RECOVERY PORTAL</div><div class="p"><b>Recovery Network</b><div id="status" class="out">Loading...</div></div><div class="p"><b>Saved Wi-Fi</b><select id="saved"></select><input id="pw" type="password" placeholder="Maintenance password"><button class="btn" onclick="connectSaved()">Connect Saved Network</button></div><div class="p"><b>Add Wi-Fi Network</b><input id="ssid" placeholder="Network name (SSID)"><input id="wifiPw" type="password" placeholder="Wi-Fi password"><input id="adminPw" type="password" placeholder="Maintenance password"><button class="btn" onclick="connectNew()">Save & Connect</button></div><div class="p"><b>Recovery Controls</b><input id="ctlPw" type="password" placeholder="Maintenance password"><button class="btn" onclick="act('start')">Start JOSH Recovery AP</button><button class="btn danger" onclick="act('stop')">Stop Recovery AP</button><div id="result" class="out"></div></div></div><script>async function j(u,o){let r=await fetch(u,o);return await r.json()}async function load(){let d=await j('/api/recovery/status');status.textContent=JSON.stringify(d,null,2);saved.innerHTML=(d.saved_networks||[]).map(x=>'<option>'+x.replaceAll('&','&amp;').replaceAll('<','&lt;')+'</option>').join('')}async function post(body){let d=await j('/api/recovery/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});result.textContent=d.output||d.error||JSON.stringify(d);setTimeout(load,1000)}function act(a){post({action:a,password:ctlPw.value})}function connectSaved(){post({action:'connect-saved',profile:saved.value,password:pw.value})}function connectNew(){post({action:'connect-new',ssid:ssid.value,wifi_password:wifiPw.value,password:adminPw.value})}load()</script></body></html>'''

def helper(args,input_text=None):
    p=subprocess.run(['sudo',HELPER,*args],input=input_text,capture_output=True,text=True,timeout=65)
    return p.returncode,((p.stdout or '')+('\n'+p.stderr if p.stderr else '')).strip()

def maintenance_password_valid(password):
    data=json.dumps({'password':password}).encode()
    req=urllib.request.Request(MAINT+'/api/maintenance/login',data=data,headers={'Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=6) as r:return r.status==200
    except Exception:return False

@app.get('/')
def index():return render_template_string(PAGE)
@app.get('/api/recovery/status')
def status():
    c,o=helper(['status'])
    try:return jsonify(json.loads(o if o else '{}')), (200 if c==0 else 500)
    except Exception:return jsonify({'error':o or 'status failed'}),500
@app.post('/api/recovery/action')
def action():
    b=request.get_json(silent=True) or {};a=str(b.get('action',''));pw=str(b.get('password',''))
    if a not in {'start','stop','connect-saved','connect-new'}:return jsonify({'ok':False,'error':'Action not allowed'}),400
    if not maintenance_password_valid(pw):return jsonify({'ok':False,'error':'Invalid maintenance password'}),401
    if a in {'start','stop'}:args=[a];stdin=None
    elif a=='connect-saved':args=[a,str(b.get('profile',''))];stdin=None
    else:args=[a,str(b.get('ssid',''))];stdin=str(b.get('wifi_password',''))+'\n'
    c,o=helper(args,stdin)
    return jsonify({'ok':c==0,'output':o}), (200 if c==0 else 500)
if __name__=='__main__':app.run(host='0.0.0.0',port=8082,debug=False,use_reloader=False)
