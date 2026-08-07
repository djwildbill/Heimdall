#!/usr/bin/env python3

from __future__ import annotations

import fcntl
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

for candidate in (
    os.environ.get("HEIMDALL_WAVESHARE_LIB"),
    os.path.expanduser("~/e-Paper/RaspberryPi_JetsonNano/python/lib"),
):
    if candidate and os.path.isdir(candidate) and candidate not in sys.path:
        sys.path.insert(0, candidate)

from PIL import Image, ImageDraw, ImageFont
from waveshare_epd import epd2in13_V2

from heimdall.display.faces import get_face
from heimdall.display.state import HeimdallState
from heimdall.display.telemetry import snapshot

NODE_ID = "OVN-002"
PERSONA = "Josh"
VERSION = "0.1.0-alpha"
REFRESH_SECONDS = 60
LOCK_PATH = "/tmp/heimdall-display.lock"


def get_font(name: str, size: int):
    paths = (
        f"/usr/share/fonts/truetype/dejavu/{name}.ttf",
        f"/usr/share/fonts/dejavu/{name}.ttf",
    )
    for path in paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def choose_state(josh: HeimdallState, data: dict, previous_captures: int) -> int:
    wireless = data["wireless"]
    captures = wireless["captures"]

    battery_text = data["battery"].rstrip("%")
    try:
        if battery_text and battery_text != "--" and int(battery_text) <= 15:
            josh.low_battery()
            return captures
    except ValueError:
        pass

    if captures > previous_captures:
        josh.capture()
    elif wireless["networks"] >= 20 or wireless["clients"] >= 30:
        josh.intense()
    elif wireless["networks"] > 0:
        josh.observing(happy=wireless["clients"] > 0)
    elif data["wifi"] == "DOWN":
        josh.bored()
    else:
        josh.normal()

    return captures


def draw_dashboard(epd, josh: HeimdallState, data: dict):
    image = Image.new("1", (epd.height, epd.width), 255)
    draw = ImageDraw.Draw(image)

    title = get_font("DejaVuSans-Bold", 16)
    face_font = get_font("DejaVuSans", 19)
    bold = get_font("DejaVuSans-Bold", 10)
    small = get_font("DejaVuSans", 8)

    wireless = data["wireless"]

    draw.text((4, 1), "HEIMDALL", font=title, fill=0)
    draw.text((205, 4), data["mode"], font=bold, fill=0)
    draw.line((4, 22, 245, 22), fill=0)

    draw.text((4, 27), f"{NODE_ID}  {PERSONA}", font=bold, fill=0)
    draw.text((118, 25), get_face(josh.state), font=face_font, fill=0)

    draw.text((4, 52), f"NET {wireless['networks']:>2}", font=bold, fill=0)
    draw.text((65, 52), f"CLI {wireless['clients']:>2}", font=bold, fill=0)
    draw.text((126, 52), f"CAP {wireless['captures']:>2}", font=bold, fill=0)
    draw.text((188, 52), f"CH {str(wireless['channel']):>2}", font=bold, fill=0)

    charge_mark = "+" if data.get("charging") is True else ""
    draw.text((4, 68), f"BAT {data['battery']}{charge_mark}", font=small, fill=0)
    draw.text((72, 68), f"TEMP {data['temperature']}", font=small, fill=0)
    draw.text((144, 68), f"UP {data['uptime']}", font=small, fill=0)

    draw.line((4, 84, 245, 84), fill=0)
    draw.text((4, 90), josh.message[:35], font=bold, fill=0)
    draw.text((4, 108), f"WiFi {data['wifi']}  {data['ip']}", font=small, fill=0)
    draw.text((190, 108), f"v{VERSION}", font=small, fill=0)

    epd.display(epd.getbuffer(image))


def main():
    lock = open(LOCK_PATH, "w", encoding="utf-8")
    try:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("Heimdall display is already running.", file=sys.stderr)
        return 2

    epd = epd2in13_V2.EPD()
    josh = HeimdallState()
    previous_captures = 0

    try:
        while True:
            data = snapshot()
            previous_captures = choose_state(josh, data, previous_captures)
            epd.init(epd.FULL_UPDATE)
            draw_dashboard(epd, josh, data)
            epd.sleep()
            time.sleep(REFRESH_SECONDS)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            epd.sleep()
        except Exception:
            pass
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
