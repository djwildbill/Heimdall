#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, time
from pathlib import Path

BASE=Path(__file__).resolve().parent
STATE=BASE/'radio_mode.json'
DEFAULT={'mode':'connected','management_interface':'wlan0','observation_interface':'wlan1','updated_at':None,'last_error':None}


def run(args):
    p=subprocess.run(args,capture_output=True,text=True,timeout=10)
    return p.returncode,(p.stdout or '').strip(),(p.stderr or '').strip()

def interfaces():
    code,out,err=run(['iw','dev'])
    if code!=0:return []
    names=[]
    for line in out.splitlines():
        line=line.strip()
        if line.startswith('Interface '):names.append(line.split(None,1)[1])
    return names

def load_state():
    if STATE.exists():
        try:
            d=json.loads(STATE.read_text())
            x=DEFAULT.copy(); x.update(d); return x
        except Exception: pass
    return DEFAULT.copy()

def save_state(d):
    d['updated_at']=time.strftime('%Y-%m-%dT%H:%M:%S%z')
    STATE.write_text(json.dumps(d,indent=2))

def set_mode(mode:str):
    mode=mode.lower().strip()
    if mode not in {'connected','survey','field'}:
        raise ValueError('mode must be connected, survey, or field')
    s=load_state(); present=interfaces(); mg=s['management_interface']; obs=s['observation_interface']
    if mg not in present:
        s['last_error']=f'management interface {mg} not present'; save_state(s); return False,s['last_error']
    if mode=='survey' and obs not in present:
        s['last_error']=f'survey requires separate observation interface {obs}; refusing to repurpose {mg}'
        save_state(s); return False,s['last_error']
    # Mode state only in this first release. The scanner reads this state and chooses behavior.
    # We intentionally do not disconnect wlan0 or alter interface type here.
    s['mode']=mode; s['last_error']=None; save_state(s); return True,mode

def main():
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument('mode',nargs='?',choices=['connected','survey','field'])
    ap.add_argument('--status',action='store_true')
    a=ap.parse_args()
    if a.status or not a.mode:
        print(json.dumps(load_state(),indent=2)); return
    ok,msg=set_mode(a.mode); print(msg); raise SystemExit(0 if ok else 2)

if __name__=='__main__': main()
