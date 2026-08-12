import json
import logging
import os
import threading
import time

from PIL import ImageFont

import pwnagotchi.plugins as plugins
from pwnagotchi.ui.components import Line, Text


class Plugin(plugins.Plugin):
    __author__ = "Project Odin"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "High-contrast live Heimdall dashboard for the 250x122 Waveshare display."

    def __init__(self):
        self.options = {}
        self.ui = None
        self.state_path = "/var/lib/heimdall/wireless.json"
        self.health_path = "/var/lib/heimdall/health.json"
        self.mode_path = "/var/lib/heimdall/mode"
        self.refresh_seconds = 5
        self._stop = threading.Event()
        self._thread = None
        self._last_handshake = 0

        # Thick, readable fonts for a small e-paper panel.
        self.font_node = ImageFont.truetype("DejaVuSansMono-Bold", 17)
        self.font_title = ImageFont.truetype("DejaVuSansMono-Bold", 10)
        self.font_stat = ImageFont.truetype("DejaVuSansMono-Bold", 11)
        self.font_label = ImageFont.truetype("DejaVuSansMono-Bold", 9)
        self.font_value = ImageFont.truetype("DejaVuSansMono-Bold", 10)
        self.font_footer = ImageFont.truetype("DejaVuSansMono-Bold", 9)
        self.font_face = ImageFont.truetype("DejaVuSansMono-Bold", 30)

    def on_loaded(self):
        self.state_path = str(self.options.get("state_path", self.state_path))
        self.health_path = str(self.options.get("health_path", self.health_path))
        self.mode_path = str(self.options.get("mode_path", self.mode_path))
        try:
            self.refresh_seconds = max(2, int(self.options.get("refresh_seconds", 5)))
        except (TypeError, ValueError):
            self.refresh_seconds = 5
        logging.info("[heimdall-display] centered live dashboard enabled")

    def on_ui_setup(self, ui):
        self.ui = ui
        if ui.width() < 240 or ui.height() < 115:
            logging.warning(
                "[heimdall-display] display is %sx%s; optimized layout expects 250x122",
                ui.width(), ui.height())

        # Remove the stock Pwnagotchi text blocks. Keep the state key 'face'
        # but replace its widget so core mood changes still animate Josh.
        for key in (
            "channel", "aps", "uptime", "line1", "line2", "face",
            "friend_face", "friend_name", "name", "status", "shakes", "mode",
            "sta",
        ):
            try:
                if ui.has_element(key):
                    ui.remove_element(key)
            except Exception:
                pass

        ui.add_element("hd_node", Text("OVN-002 JOSH", (4, -1), self.font_node))
        ui.add_element("hd_title", Text("HEIMDALL", (5, 18), self.font_title))
        ui.add_element("hd_mode", Text("SENTINEL", (186, 4), self.font_label))
        ui.add_element("hd_topline", Line((0, 30, 250, 30), width=2))

        # Main face stays in the middle of the display.
        ui.add_element("face", Text("(•‿‿•)", (77, 36), self.font_face))

        # Left / right high-value counters. No icons: text stays readable on
        # real hardware and wastes less space.
        ui.add_element("hd_net", Text("NET 0", (4, 37), self.font_stat))
        ui.add_element("hd_cli", Text("CLI 0", (4, 53), self.font_stat))
        ui.add_element("hd_cap", Text("CAP 0", (4, 69), self.font_stat))

        ui.add_element("hd_ch", Text("CH --", (196, 37), self.font_stat))
        ui.add_element("hd_temp", Text("T --C", (190, 53), self.font_stat))
        ui.add_element("hd_bat", Text("BAT --", (190, 69), self.font_stat))

        ui.add_element("hd_midline", Line((0, 87, 250, 87), width=2))

        # Pwnagotchi-style useful information: current observed SSID and
        # handshake/capture state. No management IP or 'whitelist' label.
        ui.add_element("hd_ssid_label", Text("SSID", (4, 89), self.font_label))
        ui.add_element("hd_ssid", Text("--", (4, 99), self.font_value))
        ui.add_element("hd_hs_label", Text("HANDSHAKE", (151, 89), self.font_label))
        ui.add_element("hd_hs", Text("0  --", (151, 99), self.font_value))

        ui.add_element("hd_bottomline", Line((0, 111, 250, 111), width=1))
        ui.add_element("hd_footer", Text("BRIDGE LIVE", (4, 112), self.font_footer))
        ui.add_element("hd_up", Text("UP --", (176, 112), self.font_footer))

        # Invisible changing value used only to make the e-paper redraw on a
        # predictable cadence while ui.fps remains 0 for conservative wear.
        ui.add_element("hd_tick", Text("", (400, 400), self.font_label))

        self._stop.clear()
        self._thread = threading.Thread(target=self._refresh_loop, name="heimdall-display", daemon=True)
        self._thread.start()
        self._force_refresh()

    def on_ui_update(self, ui):
        wireless = self._read_json(self.state_path)
        health = self._read_json(self.health_path)

        networks = self._safe_int(wireless.get("networks"), 0)
        clients = self._safe_int(wireless.get("clients"), 0)
        captures = self._safe_int(wireless.get("captures"), 0)
        channel = str(wireless.get("channel", "--"))
        ssid = self._clean_ssid(wireless.get("ssid", "--"))
        last_hs_ssid = self._clean_ssid(wireless.get("last_handshake_ssid", "--"))
        last_capture = self._safe_float(wireless.get("last_capture"), 0)

        temp = health.get("temperature_c")
        uptime = health.get("uptime_seconds")

        ui.set("hd_net", "NET %d" % networks)
        ui.set("hd_cli", "CLI %d" % clients)
        ui.set("hd_cap", "CAP %d" % captures)
        ui.set("hd_ch", "CH %s" % channel)
        ui.set("hd_temp", "T %sC" % self._temp_text(temp))
        ui.set("hd_bat", "BAT %s" % self._battery_text(health))
        ui.set("hd_mode", self._read_mode()[:8].upper())

        ui.set("hd_ssid", self._fit(ssid, 20))
        hs_name = last_hs_ssid if last_hs_ssid != "--" else ssid
        ui.set("hd_hs", self._fit("%d  %s" % (captures, hs_name), 15))
        ui.set("hd_up", "UP %s" % self._uptime_text(uptime))

        if last_capture and time.time() - last_capture <= 15:
            ui.set("hd_footer", "CAPTURED %s" % self._fit(last_hs_ssid, 14))
        elif networks > 0:
            ui.set("hd_footer", "OBSERVING")
        else:
            ui.set("hd_footer", "BRIDGE LIVE")

    def on_handshake(self, agent, filename, access_point, client_station):
        self._last_handshake = time.time()
        self._force_refresh()

    def on_wifi_update(self, agent, access_points):
        # Telemetry writes first/alongside this callback; general refreshes are
        # throttled by the timer to avoid hammering the e-paper panel.
        pass

    def on_unload(self, ui):
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)

    def _refresh_loop(self):
        while not self._stop.wait(self.refresh_seconds):
            self._force_refresh()

    def _force_refresh(self):
        if self.ui is None:
            return
        try:
            self.ui.set("hd_tick", str(int(time.time())))
            self.ui.update()
        except Exception as exc:
            logging.debug("[heimdall-display] refresh skipped: %s", exc)

    @staticmethod
    def _read_json(path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
                return data if isinstance(data, dict) else {}
        except (OSError, ValueError, TypeError):
            return {}

    def _read_mode(self):
        try:
            with open(self.mode_path, "r", encoding="utf-8") as handle:
                value = handle.read().strip()
                return value or "sentinel"
        except OSError:
            return "sentinel"

    @staticmethod
    def _clean_ssid(value):
        text = str(value or "--").strip()
        return text if text else "--"

    @staticmethod
    def _fit(text, max_chars):
        text = str(text)
        if len(text) <= max_chars:
            return text
        if max_chars <= 1:
            return text[:max_chars]
        return text[:max_chars - 1] + "~"

    @staticmethod
    def _safe_int(value, default):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_float(value, default):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _temp_text(value):
        try:
            return str(int(round(float(value))))
        except (TypeError, ValueError):
            return "--"

    @staticmethod
    def _uptime_text(seconds):
        try:
            seconds = int(seconds)
        except (TypeError, ValueError):
            return "--"
        days, rem = divmod(seconds, 86400)
        hours = rem // 3600
        if days:
            return "%dd%dh" % (days, hours)
        minutes = (rem % 3600) // 60
        return "%dh%dm" % (hours, minutes)

    @staticmethod
    def _battery_text(health):
        # PiSugar battery integration can populate battery_percent in health
        # later. Until then we display -- rather than invent a value.
        value = health.get("battery_percent")
        try:
            return "%d%%" % int(round(float(value)))
        except (TypeError, ValueError):
            return "--"
