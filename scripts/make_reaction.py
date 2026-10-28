"""Reaction-format editor: rebuilds the CapCut "reaction" edit from 4 clips.

  hook      -> background removed, bottom-left, over a freeze of the reacted video's first frame
  reaction  -> plays after the hook, cut right before the creator's own CTA
  pentwirl  -> background removed, small, bottom-right, muted, looped if short
  cta       -> full screen, dead air trimmed, "Comment "<Word>" for the full guide" on top

usage: make_reaction.py --hook H --reaction R --pentwirl P --cta C --out OUT.mp4 [--work DIR]
       [--cut SECONDS] [--keyword WORD]   (overrides for the auto-detected values)
"""
import argparse, json, os, re, subprocess, sys
import numpy as np

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
HOOK_SCALE = 0.69                  # tutorial: 69%, flush bottom-left
PEN_W, PEN_Y = 220, 1229           # tutorial: ~20% of width, flush right, lower third
EDGE = "format=gray,erosion,lut=y='clip((val-90)*255/(230-90),0,255)'"   # tighten matte edges
CTA_PHRASES = [r"if you'?re still", r"comment the word", r"\bcomment\b", r"if you want (the|more|my)",
               r"link in (my )?bio", r"follow (me )?for", r"\bdm me\b"]


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def duration(path):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                     capture_output=True, text=True).stdout)


def words(path, work):
    out = os.path.join(work, os.path.basename(path) + ".words.json")
    if not os.path.exists(out):
        run([sys.executable, os.path.join(SCRIPTS, "transcribe_words.py"), path, out], stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)
    return json.load(open(out))


def find_cut(reaction, ws, dur):
    """End the reacted video right before the creator comes back for their own CTA."""
    text, starts = "", []
    for i, w in enumerate(ws):
        starts.append((len(text), i)); text += w["w"].lower() + " "
    hit = None
    for pat in CTA_PHRASES:
        for m in re.finditer(pat, text):
            idx = max(i for pos, i in starts if pos <= m.start())
            if ws[idx]["s"] > dur * 0.6 and (hit is None or idx < hit):
                hit = idx
            break
    if hit is None:
        return dur, "no CTA phrase found; kept the whole video"
    # walk back to the start of that sentence
    while hit > 0 and not ws[hit - 1]["w"].endswith((".", "!", "?")) and ws[hit]["s"] - ws[hit - 1]["e"] < 0.35:
        hit -= 1
    speech = ws[hit]["s"]
    # a hard visual cut (creator popping back on screen) near the CTA speech wins if it comes first
    lo = max(0, speech - 2.5)
    log = run(["ffmpeg", "-v", "error", "-ss", str(lo), "-t", "3.5", "-i", reaction, "-vf",
               "select='gt(scene,0.25)',metadata=print:file=-", "-f", "null", "-"],
              capture_output=True, text=True).stdout
    scenes = [lo + float(t) for t in re.findall(r"pts_time:([\d.]+)", log)]
    scenes = [s for s in scenes if speech - 2.5 <= s <= speech + 0.6]
    cut = min([speech] + scenes) - 0.05
    why = f"CTA speech starts {speech:.2f}s (\"{' '.join(w['w'] for w in ws[hit:hit + 6])}...\")"
    if scenes:
        why += f", scene change at {min(scenes):.2f}s"
    return round(cut, 2), why


def find_keyword(ws):
    text = " ".join(w["w"] for w in ws)
    m = re.search(r"comment(?: the)?(?: words?)?[\s,\"']+([A-Za-z]+)", text, re.I)
    return m.group(1).capitalize() if m else None


def matte_hook(src, dst):
    """Full-res RVM cutout, then clean wall-coloured fringes (hook is big on screen and moves fast)."""
    if os.path.exists(dst):
        return
    raw = dst.replace(".mkv", "_raw.mkv")
    run([sys.executable, os.path.join(SCRIPTS, "matte.py"), src, raw, "--model", "resnet50", "--width", "1080"])
    run([sys.executable, os.path.join(SCRIPTS, "refine_matte.py"), src, raw, dst])


def matte_pen(src, dst, seconds):
    """The pen twirl is shown ~220px wide, so the light model at small size looks the same and is ~3x faster."""
    if os.path.exists(dst):
        return
    run([sys.executable, os.path.join(SCRIPTS, "matte.py"), src, dst, "--model", "mobilenetv3", "--width", "360",
         "--max-seconds", f"{seconds:.2f}"])


def speech_onset(path, near):
    """First moment the voice clearly rises above the room noise, searching from shortly before `near`."""
    raw = run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
              capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    db = 20 * np.log10(np.sqrt(np.convolve(x ** 2, np.ones(160) / 160, mode="valid"))[::160] + 1e-9)  # 10ms
    start = max(0, int((near - 0.4) * 100))
    noise = np.median(db[:max(start, 30)])
    for i in range(start, len(db) - 3):
        if (db[i:i + 3] > noise + 12).all():
            return i / 100
    return near


def main():
    ap = argparse.ArgumentParser()
    for k in ("hook", "reaction", "pentwirl", "cta", "out"):
        ap.add_argument("--" + k, required=True)
    ap.add_argument("--work", default=None)
    ap.add_argument("--cut", type=float)
    ap.add_argument("--keyword")
    a = ap.parse_args()
    work = a.work or os.path.splitext(a.out)[0] + "_work"
    os.makedirs(work, exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)

    hook_d = duration(a.hook)
    react_d = duration(a.reaction)
    pen_d = duration(a.pentwirl)

    # 1. where to end the reacted video
    if a.cut:
        cut, why = a.cut, "manual"
    else:
        cut, why = find_cut(a.reaction, words(a.reaction, work), react_d)
    print(f"reaction cut at {cut:.2f}s of {react_d:.2f}s: {why}")

    # 2. CTA: trim dead air, pick up the keyword
    cw = words(a.cta, work)
    cta_d = duration(a.cta)
    cta_in = max(0.0, speech_onset(a.cta, cw[0]["s"]) - 0.04)
    cta_out = min(cta_d, cw[-1]["e"] + 0.3)
    kw = a.keyword or find_keyword(cw)
    print(f"CTA trimmed to {cta_in:.2f}-{cta_out:.2f}s; keyword: {kw}")
    print("CTA says: " + " ".join(w["w"] for w in cw))
    text_png = os.path.join(work, "cta_text.png")
    if kw:
        run([sys.executable, os.path.join(SCRIPTS, "make_text.py"), f'Comment "{kw}"\\nfor the full guide',
             text_png], stdout=subprocess.DEVNULL)
    else:
        print("WARNING: no keyword heard in the CTA; no text added")

    # 3. background removal
    hook_a = os.path.join(work, "hook_alpha.mkv")
    pen_a = os.path.join(work, "pentwirl_alpha.mkv")
    pen_need = cut
    loop = ["-stream_loop", "-1"] if pen_d < pen_need else []
    matte_hook(a.hook, hook_a)
    matte_pen(a.pentwirl, pen_a, min(pen_d, pen_need + 0.5))

    # 4. assemble
    hook_w = round(W * HOOK_SCALE / 2) * 2
    fc = [
        # reacted video: freeze first frame for the hook's length, then play up to the cut
        f"[0:v]trim=0:{cut},setpts=PTS-STARTPTS,fps={FPS},scale={W}:{H}:flags=lanczos,setsar=1,"
        f"tpad=start_duration={hook_d}:start_mode=clone[bg]",
        # clip + matte are paired by frame number: mkv rounds timestamps to 1ms, which would otherwise
        # pair frame N with mask N-1 and leave a trail of wall behind fast movement
        f"[1:v]fps={FPS},setpts=N/{FPS}/TB,format=rgba[hs];[2:v]setpts=N/{FPS}/TB,format=gray[ha];"
        f"[hs][ha]alphamerge,scale={hook_w}:-2[hk]",
        f"[bg][hk]overlay=x=0:y=H-h:eof_action=pass[v1]",
        f"[3:v]fps={FPS},setpts=N/{FPS}/TB,scale={PEN_W}:-2,format=rgba[ps];"
        f"[4:v]setpts=N/{FPS}/TB,scale={PEN_W}:-2,{EDGE}[pa];"
        f"[ps][pa]alphamerge,trim=0:{pen_need},setpts=PTS-STARTPTS+{hook_d}/TB[pn]",
        f"[v1][pn]overlay=x=W-w:y={PEN_Y}:eof_action=pass,trim=0:{hook_d + cut},format=yuv420p[main]",
        f"[5:v]trim={cta_in}:{cta_out},setpts=PTS-STARTPTS,fps={FPS},scale={W}:{H}:flags=lanczos,setsar=1[c0]",
        (f"[c0][6:v]overlay=0:0:shortest=1,format=yuv420p[cta]" if kw else "[c0]format=yuv420p[cta]"),
        "[main][cta]concat=n=2:v=1:a=0[v]",
        # audio: hook -> reacted video -> CTA (pen twirl muted)
        f"[1:a]aresample=48000,aformat=channel_layouts=stereo,apad,atrim=0:{hook_d}[a0]",
        f"[0:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{cut},asetpts=PTS-STARTPTS[a1]",
        f"[5:a]aresample=48000,aformat=channel_layouts=stereo,atrim={cta_in}:{cta_out},asetpts=PTS-STARTPTS[a2]",
        "[a0][a1][a2]concat=n=3:v=0:a=1[a]",
    ]
    cmd = ["ffmpeg", "-v", "error", "-stats", "-y", "-i", a.reaction, "-i", a.hook, "-i", hook_a,
           *loop, "-i", a.pentwirl, *loop, "-i", pen_a, "-i", a.cta]
    if kw:
        cmd += ["-loop", "1", "-t", f"{cta_out - cta_in:.3f}", "-i", text_png]
    cmd += ["-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[a]", "-r", str(FPS), "-t", f"{hook_d + cut + cta_out - cta_in:.3f}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-profile:v", "high", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", a.out]
    run(cmd)
    print(f"done: {a.out} ({duration(a.out):.2f}s)")


if __name__ == "__main__":
    main()
