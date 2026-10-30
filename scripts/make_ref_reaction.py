"""Referenced clipping reaction: every outfit x every hook x every reaction video, with the hook,
pen twirl and text hook placed to match a reference video.

Per video:
  hook      -> background removed, over a freeze of the reaction's first frame, scaled/positioned so
               Evan's face matches the face in that hook's reference
  reaction  -> plays in full; pen twirl (background removed, muted) placed by face to match the reference
  text hook -> reference text + emojis (PNG from make_text_hook.py) for the hook and the whole reaction
  intro     -> untouched;  demo -> untouched (conformed to 1080x1920/30fps)

usage: make_ref_reaction.py SPEC.json
SPEC: {
  "out": "jobs/x/out", "work": "jobs/x/work", "demo": "...mp4",
  "outfits":   {"grey_hat": {"hooks": {"watchthis": "...", "cantbelieve": "..."}, "intro": "...",
                             "pen": "...", "green": false}},
  "hook_refs": {"watchthis": {"face": [size, cx, cy]}, "cantbelieve": "per_reaction"},
  "reactions": {"spend_money_blur": {"file": "...", "text": "...png", "pen_face": [size, cx, cy],
                                     "cantbelieve_face": [size, cx, cy]}}
}
Face boxes are on the 1080x1920 canvas: [face width, face centre x, face centre y].
"""
import json, os, subprocess, sys, time
import cv2, numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_reaction import SCRIPTS, W, H, FPS, EDGE, run, duration
from make_clipping_reaction import ENC, CONFORM, AUDIO, render_tail, join

CASCADE = os.path.expanduser("~/.cache/reaction-format/models/haarcascade_frontalface_default.xml")
_casc = None


def face_of(clip, samples=10, t_max=None):
    """Median face box [width, cx, cy] of the main face, on the 1080x1920 canvas."""
    global _casc
    _casc = _casc or cv2.CascadeClassifier(CASCADE)
    d = duration(clip) if t_max is None else min(t_max, duration(clip))
    found = []
    for t in np.linspace(0.05, d - 0.05, samples):
        b = run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", clip, "-frames:v", "1", "-vf",
                 f"scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
        f = _casc.detectMultiScale(np.frombuffer(b, np.uint8).reshape(H, W), 1.1, 6, minSize=(150, 150))
        if len(f):
            x, y, w, h = max(f, key=lambda r: r[2])
            found.append((w, x + w / 2, y + h / 2))
    a = np.array(found)
    a = a[a[:, 0] > 0.6 * np.median(a[:, 0])]       # drop stray small detections
    return np.median(a, axis=0)


def place(evan, ref, flush_bottom, cover_width=False):
    """Scale and top-left so Evan's face lands on the reference face. cover_width keeps the clip at least
    full width so its side edges (cut through the shirt) never show, as in a full-screen reference."""
    s = ref[0] / evan[0]
    x, y = ref[1] - s * evan[1], ref[2] - s * evan[2]
    if cover_width:
        s = max(s, 1.0)
        x, y = ref[1] - s * evan[1], ref[2] - s * evan[2]
        x = min(0, max(x, W - s * W))
    if flush_bottom and y + s * H < H:              # never leave a floating cut edge under a hook
        y = H - s * H
    return s, round(x), round(y)


def matte(src, dst, model, width, seconds=None):
    if not os.path.exists(dst):
        cmd = [sys.executable, os.path.join(SCRIPTS, "matte.py"), src, dst, "--model", model, "--width", str(width)]
        if seconds:
            cmd += ["--max-seconds", f"{seconds:.2f}"]
        run(cmd, stdout=subprocess.DEVNULL)


def render_head(hook, hook_a, hook_pl, green, reaction, pen, pen_a, pen_pl, text_png, out):
    hook_d, react_d, pen_d = duration(hook), duration(reaction), duration(pen)
    loop = ["-stream_loop", "-1"] if pen_d < react_d else []
    hs, hx, hy = hook_pl
    ps, px, py = pen_pl
    hw, pw = round(W * hs / 2) * 2, round(W * ps / 2) * 2
    despill = ",despill=type=green" if green else ""
    total = hook_d + react_d
    fc = ";".join([
        f"[0:v]{CONFORM},tpad=start_duration={hook_d}:start_mode=clone[bg]",
        # clip + matte paired by frame number (mkv rounds timestamps to 1ms -> off-by-one masks)
        f"[1:v]fps={FPS},setpts=N/{FPS}/TB{despill},format=rgba[hs];[2:v]setpts=N/{FPS}/TB,{EDGE}[ha];"
        f"[hs][ha]alphamerge,scale={hw}:-2[hk]",
        f"[bg][hk]overlay=x={hx}:y={hy}:eof_action=pass[v1]",
        f"[3:v]fps={FPS},setpts=N/{FPS}/TB,scale={pw}:-2,format=rgba[ps];"
        f"[4:v]setpts=N/{FPS}/TB,scale={pw}:-2,{EDGE}[pa];"
        f"[ps][pa]alphamerge,trim=0:{react_d},setpts=PTS-STARTPTS+{hook_d}/TB[pn]",
        f"[v1][pn]overlay=x={px}:y={py}:eof_action=pass[v2]",
        f"[v2][5:v]overlay=0:0:shortest=1,trim=0:{total},format=yuv420p[v]",
        f"[1:a]{AUDIO},apad,atrim=0:{hook_d}[a0];[0:a]{AUDIO},atrim=0:{react_d},asetpts=PTS-STARTPTS[a1]",
        "[a0][a1]concat=n=2:v=0:a=1[a]",
    ])
    run(["ffmpeg", "-v", "error", "-y", "-i", reaction, "-i", hook, "-i", hook_a, *loop, "-i", pen, *loop,
         "-i", pen_a, "-loop", "1", "-t", f"{total:.3f}", "-i", text_png, "-filter_complex", fc,
         "-map", "[v]", "-map", "[a]", "-t", f"{total:.3f}", *ENC, out])


def main():
    spec = json.load(open(sys.argv[1]))
    out, work = spec["out"], spec["work"]
    os.makedirs(out, exist_ok=True); os.makedirs(work, exist_ok=True)
    reactions = spec["reactions"]
    longest = max(duration(r["file"]) for r in reactions.values())
    t0 = time.time()

    prepared = {}
    for oname, o in spec["outfits"].items():
        p = {"hooks": {}}
        for hname, hfile in o["hooks"].items():
            a = os.path.join(work, f"{oname}_{hname}_alpha.mkv")
            matte(hfile, a, "resnet50", 1080)
            p["hooks"][hname] = (hfile, a, face_of(hfile, 8))
        p["pen_a"] = os.path.join(work, f"{oname}_pen_alpha.mkv")
        matte(o["pen"], p["pen_a"], "mobilenetv3", 360, min(duration(o["pen"]), longest + 0.5))
        p["pen_face"] = face_of(o["pen"], 10, t_max=longest)
        p["tail"] = os.path.join(work, f"{oname}_tail.mp4")
        render_tail(o["intro"], spec["demo"], p["tail"])
        prepared[oname] = p
        print(f"  {oname} prepared ({time.time() - t0:.0f}s): " +
              ", ".join(f"{h} face {v[2].round().astype(int).tolist()}" for h, v in p["hooks"].items()) +
              f", pen face {p['pen_face'].round().astype(int).tolist()}", flush=True)

    for oname, p in prepared.items():
        green = spec["outfits"][oname].get("green", False)
        for hname, (hfile, hook_a, hface) in p["hooks"].items():
            for rname, r in reactions.items():
                ref = spec["hook_refs"][hname]
                ref_face = r[f"{hname}_face"] if ref == "per_reaction" else ref["face"]
                hook_pl = place(hface, ref_face, flush_bottom=True,
                                cover_width=ref != "per_reaction" and ref.get("cover_width", False))
                pen_pl = place(p["pen_face"], r["pen_face"], flush_bottom=False)
                name = f"{rname}__{oname}__{hname}"
                head = os.path.join(work, name + "_head.mp4")
                render_head(hfile, hook_a, hook_pl, green, r["file"], spec["outfits"][oname]["pen"],
                            p["pen_a"], pen_pl, r["text"], head)
                final = os.path.join(out, name + ".mp4")
                join([head, p["tail"]], final, work)
                print(f"  done {name}.mp4 ({duration(final):.1f}s) hook {hook_pl[0]:.2f}x@{hook_pl[1:]}, "
                      f"pen {pen_pl[0]:.3f}x@{pen_pl[1:]} at {time.time() - t0:.0f}s", flush=True)
    print(f"all done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
