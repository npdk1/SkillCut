# AGENTS.md - single entry point (v4.4)

Template: Remotion talking-head AI explainer (VN), 1080x1920 30 fps. **Read this file first, then follow the pipeline in order.** For each step load the listed `references/*.md` BEFORE running it (each one starts with `name` / `when` frontmatter, hard rules, commands, thresholds). Style numbers live only in `style.config.json`. Nothing in this template pushes to GitHub or uploads anywhere; delivery is done by the orchestrator after V-rules pass.

## Mandatory pipeline (do not skip, do not reorder)

| # | Step | Command | Load first | Gate to pass before the next step |
|---|---|---|---|---|
| 1 | probe | `python3 scripts/probe_video.py <raw.mp4> [--target native\|vertical]` | `references/orientation-layouts.md` | `probe.json` `gate: "passed"` |
| 1b | subtitle-removal patch | if the raw had burned-in subtitles removed: FIRST `cd /workspace/render-env && venv/bin/python bin/verify_rules.py --blur-scan <raw>.mp4` (V05b scanner, exit 1 = patch found), then `python3 scripts/reinpaint_patch.py detect <raw_clean.mp4> [--orig <original.mp4>] --out out/patch.json` (diff mode with the original = exact rows; without it = EXPERIMENTAL candidates, confirm by eye), then `python3 scripts/reinpaint_patch.py fill <original.mp4> <raw_clean_v2.mp4> --audio <raw_clean.mp4>` (per-frame re-inpaint of the static pill, same frame count/audio), re-run `ensure_keyframes.py`, write `out/patch_manifest.json` (status `reinpainted`, `patch_box_xyxy`, `rows`, `method`, before/after crops) | `references/quality-control.md` (Subtitle-removal patch) | V23: no blur/smear rectangle anywhere, with or without captions |
| 2 | transcribe + cleanup | `python3 scripts/transcribe.py public/project/raw.mp4 --out public/project` (`text_cleanup.py` inside; glossary `public/project/glossary.txt`) | `references/style-system.md` (textCleanup), `references/highlight-and-tighten.md` | words.json non-empty; Mai->Mike only with AI-tool context |
| 3 | EDL / tighten | `python3 scripts/make_edl.py --words public/project/words.json --out public/project [--target-sec 30 --tol 2]` | `references/highlight-and-tighten.md`, `references/content-insights.md` | `edl_report.md` read; duration within target +-tol (V02) |
| 4 | masks | `python3 scripts/detect_faces.py public/project/raw.mp4 --out public/project/faces.json --every 0.1` and `python3 scripts/make_masks.py public/project` (person mask + person-only canvas mask `out/tbs_canvas/<id>_person`) | `references/text-behind.md` | verify the speaker mask; head-room check (see text-behind.md) |
| 5 | beats | `python3 scripts/make_beats.py --words ... --edl ...` | `references/scene-architecture.md`, `references/illustrations.md`, `references/brand-logos.md` | beats.json reviewed; framed-focus <= `max(1, floor(duration/30))`, never adjacent (V14) |
| 6 | captions | produced by step 3; style from config | `references/style-system.md` | NO background behind captions, stroke >= 6 (V05) |
| 7 | text-behind | `make_masks.py` runs `tbs_place.py` (placement search incl. 2-line wrap); lint a phrase: `python3 scripts/tbs_place.py --lint-phrase "<text>"` | `references/text-behind.md` | `text_occlusion.py ... --require-behind --max-glyph 0.30` exit 0 (V06 V07 V09 V10) |
| 8 | illustrations | in `make_beats.py` (density preselect, then `logo_place.mask_slots_place` = per-frame person mask over the whole icon window, both sides, alternate, down to ~120 px) | `references/illustrations.md` (v4.5) | V11 V12 V13 V21 V22 |
| 9 | logos | `scripts/fetch_logo.sh`, `logo_place.py` | `references/brand-logos.md` | V15 |
| 10 | render | `bash scripts/render.sh out/final.mp4` (gates: keyframes, overlaps 6 px, tbs readability, then Remotion) | `references/quality-control.md` | 0 overlaps, CTA kept (V03 V16) |
| 11 | evidence | `python3 scripts/make_evidence.py --video out/final.mp4 --prefix out/final` | `references/verified.md` (Evidence) | files for V18/V19 exist |
| 12 | VERIFY | `cd /workspace/render-env && venv/bin/python bin/verify_rules.py --video <proj>/out/final.mp4 --prefix <proj>/out/final --project <proj>/public/project --outdir <proj>/out --target-sec 30 --tol 2 --source <ORIGINAL UNPATCHED raw, e.g. raw_clean.mp4 that still has the blur pill - NOT public/project/raw.mp4 when that is the re-inpainted copy> --template <proj> --out <proj>/out/verify/verify_report_round<N>` (exit 1 = fail; or `--work <workdir>`), then `python3 scripts/check_template_rules.py --project public/project --target-sec 30 --manifest out/patch_manifest.json --out out/verify/template_rules.json` (V21 icon density - start-to-start gap, V22 icon side from person mask, V23 no subtitle-removal patch; V05b needs patches_found >= 1 with the unpatched --source, a patched --source gives patches_found 0 and proves nothing) | **`references/verified.md`** | all V-rules pass; manual V05/V09/V12/V13/V17/V18 ticked by LOOKING at `_contact.jpg` and the stills |
| 13 | FEEDBACK | write `out/verify/feedback_round<N>.md` (rule ID, timestamp, measured value, fix per failure) | **`references/feedback.md`** | one row per failure, concrete fix |
| 14 | FIX | change only what the feedback names, re-run from the earliest affected step | the reference of that step | - |
| 15 | RE-VERIFY | step 12 with round N+1 | `references/verified.md` | repeat 13-15, **max 3 rewrite rounds** |
| 16 | DELIVER | only when every V-rule passes. Otherwise write `out/blockers.md` (template in `references/feedback.md`) and report it - no delivery | `references/feedback.md` | `all_pass: true` + manual ticks (V20) |

`references/feedback-learning.md` is for user comments after delivery (edit `style.config.json` only).

## Hard rules (short list - details in the references)
1. Probe before anything; no overlay before `probe.json`. Never `npm run render` directly - always `scripts/render.sh` (it re-encodes the raw to a <= 1 s GOP so Remotion's per-frame seeks stay fast, runs the overlap gate, masks, text-behind gate).
2. Captions: no pill / box / blurred / white panel, readability = stroke (>= 6 px, config 8) + soft shadow. The framed-focus headline is stroked yellow text too (`beats.infoScene.pillFilled=false`).
3. Text-behind: complete-meaning phrase (no lone TRIỂN / NGƯỜI), overflow wraps to line 2 (never truncated), line 1 behind the crown with 3-10 % occlusion, every glyph >= 70 % visible, readable >= 90 %, measured on the PERSON-ONLY mask; the manifest `_tbs.json` records `command_person_only`. Never loosen `--max-glyph 0.30` / 3-10 % thresholds - pick a segment with head-room or another phrase (`text_occlusion.py` exit 4 `keep_phrase`).
4. Illustrations: side chosen from free space by the mask (varied sides when both have room, `_sideReason` otherwise), never over face / captions / logos / text-behind.
5. Phone-frame / app-window (framed-focus): at most `max(1, floor(duration_sec/30))` (1 for 30 s, 2 for 60 s), never adjacent (gap >= 15 s).
6. Logos: try more slots and smaller sizes before dropping; Mai -> Mike only when capitalised AND near an AI-tool word (`textCleanup.ambiguousWords.mai`, configurable).
7. Caption vs face is checked on every rendered frame (`check_caption_face.py`, inside V04).
8. Never edit `text_occlusion.py` / `verify_rules.py` or a threshold to get a PASS. Report times in Asia/Bangkok (UTC+7).

## File map
```
AGENTS.md        this file (entry point)          SKILL.md      overview + v-notes, points here
references/      verified.md (V01-V23 + D01-D13)  feedback.md (round template + blockers.md)  text-behind.md  illustrations.md  brand-logos.md  highlight-and-tighten.md  orientation-layouts.md  scene-architecture.md  style-system.md  quality-control.md  feedback-learning.md  content-insights.md
scripts/         probe_video transcribe make_edl make_beats make_masks tbs_place tbs_manifest logo_place detect_faces ensure_keyframes autofix_overlaps check_overlaps.mjs check_logo_faces check_caption_face make_evidence check_template_rules reinpaint_patch render.sh
style.config.json  single source of style numbers (+ `verify` thresholds)
```
