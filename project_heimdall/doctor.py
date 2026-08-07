#!/usr/bin/env python3
"""Heimdall field-readiness checks."""

from __future__ import annotations

import json
import shutil
import socket
import sqlite3
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG = HERE / "config.json"
DB = HERE / "data" / "heimdall.db"


def ok(msg): print(f"[ OK ] {msg}")
def warn(msg): print(f"[WARN] {msg}")
def fail(msg): print(f"[FAIL] {msg}")


def main() -> int:
    failures = 0
    print("Heimdall Doctor — field readiness\n")

    if sys.version_info >= (3, 9): ok(f"Python {sys.version.split()[0]}")
    else:
        fail(f"Python {sys.version.split()[0]} — 3.9+ recommended")
        failures += 1

    try:
        import flask  # noqa
        import psutil  # noqa
        ok("Python dependencies available")
    except Exception as exc:
        fail(f"Python dependency missing: {exc}")
        failures += 1

    nmcli = shutil.which("nmcli")
    if nmcli:
        ok(f"NetworkManager inventory interface: {nmcli}")
        try:
            result = subprocess.run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device"], capture_output=True, text=True, timeout=5)
            wifi = [x for x in result.stdout.splitlines() if ":wifi:" in x]
            if wifi:
                ok("Wi-Fi device found: " + ", ".join(wifi))
            else:
                warn("No Wi-Fi device reported by NetworkManager")
        except Exception as exc:
            warn(f"Could not query NetworkManager: {exc}")
    else:
        warn("nmcli not found — demo mode will work; live Wi-Fi inventory will not")

    if CONFIG.exists():
        try:
            cfg = json.loads(CONFIG.read_text())
            if cfg.get("authorized_scope") is True:
                ok("Authorized-scope switch enabled")
            else:
                fail("authorized_scope is not true; Heimdall will refuse live startup")
                failures += 1
            ok(f"Node: {cfg.get('node_name', 'unknown')} | Site: {cfg.get('site_name', 'unknown')}")
        except Exception as exc:
            fail(f"Config invalid: {exc}")
            failures += 1
    else:
        warn("config.json not created yet; copy config.example.json")

    try:
        sock = socket.socket()
        sock.settimeout(0.5)
        result = sock.connect_ex(("127.0.0.1", 8080))
        sock.close()
        if result == 0: ok("Dashboard port 8080 is currently open")
        else: warn("Dashboard port 8080 is not open (normal if Heimdall is stopped)")
    except Exception as exc:
        warn(f"Port check unavailable: {exc}")

    if DB.exists():
        try:
            with sqlite3.connect(DB) as conn:
                known = conn.execute("SELECT COUNT(*) FROM networks").fetchone()[0]
                alerts = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
            ok(f"Database readable — {known} known networks, {alerts} stored alerts")
        except Exception as exc:
            fail(f"Database error: {exc}")
            failures += 1
    else:
        warn("Database not created yet; it will be created on first start")

    print()
    if failures:
        print(f"Doctor result: {failures} blocking issue(s).")
        return 1
    print("Doctor result: READY (review warnings above).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
