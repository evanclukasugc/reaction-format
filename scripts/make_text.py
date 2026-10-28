"""Render the CTA text overlay as a transparent 1080x1920 PNG in TikTok Sans (CapCut "Classic" look).
usage: make_text.py "Comment \"Studio\"\nfor the full guide" out.png"""
import os, sys
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts", "TikTokSans.ttf")
W, H = 1080, 1920
CENTER_Y = 375          # matches the tutorial: text sits above the head
TARGET_W = 800          # first line spans ~74% of the frame width in the tutorial
STROKE = 7
AXES = {"wght": 550, "wdth": 104, "opsz": 36, "slnt": 0}

text = sys.argv[1].replace("\\n", "\n")
axes = TTFont(FONT)["fvar"].axes

def font(size):
    f = ImageFont.truetype(FONT, size)
    f.set_variation_by_axes([AXES.get(a.axisTag, a.defaultValue) for a in axes])
    return f

d = ImageDraw.Draw(Image.new("RGBA", (W, H)))
widest = max(text.split("\n"), key=lambda l: d.textlength(l, font=font(100)))
size = int(100 * TARGET_W / d.textlength(widest, font=font(100)))
f = font(size)
img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
box = d.multiline_textbbox((0, 0), text, font=f, align="center", spacing=-4, stroke_width=STROKE)
y = CENTER_Y - (box[3] - box[1]) // 2 - box[1]
d.multiline_text((W // 2, y), text, font=f, fill="white", stroke_width=STROKE, stroke_fill="black",
                 align="center", anchor="ma", spacing=-4)
img.save(sys.argv[2])
print(f"font size {size}px")
