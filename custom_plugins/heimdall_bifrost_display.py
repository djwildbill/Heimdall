"""Heimdall Bifrost e-paper update display.

Renders a full-screen monochrome Bifrost travel/reboot card over Josh's normal UI
when /var/lib/heimdall/bifrost-display.json requests an update state.

The final REBOOTING frame is intentionally persistent so an e-paper display keeps
showing it while the Pi is rebooting. After boot, bifrost-postboot replaces it
with RETURNED and Josh resumes normal UI after the hold period.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path

from PIL import ImageDraw, ImageFont
import pwnagotchi.plugins as plugins

STATE_PATH = Path('/var/lib/heimdall/bifrost-display.json')


class HeimdallBifrostDisplay(plugins.Plugin):
    __author__ = 'Project Odin'
    __version__ = '0.1.1'
    __license__ = 'GPL3'
    __description__ = 'Bifrost update/reboot animation for Josh e-paper display.'

    def __init__(self):
        self._ui = None
        self._last_mtime = 0.0
        self._state = {}
        self._stop = threading.Event()
        self._watcher = None

    def on_loaded(self):
        logging.info('[bifrost-display] loaded')

    def on_ui_setup(self, ui):
        self._ui = ui
        ui.on_render(self._render)
        self._load_state(force=True)
        if self._watcher is None:
            self._watcher = threading.Thread(target=self._watch_state, name='bifrost-display', daemon=True)
            self._watcher.start()

    def on_unload(self, ui=None):
        self._stop.set()

    def on_ui_update(self, ui):
        self._load_state()

    def _watch_state(self):
        while not self._stop.wait(0.75):
            changed = self._load_state()
            if changed and self._ui is not None:
                try:
                    self._ui.update(force=True)
                except Exception as exc:
                    logging.debug('[bifrost-display] deferred refresh: %s', exc)

    def _load_state(self, force=False):
        previous = dict(self._state or {})
        try:
            st = STATE_PATH.stat()
            if not force and st.st_mtime == self._last_mtime:
                return False
            self._last_mtime = st.st_mtime
            self._state = json.loads(STATE_PATH.read_text(encoding='utf-8'))
        except FileNotFoundError:
            self._state = {}
        except Exception as exc:
            logging.warning('[bifrost-display] state read failed: %s', exc)
            self._state = {}
        return force or self._state != previous

    @staticmethod
    def _font(size=12):
        candidates = [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        ]
        for path in candidates:
            try:
                return ImageFont.truetype(path, size=size)
            except OSError:
                pass
        return ImageFont.load_default()

    @staticmethod
    def _center(draw, width, y, text, font):
        try:
            box = draw.textbbox((0, 0), text, font=font)
            tw = box[2] - box[0]
        except AttributeError:
            tw = draw.textsize(text, font=font)[0]
        draw.text(((width - tw) // 2, y), text, font=font, fill=0)

    @staticmethod
    def _viking(draw, x, y, scale=1):
        # Tiny driver-independent monochrome Viking: horned helm, head, body,
        # shield, sword and walking legs. Intentionally simple for 1-bit e-ink.
        s = max(1, int(scale))
        draw.ellipse((x-6*s, y-5*s, x+6*s, y+7*s), outline=0, width=s)
        draw.arc((x-9*s, y-11*s, x-1*s, y-1*s), 185, 345, fill=0, width=s)
        draw.arc((x+1*s, y-11*s, x+9*s, y-1*s), 195, 355, fill=0, width=s)
        draw.line((x-6*s, y-3*s, x+6*s, y-3*s), fill=0, width=s)
        draw.line((x, y+7*s, x, y+23*s), fill=0, width=s)
        draw.line((x, y+12*s, x-9*s, y+18*s), fill=0, width=s)
        draw.line((x, y+12*s, x+10*s, y+16*s), fill=0, width=s)
        draw.ellipse((x-15*s, y+11*s, x-6*s, y+22*s), outline=0, width=s)
        draw.line((x+10*s, y+16*s, x+16*s, y+3*s), fill=0, width=s)
        draw.line((x+14*s, y+3*s, x+18*s, y+3*s), fill=0, width=s)
        draw.line((x, y+23*s, x-8*s, y+31*s), fill=0, width=s)
        draw.line((x, y+23*s, x+8*s, y+31*s), fill=0, width=s)

    def _render(self, canvas):
        state = dict(self._state or {})
        phase = str(state.get('phase', '')).upper()
        if phase in ('', 'IDLE'):
            return

        draw = ImageDraw.Draw(canvas)
        width, height = canvas.size
        draw.rectangle((0, 0, width, height), fill=255)

        title_font = self._font(max(12, min(20, height // 7)))
        body_font = self._font(max(9, min(14, height // 10)))
        small_font = self._font(max(8, min(11, height // 12)))

        self._center(draw, width, 2, 'BIFROST', title_font)

        bridge_y = max(38, height // 2)
        draw.line((8, bridge_y+18, width-8, bridge_y+18), fill=0, width=2)
        draw.line((8, bridge_y+22, width-8, bridge_y+22), fill=0, width=1)
        for offset in (0, 4, 8):
            draw.arc((8+offset, bridge_y-18+offset, width-8-offset, bridge_y+34-offset), 200, 340, fill=0, width=1)

        progress = int(state.get('progress', 0) or 0)
        progress = max(0, min(100, progress))
        if phase in ('REBOOTING', 'BETWEEN_WORLDS'):
            vx = width // 2
        elif phase == 'RETURNED':
            vx = width - 28
        else:
            vx = 20 + int((width - 48) * progress / 100.0)
        self._viking(draw, vx, max(31, bridge_y-8), scale=1)

        if phase == 'REBOOTING':
            message = 'BETWEEN WORLDS'
            sub = 'Josh is rebooting...'
            foot = 'Do not power off'
        elif phase == 'RETURNED':
            message = 'RETURNED FROM BIFROST'
            sub = str(state.get('message') or 'Systems ready')
            foot = 'Welcome back, Josh.'
        elif phase == 'FAILED':
            message = 'BIFROST UNSTABLE'
            sub = str(state.get('message') or 'Update paused')
            foot = 'Safe state preserved'
        else:
            message = str(state.get('label') or phase.replace('_', ' '))
            sub = str(state.get('message') or f'{progress}%')
            foot = f'{progress}% complete'

        text_y = min(height-38, bridge_y+27)
        self._center(draw, width, text_y, message[:32], body_font)
        if height >= 105:
            self._center(draw, width, text_y+14, sub[:42], small_font)
        if height >= 120:
            self._center(draw, width, height-13, foot[:42], small_font)
