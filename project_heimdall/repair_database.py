#!/usr/bin/env python3
"""Repair Heimdall field database schema without discarding existing history.

Repairs both `networks` and `observations` tables used by older Heimdall builds.
A timestamped backup is created before any change.
"""
from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB = BASE / "data" / "heimdall.db"

NETWORKS_EXPECTED = [
    "bssid", "ssid", "channel", "frequency", "security",
    "first_seen", "last_seen", "times_seen", "last_signal", "average_signal",
]
OBS_EXPECTED = [
    "id", "session_id", "observed_at", "ssid", "bssid", "channel",
    "frequency", "signal", "security",
]


def columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def repair_networks(conn: sqlite3.Connection) -> None:
    current = columns(conn, "networks")
    print("Current networks columns:", ", ".join(current) if current else "(none)")
    if current == NETWORKS_EXPECTED:
        print("Networks schema already current.")
        return
    if not current:
        conn.execute("""CREATE TABLE networks(
            bssid TEXT PRIMARY KEY, ssid TEXT, channel TEXT, frequency TEXT,
            security TEXT, first_seen TEXT, last_seen TEXT, times_seen INTEGER,
            last_signal INTEGER, average_signal REAL)""")
        print("Created current networks table.")
        return

    conn.execute("ALTER TABLE networks RENAME TO networks_legacy")
    conn.execute("""CREATE TABLE networks(
        bssid TEXT PRIMARY KEY, ssid TEXT, channel TEXT, frequency TEXT,
        security TEXT, first_seen TEXT, last_seen TEXT, times_seen INTEGER,
        last_signal INTEGER, average_signal REAL)""")
    legacy = set(columns(conn, "networks_legacy"))
    aliases = {"frequency": "frequency_mhz"} if "frequency" not in legacy and "frequency_mhz" in legacy else {}
    dest, src = [], []
    for col in NETWORKS_EXPECTED:
        if col in legacy:
            dest.append(col); src.append(col)
        elif col in aliases:
            dest.append(col); src.append(aliases[col])
    if "bssid" not in dest:
        raise RuntimeError("Legacy networks table has no bssid column; automatic migration is unsafe.")
    conn.execute(f"INSERT OR REPLACE INTO networks ({','.join(dest)}) SELECT {','.join(src)} FROM networks_legacy")
    copied = conn.execute("SELECT COUNT(*) FROM networks").fetchone()[0]
    conn.execute("DROP TABLE networks_legacy")
    print(f"Networks repaired. Preserved {copied} network record(s).")


def repair_observations(conn: sqlite3.Connection) -> None:
    current = columns(conn, "observations")
    print("Current observations columns:", ", ".join(current) if current else "(none)")
    if current == OBS_EXPECTED:
        print("Observations schema already current.")
        return
    if not current:
        conn.execute("""CREATE TABLE observations(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT, observed_at TEXT, ssid TEXT, bssid TEXT,
            channel TEXT, frequency TEXT, signal INTEGER, security TEXT)""")
        print("Created current observations table.")
        return

    conn.execute("ALTER TABLE observations RENAME TO observations_legacy")
    conn.execute("""CREATE TABLE observations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT, observed_at TEXT, ssid TEXT, bssid TEXT,
        channel TEXT, frequency TEXT, signal INTEGER, security TEXT)""")
    legacy = set(columns(conn, "observations_legacy"))
    aliases = {}
    if "frequency" not in legacy and "frequency_mhz" in legacy:
        aliases["frequency"] = "frequency_mhz"
    if "signal" not in legacy and "signal_percent" in legacy:
        aliases["signal"] = "signal_percent"

    dest, src = [], []
    for col in OBS_EXPECTED:
        if col == "id":
            continue
        if col in legacy:
            dest.append(col); src.append(col)
        elif col in aliases:
            dest.append(col); src.append(aliases[col])
    if "session_id" not in dest or "bssid" not in dest:
        raise RuntimeError("Legacy observations table lacks required fields; automatic migration is unsafe.")
    conn.execute(f"INSERT INTO observations ({','.join(dest)}) SELECT {','.join(src)} FROM observations_legacy")
    copied = conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
    conn.execute("DROP TABLE observations_legacy")
    print(f"Observations repaired. Preserved {copied} observation record(s).")


def main() -> int:
    if not DB.exists():
        print("No Heimdall database exists yet. Nothing to repair.")
        return 0

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = DB.with_name(f"heimdall.db.backup-{stamp}")
    shutil.copy2(DB, backup)
    print(f"Backup created: {backup}")

    with sqlite3.connect(DB) as conn:
        repair_networks(conn)
        repair_observations(conn)
        conn.commit()
        print("Database compatibility repair complete.")
        print("Networks schema:", ", ".join(columns(conn, "networks")))
        print("Observations schema:", ", ".join(columns(conn, "observations")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
