#!/usr/bin/env python3
"""Repair Heimdall field database schema without discarding existing history.

Current field build expects the `networks` table to have exactly these columns:
  bssid, ssid, channel, frequency, security, first_seen, last_seen,
  times_seen, last_signal, average_signal

Older Heimdall builds may have an extra column (for example `notes`). This
utility makes a timestamped backup, rebuilds only the networks table, and copies
matching columns into the current schema.
"""
from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB = BASE / "data" / "heimdall.db"
EXPECTED = [
    "bssid", "ssid", "channel", "frequency", "security",
    "first_seen", "last_seen", "times_seen", "last_signal", "average_signal",
]


def main() -> int:
    if not DB.exists():
        print("No Heimdall database exists yet. Nothing to repair.")
        return 0

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = DB.with_name(f"heimdall.db.backup-{stamp}")
    shutil.copy2(DB, backup)
    print(f"Backup created: {backup}")

    with sqlite3.connect(DB) as conn:
        rows = conn.execute("PRAGMA table_info(networks)").fetchall()
        current = [r[1] for r in rows]
        print("Current networks columns:", ", ".join(current) if current else "(none)")

        if current == EXPECTED:
            print("Schema already matches the current field build. No repair needed.")
            return 0

        if not current:
            conn.execute(
                """CREATE TABLE networks(
                bssid TEXT PRIMARY KEY, ssid TEXT, channel TEXT, frequency TEXT,
                security TEXT, first_seen TEXT, last_seen TEXT, times_seen INTEGER,
                last_signal INTEGER, average_signal REAL)"""
            )
            print("Created current networks table.")
            return 0

        conn.execute("ALTER TABLE networks RENAME TO networks_legacy")
        conn.execute(
            """CREATE TABLE networks(
            bssid TEXT PRIMARY KEY, ssid TEXT, channel TEXT, frequency TEXT,
            security TEXT, first_seen TEXT, last_seen TEXT, times_seen INTEGER,
            last_signal INTEGER, average_signal REAL)"""
        )

        legacy = {r[1] for r in conn.execute("PRAGMA table_info(networks_legacy)")}
        shared = [c for c in EXPECTED if c in legacy]

        # Handle old name used by the master-branch prototype.
        aliases = {}
        if "frequency" not in legacy and "frequency_mhz" in legacy:
            aliases["frequency"] = "frequency_mhz"

        dest_cols = []
        src_exprs = []
        for col in EXPECTED:
            if col in legacy:
                dest_cols.append(col)
                src_exprs.append(col)
            elif col in aliases:
                dest_cols.append(col)
                src_exprs.append(aliases[col])

        if "bssid" not in dest_cols:
            raise RuntimeError("Legacy table has no bssid column; automatic migration is unsafe.")

        conn.execute(
            f"INSERT OR REPLACE INTO networks ({','.join(dest_cols)}) "
            f"SELECT {','.join(src_exprs)} FROM networks_legacy"
        )
        copied = conn.execute("SELECT COUNT(*) FROM networks").fetchone()[0]
        conn.execute("DROP TABLE networks_legacy")
        conn.commit()
        print(f"Repair complete. Preserved {copied} network record(s).")
        print("Current schema:", ", ".join(EXPECTED))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
