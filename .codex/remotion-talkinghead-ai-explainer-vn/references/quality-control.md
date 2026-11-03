---
name: quality-control
when: Load at pipeline step 10 (render) and before step 12; it lists the static checks. The pass/fail rules are in verified.md.
---

# Quality control

## Trước khi giao
1. `npx tsc --noEmit` sạch.
2. `node scripts/verify-video.mjs out/final.mp4 public/project` kiểm tra: canvas = probe/layout, fps, có audio, thời lượng = tổng EDL (+-0.25s), lệch A/V <0.1s, cảnh báo đoạn >7s hoặc <0.6s. (Không tự phát hiện frame đen/đóng băng: xem still bằng mắt.) Sai số thời lượng với render một phần là bình thường.
3. Xem still ở: 0.3s (hero), cut đầu tiên, mỗi loại beat một lần, cuối video.
4. `edl_report.md`: đọc các đoạn bị bỏ có điểm .30-.42.
5. Caption: không đoạn nào >2 dòng; không chữ sai tên thương hiệu; không đè mặt; không trùng header info-scene.
6. Nghe: không cụt đầu/đuôi chữ ở điểm cắt (pad 0.04/0.08s), không ừm à lọt, âm lượng ổn định.

## Checklist theo style
- [ ] Chỉ hard cut; không whip/fade ngoài dark-scene fade 8f.
- [ ] Đổi framing mỗi 4.5-9s, punch settle 8f, không drift.
- [ ] Thay đổi thị giác mới mỗi <=3-4s.
- [ ] Hook 0-3s có caption hero; payoff có big-word; outro có CTA.
- [ ] Beat không chồng lên nhau (chỉ 1 beat to).
- [ ] Probe.json là của đúng raw (trùng `file`/duration).

## So sánh với tham chiếu
`reference-frames/_template_vs_reference_stills.jpg` đặt still template cạnh khung tham chiếu. Sai khác đã biết nằm ở `style.config.json -> gaps` và analysis.md mục "Khoảng trống".

## v4.1: cổng overlap
- `node scripts/check_overlaps.mjs public/project --report out/overlaps.json` => `OK: 0 overlaps`. Mọi cặp hộp `data-guard` (caption, title, timeline, chips, prompt, comment, big-word, logo, REC, stars) giao > 6px đều là lỗi; logo/title/chip/prompt/comment x mặt cũng là lỗi. `scripts/render.sh` tự chạy; không có cờ bỏ qua.
- Still full-res cho từng beat mới (framed-focus, text-behind-speaker): kiểm chữ đọc được, mask khớp người, caption không đè.
- Tác giả viết tay: `timeline:true` chỉ trong cửa sổ không có caption đè.


## v4.3 - cổng
- Cổng 1 `tbs_place.py --check` (đọc được + bị che qua text_occlusion.py, kể cả `--track`), cổng 2 `check_overlaps.mjs` (6px, mặt > 10%).
- Fail -> `autofix_overlaps.py` tối đa 3 vòng; CTA/comment-box (`collision.protected`) không bao giờ bị bỏ; vẫn fail => `RENDER ABORTED ... Exit 2`.
- Hạn chế: LayoutCollisionGuard bỏ qua cặp cùng tên (trừ brand-logo), nên hai beat cùng loại chồng nhau không bị phát hiện ở runtime.

## Hard rules / commands / thresholds (v4.4)
- `npx tsc --noEmit` clean; `bash scripts/render.sh out/final.mp4` (0 overlaps at 6 px, CTA kept, tbs gate passed). Render profile: `out/render_profile.json` (stages_sec). Expected: ~2 min for a 30 s vertical on 6 cores.
- Caption vs face is checked on EVERY rendered frame of a caption span (`python3 scripts/check_caption_face.py out/final.mp4` = V04; YuNet + forehead pad), not only the overlap gate on sampled frames - v4.3 had a caption brushing the forehead at 12.33 s with the gate at 0.
- The pass/fail list is `references/verified.md` (V01-V20); the loop is in `references/feedback.md`.

## v4.5 - Subtitle-removal patch (blur box) - verified.md V23
**Defect (user: "blurred background behind subtitles")**: when the source had burned-in subtitles and they were removed with one fixed mask / column interpolation, a smeared rectangle stays on the picture for the WHOLE video (on the 30 s demo: a static two-row pill on the speaker's chest, one row per original subtitle line, x 101-881 / y 1174-1327). Our own captions do not cover it (and framed-focus / text-behind pages have no captions), so it reads as the forbidden box behind subtitles. Covering it with captions is NOT enough.
0. **Blur-scan the source first (render's V05b tool)**: `cd /workspace/render-env && venv/bin/python bin/verify_rules.py --blur-scan <source>.mp4` lists frame-fixed rectangular blur patches (bbox in source px, area, level, persist); exit 1 if any. On the demo raw it reported `[95,1162,909,1339] area 100688` (zoom segments expand it to ~[16,1232,973,1437] on the canvas, exposed 68-100 % of the render) and after the fix `0 patch(es)`. Caption cover alone can never hide an ~800 px patch. The full verify then needs `--source <source>.mp4` (V05b must be clean).
1. **Detect** (`scripts/reinpaint_patch.py detect <raw_clean> --orig <original> --out out/patch.json`): diff mode = temporal mean of |clean - original| over 40 sampled frames > 30 -> exact patch pixels, `rows[]` split by width steps (stacked subtitle lines). Without the original the blind mode only lists EXPERIMENTAL static-rectangle candidates (flat noise plateau with a sharp step at top and bottom in >= 4 column bands) - it missed the real patch on the demo, so keep the original and use diff mode, or have the removal step write its own mask.
2. **Re-inpaint** (`reinpaint_patch.py fill <original> <raw_clean_v2> --audio <raw_clean>`): re-clean from the ORIGINAL (never inpaint the already-inpainted file): mask = the caption colour pill (HSV h 70-95, s > 150, v > 100) closed, hole-filled and dilated 17 px (so no coloured fringe is left); per frame: per-column linear interpolation from 5-row bands just outside the hole (low frequency) + reflected high-pass detail (sigma 3, x 0.45) + matched grain + Poisson `seamlessClone`. Frame count and audio are copied from the existing cleaned file so `words.json` / `edl.json` / beats stay valid. Temporal-median recovery is impossible when the covered content is never visible (subtitles stay on for the whole video): any fill is synthetic - say so in the manifest.
3. **Cover only as a last resort**: `status: covered-only` needs a written `reason` and the caption block must cover every row for the whole video (V05 / face rules still apply).
4. **Manifest** `out/patch_manifest.json`: `{status: reinpainted|none-found|covered-only, patch_box_xyxy, rows[], method, source, raw_before, raw_after (md5), before_after: [crop files at e.g. output 5.3 s and 24.3 s], detected_after_fix: [], known_gaps}`; V23 reads it.
5. Look at 1:1 crops (before/after) at >= 2 timestamps and at a frame where the person moves; remaining faint structure (mirrored detail ticks, grain mismatch) is a known gap, a visible box is a FAIL.


## v4.5.1 - V05b `--source` and known limit
- `verify_rules.py --source` MUST be the ORIGINAL UNPATCHED raw (it still has the blur pill). V05b takes patch locations from the source and then checks the render pixels there; a patched source gives `patches_found 0` and proves nothing. `check_template_rules.py` V23 scans the PATCHED `public/project/raw.mp4` instead (expects 0 patches).
- The V05b visible-blur predicate is an absolute energy test (median DoG 0.8/1.6 px of the uncovered patch pixels in the render <= max(1.0, 4*level/zoom)). On smooth phone/TikTok footage natural areas are 0.15-0.30, so a correct fill still reads "blurred" and V05b fails (demo: 94/94 frames). Measure before chasing it: compare the DoG median of the fill vs natural regions; do NOT add grain to reach 1.0 (a visible noisy box). Record a user-accepted waiver in the verify report + feedback.md ("source not pure raw, user accepted <date>"), never loosen thresholds.
- Better fill idea (tested, not shipped): align the rows above/below the hole with 1-D dynamic time warping and morph along the edges (x' + a*o(x') = x, pen 25, mu 0.1, R 90); it removes most smeared arm/collar streaks.
