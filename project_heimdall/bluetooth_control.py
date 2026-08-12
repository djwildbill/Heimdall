#!/usr/bin/env python3
from __future__ import annotations

import json
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request

CHANNEL = 22
MAX_LINE = 8192
BDADDR_ANY = '00:00:00:00:00:00'
BRIDGE = 'http://127.0.0.1:8090'


def run(args, *, timeout=20):
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    out = ((p.stdout or '') + ('\n' + p.stderr if p.stderr else '')).strip()
    return p.returncode, out


def http_json(method, path, body=None, timeout=120):
    data = None if body is None else json.dumps(body).encode('utf-8')
    req = urllib.request.Request(BRIDGE + path, data=data, method=method, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode('utf-8')
            return json.loads(raw or '{}')
    except urllib.error.HTTPError as exc:
        try:
            raw = exc.read().decode('utf-8')
            return json.loads(raw or '{}')
        except Exception:
            return {'ok': False, 'error': f'bridge HTTP {exc.code}'}
    except Exception as exc:
        return {'ok': False, 'error': f'control bridge unavailable: {exc}'}


def status():
    radio = http_json('GET', '/api/control/radio/status')
    recovery = http_json('GET', '/api/control/recovery/status')
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
        return http_json('GET', '/api/control/radio/status')
    if cmd == 'recovery-status':
        return http_json('GET', '/api/control/recovery/status')
    if cmd == 'doctor':
        return http_json('POST', '/api/maintenance/action/doctor', {})
    if cmd == 'check-update':
        return http_json('POST', '/api/maintenance/action/check-update', {})

    password = str(req.get('password', ''))

    if cmd in {'update', 'apply-update'}:
        return http_json('POST', '/api/control/maintenance/update', {'password': password}, timeout=20)
    if cmd == 'restart-ui':
        return http_json('POST', '/api/control/ui/restart', {'password': password})
    if cmd == 'set-mode':
        mode = str(req.get('mode', '')).strip().lower()
        if mode not in {'connected', 'survey', 'field'}:
            return {'ok': False, 'error': 'mode must be connected, survey, or field'}
        return http_json('POST', '/api/control/radio/mode', {'mode': mode, 'password': password})
    if cmd == 'recovery-start':
        return http_json('POST', '/api/control/recovery/action', {'action': 'start', 'password': password})
    if cmd == 'recovery-stop':
        return http_json('POST', '/api/control/recovery/action', {'action': 'stop', 'password': password})
    if cmd == 'connect-saved':
        profile = str(req.get('profile', '')).strip()
        if not profile:
            return {'ok': False, 'error': 'profile required'}
        return http_json('POST', '/api/control/recovery/action', {'action': 'connect-saved', 'profile': profile, 'password': password})
    if cmd == 'connect-new':
        ssid = str(req.get('ssid', '')).strip()
        wifi_password = str(req.get('wifi_password', ''))
        if not ssid:
            return {'ok': False, 'error': 'ssid required'}
        return http_json('POST', '/api/control/recovery/action', {'action': 'connect-new', 'ssid': ssid, 'wifi_password': wifi_password, 'password': password})
    if cmd == 'backup':
        return {'ok': False, 'error': 'backup over Bluetooth is not enabled yet'}

    return {'ok': False, 'error': 'unknown command'}


def client_loop(conn, addr):
    conn.settimeout(120)
    buf = b''
    try:
        conn.sendall((json.dumps({'ok': True, 'hello': 'Project Odin Heimdall', 'node': 'OVN-002', 'codename': 'Josh', 'protocol': 3}) + '\n').encode())
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
        try: conn.close()
        except Exception: pass


def main():
    if not hasattr(socket, 'AF_BLUETOOTH'):
        raise SystemExit('Python Bluetooth socket support is unavailable on this platform')
    server = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((BDADDR_ANY, CHANNEL))
    server.listen(2)
    print(f'Heimdall Bluetooth control listening on RFCOMM channel {CHANNEL}', flush=True)
    while True:
        conn, addr = server.accept()
        threading.Thread(target=client_loop, args=(conn, addr), daemon=True).start()


if __name__ == '__main__':
    main()
