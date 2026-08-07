#!/usr/bin/env python3

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from PIL import Image, ImageDraw, ImageFont
from waveshare_epd import epd2in13_V2


def font(name, size):
    paths = [
        f"/usr/share/fonts/truetype/dejavu/{name}.ttf",
        f"/usr/share/fonts/dejavu/{name}.ttf",
    ]

    for path in paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


epd = epd2in13_V2.EPD()

try:
    epd.init(epd.FULL_UPDATE)
    epd.Clear(0xFF)

    image = Image.new("1", (epd.height, epd.width), 255)
    draw = ImageDraw.Draw(image)

    big = font("DejaVuSans-Bold", 19)
    medium = font("DejaVuSans-Bold", 13)
    small = font("DejaVuSans", 10)

    draw.text((7, 3), "HEIMDALL", font=big, fill=0)
    draw.line((7, 27, 242, 27), fill=0)

    draw.text((7, 34), "OVN-002", font=medium, fill=0)
    draw.text((7, 52), "Persona: Josh", font=small, fill=0)
    draw.text((7, 68), "v0.1.0-alpha", font=small, fill=0)

    draw.line((7, 88, 242, 88), fill=0)
    draw.text((7, 96), "Watching the Bifrost...", font=small, fill=0)

    epd.display(epd.getbuffer(image))

finally:
    epd.sleep()
