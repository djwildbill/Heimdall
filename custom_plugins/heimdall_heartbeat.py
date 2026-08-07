import json
import logging
import os
import socket
import threading
import time
import urllib.error
import urllib.request

import pwnagotchi.plugins as plugins


class Plugin(plugins.Plugin):
    __author__ = "Project Odin"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Project Heimdall heartbeat reporter for Odin."

    def __init__(self):
        self.options = {}
        self._stop_event = threading.Event()
        self._thread = None
        self._last_odin_connected = False

    def on_loaded(self):
        logging.info("[heimdall-heartbeat] plugin loaded")

    def on_ready(self, agent):
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._heartbeat_loop,
            name="heimdall-heartbeat",
            daemon=True,
        )
        self._thread.start()
        logging.info("[heimdall-heartbeat] heartbeat loop started")

    def on_unload(self, ui):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        logging.info("[heimdall-heartbeat] plugin stopped")

    def _heartbeat_loop(self):
        interval = self._get_int_option("interval", 60)

        while not self._stop_event.is_set():
            try:
                payload = self._build_payload()
                self._last_odin_connected = self._send(payload)
            except Exception as exc:
                logging.exception("[heimdall-heartbeat] heartbeat failed: %s", exc)
                self._last_odin_connected = False

            self._stop_event.wait(interval)

    def _build_payload(self):
        return {
            "schema": "odin.heimdall.heartbeat.v1",
            "node": self.options.get("node_name") or socket.gethostname(),
            "role": "wireless-intelligence",
            "timestamp": int(time.time()),
            "uptime_seconds": self._read_uptime(),
            "temperature_c": self._read_temperature(),
            "wifi": self._wifi_status(),
            "odin_connected": self._last_odin_connected,
            "version": self.__version__,
        }

    def _send(self, payload):
        endpoint = str(self.options.get("endpoint", "")).strip()
        if not endpoint:
            logging.debug("[heimdall-heartbeat] no Odin endpoint configured")
            return False

        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Project-Heimdall/0.1",
        }

        token = str(self.options.get("token", "")).strip()
        if token:
            headers["Authorization"] = "Bearer " + token

        request = urllib.request.Request(
            endpoint,
            data=body,
            headers=headers,
            method="POST",
        )

        timeout = self._get_int_option("timeout", 5)

        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                status = getattr(response, "status", 200)
                if 200 <= status < 300:
                    logging.debug("[heimdall-heartbeat] Odin heartbeat accepted")
                    return True
                logging.warning(
                    "[heimdall-heartbeat] Odin returned HTTP %s", status
                )
                self._queue_failed_payload(payload)
                return False
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            logging.warning("[heimdall-heartbeat] Odin unavailable: %s", exc)
            self._queue_failed_payload(payload)
            return False

    def _queue_failed_payload(self, payload):
        queue_path = str(
            self.options.get(
                "queue_path",
                "/var/lib/heimdall/heartbeat-queue.jsonl",
            )
        )

        try:
            directory = os.path.dirname(queue_path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(queue_path, "a", encoding="utf-8") as queue_file:
                queue_file.write(json.dumps(payload, separators=(",", ":")) + "\n")
        except OSError as exc:
            logging.warning("[heimdall-heartbeat] could not queue heartbeat: %s", exc)

    @staticmethod
    def _read_uptime():
        try:
            with open("/proc/uptime", "r", encoding="utf-8") as uptime_file:
                return int(float(uptime_file.read().split()[0]))
        except (OSError, ValueError, IndexError):
            return None

    @staticmethod
    def _read_temperature():
        paths = (
            "/sys/class/thermal/thermal_zone0/temp",
            "/sys/devices/virtual/thermal/thermal_zone0/temp",
        )
        for path in paths:
            try:
                with open(path, "r", encoding="utf-8") as temp_file:
                    return round(float(temp_file.read().strip()) / 1000.0, 1)
            except (OSError, ValueError):
                continue
        return None

    def _wifi_status(self):
        interface = str(self.options.get("interface", "wlan0"))
        operstate_path = f"/sys/class/net/{interface}/operstate"

        state = "unknown"
        try:
            with open(operstate_path, "r", encoding="utf-8") as state_file:
                state = state_file.read().strip()
        except OSError:
            pass

        return {
            "interface": interface,
            "state": state,
        }

    def _get_int_option(self, name, default):
        try:
            value = int(self.options.get(name, default))
            return max(1, value)
        except (TypeError, ValueError):
            return default
