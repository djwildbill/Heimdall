import json
import logging
import threading
import time

from PIL import ImageFont

import pwnagotchi.plugins as plugins
from pwnagotchi.ui.components import Widget


BLACK = 0
WHITE = 255


class HeimdallDashboard(Widget):
    """Draw the entire 250x122 Josh dashboard as one coherent screen."""

    def __init__(self, plugin):
        super().__init__((0, 0), BLACK)
        self.plugin = plugin

    def draw(self, canvas, drawer):
        p = self.plugin
        w, h = canvas.size

        # This layout is designed for the Waveshare 2.13in V2 landscape canvas
        # used by Josh: 250 x 122 pixels.
        drawer.rectangle((0, 0, w - 1, h - 1), fill=WHITE, outline=BLACK)

        # ------------------------------------------------------------------
        # Header: large node identity, Heimdall directly beneath it.
        # ------------------------------------------------------------------
        p._center_text(drawer, "OVN-002 JOSH", 1, p.font_node)
        p._center_text(drawer, "HEIMDALL", 18, p.font_title)
        drawer.line((4, 30, w - 5, 30), fill=BLACK, width=2)

        # Main three-column area.
        left_x2 = 54
        right_x1 = 194
        drawer.line((left_x2, 33, left_x2, 87), fill=BLACK, width=1)
        drawer.line((right_x1, 33, right_x1, 87), fill=BLACK, width=1)

        # Left column: NET / CLI / CAP with simple high-contrast glyphs.
        p._draw_wifi(drawer, 27, 39)
        p._center_text_in(drawer, "NET %d" % p.networks, 1, left_x2 - 1, 50, p.font_stat)
        drawer.line((5, 58, left_x2 - 5, 58), fill=BLACK, width=1)

        p._draw_terminal(drawer, 18, 62)
        p._center_text_in(drawer, "CLI %d" % p.clients, 1, left_x2 - 1, 72, p.font_stat)

        p._draw_target(drawer, 27, 82)
        p._center_text_in(drawer, "CAP %d" % p.captures, 1, left_x2 - 1, 82, p.font_stat)

        # Center: Josh's face is intentionally the visual focus.
        p._draw_face(drawer, 124, 59)

        # Right column: channel, battery, temperature.
        p._draw_radio(drawer, 221, 40)
        p._center_text_in(drawer, "CH %s" % p.channel, right_x1 + 1, w - 2, 50, p.font_stat)
        drawer.line((right_x1 + 5, 58, w - 5, 58), fill=BLACK, width=1)

        p._draw_battery(drawer, 202, 65, p.battery_percent)
        bat = "-- %" if p.battery_percent is None else "%d%%" % p.battery_percent
        drawer.text((220, 62), bat, font=p.font_stat, fill=BLACK)
        drawer.line((right_x1 + 5, 76, w - 5, 76), fill=BLACK, width=1)

        p._draw_thermometer(drawer, 204, 80)
        drawer.text((218, 79), "TEMP", font=p.font_label, fill=BLACK)
        drawer.text((218, 89), "%sC" % p.temperature, font=p.font_stat, fill=BLACK)

        # ------------------------------------------------------------------
        # Lower information row: uptime / SSID / handshake.
        # No management IP and no whitelist wording.
        # ------------------------------------------------------------------
        drawer.line((4, 92, w - 5, 92), fill=BLACK, width=2)
        drawer.line((69, 94, 69, 109), fill=BLACK, width=1)
        drawer.line((184, 94, 184, 109), fill=BLACK, width=1)

        p._center_text_in(drawer, "UPTIME", 1, 68, 94, p.font_label)
        p._center_text_in(drawer, p.uptime, 1, 68, 102, p.font_value)

        p._center_text_in(drawer, "SSID", 70, 183, 94, p.font_label)
        p._center_text_in(drawer, p._fit(p.ssid, 16), 70, 183, 102, p.font_value)

        p._center_text_in(drawer, "HANDSHAKE", 185, w - 2, 94, p.font_label)
        p._center_text_in(drawer, str(p.captures), 185, w - 2, 102, p.font_value)

        # Footer status + version.
        drawer.line((4, 111, w - 5, 111), fill=BLACK, width=1)
        p._draw_check(drawer, 11, 116)
        drawer.text((22, 112), p.footer, font=p.font_footer, fill=BLACK)
        version = p.version_text
        tw = p._text_width(drawer, version, p.font_small)
        drawer.text((w - tw - 5, 113), version, font=p.font_small, fill=BLACK)


class Plugin(plugins.Plugin):
    __author__ = "Project Odin"
    __version__ = "0.2.0"
    __license__ = "GPL3"
    __description__ = "Josh high-contrast full-screen Heimdall e-paper dashboard."

    def __init__(self):
        self.options = {}
        self.ui = None
        self.state_path = "/var/lib/heimdall/wireless.json"
        self.health_path = "/var/lib/heimdall/health.json"
        self.refresh_seconds = 5
        self._stop = threading.Event()
        self._thread = None

        # Bold fonts throughout: designed for readability on a physical 2.13in
        # e-paper panel instead of maximizing the amount of tiny text.
        self.font_node = ImageFont.truetype("DejaVuSansMono-Bold", 18)
        self.font_title = ImageFont.truetype("DejaVuSansMono-Bold", 10)
        self.font_stat = ImageFont.truetype("DejaVuSansMono-Bold", 10)
        self.font_label = ImageFont.truetype("DejaVuSansMono-Bold", 8)
        self.font_value = ImageFont.truetype("DejaVuSansMono-Bold", 9)
        self.font_footer = ImageFont.truetype("DejaVuSansMono-Bold", 10)
        self.font_small = ImageFont.truetype("DejaVuSansMono-Bold", 7)

        self.networks = 0
        self.clients = 0
        self.captures = 0
        self.channel = "--"
        self.ssid = "--"
        self.temperature = "--"
        self.battery_percent = None
        self.uptime = "--"
        self.footer = "BRIDGE LIVE"
        self.version_text = "v0.1.0-alpha"

    def on_loaded(self):
        self.state_path = str(self.options.get("state_path", self.state_path))
        self.health_path = str(self.options.get("health_path", self.health_path))
        try:
            self.refresh_seconds = max(3, int(self.options.get("refresh_seconds", 5)))
        except (TypeError, ValueError):
            self.refresh_seconds = 5
        logging.info("[heimdall-display] reference-layout dashboard enabled")

    def on_ui_setup(self, ui):
        self.ui = ui

        # Remove every stock Pwnagotchi widget so PWN, management IP, old status
        # text, and the small legacy face cannot remain underneath the new UI.
        for key in (
            "channel", "aps", "uptime", "line1", "line2", "face",
            "friend_face", "friend_name", "name", "status", "shakes", "mode",
            "sta",
        ):
            try:
                ui.remove_element(key)
            except Exception:
                pass

        ui.add_element("heimdall_dashboard", HeimdallDashboard(self))
        self._read_live_state()

        self._stop.clear()
        self._thread = threading.Thread(
            target=self._refresh_loop,
            name="heimdall-display",
            daemon=True,
        )
        self._thread.start()
        self._force_refresh()

    def on_ui_update(self, ui):
        self._read_live_state()

    def on_handshake(self, agent, filename, access_point, client_station):
        self._read_live_state()
        self.footer = "HANDSHAKE CAPTURED"
        self._force_refresh()

    def on_unload(self, ui):
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)

    def _refresh_loop(self):
        while not self._stop.wait(self.refresh_seconds):
            self._read_live_state()
            self._force_refresh()

    def _force_refresh(self):
        if self.ui is None:
            return
        try:
            # Updating this full-screen widget marks the state dirty and causes
            # the Waveshare partial refresh while ui.fps remains zero.
            self.ui.set("heimdall_dashboard", str(time.time()))
        except Exception:
            # Custom widgets do not expose a simple value on all inherited
            # Pwnagotchi runtimes; force the view update either way.
            pass
        try:
            self.ui.update(force=True)
        except Exception as exc:
            logging.debug("[heimdall-display] refresh skipped: %s", exc)

    def _read_live_state(self):
        wireless = self._read_json(self.state_path)
        health = self._read_json(self.health_path)

        self.networks = self._safe_int(wireless.get("networks"), 0)
        self.clients = self._safe_int(wireless.get("clients"), 0)
        self.captures = self._safe_int(wireless.get("captures"), 0)
        self.channel = str(wireless.get("channel", "--"))
        self.ssid = self._clean_ssid(wireless.get("ssid", "--"))
        self.temperature = self._temp_text(health.get("temperature_c"))
        self.battery_percent = self._battery_value(health.get("battery_percent"))
        self.uptime = self._uptime_text(health.get("uptime_seconds"))

        last_capture = self._safe_float(wireless.get("last_capture"), 0)
        if last_capture and time.time() - last_capture <= 15:
            self.footer = "HANDSHAKE CAPTURED"
        elif self.networks > 0:
            self.footer = "OBSERVING"
        else:
            self.footer = "BRIDGE LIVE"

    # ---------------------------- drawing helpers ----------------------------
    @staticmethod
    def _text_width(drawer, text, font):
        box = drawer.textbbox((0, 0), str(text), font=font)
        return box[2] - box[0]

    @classmethod
    def _center_text(cls, drawer, text, y, font):
        width = cls._text_width(drawer, text, font)
        drawer.text(((250 - width) // 2, y), text, font=font, fill=BLACK)

    @classmethod
    def _center_text_in(cls, drawer, text, x1, x2, y, font):
        width = cls._text_width(drawer, text, font)
        x = x1 + max(0, ((x2 - x1 + 1) - width) // 2)
        drawer.text((x, y), text, font=font, fill=BLACK)

    @staticmethod
    def _draw_face(drawer, cx, cy):
        # Two large eyes and a smile, scaled to the real 250x122 panel.
        for ex in (cx - 32, cx + 32):
            drawer.ellipse((ex - 13, cy - 15, ex + 13, cy + 11), fill=BLACK)
            drawer.ellipse((ex - 8, cy - 11, ex - 1, cy - 4), fill=WHITE)
            drawer.ellipse((ex + 5, cy + 3, ex + 8, cy + 6), fill=WHITE)
        drawer.arc((cx - 18, cy - 2, cx + 18, cy + 22), 20, 160, fill=BLACK, width=3)

    @staticmethod
    def _draw_wifi(drawer, cx, cy):
        drawer.arc((cx - 13, cy - 8, cx + 13, cy + 13), 205, 335, fill=BLACK, width=2)
        drawer.arc((cx - 9, cy - 3, cx + 9, cy + 11), 205, 335, fill=BLACK, width=2)
        drawer.ellipse((cx - 2, cy + 7, cx + 2, cy + 11), fill=BLACK)

    @staticmethod
    def _draw_terminal(drawer, x, y):
        drawer.rectangle((x, y, x + 20, y + 10), fill=BLACK)
        drawer.line((x + 4, y + 3, x + 8, y + 5, x + 4, y + 7), fill=WHITE, width=1)
        drawer.line((x + 10, y + 7, x + 15, y + 7), fill=WHITE, width=1)

    @staticmethod
    def _draw_target(drawer, cx, cy):
        drawer.ellipse((cx - 7, cy - 7, cx + 7, cy + 7), outline=BLACK, width=1)
        drawer.ellipse((cx - 2, cy - 2, cx + 2, cy + 2), fill=BLACK)
        drawer.line((cx - 10, cy, cx - 5, cy), fill=BLACK)
        drawer.line((cx + 5, cy, cx + 10, cy), fill=BLACK)
        drawer.line((cx, cy - 10, cx, cy - 5), fill=BLACK)
        drawer.line((cx, cy + 5, cx, cy + 10), fill=BLACK)

    @staticmethod
    def _draw_radio(drawer, cx, cy):
        drawer.line((cx, cy - 3, cx - 5, cy + 8, cx + 5, cy + 8, cx, cy - 3), fill=BLACK, width=1)
        drawer.line((cx, cy - 3, cx, cy + 9), fill=BLACK, width=1)
        drawer.arc((cx - 9, cy - 12, cx + 9, cy + 2), 200, 340, fill=BLACK, width=1)
        drawer.arc((cx - 13, cy - 16, cx + 13, cy + 6), 205, 335, fill=BLACK, width=1)

    @staticmethod
    def _draw_battery(drawer, x, y, value):
        drawer.rectangle((x, y, x + 15, y + 8), outline=BLACK, width=1)
        drawer.rectangle((x + 16, y + 2, x + 18, y + 6), fill=BLACK)
        if value is not None:
            fill = max(0, min(13, int(round(13 * value / 100.0))))
            if fill:
                drawer.rectangle((x + 2, y + 2, x + 1 + fill, y + 6), fill=BLACK)

    @staticmethod
    def _draw_thermometer(drawer, x, y):
        drawer.ellipse((x, y + 7, x + 7, y + 14), outline=BLACK, width=1)
        drawer.rectangle((x + 2, y, x + 5, y + 10), outline=BLACK, width=1)
        drawer.line((x + 3, y + 5, x + 3, y + 11), fill=BLACK, width=1)

    @staticmethod
    def _draw_check(drawer, cx, cy):
        drawer.ellipse((cx - 7, cy - 5, cx + 7, cy + 9), fill=BLACK)
        drawer.line((cx - 4, cy + 2, cx - 1, cy + 5, cx + 5, cy - 2), fill=WHITE, width=2)

    # ------------------------------ data helpers -----------------------------
    @staticmethod
    def _read_json(path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
                return data if isinstance(data, dict) else {}
        except (OSError, ValueError, TypeError):
            return {}

    @staticmethod
    def _clean_ssid(value):
        text = str(value or "--").strip()
        return text if text else "--"

    @staticmethod
    def _fit(text, max_chars):
        text = str(text)
        if len(text) <= max_chars:
            return text
        return text[: max(1, max_chars - 1)] + "~"

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
    def _battery_value(value):
        try:
            return max(0, min(100, int(round(float(value)))))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _uptime_text(seconds):
        try:
            seconds = int(seconds)
        except (TypeError, ValueError):
            return "--"
        days, rem = divmod(seconds, 86400)
        hours = rem // 3600
        if days:
            return "%dd %dh" % (days, hours)
        minutes = (rem % 3600) // 60
        return "%dh %dm" % (hours, minutes)
