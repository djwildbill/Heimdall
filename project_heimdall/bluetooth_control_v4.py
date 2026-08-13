#!/usr/bin/env python3
from __future__ import annotations

import json
import urllib.error
import urllib.request

import bluetooth_control as legacy

HEIMDALL = 'http://127.0.0.1:8080'
_old_handle = legacy.handle


def get_json(path: str, timeout: int = 15):
    req = urllib.request.Request(HEIMDALL + path, method='GET')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode('utf-8') or '{}')
    except urllib.error.HTTPError as exc:
        return {'ok': False, 'error': f'Heimdall HTTP {exc.code}'}
    except Exception as exc:
        return {'ok': False, 'error': f'Heimdall inventory unavailable: {exc}'}


def handle(req):
    cmd = str(req.get('cmd', '')).strip().lower()

    if cmd in {'wifi-status', 'scan-status'}:
        data = get_json('/api/status')
        return {'ok': True, 'wifi': data} if not (isinstance(data, dict) and data.get('ok') is False) else data

    if cmd in {'wifi-networks', 'networks'}:
        data = get_json('/api/networks')
        if not isinstance(data, list):
            return data if isinstance(data, dict) else {'ok': False, 'error': 'wireless inventory unavailable'}
        return {'ok': True, 'count': len(data), 'networks': data[:60]}

    if cmd in {'wifi-activity', 'activity'}:
        data = get_json('/api/activity')
        if not isinstance(data, list):
            return data if isinstance(data, dict) else {'ok': False, 'error': 'wireless activity unavailable'}
        return {'ok': True, 'count': len(data), 'activity': data[:40]}

    if cmd in {'wifi-dashboard', 'dashboard'}:
        status_data = get_json('/api/status')
        networks = get_json('/api/networks')
        activity = get_json('/api/activity')
        if isinstance(status_data, dict) and status_data.get('ok') is False:
            return status_data
        return {
            'ok': True,
            'node': 'OVN-002',
            'codename': 'Josh',
            'wifi': status_data,
            'networks': networks[:40] if isinstance(networks, list) else [],
            'activity': activity[:20] if isinstance(activity, list) else [],
        }

    return _old_handle(req)


legacy.handle = handle

if __name__ == '__main__':
    legacy.main()
