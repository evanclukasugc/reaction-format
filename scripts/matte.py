"""Background removal with Robust Video Matting (ONNX). Writes a grayscale alpha-matte video
matching the input's frame count; combine with the source via ffmpeg alphamerge.
usage: matte.py in.mov out_alpha.mkv --model resnet50|mobilenetv3 --width 1080 [--max-seconds N]"""
import argparse, os, subprocess, json, time
import numpy as np, onnxruntime as ort

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("dst")
ap.add_argument("--model", default="mobilenetv3")
ap.add_argument("--width", type=int, default=540)
ap.add_argument("--max-seconds", type=float, default=None)
a = ap.parse_args()

info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
    "stream=width,height", "-of", "json", a.src], capture_output=True, check=True).stdout)["streams"][0]
W = a.width; H = round(info["height"] * W / info["width"] / 2) * 2
dec = ["ffmpeg", "-v", "error"] + (["-t", str(a.max_seconds)] if a.max_seconds else []) + \
      ["-i", a.src, "-vf", f"fps=30,scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
enc = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W}x{H}", "-r", "30",
       "-i", "-", "-c:v", "ffv1", a.dst]
pd = subprocess.Popen(dec, stdout=subprocess.PIPE); pe = subprocess.Popen(enc, stdin=subprocess.PIPE)

MODELS = os.path.expanduser(os.environ.get("REACTION_MODELS", "~/.cache/reaction-format/models"))
sess = ort.InferenceSession(os.path.join(MODELS, f"rvm_{a.model}_fp32.onnx"), providers=["CPUExecutionProvider"])
rec = [np.zeros((1, 1, 1, 1), np.float32)] * 4
# RVM recommends the downsampled side to be ~256-512px
ratio = np.array([min(1.0, 512 / max(W, H))], np.float32)
def frames():
    while True:
        buf = pd.stdout.read(W * H * 3)
        if len(buf) < W * H * 3: return
        yield np.frombuffer(buf, np.uint8).reshape(H, W, 3).transpose(2, 0, 1)[None].astype(np.float32) / 255

def step(src):
    global rec
    fgr, pha, *rec = sess.run(None, {"src": src, "r1i": rec[0], "r2i": rec[1], "r3i": rec[2], "r4i": rec[3],
                                     "downsample_ratio": ratio})
    return pha

# The recurrent state is poor on the first frames; warm it up on the opening second, then start over.
it = frames(); head = [f for _, f in zip(range(30), it)]
for _ in range(2):
    for f in head: step(f)
n, t0 = 0, time.time()
import itertools
for src in itertools.chain(head, it):
    pha = step(src)
    pe.stdin.write((pha[0, 0] * 255).clip(0, 255).astype(np.uint8).tobytes())
    n += 1
    if n % 100 == 0: print(f"{n} frames, {n / (time.time() - t0):.1f} fps", flush=True)
pe.stdin.close(); pe.wait(); pd.wait()
print(f"done: {n} frames in {time.time() - t0:.0f}s")
