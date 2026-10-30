# Reaction format: video editing for Evan

This repo automates Evan's "reaction" short-form video edit, which used to be done by hand in CapCut.
When Evan asks for a reaction video, or a "reaction format" video, follow this file. Evan isn't a
programmer: keep explanations plain, don't make them run commands, and send the finished video back.

Formats so far: **reaction** (below), **clipping reaction** and **referenced clipping reaction** (own sections further down). Evan plans
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

**Getting finished videos out (learned 2026-10-29):** the finished videos exist only on the cloud machine.
- The Drive connector only takes inline base64, so it can't upload videos. It *can* create folders
  (e.g. a "batch <date>" folder inside Claude Videos) for Evan to drag files into.
- SendUserFile caps each file at 500 MB. For a batch, send one zip per outfit (ZIP_STORED, ~270 MB each)
  rather than one big zip.
- Publer (MCP) needs a public URL for media. Evan uploads the video to Drive as "Anyone with the link",
  then pass `https://drive.usercontent.google.com/download?id=<id>&export=download&confirm=t`.
  Publer "viewmax" workspace accounts: Instagram "Evan Lukas" and Facebook Page "evanlukasmp44" (added
  2026-10-29; Publer posts to Instagram do NOT auto-share to Facebook, so post to both explicitly).
  Evan wants a "regular main feed reel": Instagram = post_type video + details {type: reel, feed: true};
  Facebook = post_type video + details {type: reel} (feed is Instagram-only).
  Video imports take a few minutes. Submit with wait_for_completion false and check with get_recent_posts;
  never resubmit after a timeout (the first post timed out but had gone through).
  **Evan's preference (2026-10-29): post each video as ONE post to both accounts** (`accounts: [instagram id,
  facebook id]`, post_type video, details type reel). Don't split per network. On the first combined batch,
  confirm both networks published as Reels and note the result here.
  Batches: one submit call with all posts works, but it always times out at 60s while Publer keeps importing
  (~10 min for 19 x 55 MB). Check with list_publer_posts state scheduled. Publer runs one "download from URL"
  job at a time, so a second submit during an import is rejected (no duplicate is created). The posts listing
  repeats rows across pages, so count unique post ids. get_recent_posts doesn't show future-dated posts.

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

## Referenced clipping reaction (third format; batch 10/29, decided with Evan 2026-10-29)

Like the clipping reaction, but Evan supplies **reference videos** (another creator's edits of the same
reaction clips) and everything is matched to them: hook size/position, pen-twirl size/position, and a text hook.
Batch = every outfit x every hook x every reaction (batch 10/29: 4 x 2 x 4 = 32).

Drive layout ("Batch 10/29" in Claude Videos): one folder per outfit with **named** hooks (`watch this`,
`can't believe`), an intro (`copy_*`, ~4s) and the pen twirl (`copy_*`, ~30s, the longest). There's also a
"react to these videos" folder, `streamer demo .mp4`, and the references in the batch folder:
`cantbelieve+texthookreference1/2.MP4` and `watchthishookreferencesize.MP4`.

Matching rules Evan gave:
- **Each reaction video matches its own reference** (the references show the same reaction clips; reference 1 =
  "spend your money" Impaulsive clip, reference 2 = "millionaire clipper vs haters"). The text hook, pen side
  and "can't believe" hook position all follow that reference. The pen moves sides per video.
- **"Can't believe" hook:** Evan's face matched to the face in the reference (size and centre), flush bottom.
- **"Watch this" hook:** size from `watchthishookreferencesize` (face ~641px, centre 385,1172), but kept at
  least full width (`cover_width`) so the clip's side edges never cut through the shirt. That comes out ~10%
  bigger than the reference face, which Evan's reference framing implies.
- **Text hook** on BOTH hook types, for the hook and the whole reaction: the reference text exactly
  ("He's living in 3026 😭😭" for ref 1, "He's living in 3026 😭🤯" for ref 2). TikTok Sans weight 700,
  4px black outline, box 84,478 to 802,554. The emojis are the real Apple ones lifted from the reference
  (`assets/batch_1029/emoji_*_1080.png`; text PNGs and spec.json saved there too, extracted as pixels that stay static while the video changes, then
  cleaned by colour).
- **Pen twirl:** placed by face match (ref 1 face 131px at 235,1445; ref 2 face 140px at 828,1462).
- The green flash at the end of the reaction clips is part of the source edit, and the reference keeps it.

Run: `python3 scripts/make_ref_reaction.py jobs/b1029/spec.json` (the spec lists outfits, refs and reaction
to reference mapping). `scripts/make_text_hook.py` renders text hooks; faces use OpenCV's Haar cascade
(`~/.cache/reaction-format/models/haarcascade_frontalface_default.xml`, fetched from GitHub; OpenCV 5 doesn't
ship it). Test on one outfit first and compare frames side by side with the references.

**Green screen:** Evan filmed the blue-shirt hooks on a (checkered) green backdrop. RVM handles it fine, and
`despill=type=green` is applied to green hooks (`"green": true`); no green fringe was seen. Advice given to Evan:
solid evenly lit green, stand a step in front, never wear green, mainly worth it for hooks.

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
