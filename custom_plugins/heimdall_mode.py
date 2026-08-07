import json
import logging
import os
import threading
import time
import urllib.error
import urllib.request

import pwnagotchi.plugins as plugins


MODES = {
    "pwn": {
        "label": "PWN",
        "deauth": True,
        "associate": True,
        "advertise": True,
        "description": "Original Pwnagotchi-style active behavior for authorized environments.",
    },
    "sentinel": {
        "label": "SENT",
        "deauth": False,
        "associate": False,
        "advertise": False,
        "description": "Passive wireless observation and collection only.",
    },
    "recon": {
        "label": "RECN",
        "deauth": False,
        "associate": False,
        "advertise": True,
        "description": "Wireless reconnaissance with peer advertising, without client disruption.",
    },
    "maintenance": {
        "label": "CMD",
        "deauth": False,
        "associate": False,
        "advertise": False,
        "description": "Management and maintenance mode.",
    },
}


class Plugin(plugins.Plugin):
    __author__ = "Odin"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Heimdall runtime mode controller for local or Odin/Geri-directed operation."

    def __init__(self):
        self.options = {}
        self._agent = None
        self._thread = None
        self._stop_event = threading.Event()
        self._mode = None

    def on_loaded(self):
        logging.info("[heimdall-mode] plugin loaded")

    def on_ready(self, agent):
        self._agent = agent
        initial = self._read_local_mode() or str(self.options.get("default_mode", "pwn")).lower()
        self._apply_mode(initial)

        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._control_loop,
            name="heimdall-mode",
            daemon=True,
        )
        self._thread.start()

    def on_unload(self, ui):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def _control_loop(self):
        interval = self._int_option("poll_interval", 15)
        while not self._stop_event.is_set():
            try:
                local_mode = self._read_local_mode()
                if local_mode and local_mode != self._mode:
                    self._apply_mode(local_mode)

                remote_mode = self._fetch_remote_mode()
                if remote_mode and remote_mode != self._mode:
                    self._write_local_mode(remote_mode)
                    self._apply_mode(remote_mode)
            except Exception as exc:
                logging.warning("[heimdall-mode] control poll failed: %s", exc)

            self._stop_event.wait(interval)

    def _apply_mode(self, mode):
        mode = str(mode).strip().lower()
        if mode not in MODES:
            logging.warning("[heimdall-mode] ignoring unknown mode: %s", mode)
            return False
        if self._agent is None:
            return False

        settings = MODES[mode]
        personality = self._agent.config()["personality"]
        personality["deauth"] = settings["deauth"]
        personality["associate"] = settings["associate"]
        personality["advertise"] = settings["advertise"]
        self._mode = mode
        self._write_local_mode(mode)

        try:
            view = self._agent.view()
            view.set("mode", settings["label"])
            view.set("status", "Mode: %s" % mode.upper())
            view.update(force=True)
        except Exception:
            pass

        logging.warning(
            "[heimdall-mode] mode=%s deauth=%s associate=%s advertise=%s",
            mode,
            settings["deauth"],
            settings["associate"],
            settings["advertise"],
        )
        return True

    def _fetch_remote_mode(self):
        endpoint = str(self.options.get("control_endpoint", "")).strip()
        if not endpoint:
            return None

        headers = {"Accept": "application/json", "User-Agent": "Heimdall/0.1"}
        token = str(self.options.get("token", "")).strip()
        if token:
            headers["Authorization"] = "Bearer " + token

        request = urllib.request.Request(endpoint, headers=headers, method="GET")
        timeout = self._int_option("timeout", 5)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            logging.debug("[heimdall-mode] remote control unavailable: %s", exc)
            return None

        mode = str(payload.get("mode", "")).strip().lower()
        return mode if mode in MODES else None

    def _mode_path(self):
        return str(self.options.get("mode_path", "/var/lib/heimdall/mode"))

    def _read_local_mode(self):
        try:
            with open(self._mode_path(), "r", encoding="utf-8") as fh:
                mode = fh.read().strip().lower()
            return mode if mode in MODES else None
        except OSError:
            return None

    def _write_local_mode(self, mode):
        path = self._mode_path()
        try:
            directory = os.path.dirname(path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(mode + "\n")
        except OSError as exc:
            logging.warning("[heimdall-mode] could not save mode: %s", exc)

    def _int_option(self, name, default):
        try:
            return max(1, int(self.options.get(name, default)))
        except (TypeError, ValueError):
            return default
