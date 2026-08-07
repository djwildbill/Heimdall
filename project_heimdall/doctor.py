#!/usr/bin/env python3
import importlib.util, json, shutil, socket, sys
from pathlib import Path
base=Path(__file__).resolve().parent
fails=0
print('Heimdall Doctor — field readiness\n')
def check(ok,msg):
 global fails
 print(('[ OK ] ' if ok else '[FAIL] ')+msg)
 if not ok:fails+=1
check(sys.version_info >= (3,10), f'Python {sys.version.split()[0]}')
check(importlib.util.find_spec('flask') is not None,'Flask installed')
check(shutil.which('nmcli') is not None,'NetworkManager inventory interface available')
if shutil.which('nmcli'):
 import subprocess
 p=subprocess.run(['nmcli','-t','-f','DEVICE,TYPE,STATE','device'],capture_output=True,text=True)
 wifi=[x for x in p.stdout.splitlines() if ':wifi:' in x]
 check(bool(wifi),'Wi-Fi device found'+((' — '+', '.join(wifi)) if wifi else ''))
config=base/'config.json'
if config.exists():
 try:
  d=json.loads(config.read_text()); check(bool(d.get('authorized_scope')),'authorized_scope enabled'); print(f"[ OK ] Scan interval: {d.get('scan_interval_seconds',10)}s"); print(f"[ OK ] Privacy mode: {bool(d.get('privacy_mode',True))}")
 except Exception as e: check(False,f'config.json invalid: {e}')
else: print('[WARN] config.json missing; installer/first start will create it')
print('\nDoctor result:', 'READY' if fails==0 else f'{fails} blocking issue(s)')
raise SystemExit(0 if fails==0 else 1)
