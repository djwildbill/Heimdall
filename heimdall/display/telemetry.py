"""Telemetry helpers for the Heimdall e-paper UI.

Wireless counters are read from /var/lib/heimdall/wireless.json.  The wireless
engine will own that file once it is installed; until then the UI safely shows
zero/unknown values instead of failing.
"""

from __future__ import annotations

import json
import os
import subprocess
import time

WIRELESS_STATE = "/var/lib/heimdall/wireless.json"
MODE_FILE = "/var/lib/heimdall/mode"
HEALTH_STATE = "/var/lib/heimdall/health.json"


def _read_text(path: str) -> str | None:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read().strip()
    except OSError:
        return None


def _read_json(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            value = json.load(handle)
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def mode() -> str:
    value = (_read_text(MODE_FILE) or "boot").lower()
    return {
        "pwn": "PWN",
        "sentinel": "SENT",
        "recon": "RECN",
        "maintenance": "CMD",
    }.get(value, value[:4].upper())


def temperature() -> str:
    health = _read_json(HEALTH_STATE)
    value = health.get("temperature_c")
    if isinstance(value, (int, float)):
        return f"{value:.0f}C"

    raw = _read_text("/sys/class/thermal/thermal_zone0/temp")
    try:
        return f"{float(raw) / 1000:.0f}C"
    except (TypeError, ValueError):
        return "--C"


def uptime() -> str:
    raw = _read_text("/proc/uptime")
    try:
        seconds = int(float(raw.split()[0]))
    except (AttributeError, ValueError, IndexError):
        return "--:--"

    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    if hours >= 24:
        days, hours = divmod(hours, 24)
        return f"{days}d{hours:02}h"
    return f"{hours:02}:{minutes:02}"


def ip_address() -> str:
    try:
        output = subprocess.check_output(
            ["hostname", "-I"], text=True, stderr=subprocess.DEVNULL
        ).strip()
        return output.split()[0] if output else "OFFLINE"
    except (OSError, subprocess.SubprocessError):
        return "OFFLINE"


def wifi_up() -> bool:
    return os.path.exists("/sys/class/net/wlan0") and (
        _read_text("/sys/class/net/wlan0/operstate") in {"up", "unknown"}
    )


def battery() -> str:
    """Return battery percentage when a battery provider has populated health.json."""
    health = _read_json(HEALTH_STATE)
    value = health.get("battery_percent")
    if isinstance(value, (int, float)):
        return f"{max(0, min(100, round(value)))}%"
    return "--%"


def wireless() -> dict:
    data = _read_json(WIRELESS_STATE)
    return {
        "networks": int(data.get("networks", 0) or 0),
        "clients": int(data.get("clients", 0) or 0),
        "captures": int(data.get("captures", 0) or 0),
        "channel": data.get("channel", "--"),
        "last_activity": float(data.get("last_activity", 0) or 0),
        "last_capture": float(data.get("last_capture", 0) or 0),
    }


def snapshot() -> dict:
    return {
        "mode": mode(),
        "temperature": temperature(),
        "uptime": uptime(),
        "ip": ip_address(),
        "wifi": "UP" if wifi_up() else "DOWN",
        "battery": battery(),
        "wireless": wireless(),
        "timestamp": time.time(),
    }
