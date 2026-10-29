"""Clipping-reaction format: every reaction video x every outfit, in one batch.

Per video:
  hook      -> background removed, bottom-left, over a freeze of the reaction video's first frame
  reaction  -> plays in full (these have no CTA of their own), pen twirl background-removed bottom-right, muted
  intro     -> Evan's "let me show you how to clip" clip, untouched
  demo      -> the streamer demo, untouched (only conformed to 1080x1920 / 30fps)

Work is shared to keep the batch fast: cutouts are made once per outfit, and intro+demo ("tail") is
rendered once per outfit; each video only renders its own hook+reaction part and then the parts are
joined without re-encoding.

usage: make_clipping_reaction.py --outfits DIR [DIR ...] --reactions DIR --demo FILE --out DIR [--work DIR]
  Each outfit DIR holds 3 clips; they're told apart by length: shortest = hook ("watch this"),
  middle = intro ("let me show you..."), longest = pen twirl.
"""
import argparse, os, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_reaction import (SCRIPTS, W, H, FPS, HOOK_SCALE, PEN_W, PEN_Y, EDGE, run, duration, matte_pen)

VIDEO_EXT = (".mov", ".mp4", ".m4v")
# identical encode settings for every part so they can be joined without re-encoding
ENC = ["-c:v", "libx264", "-preset", "faster", "-crf", "18", "-profile:v", "high", "-pix_fmt", "yuv420p",
       "-r", str(FPS), "-video_track_timescale", "15360", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]
CONFORM = f"fps={FPS},scale={W}:{H}:flags=lanczos:force_original_aspect_ratio=decrease," \
          f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p"
AUDIO = "aresample=48000,aformat=channel_layouts=stereo"


def videos(d):
    return sorted(os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith(VIDEO_EXT))


def sort_outfit(d):
    clips = sorted(videos(d), key=duration)
    if len(clips) != 3:
        sys.exit(f"{d}: expected 3 clips (hook, intro, pen twirl), found {len(clips)}")
    return dict(zip(("hook", "intro", "pen"), clips))


def matte_hook_raw(src, dst):
    """Full-res RVM cutout. No wall clean-up: it misfires when the wall is close to skin tone."""
    if not os.path.exists(dst):
        run([sys.executable, os.path.join(SCRIPTS, "matte.py"), src, dst, "--model", "resnet50", "--width", "1080"],
            stdout=subprocess.DEVNULL)


def render_tail(intro, demo, out):
    if os.path.exists(out):
        return
    fc = (f"[0:v]{CONFORM}[v0];[1:v]{CONFORM}[v1];[0:a]{AUDIO}[a0];[1:a]{AUDIO}[a1];"
          "[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]")
    run(["ffmpeg", "-v", "error", "-y", "-i", intro, "-i", demo, "-filter_complex", fc,
         "-map", "[v]", "-map", "[a]", *ENC, out])


def render_head(hook, hook_a, reaction, pen, pen_a, out):
    hook_d, react_d, pen_d = duration(hook), duration(reaction), duration(pen)
    loop = ["-stream_loop", "-1"] if pen_d < react_d else []
    hook_w = round(W * HOOK_SCALE / 2) * 2
    fc = ";".join([
        f"[0:v]{CONFORM},tpad=start_duration={hook_d}:start_mode=clone[bg]",
        # clip + matte paired by frame number (mkv rounds timestamps to 1ms -> off-by-one masks)
        f"[1:v]fps={FPS},setpts=N/{FPS}/TB,format=rgba[hs];[2:v]setpts=N/{FPS}/TB,{EDGE}[ha];"
        f"[hs][ha]alphamerge,scale={hook_w}:-2[hk]",
        "[bg][hk]overlay=x=0:y=H-h:eof_action=pass[v1]",
        f"[3:v]fps={FPS},setpts=N/{FPS}/TB,scale={PEN_W}:-2,format=rgba[ps];"
        f"[4:v]setpts=N/{FPS}/TB,scale={PEN_W}:-2,{EDGE}[pa];"
        f"[ps][pa]alphamerge,trim=0:{react_d},setpts=PTS-STARTPTS+{hook_d}/TB[pn]",
        f"[v1][pn]overlay=x=W-w:y={PEN_Y}:eof_action=pass,trim=0:{hook_d + react_d},format=yuv420p[v]",
        f"[1:a]{AUDIO},apad,atrim=0:{hook_d}[a0];[0:a]{AUDIO},atrim=0:{react_d},asetpts=PTS-STARTPTS[a1]",
        "[a0][a1]concat=n=2:v=0:a=1[a]",
    ])
    run(["ffmpeg", "-v", "error", "-y", "-i", reaction, "-i", hook, "-i", hook_a, *loop, "-i", pen, *loop,
         "-i", pen_a, "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-t", f"{hook_d + react_d:.3f}",
         *ENC, out])


def join(parts, out, work):
    lst = os.path.join(work, os.path.basename(out) + ".txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{os.path.abspath(p)}'\n" for p in parts)
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
         "-movflags", "+faststart", out])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outfits", nargs="+", required=True)
    ap.add_argument("--reactions", required=True)
    ap.add_argument("--demo", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--work")
    a = ap.parse_args()
    work = a.work or os.path.join(a.out, "_work")
    os.makedirs(work, exist_ok=True)
    reactions = videos(a.reactions)
    longest = max(duration(r) for r in reactions)
    t0 = time.time()

    outfits = {}
    for d in a.outfits:
        name = os.path.basename(os.path.normpath(d))
        c = sort_outfit(d)
        print(f"{name}: hook={os.path.basename(c['hook'])} ({duration(c['hook']):.1f}s), "
              f"intro={os.path.basename(c['intro'])} ({duration(c['intro']):.1f}s), "
              f"pen={os.path.basename(c['pen'])} ({duration(c['pen']):.1f}s)", flush=True)
        c["hook_a"] = os.path.join(work, f"{name}_hook_alpha.mkv")
        c["pen_a"] = os.path.join(work, f"{name}_pen_alpha.mkv")
        c["tail"] = os.path.join(work, f"{name}_tail.mp4")
        matte_hook_raw(c["hook"], c["hook_a"])
        matte_pen(c["pen"], c["pen_a"], min(duration(c["pen"]), longest + 0.5))
        render_tail(c["intro"], a.demo, c["tail"])
        print(f"  {name} prepared ({time.time() - t0:.0f}s)", flush=True)
        outfits[name] = c

    for name, c in outfits.items():
        for r in reactions:
            rname = os.path.splitext(os.path.basename(r))[0]
            out = os.path.join(a.out, f"{rname}__{name}.mp4")
            head = os.path.join(work, f"{rname}__{name}_head.mp4")
            render_head(c["hook"], c["hook_a"], r, c["pen"], c["pen_a"], head)
            join([head, c["tail"]], out, work)
            print(f"  done {os.path.basename(out)} ({duration(out):.1f}s) at {time.time() - t0:.0f}s", flush=True)
    print(f"all done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
