#!/usr/bin/env python3
from __future__ import annotations
import json, secrets, subprocess, time
from pathlib import Path
from flask import Flask, jsonify, request, session
from werkzeug.security import check_password_hash

BASE=Path(__file__).resolve().parent
AUTH_FILE=BASE/'maintenance_auth.json'
HELPER='/usr/local/sbin/heimdall-maintenance'
SESSION_MINUTES=15
ALLOWED={'doctor','restart-backend','restart-ui','repair-db','check-update','apply-update','backup','reboot','shutdown'}
READ_ONLY={'doctor','check-update'}

app=Flask(__name__)
app.config.update(SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Strict',PERMANENT_SESSION_LIFETIME=SESSION_MINUTES*60)

def load_auth():
    try:return json.loads(AUTH_FILE.read_text(encoding='utf-8')) if AUTH_FILE.exists() else {}
    except Exception:return {}
app.secret_key=load_auth().get('session_secret') or secrets.token_hex(32)
def configured():return bool(load_auth().get('password_hash'))
def valid_password(p):
    h=load_auth().get('password_hash');return bool(h and check_password_hash(h,p or ''))
def authed():return bool(session.get('maintenance_authenticated')) and time.time()-float(session.get('authenticated_at',0))<=SESSION_MINUTES*60

def run_helper(action):
    if action not in ALLOWED:return 'Action not allowed',400
    try:
        p=subprocess.run(['sudo',HELPER,action],capture_output=True,text=True,timeout=120)
        out=((p.stdout or '')+('\n'+p.stderr if p.stderr else '')).strip()
        return out or f'{action}: completed',(200 if p.returncode==0 else 500)
    except subprocess.TimeoutExpired:return f'{action}: timed out',504
    except Exception as e:return str(e),500

@app.get('/api/maintenance/status')
def status():return jsonify({'configured':configured(),'authenticated':authed(),'session_minutes':SESSION_MINUTES,'read_only_without_password':sorted(READ_ONLY)})
@app.post('/api/maintenance/login')
def login():
    body=request.get_json(silent=True) or {};pw=str(body.get('password',''))
    if not configured():return jsonify({'ok':False,'error':'Maintenance password has not been configured.'}),503
    if not valid_password(pw):time.sleep(.5);return jsonify({'ok':False,'error':'Invalid maintenance password.'}),401
    session.permanent=True;session['maintenance_authenticated']=True;session['authenticated_at']=time.time()
    return jsonify({'ok':True,'expires_minutes':SESSION_MINUTES})
@app.post('/api/maintenance/logout')
def logout():session.clear();return jsonify({'ok':True})
@app.post('/api/maintenance/action/<action>')
def action(action):
    if action not in ALLOWED:return jsonify({'ok':False,'error':'Action not allowed.'}),400
    if action not in READ_ONLY and not authed():return jsonify({'ok':False,'error':'Maintenance authentication required.'}),401
    if action in {'reboot','shutdown'}:
        body=request.get_json(silent=True) or {};pw=str(body.get('password',''));confirm=str(body.get('confirm','')).strip().upper();need=action.upper()
        if not valid_password(pw):return jsonify({'ok':False,'error':'Password confirmation required for node power action.'}),401
        if confirm!=need:return jsonify({'ok':False,'error':f'Type {need} to confirm this action.'}),400
    out,code=run_helper(action);return jsonify({'ok':code==200,'action':action,'output':out}),code
if __name__=='__main__':app.run(host='127.0.0.1',port=8090,debug=False,use_reloader=False)
