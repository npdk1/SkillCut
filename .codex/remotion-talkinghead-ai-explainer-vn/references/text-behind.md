---
name: text-behind
when: Load at pipeline steps 4 and 7 (masks, text-behind) and whenever a text-behind beat fails V06/V07/V09/V10.
---

# Text-behind-speaker (v4.2, MANDATORY verify)

Big text sits **behind** the speaker (person mask applied to the zoomed video, text on the blurred/plain background layer). It is only allowed where the speaker does not hide it.

## Canonical tool
**Render's shared `text_occlusion.py` is the measuring tool** (`/workspace/render-env/bin/text_occlusion.py DIR --box x,y,w,h --text "..." --range S,E`, `--suggest WxH`; exit code 3 when more than 10 % is occluded; companion `person_mask.py --analyze DIR` adds `union_bbox`/`free_regions` to `mask.json`; README `/workspace/render-env/README.md`). Do not write a competing tool. If it is missing, `scripts/tbs_place.py` falls back to an internal raster measurement behind the same interface and the same threshold, and flags it in the beat (`_tool`) and in the log line.
It is not zoom-aware, so the pipeline writes zoom-warped composition-space masks to `out/tbs_canvas/<id>/` and measures there.

## Gate
- mean readability over the window **≥ 90 %** AND worst frame **≥ 90 %** (occluded ≤ 10 %) - `style.config.json → autoBeats.textBehind.tuneMinReadable / tuneWorstFrameMin`.
- Nothing passes ⇒ **do not render occluded text**: `make_masks.py` converts the beat to a plain `big-word` headline (`_fallbackFrom: 'text-behind-speaker'`, upper-case). `render.sh` re-runs `tbs_place.py --check` on the final canvas masks; a failure is auto-converted the same way.

## Steps
1. `make_beats.py` proposes windows only inside ONE steady EDL segment (after the punch settles, no zoom ramp, ≥ `minHoldSec` 1.4 s, not over the CTA, not on a cut-out part, faces present). Every rejection is logged (`skip text-behind-speaker @ t: reason`, stored as `_skips`). Beats overlapping in time that the text can collide with become `_blockers` (kept free during the search).
2. `make_masks.py public/project` runs `person_mask.py` per window, then **scans positions, sizes and line splits**: 1 line ≈ 0.55 scale, 2 lines ≈ 0.75, anchored left / centre / right, y from `tuneMinTopR` (0.045 H) downward, only into empty background; scored by `text_occlusion.py` on the mask frames.
3. The winner is written as `items:[{text, align, size, x, y, ink}]` + `_readable {mean, worst}`, `_tool`, `_layout`.
4. Look at a still from the middle of the window.

## Known limits
One main face; canvas == source framing assumed for the mask; window must be inside a steady segment; short phrases (≤ 12 chars per line) only.


## v4.3 - behind the crown, tracked
- Mục tiêu đo bằng `text_occlusion.py`: **bị che (mean) 3-10%**, worst frame <= 10%, **đọc được >= 90% ở mean và worst**; person-only (chỉ người) mean >= 3% để chữ thật sự ở SAU đầu.
- Thứ tự thử (make_masks.py): `--suggest WxH --text "..." --range S,E --require-behind` (dùng nguyên chuỗi `text` trả về) -> tìm nội bộ -> crown-tracking -> cửa sổ con ít chuyển động đầu -> beat khác (cỡ nhỏ / 2 dòng) -> bỏ + log (`_fallbackFrom`).
- Crown-tracking: `crown_y` = hàng trên cùng của người trong cột đầu (+-0.08W); median 5 khung -> EMA 0.4 zero-phase -> giới hạn vận tốc 0.012H/khung -> kẹp 0.10H. `beat.track[k]` = dy/H (k = chỉ số mask); Scenes.tsx cộng `track[mi]*H` vào y mọi dòng.
- File track: `public/project/tbs_track_<id>.json` (mảng `[frame,x,y,w,h]`); kiểm: `python3 /workspace/render-env/bin/text_occlusion.py <mask_dir> --track tbs_track_<id>.json --text "..." --require-behind` (exit 3 nếu max > 0.10; exit 4 nếu mean < 0.03). mask_dir = `out/tbs_canvas/<id>` (composition-space, có blocker) hoặc `<id>_person` (chỉ người).

## v4.3.1 - 2 tracked text-behind beats on a 60s cut

* `autoBeats.textBehind.tbsMinHoldSec` (**0.8s**) replaces the general `minHoldSec` (1.4s) for text-behind windows: the text only needs 0.8s of ONE constant framing to be readable behind the head.
* A window may **span a jump cut** (`tbsMaxCutGapSec` 0.6s): in `make_beats.steady()` the window continues into the next EDL segment when that segment has the same framing, no zoom ramp and no punch. `tbs_place.Stage.zoom_for_src_frame` returns the nearest segment's zoom for the frames inside the cut gap, so the mask warp stays continuous. Crown tracking lags across a head jump, so keep the gap <= 0.6s.
* `make_masks.py` sub-windows use `tbsMinHoldSec` too.
* Every kept beat is verified with the canonical command: `python3 /workspace/render-env/bin/text_occlusion.py <out/tbs_canvas/ID> --track tbs_track_ID.json --text "TEXT" --require-behind` (mean 3-10% occluded, >= 90% readable, exit 0).

## v4.3.2 - PER-GLYPH RULE (no hidden letters) - `text_occlusion.py --max-glyph 0.30`
The total-pixel rule (3-10 % mean/max) is NOT enough: a head that covers 8 % of a whole line can still swallow ONE letter (v43 shipped "N" of TRIEN 49 % covered, "G" 57.5 %).
- **Rule:** every glyph (diacritics included) is >= 70 % visible on EVERY frame = no glyph more than 30 % covered. The head may cut glyph edges or the bottom band of the line; it must not swallow a letter.
- **Tool (canonical, Render's, do not edit it):** add `--max-glyph 0.30` to every `text_occlusion.py` call - `--track FILE.json` / `--box` measuring AND `--suggest` (suggest then skips violating positions). JSON adds `glyph_occlusion_max`, `worst_glyph{char,index,frame,occlusion}`, `glyph_fail_count`, `pass_glyph`, `glyph_occlusion[]` (per character max/mean/fail). **Exit codes: 3 = max-occlusion, 5 = glyph rule, 4 = --require-behind below min (priority 3 > 5 > 4).**
- **Where it is enforced:** `tbs_place.py` (`suggest_candidate`, `tool_track`, `tool_measure` pass the flag; `search()` pre-filters candidates with an in-house low-res glyph check + 2 % margin) -> `make_masks.py verify_tracked` (a candidate is accepted only if the tool's `pass_glyph` is true AND mean >= 3 %) -> `tbs_place.py --check` gate in `render.sh` (g1; prints `glyph min visible X %`, FAIL = `LETTER HIDDEN`). The in-house `Typeset.glyphs()` check is only the fast pre-filter / fallback when the tool lacks the flag; the tool's verdict wins. `autoBeats.textBehind.tuneGlyphMinVisible` = 0.70 (0 disables).
- **Manifest commands** carry the flag: `... --track tbs_track_<id>.json --text "..." --require-behind --max-glyph 0.30` (also the person-only one) and `measured` records `min_glyph_visibility`, `worst_glyph`, `glyph_occlusion[]`, `pass_glyph`.
- **When it conflicts with the 3 % minimum:** (1) sit the text lower so the hairline of the crown only cuts the bottom band across the middle of the word; (2) shorten to the single longest word (`short` phase, e.g. "TRIEN") so fewer letters meet the crown; (3) put the crown between two words / lines (stacked, gap over the crown); (4) another window of the beat, crown-tracked or static. If NO position gives mean >= 3 % with every glyph >= 70 % (typical when the speaker's head is at the very top of the frame - crown y < ~100 px, no room above it) the beat is DROPPED as text-behind and rendered as a plain headline, and the log says why. Never ship a swallowed letter to keep a beat; keep >= 2 text-behind beats per 60 s demo when the footage allows.
- `TBS_DEBUG=1 python3 scripts/make_masks.py` prints one `[dbg]` line per verified candidate (occ max/mean, person mean, glyph min, tool glyph max, verdict).
- **Bug to avoid:** `pass_glyph` can be absent from `--track` JSON when `--max-occlusion` is given; compare `glyph_occlusion_max <= 0.30` instead of treating a missing key as failure.

## v4.4 - HARD RULES / commands / thresholds (read this block first)
1. **Complete meaning**: the phrase is a whole expression, never a fragment ("TRIỂN" of "PHÁT TRIỂN", lone "NGƯỜI"). Lint: `python3 scripts/tbs_place.py --lint-phrase "<text>"` (`vi_phrases.py`, `autoBeats.textBehind.badFragments`, `completeSingleWords`). Pick phrases from segments with head-room (head not near the top edge).
2. **Overflow wraps to line 2, never truncated.** Layout `wrap`: line 1 sits behind the crown, the rest of the words continue on line 2 in a band just below (`tbs_track_<id>_0.json` = line 1, `_1.json` = line 2). Words of all lines == phrase (V10). `wrapPenalty` / `comfortPenalty` in `autoBeats.textBehind` rank wrap vs one-liner.
3. **Line 1 behind the crown**: occlusion 3-10 % (mean >= 3 %, max <= 10 %), every glyph >= 70 % visible (`--max-glyph 0.30`), readable >= 90 % (mean and worst frame). **Never loosen**; `text_occlusion.py` exit 4 (`keep_phrase`) = this head position can't do it -> other phrase / other segment.
4. **Measured on the person-only mask**: `out/tbs_canvas/<id>_person` (merged masks are only used to place). `python3 scripts/tbs_manifest.py --project public/project --out-dir out --output-mp4 <mp4> --write` records per beat `command` and `command_person_only` in `<out>_tbs.json` (V06/V07 evidence). Canonical command: `python3 /workspace/render-env/bin/text_occlusion.py out/tbs_canvas/<id>_person --track public/project/tbs_track_<id>.json --text "<text>" --require-behind --max-glyph 0.30` (wrap: once per line with `tbs_track_<id>_<i>.json`).
5. Count: >= 1 per 30 s of output (V08, else `_skips` reason). Evidence: `<out>_still_<id>.jpg` at the middle of the beat showing line 1 behind the crown and line 2 below.
6. Debug: `TBS_DEBUG=1 python3 scripts/make_masks.py public/project`.
