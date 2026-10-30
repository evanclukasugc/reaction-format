"""Render a top-of-video text hook (TikTok Sans, white with a thin black outline) plus emoji images
onto a transparent 1080x1920 PNG, at a position measured from a reference video.

usage: make_text_hook.py OUT.png --text "He's living in 3026" --box X0 Y0 X1 Y1 \
           [--emoji IMG X Y ...] [--weight 620] [--stroke 3]
  --box     the text's bounding box (outline included) on the 1080x1920 canvas; the font size is
            chosen so the text fills that width, and it's vertically centred in the box
  --emoji   an emoji image (RGBA, already at final size) pasted with its top-left at X Y
"""
import argparse, os
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts", "TikTokSans.ttf")

ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("--text", required=True)
ap.add_argument("--box", type=int, nargs=4, required=True)
ap.add_argument("--emoji", nargs=3, action="append", default=[])
ap.add_argument("--weight", type=int, default=620)
ap.add_argument("--stroke", type=int, default=3)
ap.add_argument("--width", type=int, default=100, help="font width axis (75-150)")
a = ap.parse_args()

axes = TTFont(FONT)["fvar"].axes
def font(size):
    f = ImageFont.truetype(FONT, size)
    f.set_variation_by_axes([{"wght": a.weight, "wdth": a.width}.get(x.axisTag, x.defaultValue) for x in axes])
    return f

x0, y0, x1, y1 = a.box
img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
size = 100
for _ in range(3):   # converge on the size whose outlined width matches the box
    b = d.textbbox((0, 0), a.text, font=font(size), stroke_width=a.stroke)
    size = round(size * (x1 - x0) / (b[2] - b[0]))
f = font(size)
b = d.textbbox((0, 0), a.text, font=f, stroke_width=a.stroke)
x = x0 - b[0]
y = (y0 + y1) / 2 - (b[1] + b[3]) / 2
d.text((x, y), a.text, font=f, fill="white", stroke_width=a.stroke, stroke_fill="black")
for path, ex, ey in a.emoji:
    e = Image.open(path).convert("RGBA")
    img.alpha_composite(e, (int(ex), int(ey)))
img.save(a.out)
print(f"font size {size}px")
