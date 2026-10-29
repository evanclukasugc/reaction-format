# Reaction format: video editing for Evan

This repo automates Evan's "reaction" short-form video edit, which used to be done by hand in CapCut.
When Evan asks for a reaction video, or a "reaction format" video, follow this file. Evan isn't a
programmer: keep explanations plain, don't make them run commands, and send the finished video back.

Formats so far: **reaction** (below) and **clipping reaction** (its own section further down). Evan plans
to add more. Give each new format its own section, and keep existing ones unchanged unless Evan changes them.

## The format (decided with Evan; don't change without asking)

Inputs are 4 clips Evan records or downloads (9:16, usually 1080x1920 from iPhone):

| Clip | Filename contains | What it is |
|---|---|---|
| Hook | `hook` (or "watch this") | Evan saying "Watch this" or similar. **Already trimmed; don't cut it.** |
| Reaction video | anything else, e.g. `reactionvid` | Someone else's video that Evan reacts to. Has their own CTA at the end. |
| Pen twirl | `pentwirl` | Evan silently twirling a pen. Usually already muted. |
| CTA | `CTA` | Evan's call to action, e.g. "...just comment the word studio, I'll send it to you for completely free". |

Edit, in order:
1. **Hook over a freeze frame.** Freeze the reaction video's first frame for exactly the hook's length.
   The hook plays on top with its **background removed**, at **69% scale, flush bottom-left**.
   Hook audio plays.
2. **Reaction.** When the hook ends, the reaction video plays with its own audio. The pen twirl sits on top
   with its **background removed**, small (**~220px wide on the 1080 canvas**), **flush right, top at y=1229**
   (bottom-right area), **muted**, for the whole reaction. **Loop it if it's shorter.**
3. **Cut their CTA.** End the reaction video right **before the creator comes back on screen for their own
   CTA** ("if you're still confused...", "comment the word...", etc.).
4. **Evan's CTA.** It goes after the reaction on the main track, full screen (not an overlay). Trim dead air:
   **start exactly when Evan starts talking** and end right after he stops (Evan approved the end at
   last word + 0.3s). The start is measured from the audio level, because Whisper's word times run early.
5. **CTA text.** Evan says a keyword ("studio", "Claude", "creator", ...). Over the whole CTA, put
   `Comment "<Keyword>"` / `for the full guide` (two lines, keyword capitalised), in **TikTok Sans**
   (= CapCut's "Classic"/TikTok classic font), weight ~550, white with a ~7px black outline, centred,
   centre at y≈375 (above his head), first line ~800px wide.
6. Export **1080x1920, 30fps, H.264 MP4**.

## How to make one

1. Find the clips in the Google Drive folder **"Claude Videos"** (folder id `1jP8PvKFbB65Vpn0eV6NeIamrOrPkgFNb`,
   owner evanclukasugc@gmail.com) with the Drive connector: search `parentId = '<folder id>'`. Use the newest
   clips Evan points at. Ignore `reactionvideoexplanation.mov` (the CapCut tutorial).
2. The Drive connector can't move large videos, so download each with
   `scripts/fetch_drive.sh <file id> jobs/<name>/in/<filename>`. If you get a web page instead of a video,
   the file isn't shared "Anyone with the link"; ask Evan to change that (or share the whole folder that way).
3. Run (about 5 minutes on the 4-core CPU cloud machine):
   ```
   python3 scripts/make_reaction.py --hook H --reaction R --pentwirl P --cta C \
       --out jobs/<name>/out/<name>.mp4 --work jobs/<name>/work
   ```
   It prints the cut point and why, the CTA trim, and the keyword it heard. Overrides: `--cut SECONDS`,
   `--keyword WORD`.
4. **Check before sending.** Pull a few frames (hook at frames 0-35, pen-twirl corner, CTA with text) and
   look at them. Check the printed keyword matches what Evan says, and that the cut lands before the creator
   reappears. Then send the MP4 with the SendUserFile tool and tell Evan the cut point, keyword and CTA trim.
   The Drive connector can't upload a file this size, so don't promise a Drive upload.

If `setup.sh` hasn't run in this session (e.g. `import faster_whisper` fails), run `bash setup.sh` first.

## Clipping reaction format (second format; decided with Evan 2026-10-29)

Batch format: **every reaction video x every outfit** (e.g. 5 reactions x 4 outfits = 20 videos).

Drive layout inside "Claude Videos":
- One folder per outfit ("gray shirt no hat", "gray shirt hat", "Black shirt no hat", "Black shirt hat"). Each has
  3 clips with meaningless names (`copy_<uuid>.MOV`), so they're told apart by length: **shortest = hook**
  ("Watch this", ~1.1s), **middle = intro** ("Let me show you how easy it is to start clipping... comment the
  word clip", ~4.4s), **longest = pen twirl** (~28-32s).
- "CLIPPING react videos": the reaction videos (streamer clips, 10-27s, various resolutions, no CTA of their own).
- `streamer demo .mp4` in the top folder: a screen-recorded tutorial with its own captions, ending on
  "COMMENT 'CLIP' FOR A FREE GUIDE!".

Each video, in order:
1. Hook (background removed, 69%, bottom-left) over a freeze of the reaction video's first frame for the hook's length.
2. The reaction video **in full** (nothing cut), with the pen twirl (background removed, muted, bottom-right,
   same size/position as the reaction format).
3. The intro clip **untouched**; Evan already trimmed it.
4. The streamer demo **untouched** (only conformed to 1080x1920/30fps; it's 60fps).
No text overlays (the demo already carries the CTA). Same export as the reaction format.

Run:
```
python3 scripts/make_clipping_reaction.py --outfits <outfit dirs...> --reactions <react dir> \
    --demo <streamer demo> --out jobs/<name>/out
```
Outputs `<reaction>__<outfit>.mp4`. Speed comes from sharing work: cutouts once per outfit, intro+demo
rendered once per outfit, then each video renders only hook+reaction (~20s each) and is joined without
re-encoding. First full batch: 20 videos in 15m40s (4 outfits prepared in ~9 min, then ~15-35s per video).

**No wall clean-up (`refine_matte.py`) on these clips.** They were filmed against a warm beige wall close to
skin tone. The fixed "grey wall" rule would eat the gray shirt, and an adaptive colour version punched holes
in Evan's face. Plain RVM with frame-exact pairing looked clean.

## Environment requirements

Network "Allowed domains" in the cloud environment must include: `drive.google.com`,
`drive.usercontent.google.com`, `huggingface.co`, `cdn-lfs.huggingface.co`, `cas-bridge.xethub.hf.co`,
`cas-server.xethub.hf.co`, `us.aws.cdn.hf.co`. GitHub (for the matting models) is reachable by default.

## Pipeline notes and lessons learned (don't re-learn these)

- **Clip and matte must be paired by frame number** (`setpts=N/30/TB` on both before `alphamerge`).
  Matte files are FFV1 in MKV, which rounds timestamps to 1ms, so a timestamp pairing gives frame N the
  mask from N-1. That left a grey "ghost" of wall behind Evan's fast-moving finger.
- **Hook cutout:** RVM resnet50 at full res (warm-up pass over the first second, because the recurrent model
  is poor on its first frames), then `refine_matte.py`. That removes wall-coloured (bright, colourless)
  regions that connect to the background, and keeps enclosed ones like teeth and eye whites. Evan records in front of a light
  grey/white wall. If he changes background, revisit the refine thresholds.
- **Pen-twirl cutout:** RVM mobilenetv3 at 360px wide, only as many seconds as are used. It's shown so small
  that this looks the same as resnet50 and is ~3x faster (~2 min instead of ~6).
- Rejected: BiRefNet (best edges but 13 GB RAM / ~50s per frame on CPU; ran out of memory),
  isnet-general-use (cut off a finger), u2net_human_seg (blobby masks).
- Every overlay or looped input needs an explicit end (`shortest=1`, `-t`). A `-loop 1` image without one
  made the first render run forever.
- **Cut detection:** find the first CTA phrase in the last 40% of the reaction transcript, walk back to the
  sentence start, and take the earlier of that and any hard scene change up to 2.5s before it, minus 0.05s.
  For the test video: cut 45.63s (speech 45.68, scene change 45.73), which matches where Evan cut in CapCut.
- faster-whisper's built-in decoder (PyAV) breaks with av 19, so the scripts decode audio with ffmpeg.
- Timing on this machine: transcription ~1 min, hook ~20s, pen twirl ~2 min, render ~2 min, ~5 min total.

## Keeping this file current

When Evan changes a preference ("make the pen twirl bigger from now on", a new keyword, a new text line), update
the constants in `scripts/make_reaction.py` / `scripts/make_text.py` **and** this file, then commit and push,
so the next session knows.
