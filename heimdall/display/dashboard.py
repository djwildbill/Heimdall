#!/usr/bin/env python3

import os
import sys
import time
import socket
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from PIL import Image, ImageDraw, ImageFont
from waveshare_epd import epd2in13_V2


NODE_ID = "OVN-002"
PERSONA = "Josh"
VERSION = "0.1.0-alpha"
MODE_FILE = "/var/lib/heimdall/mode"


def get_font(name, size):
    paths = [
        f"/usr/share/fonts/truetype/dejavu/{name}.ttf",
        f"/usr/share/fonts/dejavu/{name}.ttf",
    ]

    for path in paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return None


def get_mode():
    mode = read_text(MODE_FILE)
    if not mode:
        return "BOOT"

    modes = {
        "pwn": "PWN",
        "sentinel": "SENT",
        "recon": "RECN",
        "maintenance": "CMD",
    }

    return modes.get(mode.lower(), mode[:4].upper())


def get_temperature():
    value = read_text("/sys/class/thermal/thermal_zone0/temp")

    try:
        return f"{float(value) / 1000:.0f}C"
    except Exception:
        return "--C"


def get_uptime():
    value = read_text("/proc/uptime")

    try:
        seconds = int(float(value.split()[0]))
        hours, remainder = divmod(seconds, 3600)
        minutes = remainder // 60

        if hours >= 24:
            days, hours = divmod(hours, 24)
            return f"{days}d{hours:02}h"

        return f"{hours:02}:{minutes:02}"
    except Exception:
        return "--:--"


def get_ip():
    try:
        output = subprocess.check_output(
            ["hostname", "-I"],
            text=True,
        ).strip()

        if output:
            return output.split()[0]

    except Exception:
        pass

    return "OFFLINE"


def wifi_status():
    try:
        result = subprocess.check_output(
            ["iwgetid", "-r"],
            text=True,
        ).strip()

        return "UP" if result else "DOWN"

    except Exception:
        return "DOWN"


def battery():
    # PiSugar integration comes next.
    return "--%"


def render(epd):
    image = Image.new("1", (epd.height, epd.width), 255)
    draw = ImageDraw.Draw(image)

    title = get_font("DejaVuSans-Bold", 18)
    bold = get_font("DejaVuSans-Bold", 11)
    small = get_font("DejaVuSans", 9)

    # Header
    draw.text((5, 2), "HEIMDALL", font=title, fill=0)
    draw.text((196, 7), get_mode(), font=bold, fill=0)

    draw.line((5, 25, 244, 25), fill=0)

    # Identity
    draw.text((5, 31), NODE_ID, font=bold, fill=0)
    draw.text((75, 31), PERSONA, font=bold, fill=0)

    # Live status
    draw.text((5, 49), f"WIFI {wifi_status()}", font=small, fill=0)
    draw.text((89, 49), f"BAT {battery()}", font=small, fill=0)
    draw.text((168, 49), f"T {get_temperature()}", font=small, fill=0)

    draw.text((5, 65), f"IP {get_ip()}", font=small, fill=0)
    draw.text((168, 65), f"UP {get_uptime()}", font=small, fill=0)

    draw.line((5, 84, 244, 84), fill=0)

    draw.text((5, 91), "Watching the Bifrost...", font=bold, fill=0)
    draw.text((5, 111), f"v{VERSION}", font=small, fill=0)

    epd.display(epd.getbuffer(image))


def main():
    epd = epd2in13_V2.EPD()

    try:
        while True:
            epd.init(epd.FULL_UPDATE)
            render(epd)
            epd.sleep()

            # v0.1 uses conservative full refreshes.
            time.sleep(120)

    except KeyboardInterrupt:
        epd.sleep()


if __name__ == "__main__":
    main()
