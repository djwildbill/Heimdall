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
PERSONA = "JOSH"
VERSION = "0.1.0-alpha"
POLL_SECONDS = 5
FORCE_REFRESH_SECONDS = 60
LOCK_PATH = "/tmp/heimdall-display.lock"
BOOT_TIME = time.time()


def get_font(name: str, size: int):
    paths = (
        f"/usr/share/fonts/truetype/dejavu/{name}.ttf",
        f"/usr/share/fonts/dejavu/{name}.ttf",
    )
    for path in paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def text_width(draw, text, font):
    box = draw.textbbox((0, 0), str(text), font=font)
    return box[2] - box[0]


def centered(draw, y, text, font, width=250, fill=0):
    x = max(0, (width - text_width(draw, text, font)) // 2)
    draw.text((x, y), text, font=font, fill=fill)


def clip_text(draw, text, font, max_width):
    text = str(text or "--")
    if text_width(draw, text, font) <= max_width:
        return text
    while text and text_width(draw, text + "…", font) > max_width:
        text = text[:-1]
    return (text + "…") if text else "--"


def choose_state(josh: HeimdallState, data: dict, previous_captures: int) -> int:
    """Give Josh a Pwnagotchi-like personality driven by real node activity."""
    wireless = data["wireless"]
    captures = wireless["captures"]
    now = time.time()
    last_activity = float(wireless.get("last_activity", 0) or 0)
    last_capture = float(wireless.get("last_capture", 0) or 0)
    activity_age = now - last_activity if last_activity else 999999
    mode = str(data.get("mode", "")).upper()

    battery_text = data["battery"].rstrip("%")
    try:
        if battery_text and battery_text != "--" and int(battery_text) <= 15:
            josh.low_battery()
            return captures
    except ValueError:
        pass

    # Boot personality: let Josh visibly wake up instead of instantly appearing idle.
    if now - BOOT_TIME < 25:
        josh.awakening()
        return captures

    # A new capture gets the strongest reaction and remains visible briefly.
    if captures > previous_captures or (last_capture and now - last_capture < 20):
        josh.capture()
        return captures

    # Heimdall operating modes have their own personalities.
    if mode.startswith("SURV"):
        josh.smart()
        return captures
    if mode.startswith("FIEL"):
        josh.motivated()
        return captures

    # Lots of nearby activity = focused/intense Josh.
    if wireless["networks"] >= 20 or wireless["clients"] >= 30:
        josh.intense()
    elif wireless["clients"] > 0:
        josh.observing(happy=True)
    elif wireless["networks"] > 0:
        josh.observing()
    elif data["wifi"] == "DOWN":
        josh.lonely()
    elif activity_age > 900:
        josh.sleeping()
    elif activity_age > 300:
        josh.bored()
    elif mode.startswith("CONN"):
        josh.friendly()
    else:
        josh.normal()

    return captures


def draw_dashboard(epd, josh: HeimdallState, data: dict):
    image = Image.new("1", (epd.height, epd.width), 255)
    draw = ImageDraw.Draw(image)

    header = get_font("DejaVuSans-Bold", 18)
    subhead = get_font("DejaVuSans-Bold", 9)
    face_font = get_font("DejaVuSans-Bold", 25)
    metric = get_font("DejaVuSans-Bold", 10)
    tiny_bold = get_font("DejaVuSans-Bold", 8)
    tiny = get_font("DejaVuSans", 7)

    wireless = data["wireless"]

    centered(draw, 0, f"{NODE_ID} {PERSONA}", header)
    centered(draw, 18, "HEIMDALL", subhead)
    draw.line((4, 29, 245, 29), fill=0)

    draw.line((58, 32, 58, 82), fill=0)
    draw.line((192, 32, 192, 82), fill=0)

    draw.text((5, 34), f"NET {wireless['networks']}", font=metric, fill=0)
    draw.text((5, 51), f"CLI {wireless['clients']}", font=metric, fill=0)
    draw.text((5, 68), f"CAP {wireless['captures']}", font=metric, fill=0)

    draw.text((197, 34), f"CH {wireless['channel']}", font=metric, fill=0)
    charge_mark = "+" if data.get("charging") is True else ""
    draw.text((197, 51), f"BAT {data['battery']}{charge_mark}", font=tiny_bold, fill=0)
    draw.text((197, 68), f"TMP {data['temperature']}", font=tiny_bold, fill=0)

    face = get_face(josh.state)
    face_x0, face_x1 = 60, 190
    face_w = text_width(draw, face, face_font)
    draw.text((face_x0 + max(0, (face_x1 - face_x0 - face_w) // 2), 43), face, font=face_font, fill=0)

    draw.line((4, 85, 245, 85), fill=0)

    draw.text((5, 88), "UP", font=tiny_bold, fill=0)
    draw.text((20, 88), data["uptime"], font=tiny_bold, fill=0)

    ssid = clip_text(draw, wireless.get("ssid", "--"), tiny_bold, 92)
    draw.text((67, 88), "SSID", font=tiny_bold, fill=0)
    draw.text((94, 88), ssid, font=tiny_bold, fill=0)

    draw.text((199, 88), f"HS {wireless['captures']}", font=tiny_bold, fill=0)

    draw.line((4, 102, 245, 102), fill=0)
    status = "HANDSHAKE CAPTURED" if wireless["last_capture"] and (time.time() - wireless["last_capture"] < 20) else josh.message
    status = clip_text(draw, str(status).upper(), tiny_bold, 178)
    draw.text((5, 106), status, font=tiny_bold, fill=0)
    draw.text((191, 108), f"v{VERSION}", font=tiny, fill=0)

    epd.display(epd.getbuffer(image))


def signature(data: dict, state: str):
    w = data["wireless"]
    return (
        state, data["temperature"], data["battery"], data.get("charging"), data["uptime"],
        w["networks"], w["clients"], w["captures"], str(w["channel"]),
        w.get("ssid"), w.get("last_handshake_ssid"), int(w.get("last_capture", 0)),
    )


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
    previous_signature = None
    last_refresh = 0.0

    try:
        while True:
            data = snapshot()
            previous_captures = choose_state(josh, data, previous_captures)
            current = signature(data, josh.state)
            now = time.time()
            if current != previous_signature or now - last_refresh >= FORCE_REFRESH_SECONDS:
                epd.init(epd.FULL_UPDATE)
                draw_dashboard(epd, josh, data)
                epd.sleep()
                previous_signature = current
                last_refresh = now
            time.sleep(POLL_SECONDS)
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
