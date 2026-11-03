---
name: illustrations
when: Load at pipeline step 8 (illustrations) and whenever a spoken concept can be drawn (customer talk, sale, money, growth, AI, learning).
---

# Illustrations (v4.2, MANDATORY rule) + concept→icon map

**Rule.** When the speech names a concept that can be pictured, an icon card (`type:'illustration'`) pops in next to the speaker, never over the face. Customer communication → two people talking, sale → cart/tag, money, growth, time, AI, learning, documents, jobs, idea, goal, team, data, email. A card is **never blank**: a real icon or a hand-drawn SVG composition, nothing else.

## 1. Detect
`make_beats.py` matches `style.config.json → autoBeats.illustration.concepts[].keywords` against `words.json`:
- whole-word match, **accent-sensitive** (folding accents would make `bán` = `bạn`), case-sensitive when the keyword has capitals (`AI`; Vietnamese `ai` means "who");
- also read the transcript yourself for pictureable concepts the table lacks and add a row (`id`, `label`, `keywords`, `icons`, `hand`, `color`).

## 2. Fetch - source order
1. **Lucide** (ISC) · 2. **Tabler** (MIT) · 3. **Phosphor** (MIT) · 4. **Material Symbols** (Apache-2.0) · 5. any other **Iconify** set (check its licence) - all via `scripts/fetch_icon.sh <slug> lucide:<name> tabler:<name> ph:<name> mi:<name> iconify:<prefix>/<name> [--color #fff] [--dir public/project/illustrations]`. First name that resolves wins; the script recolours `currentColor` to white and writes `{icon,url,license}` to `<dir>/icons.json`; exit 3 = none resolved.
6. **Hand-drawn SVG composition** (`assets/illustrations/<name>.svg`, white strokes on a 256 viewBox, original, CC0) when no set has the picture. Set `"hand": "<file>"` on the concept; `"handFirst": true` when the comparison below shows the sets cannot draw it.
7. Never a placeholder / empty card. No icon + no hand-drawn file ⇒ the beat is dropped and logged (`skip illustration …`).

## 3. Compare, then record (like the brand-logo registry)
Before using an icon compare it with the map below: new concept ⇒ add a row; existing ⇒ replace only with a better one (more literal meaning, cleaner stroke, clearer licence) and say why.

| concept id | label | keywords (examples) | icon used | source | licence | note |
|---|---|---|---|---|---|---|
| customer-talk | Giao tiếp | giao tiếp với khách hàng, khách hàng, nói chuyện | `assets/illustrations/two-people-talking.svg` | hand-drawn | CC0 | Lucide `messages-square`, Phosphor `chats-circle`, Material `conversation` and mdi `conversation` are only speech bubbles, no people ⇒ hand-drawn two people + two bubbles chosen |
| sales | Bán hàng | sale, bán hàng, chốt đơn, doanh số | `lucide:shopping-cart` | lucide-static (jsDelivr) | ISC | fallbacks tabler/ph shopping-cart |
| money | Tiền | tiền, thu nhập, lương, doanh thu | `lucide:banknote` | lucide | ISC | fallback circle-dollar-sign, ph money |
| growth | Phát triển | phát triển, tăng trưởng, thăng tiến | `lucide:trending-up` | lucide | ISC | |
| time | Thời gian | thời gian, mỗi ngày | `lucide:clock` | lucide | ISC | |
| ai | AI | AI, trí tuệ nhân tạo, ChatGPT | `lucide:bot` | lucide | ISC | fallback sparkles / ph robot |
| learning | Học tập | kiến thức, đào tạo, khóa học | `lucide:graduation-cap` | lucide | ISC | |
| documents | Tài liệu | tài liệu, báo cáo, hợp đồng | `lucide:file-text` | lucide | ISC | |
| jobs | Công việc | công việc, việc làm, văn phòng | `lucide:briefcase` | lucide | ISC | |
| idea | Ý tưởng | ý tưởng, sáng tạo, giải pháp | `lucide:lightbulb` | lucide | ISC | |
| goal | Mục tiêu | mục tiêu, hiệu quả, kết quả | `lucide:target` | lucide | ISC | |
| team | Họp nhóm | họp, meeting, đồng nghiệp | `lucide:users` | lucide | ISC | |
| data | Dữ liệu | dữ liệu, data, thống kê | `lucide:database` | lucide | ISC | |
| email | Email | email, gửi mail | `lucide:mail` | lucide | ISC | |

Each project's real fetched sources are in `public/project/illustrations/icons.json` and in the beat's `source` field.

## 4. Placement + gate
- `logo_place.place(..., strict=True)` with the brand-logo card model (`label` = card text); `autoBeats.illustration.placement` (face expand 5%/8%/4%, prefer left → right → above → below, scales 1.0→0.6). No slot clear of the real face / other beats / captions ⇒ **beat dropped + logged**, never "least overlap".
- A full-screen beat (info-scene, topic-card, broll, framed-focus) in the same window ⇒ skipped (logged).
- Quick enumerations ("giao tiếp, sale, tài liệu"): the next icon replaces the previous one in the slot (`t1` of the previous is cut to the next `t0`).
- Window stays inside one EDL segment (never straddles a cut), `holdSec` 2.0, `minHoldSec` 1.2, `maxPerVideo` 8.
- `render.sh` gate (6 px, `data-guard="illustration"`, `check_logo_faces.py` zero-overlap with the real face) re-checks; failures are auto-dropped by `autofix_overlaps.py`.

## 5. Look
Dark gradient card, accent border + glow in the concept colour, icon at 0.64 of the card, label under it; pop-in `envelope(7f)` + damped rotate wobble. Always check a still of the beat by eye.


## v4.3 - kích thước
Icon ~157-196px trên canvas 1080 (card = `layout.logo.size` 250 x scales [1.12, 1.03, 0.95, 0.90], icon = 0.70 card; Beats.tsx `S*0.7`). Không có slot không che mặt ở 0.90 -> thử thời điểm khác (`illustration.placement.retryOffsetsSec`) rồi bỏ + log.

## v4.3.1 - FALLBACK LADDER (an icon is never dropped just because the big size does not fit)

`scripts/logo_place.py place()` (used by `make_beats.py` AND `autofix_overlaps.py`) tries, in this order, always **face-free (0 overlap with the real face box) and clear (6px) of every other overlay on screen**:

1. **Big icon beside the face** - scales 1.12 / 1.03 / 0.95 / 0.90 (icon ~196 / 180 / 167 / 157px on the 1080 canvas) in the modes `left, right, above, below`.
2. **A slot beside the shoulder** - the `left-edge` / `right-edge` of the safe area at several heights between the face's mid-line and the caption zone, then top-left / top-right just below the safe area, then the row right above the captions (`mode: slot:<side>-edge`). Same big scales.
3. **Smaller icon** - `ladder.smallScales` 0.80 / 0.72 / 0.686 (icon ~140 / 126 / **120px = the floor**), rungs 1+2 again.
4. **Compact icon+label pill** (`pill: true`, `ladder.pill`) - ~125px high capsule, small icon + label; sized by `card_size(..., pill=True)`, `assets/zones.ts` and `Beats.tsx` (the DOM box is still `data-guard="illustration"`, so the overlap guard sees it).
5. **Reframe** (`ladder.reframe`) - if the whole ladder fails because a tight/mid close-up fills the frame, the ONE EDL segment the card sits in is switched to `wide` (no zoom ramp, no other card in it) and rungs 1-4 run again; `make_beats` writes the change to `edl.json` (`_reframedBy`). In `--report` the line shows `[ladder rung 5: segment sNN reframed to wide so the face shrinks]`.

Only after all five fail is the beat skipped, with `no face-free, overlap-free slot ... even after the whole ladder`. The `--report` line of every placed icon states the rung and the real icon size (`[icon ~158px, ladder rung 2/3 shoulder-edge slot + smaller size]`). Aim for >= 4 icon beats per 60s; concepts that appear in the speech (customer-talk, sales, money, ...) are protected from the cut by `tighten.conceptBonus` when `make_edl.py --target-sec` builds the cut.

## v4.3.2 - an icon never competes with a text-behind
An illustration and a text-behind-speaker beat must not share a CONCEPT (accent-sensitive token match, >= 3 chars, within `autoBeats.illustration.tbsConceptWindowSec` = 8 s, e.g. "phat trien" text-behind vs the growth icon) or overlap in TIME (`tbsPadSec` = 0.25 s). `make_beats.py` keeps the text-behind and moves the icon (needs >= `minHoldSec` left) or drops it, logging `skip illustration @ t: growth ...: same concept as the text-behind "..." (tbsN) - the text-behind keeps it`. Accent folding is NOT used ("bán" != "bản").

## Hard rules / commands / thresholds (v4.4)
- Detect + place in `make_beats.py` via `logo_place.place(strict=True, last_side=...)`. Icon >= 120 px, source (real open-source icon) recorded in `public/project/illustrations/icons.json` (V13).
- **Side is chosen from free space by the person mask / face box, not pinned**: the beat records `side`, `_freeLeftPx`, `_freeRightPx`, `_sideReason`. With >= 2 icons both sides are used when both have `>= card + 6 px`; never 3 in a row on the same side (V11). If one side has no room (speaker's face fills the right of a close-up) all icons go to the free side and `_sideReason` states the numbers.
- Never covers face / captions / logos / text-behind (6 px gate, V12); never shares a concept (8 s) or time (+-0.25 s) with a text-behind.
- Evidence: `<out>_still_ill<k>_<concept>_<side>.jpg` per icon (V19), made by `scripts/make_evidence.py`.

## v4.5 - DENSITY + PERSON-MASK SLOTS (verified.md V21, V22)
**Density (V21, `autoBeats.illustration.density`)** - the user found 7 icons in 30 s too busy. Rule: at most **1 icon per 7.5 s of OUTPUT time** (`secPerIcon`; <= 4 in 30 s, <= 8 in 60 s, `maxPerVideo` still caps), **>= 5 s clear time between the END of one icon and the START of the next** (`minGapSec`, output time, measured with the EDL), and the **same concept never twice within 15 s** (`sameConceptGapSec`; learning x2 / customer-talk x2 collapse into one). Competing keyword hits are ranked by the per-concept `strength` in the config (ai 10, growth 8, sales 7, money 7, ... team 4, learning 5; ties -> earlier) and the strongest wins; dropped hits are logged in `beats.json -> _skips` (`closer than 5.0s ... to the stronger/earlier ai icon`). Before ranking, hits that cannot be shown anyway (inside a framed-focus / info-scene / broll window, no room left in the segment, same word as a text-behind) are removed so they never use up a density slot. Checked by `scripts/check_template_rules.py` (V21).

**Person-mask slots (V22, `placement.maskSlots`)** - the legacy `logo_place.place()` ladder only knows the face box, so on a close-up (speaker fills the frame) it said "right has no room" without looking. Now `logo_place.mask_slots_place()` runs the per-frame person matte (`person_mask.py`, source-frame masks, mapped to canvas with the framing zoom) over the icon's WHOLE window `[t0, t1]`, takes the union of the person over all frames (dilated `placement.maskClearPx` = 6 px) and tests candidate slots on BOTH sides: 12 y-positions (top-right/left corner above or beside the head down to the shoulder line) x {screen-edge, shoulder-hug}, sizes `scales` 1.12 / 1.03 / 0.95 / 0.9 then `smallScales` 0.8 / 0.72 / 0.686 (down to ~120 px). A candidate is rejected for: canvas/safe bounds, face box (expanded), person pixels, captions/logos (6 px). Side choice: prefer the side opposite the previous icon (alternate); first icon -> the side with more free room; try ALL sizes on the preferred side before falling to the other. If no candidate on a side is free, the icon stays on the other side and `_sideReason` says why (`right NOT free for the whole window at any size 1.12..0.686 (bounds 84, face 84)`); the icon is NEVER forced over the person. Beats record `side`, `mode` (`mask-slot:<side>:<corner|shoulder-hug>`), `_freeLeftPx`, `_freeRightPx`, `_sideReason`, `_personMaskChecked: true`. `autoBeats.illustration.placement.maskSlots=false` restores the v4.4 ladder.

## v4.5.1 - GAP SEMANTICS + CONCEPT PRIORITY
- **`density.gapMode`** (style.config.json): `start-to-start` (default) = the START of an icon must be >= `minGapSec` (5 s) after the START of the previous icon, in OUTPUT time (with `holdSec` 2 that leaves ~3 s of clear air); `end-to-start` = `minGapSec` of clear air after the previous icon ends (old v4.5.0 behaviour, i.e. 7 s start-to-start). Cap stays `int(dur/secPerIcon + 0.2)` = 4 per 30 s. Same concept still >= `sameConceptGapSec` (15 s).
- **Concept priority**: `autoBeats.illustration.concepts.<concept>.priority` (default 0). The density preselect sorts hits by `(-priority, -strength, time)`, so the user's own example concepts (customer-talk = two people talking, sales = tag/cart; both `priority: 10`) win spacing/cap conflicts over generic ones (ai, a second learning). A skipped hit logs "start of one icon -> start of the next ... to the higher-priority/earlier X icon". Demo 30 s result: learning 2.2 s, team 7.9 s, sales 19.0 s, customer-talk 24.4 s (ai dropped).
- V21 (`scripts/check_template_rules.py`) reads `gapMode`, so a 4-icon result passes with start-to-start gaps >= 5 s.
