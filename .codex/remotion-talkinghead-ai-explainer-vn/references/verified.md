---
name: verified
when: MANDATORY after every build/render and before ANY delivery to the customer. Load it right after `render`, and again after every rewrite.
---

# verified.md - the verification checklist (v4.5)

Loop (no step may be skipped): **build -> VERIFY (this file) -> FEEDBACK (`references/feedback.md`) -> REWRITE -> VERIFY again -> deliver only when every rule is PASS**.
Max **3 rewrite rounds** (verify rounds 1..4). Still failing after round 3 => do NOT deliver; write `blockers.md` (template in `references/feedback.md`) and report the blockers.

Automatic runner = Render's `verify_rules.py` (implements the `A` rules V01-V20, read-only tool, do NOT edit it; V21-V23 are checked by `scripts/check_template_rules.py`, run it right after verify_rules):
```
cd /workspace/render-env && venv/bin/python bin/verify_rules.py --video <project>/out/final.mp4 --prefix <project>/out/final \
      --project <project>/public/project --outdir <project>/out --target-sec 30 --tol 2 --template <project> \
      --out <project>/out/verify/verify_report_round<N>
# or, from a finished work dir:   ... verify_rules.py --work <workdir> --target-sec 30 --out <file>
```
Exit 0 = no FAIL (rules marked MANUAL / `(+M)` still need your look: V05 V09 V12 V13 V17 V18 V20); exit 1 = at least one FAIL. It writes `<out>.json` and `<out>.md` (table: ID, status, rule, evidence incl. `rule_id`, timestamp/bbox, measured value). Copy those numbers into `feedback_round<N>.md` (references/feedback.md). Never edit a report by hand to turn a FAIL into PASS. The evidence bundle it needs is produced by `python3 scripts/make_evidence.py --video out/final.mp4 --prefix out/final` (contact sheet, stills, `_tbs.json`, `_icons.json`, `_beats.json`).
If the installed `verify_rules.py` still has V14 fixed at 2, enforce the length-scaled rule below yourself and write it in the report (`enforced_by_hand`).

Legend: **A** = automatic (command/threshold), **M** = manual look (still / contact sheet / ear), **A+M** both.
All times are OUTPUT seconds. Thresholds live in `style.config.json -> verify` (single place; the numbers below are the defaults).

## Rules

| ID | Kind | Rule | Command / how | PASS threshold |
|---|---|---|---|---|
| V01 | A | File plays | `ffprobe -v error -show_streams -of json F`; `ffmpeg -v error -i F -f null -` | h264 + yuv420p, 30 fps, canvas == probe canvas (1080x1920 for vertical/16:9 input), audio stream present (aac), decode prints NOTHING (exit 0) |
| V02 | A | Duration on target | `ffprobe -show_entries format=duration` | `abs(duration - targetSec) <= tolSec` (30 s +-2 => 28.0-32.0; 60 s +-2 => 58-62). `targetSec` = the `make_edl.py --target-sec` value |
| V03 | A | Overlap gate 6 px | `node scripts/check_overlaps.mjs public/project --report out/overlaps.json` | exit 0, `overlaps == 0` (threshold `OVL_PX = 6` px on both axes) AND no element/logo/caption covers > 10 % of the face box AND `out/autofix.json` dropped nothing from `autoBeats.collision.protected` (CTA, brand-logo, text-behind) |
| V04 | A | Captions face-checked | captions are in `FACE_CHECKED` (LayoutCollisionGuard) and `overlaps.json` lists 0 caption x face hits | caption box x face overlap <= 10 % of face area on every checked frame |
| V05 | A+M | NO caption background | `verify_rules.py`: static check of `src/components/Captions.tsx` + `style.config.json -> caption.background` + a pixel check of every caption page (pill-colour #F8E277 mass / flat panel); M: look at 3 stills. The framed-focus headline is yellow text with a stroke (`beats.infoScene.pillFilled=false`), not a pill | `caption.background.enabled == false`; Captions.tsx has no `backdrop-filter`, no `blur(`, no `background:` other than `transparent`, no pill/box for ANY caption line; text readable by stroke + shadow only (`caption.stroke.widthPx >= 6`); source video has no leftover smeared box (`clean_burned_captions.py` report or manual look) |
| V06 | A | Text-behind occlusion | per beat: `python3 /workspace/render-env/bin/text_occlusion.py out/tbs_canvas/<id> --track public/project/tbs_track_<id>.json --text "<text with \n>" --require-behind --max-glyph 0.30` | exit 0; `occlusion_mean` 0.03-0.10, `occlusion_max <= 0.10`; readable (1-occlusion) >= 90 % on the mean AND the worst frame; `behind_effect == true` |
| V07 | A | No swallowed letter | same call, field `glyph_occlusion_max` / `pass_glyph` | every glyph >= 70 % visible on every frame (`glyph_occlusion_max <= 0.30`). Applies to EVERY line of a wrapped phrase. Exit 5 = FAIL |
| V08 | A | Text-behind count | count beats `type == text-behind-speaker` (not `fallback`) | >= 1 per 30 s of output (30 s => >= 1, 60 s => >= 2); if none can be placed the report must say why (`_skips`) - then V08 = WARN, not PASS |
| V09 | A+M | Phrase is complete in meaning | `python3 scripts/tbs_place.py --lint-phrase "<text>"` (uses `scripts/vi_phrases.py` + `autoBeats.textBehind.badFragments`) | NOT a lone fragment of a longer phrase ("TRIỂN" out of "PHÁT TRIỂN TIẾP"), does not start/end with a function word (và, thì, là, của, để, mà...), 1 word only if it is in `autoBeats.textBehind.completeSingleWords` (CƠ HỘI is 2 words; "AI", "SALE", "TIỀN"...). Prefer "TRIỂN KHAI", "CƠ HỘI", "BIẾN BẢN THÂN" |
| V10 | A | Wrap to line 2, never drop words | beat `items[]`: `lines` + `_wrap` ; words of all lines joined == beat phrase | when the phrase does not fit on one line at the minimum scale, line 2 is used (`TRIỂN` / `KHAI`); `phrase_words(items) == phrase_words(beat.phrase)`, no truncation / ellipsis; line 2 is below line 1 (`y2 > y1`), inside the safe area, and V06+V07 hold for the whole text including line 2 |
| V11 | A | Icon side by free space | `beats.json` illustration beats: `side` (`left`/`right`), `_freeLeftPx`, `_freeRightPx` (from the person mask / face box) | `side` is the side with `>= card width + 6 px` free; not pinned: with >= 2 icons BOTH sides are used unless the other side had no room (`_sideReason` states the numbers); never 3 icons in a row on the same side |
| V12 | A | Icon never covers / competes | V03 + `check_logo_faces.py` + tbs de-dup | 0 px overlap with face, captions, logos, text-behind; an icon and a text-behind never share a concept (8 s window) or time (+-0.25 s) |
| V13 | A+M | Icon matches the sentence | each `illustration.concept` keyword occurs in the spoken words within +-1.5 s | concept matches speech (customer talk = two people, sale = cart/tag, money, growth...); icon >= 120 px; source recorded in `public/project/illustrations/icons.json`; >= 2 icons per 30 s when the speech has such concepts |
| V14 | A | Phone / window frame cap | count `framed-focus` beats | `count <= max(1, floor(duration_sec / 30))` (<30 s and 30 s => 1, 60 s => 2, 90 s => 3); never adjacent / back-to-back: gap between the END of one and the START of the next >= 15 s (`autoBeats.framedFocus.minGapSec`) |
| V15 | A | Logos are real | every `brand-logo` beat: file in `public/project/logos/`, entry in `references/brand-logos.md` Registry, `logos.json` source != placeholder | file exists and is a real logo (SVG, or PNG >= 128 px, not generated by us), brands spoken but missing = listed `NOT FOUND` in the Registry (else FAIL) |
| V16 | A | CTA kept | last beat `comment-box` present in the final beats.json | present, not dropped by autofix, fully on screen at the end |
| V17 | A+M | Text is spelled right | grep `captions.json` + beat text for the `textCleanup.asrFixes` bad tokens ("xửa", "claw", "vắt triển", "Opus 5 .5", "chát GPT"...); M: read 10 random captions | 0 bad tokens; 10/10 sampled captions correct Vietnamese |
| V18 | M | Contact sheet reviewed | `python3 scripts/make_evidence.py --video out/final.mp4 --prefix out/final` (writes `out/final_contact.jpg`, 1 fps, output-time stamp per tile) then LOOK | every beat visible in a still; nothing covers the face; no white/blurred box behind captions; text-behind sits right behind the crown; icons readable |
| V19 | A | Evidence files exist | files listed in "Evidence" below | all present |
| V20 | A | Loop followed | `out/verify/verify_report_round*.json` + `feedback_round*.md` | each failed round N has `feedback_round<N>.md`; delivery only from a round whose report has `all_pass: true`; rounds <= 4 |
| V21 | A | Icon density | `python3 scripts/check_template_rules.py --project public/project --target-sec 30` (V21) | `icons <= floor(dur / 7.5 + 0.2)` (30 s -> 4, 60 s -> 8); >= 5 s clear time between the END of one icon and the START of the next (output time); the same concept >= 15 s apart; strongest concepts kept (`autoBeats.illustration.density`) |
| V22 | A | Icon side from the person mask | same script (V22) | every icon has `side`, `_freeLeftPx`, `_freeRightPx`, `_sideReason`, `_personMaskChecked: true` (per-frame matte over the whole icon window, >= 6 px clearance); right-side slots (top-right corner, beside head, near shoulder, down to ~120 px) were tried; when all icons sit on one side every icon after the first states `NOT free` + numbers; never 3 in a row on one side; never forced over the person |
| V23 | A | No visible subtitle-removal patch | same script (V23) + `scripts/reinpaint_patch.py detect` | `out/patch_manifest.json` exists, `status` `reinpainted` (method + before/after crops) or `none-found`; `covered-only` needs a written reason; `detected_after_fix` empty; NO blurred / smeared / flat rectangle (or stacked rows of them) anywhere in the raw, with or without captions (framed-focus pages have none) |

### Evidence (V19) - saved next to the output, named after it
`<out>.mp4`, `<out>_contact.jpg`, `<out>_still_<tbsId>.jpg` e.g. `_still_tbs1.jpg` (one per text-behind beat, taken at the middle of the beat; show the 2-line wrap when used), `<out>_still_ill<k>_<concept>_<side>.jpg` (one per icon), `<out>_verify_report.json` + `.md` (the final all-pass round), `<out>_feedback_round<N>.md` (every failed round), `<out>_verify/` (all rounds), `<out>_beats.json`, `<out>_tbs.json` (+ `<out>_tbs_track_<id>[_i].json`; manifest per beat: `command`, `command_person_only`, person-only occlusion/glyph numbers, `output_window_s`, `_wrap`), `<out>_icons.json`.

### verify_rules report shape (real output)
```json
{"video": "out/final.mp4", "duration": 29.6, "all_pass": false, "summary": {"pass": 17, "fail": 1, "manual": 2},
 "results": [{"rule_id": "V05", "status": "fail", "title": "NO caption background",
              "evidence": {"problems": ["2 page(s) with a pill-colour mass ..."], "video_box_heuristic": {"suspected": [{"page": 4, "bbox": [140,124,260,41], "fill": 0.57}]}}}]}
```
Status values: `pass`, `fail`, `warn` (V08 only, with a logged reason), `manual` (needs your tick). `(+M)` in the .md = pass on the automatic leg, manual leg still to do.

## Demo review criteria (Mèo Bel Demo fills / extends this section)
Mèo Bel Demo reviews AFTER `verify_rules.py` is green, from the real mp4, and may add lines below (give each a new ID `D<nn>`; a `D` FAIL blocks the upload exactly like a `V` FAIL). Draft merged from `/workspace/SkillCut-output/verified_checklist_draft.md` (duplicates of V-rules point at the V-rule):

| ID | Check (from Demo draft) | Same as |
|---|---|---|
| D01 | `ffprobe` duration within target +-0.5 s of what was announced, 1080x1920, h264 yuv420p 30 fps, aac; full decode without error | V01, V02 |
| D02 | `render.sh` reported 0 overlaps (6 px) WITHOUT the autofix deleting CTA / logos | V03, V16 |
| D03 | no element (captions, title, chip, icon, logo, comment box) covers the face (YuNet) | V03, V04 |
| D04 | captions have NO white / blurred / boxed background, only text + stroke/shadow | V05 |
| D05 | each text-behind: `text_occlusion.py --track ... --require-behind --max-glyph 0.30` exit 0; mean 3-10 %, every glyph >= 70 % | V06, V07 |
| D06 | complete phrase; when out of room, line 2 ("TRIỂN / KHAI"), never a cut word | V09, V10 |
| D07 | icon matches what is said (talk = two people, sale = cart/tag, learning = cap ...) | V13 |
| D08 | icon side not pinned: chosen left OR right from free space, not the same spot every time | V11 |
| D09 | icon never at the same time as a text-behind with the same meaning; large enough on a phone | V12, V13 |
| D10 | phone / app-window frame <= 1 per 30 s (2 per 60 s), gap >= 15 s | V14 |
| D11 | captions spelled right after cleanup + glossary (10 random lines) | V17 |
| D12 | contact sheet 1 fps with timestamps + one still per text-behind and per icon + JSON measurements shipped | V18, V19 |
| D13 | ONLY when everything above is PASS: upload ONE link (with md5) for the customer - Demo is the only uploader | V20 |
| D14.. | _(Demo: add rules here)_ | |

## Delivery rule
Deliver (hand over to Mèo Bel Demo / the customer) only when: `verify_report_roundN.json.all_pass == true` AND `manual_roundN.json` ticks V05/V09/V12/V13/V17/V18 AND Demo's `D` rows are PASS. Never upload or push from the build step.

## v4.5 notes
- `verify_rules.py` V04/V05 now skip caption pages that are hidden (framed-focus, text-behind-only pages). The old "flat-panel false positive on framed-focus" workaround (ship without the beat) is obsolete: keep ONE framed-focus beat per 30 s (V14) and let V05 judge it.
- V05b (render v4.5): **`--source` = the ORIGINAL UNPATCHED raw** (the file that still has the blur pill, e.g. `raw_clean.mp4`; NOT the re-inpainted copy). V05b takes the patch locations from `--source`, then checks whether the RENDER pixels there are still blurred (ORB-mapped, zoom/framed layouts included). With an already-patched source it finds 0 patches and proves nothing - a valid run reports `patches_found >= 1` and `visible_uncovered_patches 0`. Scans the SOURCE (`--source`, default `<project>/raw.mp4`) for frame-fixed rectangular blur patches and fails when > 5 % of a visible patch is not under a caption. Standalone: `verify_rules.py --blur-scan <src.mp4>`. Fix = re-inpaint the raw (`references/quality-control.md` v4.5), never a caption cover for an ~800 px patch. Always pass `--source <unpatched original>` in the full verify. Known limit (v4.5.1 measurement): the visible-blur predicate is `median DoG(0.8/1.6) of the uncovered patch pixels in the render <= max(1.0, 4*level/zoom)`, an ABSOLUTE energy; on smooth phone/TikTok footage whose natural static areas measure 0.15-0.30, every region (patched or natural) is below 1.0, so the check cannot tell a good fill from the old blur there - see references/quality-control.md.
- V11 (icon side) is satisfied by V22 (person-mask slots); V21 limits how many icons exist at all.
- Run order after a render: `make_evidence.py` -> `verify_rules.py` -> `check_template_rules.py --manifest out/patch_manifest.json` -> manual ticks.

- Waivers: a rule may be waived ONLY by an explicit user decision; write it in `_verify_report.json/.md` (status `waived`, reason, date) and in `_feedback_*.md`, keep the unwaived raw report next to it. Demo v44: V05b waived 2026-11-03 ("source not pure raw, user accepted").
