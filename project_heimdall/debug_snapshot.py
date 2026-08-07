#!/usr/bin/env python3
"""Privacy-safe Heimdall developer snapshot.

Collects enough local state to debug Josh without exposing observed SSIDs/BSSIDs.
Safe to paste into a support/debug conversation after reviewing the output.
"""
from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
API = "http://127.0.0.1:8080"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run(cmd: list[str], timeout: int = 5) -> dict:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        return {
            "ok": p.returncode == 0,
            "returncode": p.returncode,
            "stdout": (p.stdout or "").strip(),
            "stderr": (p.stderr or "").strip(),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def get_json(path: str) -> tuple[bool, object]:
    try:
        with urllib.request.urlopen(API + path, timeout=3) as r:
            return True, json.loads(r.read().decode("utf-8"))
    except Exception as exc:
        return False, str(exc)


def safe_activity(items: object) -> list[dict]:
    if not isinstance(items, list):
        return []
    out = []
    for item in items[:20]:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind", "UNKNOWN"))
        safe = {"time": item.get("time"), "kind": kind}
        # NEW/CHANGE messages may contain SSIDs. Only retain event type.
        if kind in {"NEW", "CHANGE"}:
            safe["message"] = "wireless identifier redacted"
        elif kind == "PRIVACY":
            safe["message"] = item.get("message", "privacy filter event")
        else:
            safe["message"] = item.get("message", "")
            # Error details are useful for debugging and normally contain no SSID.
            if kind == "ERROR":
                safe["detail"] = item.get("detail", "")
        out.append(safe)
    return out


def main() -> int:
    status_ok, status = get_json("/api/status")
    activity_ok, activities = get_json("/api/activity")
    networks_ok, networks = get_json("/api/networks")

    nmcli = run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device", "status"]) if shutil.which("nmcli") else {"ok": False, "error": "nmcli not installed"}
    ssh = run(["systemctl", "is-active", "ssh"]) if shutil.which("systemctl") else {"ok": False, "error": "systemctl unavailable"}
    heimdall_service = run(["systemctl", "is-active", "heimdall"]) if shutil.which("systemctl") else {"ok": False, "error": "systemctl unavailable"}

    doc = {
        "snapshot_format": "heimdall-dev-snapshot-v1",
        "privacy": "SSID/BSSID values intentionally omitted",
        "generated_at": now(),
        "system": {
            "hostname": platform.node(),
            "architecture": platform.machine(),
            "python": platform.python_version(),
            "kernel": platform.release(),
        },
        "dashboard_reachable": status_ok,
        "status": status if status_ok else {"error": status},
        "activity": safe_activity(activities) if activity_ok else [{"kind": "ERROR", "message": str(activities)}],
        "wireless_inventory_count": len(networks) if networks_ok and isinstance(networks, list) else None,
        "wireless_device_state": nmcli,
        "ssh_service": ssh,
        "heimdall_service": heimdall_service,
        "local_files": {
            "config_present": (BASE / "config.json").exists(),
            "database_present": (BASE / "data" / "heimdall.db").exists(),
            "session_directory_present": (BASE / "data" / "sessions").exists(),
        },
    }

    print(json.dumps(doc, indent=2))
    return 0 if status_ok else 2


if __name__ == "__main__":
    sys.exit(main())
