#!/usr/bin/env python3
"""Privacy-safe terminal watcher for Heimdall/Josh."""
from __future__ import annotations

import json
import time
import urllib.request

API = "http://127.0.0.1:8080"


def get(path):
    with urllib.request.urlopen(API + path, timeout=3) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    seen = None
    while True:
        try:
            s = get("/api/status")
            a = get("/api/activity")
            newest = a[0] if a else {}
            token = (newest.get("time"), newest.get("kind"), newest.get("detail"))
            print(
                f"\rJosh ONLINE | scan #{s.get('scan_number')} | visible {s.get('observed_networks')} | "
                f"known {s.get('known_networks')} | protected {s.get('protected_filtered')} | "
                f"last {s.get('last_inventory_at') or 'waiting'}",
                end="",
                flush=True,
            )
            if token != seen and newest:
                print()
                kind = newest.get("kind", "EVENT")
                detail = newest.get("detail", "")
                if kind in {"NEW", "CHANGE"}:
                    msg = "wireless environment changed (identifier redacted)"
                    detail = ""
                else:
                    msg = newest.get("message", "")
                if kind == "ERROR" and detail:
                    print(f"[{newest.get('time')}] {kind}: {msg} — {detail}")
                else:
                    print(f"[{newest.get('time')}] {kind}: {msg}")
                seen = token
        except KeyboardInterrupt:
            print("\nWatcher stopped.")
            break
        except Exception as exc:
            print(f"\nJosh dashboard unavailable: {exc}")
        time.sleep(2)


if __name__ == "__main__":
    main()
