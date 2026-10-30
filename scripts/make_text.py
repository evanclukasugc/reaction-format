"""Render the CTA text overlay as a transparent 1080x1920 PNG in CapCut "Classic" (TikTok Display Medium,
white with a black outline, no bold), Evan's default for all text since 2026-10-30.
usage: make_text.py "Comment \"Studio\"\nfor the full guide" out.png"""
import os, sys
from PIL import Image, ImageDraw, ImageFont

FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts", "TikTokDisplay-Medium.ttf")
W, H = 1080, 1920
CENTER_Y = 375          # matches the tutorial: text sits above the head
TARGET_W = 800          # first line spans ~74% of the frame width in the tutorial
STROKE_RATIO = 0.056    # CapCut Classic outline; 5px at ~89px matched the reference

text = sys.argv[1].replace("\\n", "\n")
def font(size):
    return ImageFont.truetype(FONT, size)

d = ImageDraw.Draw(Image.new("RGBA", (W, H)))
widest = max(text.split("\n"), key=lambda l: d.textlength(l, font=font(100)))
size = int(100 * TARGET_W / d.textlength(widest, font=font(100)))
f = font(size)
STROKE = max(2, round(size * STROKE_RATIO))
img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
box = d.multiline_textbbox((0, 0), text, font=f, align="center", spacing=-4, stroke_width=STROKE)
y = CENTER_Y - (box[3] - box[1]) // 2 - box[1]
d.multiline_text((W // 2, y), text, font=f, fill="white", stroke_width=STROKE, stroke_fill="black",
                 align="center", anchor="ma", spacing=-4)
img.save(sys.argv[2])
print(f"font size {size}px")
