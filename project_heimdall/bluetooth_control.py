#!/usr/bin/env python3
from __future__ import annotations

import json
import socket
import subprocess
import threading
import time
from pathlib import Path

from werkzeug.security import check_password_hash

BASE = Path(__file__).resolve().parent
AUTH_FILE = BASE / 'maintenance_auth.json'
RADIO_HELPER = '/usr/local/sbin/heimdall-radio-control'
RECOVERY_HELPER = '/usr/local/sbin/heimdall-recovery'
MAINT_HELPER = '/usr/local/sbin/heimdall-maintenance'
CHANNEL = 22
MAX_LINE = 8192
BDADDR_ANY = '00:00:00:00:00:00'


def run(args, *, input_text=None, timeout=70):
    p = subprocess.run(args, input=input_text, capture_output=True, text=True, timeout=timeout)
    out = ((p.stdout or '') + ('\n' + p.stderr if p.stderr else '')).strip()
    return p.returncode, out


def load_auth():
    try:
        return json.loads(AUTH_FILE.read_text(encoding='utf-8')) if AUTH_FILE.exists() else {}
    except Exception:
        return {}


def valid_password(password):
    h = load_auth().get('password_hash')
    return bool(h and check_password_hash(h, password or ''))


def json_from_command(args):
    code, out = run(args)
    if code:
        return {'ok': False, 'error': out or 'command failed'}
    try:
        data = json.loads(out or '{}')
        if isinstance(data, dict):
            data.setdefault('ok', True)
        return data
    except Exception:
        return {'ok': True, 'output': out}


def status():
    radio = json_from_command(['sudo', RADIO_HELPER, 'status'])
    recovery = json_from_command(['sudo', RECOVERY_HELPER, 'status'])
    code, host = run(['hostname'])
    return {
        'ok': True,
        'node': 'OVN-002',
        'codename': 'Josh',
        'hostname': host if code == 0 else 'Ovn-002',
        'bluetooth_control': True,
        'radio': radio,
        'recovery': recovery,
        'time': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
    }


def handle(req):
    cmd = str(req.get('cmd', '')).strip().lower()
    if cmd in {'ping', 'status'}:
        return status()
    if cmd == 'radio-status':
        return json_from_command(['sudo', RADIO_HELPER, 'status'])
    if cmd == 'recovery-status':
        return json_from_command(['sudo', RECOVERY_HELPER, 'status'])
    if cmd == 'doctor':
        code, out = run(['sudo', MAINT_HELPER, 'doctor'])
        return {'ok': code == 0, 'output': out}
    if cmd == 'check-update':
        code, out = run(['sudo', MAINT_HELPER, 'check-update'])
        return {'ok': code == 0, 'output': out}

    # Everything below changes Josh and therefore requires the local
    # maintenance password. Pairing alone is not treated as authorization.
    if not valid_password(str(req.get('password', ''))):
        return {'ok': False, 'error': 'maintenance authentication required'}

    if cmd == 'set-mode':
        mode = str(req.get('mode', '')).strip().lower()
        if mode not in {'connected', 'survey', 'field'}:
            return {'ok': False, 'error': 'mode must be connected, survey, or field'}
        code, out = run(['sudo', RADIO_HELPER, mode])
        return {'ok': code == 0, 'mode': mode, 'output': out}
    if cmd == 'recovery-start':
        code, out = run(['sudo', RECOVERY_HELPER, 'start'])
        return {'ok': code == 0, 'output': out}
    if cmd == 'recovery-stop':
        code, out = run(['sudo', RECOVERY_HELPER, 'stop'])
        return {'ok': code == 0, 'output': out}
    if cmd == 'connect-saved':
        profile = str(req.get('profile', '')).strip()
        if not profile:
            return {'ok': False, 'error': 'profile required'}
        code, out = run(['sudo', RECOVERY_HELPER, 'connect-saved', profile])
        return {'ok': code == 0, 'output': out}
    if cmd == 'connect-new':
        ssid = str(req.get('ssid', '')).strip()
        wifi_password = str(req.get('wifi_password', ''))
        if not ssid:
            return {'ok': False, 'error': 'ssid required'}
        code, out = run(['sudo', RECOVERY_HELPER, 'connect-new', ssid], input_text=wifi_password + '\n')
        return {'ok': code == 0, 'output': out}
    if cmd == 'backup':
        code, out = run(['sudo', MAINT_HELPER, 'backup'])
        return {'ok': code == 0, 'output': out}

    return {'ok': False, 'error': 'unknown command'}


def client_loop(conn, addr):
    conn.settimeout(120)
    buf = b''
    try:
        conn.sendall((json.dumps({'ok': True, 'hello': 'Project Odin Heimdall', 'node': 'OVN-002', 'codename': 'Josh', 'protocol': 1}) + '\n').encode())
        while True:
            chunk = conn.recv(1024)
            if not chunk:
                return
            buf += chunk
            if len(buf) > MAX_LINE:
                conn.sendall(b'{"ok":false,"error":"request too large"}\n')
                return
            while b'\n' in buf:
                raw, buf = buf.split(b'\n', 1)
                if not raw.strip():
                    continue
                try:
                    req = json.loads(raw.decode('utf-8'))
                    if not isinstance(req, dict):
                        raise ValueError('request must be an object')
                    res = handle(req)
                except Exception as exc:
                    res = {'ok': False, 'error': str(exc)}
                conn.sendall((json.dumps(res, separators=(',', ':')) + '\n').encode('utf-8'))
    except (ConnectionError, TimeoutError, socket.timeout):
        return
    finally:
        try:
            conn.close()
        except Exception:
            pass


def main():
    if not hasattr(socket, 'AF_BLUETOOTH'):
        raise SystemExit('Python Bluetooth socket support is unavailable on this platform')
    server = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Python's stdlib Bluetooth socket requires an explicit Bluetooth address
    # on this Raspberry Pi build; an empty string raises "bad bluetooth address".
    server.bind((BDADDR_ANY, CHANNEL))
    server.listen(2)
    print(f'Heimdall Bluetooth control listening on RFCOMM channel {CHANNEL}', flush=True)
    while True:
        conn, addr = server.accept()
        threading.Thread(target=client_loop, args=(conn, addr), daemon=True).start()


if __name__ == '__main__':
    main()
