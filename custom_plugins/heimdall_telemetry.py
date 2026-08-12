import json
import os
import time
import logging

import pwnagotchi.plugins as plugins


class HeimdallTelemetry(plugins.Plugin):
    __author__ = "Project Odin"
    __version__ = "0.2.0"
    __license__ = "GPL3"
    __description__ = "Feeds live Pwnagotchi wireless state into Heimdall telemetry."

    def __init__(self):
        self.state_path = "/var/lib/heimdall/wireless.json"
        self.channel = "--"
        self.networks = 0
        self.clients = 0
        self.captures = 0
        self.ssid = "--"
        self.last_handshake_ssid = "--"
        self.last_capture = 0
        self.last_activity = 0

    def on_loaded(self):
        self.state_path = self.options.get("state_path", self.state_path)
        os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
        self._write()
        logging.info("Heimdall telemetry writing to %s", self.state_path)

    def on_ready(self, agent):
        self._refresh_from_agent(agent)

    def on_channel_hop(self, agent, channel):
        self.channel = channel
        self.last_activity = time.time()
        self._write()

    def on_wifi_update(self, agent, access_points):
        aps = access_points or []
        self.networks = len(aps)
        self.clients = 0
        for ap in aps:
            clients = ap.get("clients") or ap.get("stations") or []
            self.clients += len(clients)

        # wifi_update receives the post-policy list from the agent. Protected /
        # whitelisted SSIDs have already been excluded, so the display never
        # needs to expose Josh's management/private network name.
        focus = self._focus_ap(aps)
        if focus:
            self.ssid = self._ap_name(focus)
            if focus.get("channel") is not None:
                self.channel = focus.get("channel")

        self.last_activity = time.time()
        self._write()

    def on_unfiltered_ap_list(self, agent, access_points):
        # Preserve only aggregate counts here. Never derive the displayed SSID
        # from the unfiltered list because that list can contain protected
        # networks.
        if access_points is not None:
            self.networks = len(access_points)
            self.clients = 0
            for ap in access_points:
                clients = ap.get("clients") or ap.get("stations") or []
                self.clients += len(clients)
            self.last_activity = time.time()
            self._write()

    def on_handshake(self, agent, filename, access_point, client_station):
        self.captures += 1
        self.last_capture = time.time()
        self.last_activity = self.last_capture

        if isinstance(access_point, dict):
            self.last_handshake_ssid = self._ap_name(access_point)
            self.ssid = self.last_handshake_ssid
            if access_point.get("channel") is not None:
                self.channel = access_point.get("channel")
        elif access_point:
            self.last_handshake_ssid = str(access_point)
            self.ssid = self.last_handshake_ssid

        self._write()

    def on_epoch(self, agent, epoch, epoch_data):
        self._refresh_from_agent(agent)

    def _refresh_from_agent(self, agent):
        try:
            session = agent.session() or {}
            wifi = session.get("wifi", {})
            aps = wifi.get("aps") or wifi.get("access_points") or []
            if aps:
                self.networks = len(aps)
                self.clients = sum(len((ap.get("clients") or ap.get("stations") or [])) for ap in aps)
            if wifi.get("channel") is not None:
                self.channel = wifi.get("channel")

            handshakes = getattr(agent, "_handshakes", None)
            if isinstance(handshakes, dict):
                self.captures = len(handshakes)

            last_pwnd = getattr(agent, "_last_pwnd", None)
            if last_pwnd and self.last_handshake_ssid == "--":
                self.last_handshake_ssid = str(last_pwnd)

            self.last_activity = time.time()
        except Exception as exc:
            logging.debug("Heimdall telemetry session refresh failed: %s", exc)
        self._write()

    @staticmethod
    def _ap_name(ap):
        name = str(ap.get("hostname") or "").strip()
        if name and name != "<hidden>":
            return name
        return "<hidden>"

    @staticmethod
    def _focus_ap(aps):
        if not aps:
            return None
        try:
            return max(aps, key=lambda ap: int(ap.get("rssi", -999)))
        except (TypeError, ValueError):
            return aps[0]

    def _write(self):
        payload = {
            "networks": int(self.networks),
            "clients": int(self.clients),
            "captures": int(self.captures),
            "channel": self.channel,
            "ssid": self.ssid,
            "last_handshake_ssid": self.last_handshake_ssid,
            "last_activity": float(self.last_activity),
            "last_capture": float(self.last_capture),
            "updated_at": time.time(),
        }
        tmp = self.state_path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as handle:
                json.dump(payload, handle)
            os.replace(tmp, self.state_path)
        except OSError as exc:
            logging.warning("Heimdall telemetry write failed: %s", exc)
