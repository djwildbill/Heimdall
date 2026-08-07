#!/usr/bin/env python3
from __future__ import annotations
import getpass, json, secrets
from pathlib import Path
from werkzeug.security import generate_password_hash

BASE=Path(__file__).resolve().parent
OUT=BASE/'maintenance_auth.json'

p1=getpass.getpass('Set Heimdall maintenance password: ')
p2=getpass.getpass('Confirm maintenance password: ')
if not p1:
    raise SystemExit('Password cannot be empty.')
if p1 != p2:
    raise SystemExit('Passwords did not match.')
if len(p1) < 8:
    raise SystemExit('Use at least 8 characters.')

data={'password_hash':generate_password_hash(p1),'session_secret':secrets.token_hex(32)}
OUT.write_text(json.dumps(data,indent=2),encoding='utf-8')
OUT.chmod(0o600)
print(f'Maintenance password configured locally: {OUT}')
