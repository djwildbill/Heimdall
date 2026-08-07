"""PiSugar power integration for Heimdall.

Uses the official PiSugar Power Manager unix socket when available.  Heimdall
never writes raw PiSugar I2C registers; the vendor service owns the hardware.
"""

from __future__ import annotations

import os
import socket

SOCKET_CANDIDATES = (
    "/tmp/pisugar-server.sock",
    "/tmp/pisugar.sock",
)


def _query(command: str, timeout: float = 1.5) -> str | None:
    for path in SOCKET_CANDIDATES:
        if not os.path.exists(path):
            continue
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.settimeout(timeout)
        try:
            client.connect(path)
            client.sendall((command.strip() + "\n").encode("utf-8"))
            chunks: list[bytes] = []
            while True:
                try:
                    chunk = client.recv(4096)
                except socket.timeout:
                    break
                if not chunk:
                    break
                chunks.append(chunk)
                if b"\n" in chunk:
                    break
            response = b"".join(chunks).decode("utf-8", errors="replace").strip()
            return response or None
        except OSError:
            continue
        finally:
            client.close()
    return None


def battery_percent() -> float | None:
    value = _query("get battery")
    if value is None:
        return None
    # Rust server commonly responds as either a bare number or 'battery: N'.
    try:
        return max(0.0, min(100.0, float(value.split(":")[-1].strip())))
    except (TypeError, ValueError):
        return None


def battery_voltage() -> float | None:
    value = _query("get battery_v")
    if value is None:
        return None
    try:
        return float(value.split(":")[-1].strip())
    except (TypeError, ValueError):
        return None


def charging() -> bool | None:
    value = _query("get battery_charging")
    if value is None:
        return None
    normalized = value.split(":")[-1].strip().lower()
    if normalized in {"true", "1", "yes", "charging"}:
        return True
    if normalized in {"false", "0", "no", "discharging"}:
        return False
    return None


def status() -> dict:
    return {
        "battery_percent": battery_percent(),
        "battery_voltage": battery_voltage(),
        "charging": charging(),
        "available": any(os.path.exists(path) for path in SOCKET_CANDIDATES),
    }
