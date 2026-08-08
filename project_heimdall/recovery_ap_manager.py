#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, secrets, subprocess, sys, time
from pathlib import Path

BASE=Path(__file__).resolve().parent
STATE=BASE/'recovery_ap.json'
PROFILE='JOSH-RECOVERY'
SSID='JOSH-RECOVERY'
IFACE='wlan0'
ADDR='10.42.0.1/24'

def run(args, timeout=25, input_text=None):
    p=subprocess.run(args,input=input_text,capture_output=True,text=True,timeout=timeout)
    return p.returncode,(p.stdout or '').strip(),(p.stderr or '').strip()
def state(extra=None):
    d={'profile':PROFILE,'ssid':SSID,'interface':IFACE,'portal':'http://10.42.0.1:8082','updated_at':time.strftime('%Y-%m-%dT%H:%M:%S%z')}
    if STATE.exists():
        try:d.update(json.loads(STATE.read_text(encoding='utf-8')))
        except Exception:pass
    if extra:d.update(extra)
    STATE.write_text(json.dumps(d,indent=2),encoding='utf-8')
    return d
def profile_exists(name):
    c,o,e=run(['nmcli','-t','-f','NAME','connection','show'])
    return c==0 and name in o.splitlines()
def ensure_recovery_profile():
    if profile_exists(PROFILE):return state()
    psk=secrets.token_urlsafe(12)[:16]
    c,o,e=run(['nmcli','connection','add','type','wifi','ifname',IFACE,'con-name',PROFILE,'ssid',SSID])
    if c:raise RuntimeError(e or o)
    for cmd in [
      ['nmcli','connection','modify',PROFILE,'802-11-wireless.mode','ap','802-11-wireless.band','bg','ipv4.method','shared','ipv4.addresses',ADDR,'ipv6.method','disabled'],
      ['nmcli','connection','modify',PROFILE,'wifi-sec.key-mgmt','wpa-psk','wifi-sec.psk',psk],
      ['nmcli','connection','modify',PROFILE,'connection.autoconnect','no']]:
        c,o,e=run(cmd)
        if c:raise RuntimeError(e or o)
    return state({'ap_key':psk,'active':False,'last_error':None})
def prepare():
    d=ensure_recovery_profile();print(json.dumps({'ssid':SSID,'ap_key':d.get('ap_key'),'portal':'http://10.42.0.1:8082'},indent=2))
def start_ap():
    ensure_recovery_profile();run(['nmcli','device','disconnect',IFACE])
    c,o,e=run(['nmcli','connection','up',PROFILE],timeout=35)
    if c:state({'active':False,'last_error':e or o});raise RuntimeError(e or o)
    state({'active':True,'last_error':None});print('JOSH recovery AP active')
def stop_ap():
    if profile_exists(PROFILE):run(['nmcli','connection','down',PROFILE])
    state({'active':False,'last_error':None});print('JOSH recovery AP stopped')
def saved_networks():
    c,o,e=run(['nmcli','-t','-f','NAME,TYPE','connection','show'])
    if c:return []
    out=[]
    for line in o.splitlines():
        if not line or ':' not in line:continue
        name,typ=line.rsplit(':',1)
        if typ in {'802-11-wireless','wifi'} and name!=PROFILE:out.append(name)
    return out
def connect_saved(name):
    if name not in saved_networks():raise RuntimeError('Saved Wi-Fi profile not found')
    stop_ap();c,o,e=run(['nmcli','connection','up',name,'ifname',IFACE],timeout=45)
    if c:start_ap();raise RuntimeError('Connection failed; recovery AP restored')
    state({'active':False,'connected_profile':name,'last_error':None});print('connected')
def connect_new(ssid,password):
    if not ssid:raise RuntimeError('SSID required')
    stop_ap();args=['nmcli','device','wifi','connect',ssid,'ifname',IFACE]
    if password:args += ['password',password]
    c,o,e=run(args,timeout=50)
    if c:start_ap();raise RuntimeError('Connection failed; recovery AP restored')
    state({'active':False,'connected_profile':ssid,'last_error':None});print('connected')
def status(show_key=False):
    d=state();d['saved_networks']=saved_networks()
    if not show_key:d.pop('ap_key',None)
    print(json.dumps(d,indent=2))
def main():
    ap=argparse.ArgumentParser();sp=ap.add_subparsers(dest='cmd',required=True)
    sp.add_parser('prepare');sp.add_parser('start');sp.add_parser('stop');sp.add_parser('status').add_argument('--show-key',action='store_true')
    p=sp.add_parser('connect-saved');p.add_argument('name')
    p=sp.add_parser('connect-new');p.add_argument('ssid');p.add_argument('--password-stdin',action='store_true')
    a=ap.parse_args()
    try:
        if a.cmd=='prepare':prepare()
        elif a.cmd=='start':start_ap()
        elif a.cmd=='stop':stop_ap()
        elif a.cmd=='status':status(a.show_key)
        elif a.cmd=='connect-saved':connect_saved(a.name)
        elif a.cmd=='connect-new':connect_new(a.ssid,sys.stdin.readline().rstrip('\n') if a.password_stdin else '')
    except Exception as exc:
        state({'last_error':str(exc)});print(str(exc),file=sys.stderr);raise SystemExit(2)
if __name__=='__main__':main()
