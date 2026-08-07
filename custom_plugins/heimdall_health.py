import json
import logging
import os
import socket
import threading
import time

import pwnagotchi.plugins as plugins


class Plugin(plugins.Plugin):
    __author__ = "Odin / Heimdall"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Heimdall local health telemetry for Josh."

    def __init__(self):
        self.options = {}
        self._stop_event = threading.Event()
        self._thread = None

    def on_loaded(self):
        logging.info("[heimdall-health] plugin loaded")

    def on_ready(self, agent):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop,
            name="heimdall-health",
            daemon=True,
        )
        self._thread.start()

    def on_unload(self, ui):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def _loop(self):
        interval = self._get_int_option("interval", 60)
        while not self._stop_event.is_set():
            try:
                self._write_status(self._build_status())
            except Exception as exc:
                logging.exception("[heimdall-health] update failed: %s", exc)
            self._stop_event.wait(interval)

    def _build_status(self):
        return {
            "schema": "odin.heimdall.health.v1",
            "system": "Heimdall",
            "persona": "Josh",
            "node": socket.gethostname(),
            "timestamp": int(time.time()),
            "uptime_seconds": self._read_uptime(),
            "temperature_c": self._read_temperature(),
            "load_average": self._read_load_average(),
            "memory": self._read_memory(),
            "disk": self._read_disk(),
        }

    def _write_status(self, payload):
        path = str(self.options.get("status_path", "/var/lib/heimdall/health.json"))
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        temp_path = path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as status_file:
            json.dump(payload, status_file, separators=(",", ":"), sort_keys=True)
            status_file.write("\n")
        os.replace(temp_path, path)

    @staticmethod
    def _read_uptime():
        try:
            with open("/proc/uptime", "r", encoding="utf-8") as handle:
                return int(float(handle.read().split()[0]))
        except (OSError, ValueError, IndexError):
            return None

    @staticmethod
    def _read_temperature():
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r", encoding="utf-8") as handle:
                return round(float(handle.read().strip()) / 1000.0, 1)
        except (OSError, ValueError):
            return None

    @staticmethod
    def _read_load_average():
        try:
            one, five, fifteen = os.getloadavg()
            return {"1m": round(one, 2), "5m": round(five, 2), "15m": round(fifteen, 2)}
        except (OSError, AttributeError):
            return None

    @staticmethod
    def _read_memory():
        values = {}
        try:
            with open("/proc/meminfo", "r", encoding="utf-8") as handle:
                for line in handle:
                    key, value = line.split(":", 1)
                    if key in ("MemTotal", "MemAvailable"):
                        values[key] = int(value.strip().split()[0]) * 1024
        except (OSError, ValueError, IndexError):
            return None
        if not values:
            return None
        total = values.get("MemTotal")
        available = values.get("MemAvailable")
        used = total - available if total is not None and available is not None else None
        return {"total_bytes": total, "available_bytes": available, "used_bytes": used}

    @staticmethod
    def _read_disk():
        try:
            stat = os.statvfs("/")
            total = stat.f_blocks * stat.f_frsize
            available = stat.f_bavail * stat.f_frsize
            return {
                "total_bytes": total,
                "available_bytes": available,
                "used_bytes": total - available,
            }
        except OSError:
            return None

    def _get_int_option(self, name, default):
        try:
            return max(1, int(self.options.get(name, default)))
        except (TypeError, ValueError):
            return default
