"""Clean up a rough alpha matte against a plain, light background (e.g. a white/grey wall).

Wall-looking pixels (bright and colourless) inside the cutout are made transparent when they connect
to the real background through other wall-looking pixels; enclosed ones (teeth, eye whites) are kept.
A guided filter then snaps the edge to the real image edges.
usage: refine_matte.py src.mov alpha_in.mkv alpha_out.mkv"""
import json, subprocess, sys
import cv2, numpy as np

SAT_LO, SAT_HI = 0.10, 0.20   # saturation ramp: below LO = wall-like, above HI = keep
VAL_LO, VAL_HI = 0.45, 0.60   # brightness ramp: above HI = wall-like

src, a_in, a_out = sys.argv[1:4]
info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
    "stream=width,height", "-of", "json", src], capture_output=True, check=True).stdout)["streams"][0]
W, H = info["width"], info["height"]

def reader(path, fmt, ch, vf):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-vf", f"{vf},scale={W}:{H}", "-f", "rawvideo",
                          "-pix_fmt", fmt, "-"], stdout=subprocess.PIPE)
    while True:
        b = p.stdout.read(W * H * ch)
        if len(b) < W * H * ch: return
        yield np.frombuffer(b, np.uint8).reshape(H, W, ch) if ch > 1 else np.frombuffer(b, np.uint8).reshape(H, W)

enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W}x{H}",
                        "-r", "30", "-i", "-", "-c:v", "ffv1", a_out], stdin=subprocess.PIPE)
ramp = lambda x, lo, hi: np.clip((x - lo) / (hi - lo), 0, 1)
n = 0
for rgb, a in zip(reader(src, "rgb24", 3, "fps=30"), reader(a_in, "gray", 1, "setpts=N/30/TB")):
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32) / 255
    wall = (1 - ramp(hsv[..., 1], SAT_LO, SAT_HI)) * ramp(hsv[..., 2], VAL_LO, VAL_HI)
    # regions of wall-like pixels that touch the background (alpha ~ 0) are background
    walls = ((wall > 0.3) | (a < 30)).astype(np.uint8)
    _, labels = cv2.connectedComponents(walls, connectivity=8)
    bg_labels = np.unique(labels[(a < 30) & (walls > 0)])
    connected = np.isin(labels, bg_labels[bg_labels > 0])
    keep = np.where(connected, 1 - wall, 1.0)
    alpha = a.astype(np.float32) / 255 * keep
    alpha = cv2.ximgproc.guidedFilter(rgb, alpha, 6, 1e-3)
    enc.stdin.write((np.clip(alpha, 0, 1) * 255).astype(np.uint8).tobytes())
    n += 1
enc.stdin.close(); enc.wait()
print(f"refined {n} frames")
