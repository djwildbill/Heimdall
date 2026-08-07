"""Heimdall protected-network privacy guard.

Pwnagotchi's whitelist prevents active interaction, but passive monitoring can
still capture handshakes by chance. This plugin makes Heimdall's protected
network policy stronger: protected SSIDs/BSSIDs are not retained locally.

Protection sources:
- main.whitelist
- main.plugins.grid.exclude
- this plugin's optional `protected` list

PwnGrid remains disabled by default in Heimdall configuration.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import pwnagotchi.plugins as plugins


class HeimdallPrivacy(plugins.Plugin):
    __author__ = "Project Odin"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Discard captures for Heimdall protected networks."

    def __init__(self):
        self._protected: set[str] = set()

    @staticmethod
    def _norm(value) -> str:
        return str(value or "").strip().lower()

    def _load_policy(self, config: dict) -> None:
        values = []
        values.extend(config.get("main", {}).get("whitelist", []) or [])
        values.extend(
            config.get("main", {})
            .get("plugins", {})
            .get("grid", {})
            .get("exclude", [])
            or []
        )
        values.extend(self.options.get("protected", []) or [])
        self._protected = {self._norm(v) for v in values if self._norm(v)}
        logging.info("[heimdall-privacy] protecting %d network identifiers", len(self._protected))

    def on_loaded(self):
        logging.info("[heimdall-privacy] loaded")

    def on_config_changed(self, config):
        self._load_policy(config)

    def _is_protected(self, access_point) -> bool:
        if isinstance(access_point, dict):
            candidates = (
                access_point.get("hostname"),
                access_point.get("essid"),
                access_point.get("ssid"),
                access_point.get("mac"),
                access_point.get("bssid"),
            )
        else:
            candidates = (access_point,)
        return any(self._norm(v) in self._protected for v in candidates if v)

    @staticmethod
    def _discard_capture(filename: str) -> None:
        path = Path(filename)
        # Captures are organized per AP. Remove the capture and common metadata
        # sidecars sharing the same stem so protected-network data is not kept.
        candidates = [path]
        if path.suffix:
            candidates.extend(path.parent.glob(path.stem + ".*"))
        for candidate in set(candidates):
            try:
                if candidate.is_file():
                    candidate.unlink()
            except OSError as exc:
                logging.warning("[heimdall-privacy] could not remove %s: %s", candidate, exc)

    def on_handshake(self, agent, filename, access_point, client_station):
        if not self._protected:
            return
        if self._is_protected(access_point):
            logging.info("[heimdall-privacy] discarded protected-network capture")
            self._discard_capture(filename)
