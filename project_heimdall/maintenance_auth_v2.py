#!/usr/bin/env python3
from __future__ import annotations
import json, secrets, subprocess, time
from pathlib import Path
from flask import Flask, jsonify, request, session
from werkzeug.security import check_password_hash

BASE=Path(__file__).resolve().parent
AUTH_FILE=BASE/'maintenance_auth.json'
HELPER='/usr/local/sbin/heimdall-maintenance'
RADIO_HELPER='/usr/local/sbin/heimdall-radio-control'
RECOVERY_HELPER='/usr/local/sbin/heimdall-recovery'
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

def run_cmd(args,input_text=None,timeout=120):
    try:
        p=subprocess.run(args,input=input_text,capture_output=True,text=True,timeout=timeout)
        out=((p.stdout or '')+('\n'+p.stderr if p.stderr else '')).strip()
        return p.returncode,out
    except subprocess.TimeoutExpired:return 124,'command timed out'
    except Exception as e:return 125,str(e)

def run_helper(action):
    if action not in ALLOWED:return 'Action not allowed',400
    helper_action='apply-update-async' if action=='apply-update' else action
    code,out=run_cmd(['sudo',HELPER,helper_action])
    return out or f'{action}: completed',(200 if code==0 else 500)

def auth_from_body(body):
    pw=str((body or {}).get('password',''))
    return valid_password(pw)

def command_json(args,input_text=None):
    code,out=run_cmd(args,input_text=input_text)
    if code:return {'ok':False,'error':out or 'command failed'},500
    try:
        data=json.loads(out or '{}')
        if isinstance(data,dict):data.setdefault('ok',True)
        return data,200
    except Exception:return {'ok':True,'output':out},200

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
    out,code=run_helper(action)
    payload={'ok':code==200,'action':action,'output':out}
    if action=='apply-update' and code==200:
        payload['status']='update-started';payload['reconnect_required']=True
    return jsonify(payload),code

@app.get('/api/control/radio/status')
def control_radio_status():
    data,code=command_json(['sudo',RADIO_HELPER,'status']);return jsonify(data),code
@app.post('/api/control/radio/mode')
def control_radio_mode():
    body=request.get_json(silent=True) or {}
    if not auth_from_body(body):return jsonify({'ok':False,'error':'maintenance authentication required'}),401
    mode=str(body.get('mode','')).strip().lower()
    if mode not in {'connected','survey','field'}:return jsonify({'ok':False,'error':'mode must be connected, survey, or field'}),400
    data,code=command_json(['sudo',RADIO_HELPER,mode]);data['mode']=mode;return jsonify(data),code

@app.get('/api/control/recovery/status')
def control_recovery_status():
    data,code=command_json(['sudo',RECOVERY_HELPER,'status']);return jsonify(data),code
@app.post('/api/control/recovery/action')
def control_recovery_action():
    body=request.get_json(silent=True) or {}
    if not auth_from_body(body):return jsonify({'ok':False,'error':'maintenance authentication required'}),401
    action=str(body.get('action','')).strip().lower()
    if action in {'start','stop'}:
        data,code=command_json(['sudo',RECOVERY_HELPER,action]);return jsonify(data),code
    if action=='connect-saved':
        profile=str(body.get('profile','')).strip()
        if not profile:return jsonify({'ok':False,'error':'profile required'}),400
        data,code=command_json(['sudo',RECOVERY_HELPER,'connect-saved',profile]);return jsonify(data),code
    if action=='connect-new':
        ssid=str(body.get('ssid','')).strip();wifi_password=str(body.get('wifi_password',''))
        if not ssid:return jsonify({'ok':False,'error':'ssid required'}),400
        data,code=command_json(['sudo',RECOVERY_HELPER,'connect-new',ssid],input_text=wifi_password+'\n');return jsonify(data),code
    return jsonify({'ok':False,'error':'Action not allowed'}),400

@app.post('/api/control/ui/restart')
def control_ui_restart():
    body=request.get_json(silent=True) or {}
    if not auth_from_body(body):return jsonify({'ok':False,'error':'maintenance authentication required'}),401
    out,code=run_helper('restart-ui')
    return jsonify({'ok':code==200,'action':'restart-ui','output':out}),code

@app.post('/api/control/maintenance/update')
def control_maintenance_update():
    body=request.get_json(silent=True) or {}
    if not auth_from_body(body):return jsonify({'ok':False,'error':'maintenance authentication required'}),401
    out,code=run_cmd(['sudo',HELPER,'apply-update-async'])
    return jsonify({'ok':code==0,'action':'apply-update','status':'update-started' if code==0 else 'failed','reconnect_required':code==0,'output':out}), (200 if code==0 else 500)

if __name__=='__main__':app.run(host='127.0.0.1',port=8090,debug=False,use_reloader=False)
