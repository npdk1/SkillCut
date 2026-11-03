---
name: brand-logos
when: Load at pipeline step 9 (logos), and whenever the transcript names a brand/product (ChatGPT, TikTok, Claude...).
---

# Brand logos (MANDATORY rule) + Registry

**Rule.** If the transcript mentions a well-known brand / product (ChatGPT, OpenAI, Claude, Anthropic, Gemini, Stripe, SQLite, GitHub, Cursor, Notion, Figma, YouTube, TikTok, Remotion, Python, Node.js, ...), the agent running this template MUST get the **real logo** and show it in a `brand-logo` beat. Never draw, trace or "approximate" a logo. If no source has it: log it in the Registry as `NOT FOUND`, skip the beat, tell the user.

## 1. Detect
`scripts/make_beats.py` prints `BRAND LOGOS MISSING (...)` for every alias in `style.config.json -> brandLogos.brands` that appears in `words.json` but has no file in `public/project/logos/`. Also read the transcript yourself: ASR mangles brands ('chát GPT', 'cớt' = Claude, 'sờ quy lai' = SQLite, 'du túp'...), and rare brands are not in the alias list. Add any new brand + its mishearings to `brandLogos.brands` (ASCII alias = accent-folded match; alias with diacritics = strict match; `caseSensitive:true` for common English words such as Apple/Word/Zoom).

## 2. Fetch - try EVERY source in this order before giving up
1. **Simple Icons** (`https://cdn.jsdelivr.net/npm/simple-icons@latest/icons/<slug>.svg`, hex colours in `.../data/simple-icons.json`; or `https://cdn.simpleicons.org/<slug>`). Single-colour path; the helper injects the brand fill.
2. **svgl.app** (`https://api.svgl.app?search=<name>` -> `route`): multi-colour official-style SVGs (light/dark variants).
3. **Wikimedia Commons / Wikipedia** (`https://commons.wikimedia.org/w/api.php?action=query&list=search&srnamespace=6&srsearch=<name>+logo+svg&format=json`, then `prop=imageinfo&iiprop=url|extmetadata`): choose a `.svg` whose title contains the brand; record the file page + licence.
4. **The official site / press kit / brand guidelines** (e.g. `<domain>/brand`, `/press`, `/media-kit`; GitHub brand toolkit; `https://<domain>/favicon.svg`, `apple-touch-icon.png`).
5. **Favicon, last resort** (raster): `https://www.google.com/s2/favicons?domain=<domain>&sz=256`. Clearbit's logo API is dead (checked 2026-11-02).

`scripts/fetch_logo.sh <slug> [simple-icons-slug] [domain] [svgl query...]` automates 1, 2 and 5 and prints the Registry line; 3 and 4 are manual (curl). Output: `public/project/logos/<slug>.svg|png`. Optional `public/project/logos/logos.json` `{ "<slug>": {"color": "#635BFF"} }` overrides the glow colour (otherwise `brandLogos.brands[].color` [E] hint is used).

Examples of what is NOT in a source: Simple Icons has no `chatgpt` (use the `openai` mark: `fetch_logo.sh chatgpt openai chatgpt.com`), Microsoft/LinkedIn-type marks were removed from Simple Icons (use svgl / Wikimedia).

## 3. Compare with the Registry, then record
Before using a fetched file look the brand up in the Registry below:
- not there -> add a row;
- there -> keep whichever is **better**: SVG over PNG, vector over raster, larger raster, official source (press kit, svgl, Simple Icons) over favicon, valid clean SVG (has `viewBox`, no `<script>`, no embedded bitmap). Better -> overwrite the file, update the row (source, date, colour, `previous:` note). Not better -> keep the old one and leave the row.
- if the logo is SVG and you want to use it as a component elsewhere, add/update `src/components/brands/<Name>Logo.tsx` (inline `<svg viewBox>`, props `{size, color}`) - optional; the `brand-logo` beat itself just renders the file with `<Img>`.

## 4. Use
`make_beats.py` emits one `{type:'brand-logo', name, logo:'project/logos/<slug>.svg', color}` per brand at its **first mention** (hold `brandLogos.holdSec`=2.0 s, at most one per `minGapSec`=4 s; a close second brand is delayed up to `maxDelaySec`=2 s, else skipped). Layout `layout.<orientation>.logo` (white rounded card + brand-colour glow + name; zone just below the title zone, above the caption zone). Collision priority: above `sticker`/`avatar-chain` (so the real logo replaces the generic brand tile), below title/prompt/chip/big-word. A logo is dropped (reason logged) when it would sit on a full-screen `topic-card`/`info-scene`. In Studio `LayoutCollisionGuard` checks it like every other beat.

## Registry (append / update; source URL, colour, date; newest info wins only when better)
| slug | name | file | source | source URL | colour | fetched | notes |
|---|---|---|---|---|---|---|---|
| stripe | Stripe | stripe.svg | Simple Icons (jsDelivr) | https://cdn.jsdelivr.net/npm/simple-icons@latest/icons/stripe.svg | #635BFF | 2026-11-02 | SVG mono, brand fill injected |
| sqlite | SQLite | sqlite.svg | Simple Icons (jsDelivr) | https://cdn.jsdelivr.net/npm/simple-icons@latest/icons/sqlite.svg | #003B57 | 2026-11-02 | SVG mono |
| claude | Claude | claude.svg | Simple Icons (jsDelivr) | https://cdn.jsdelivr.net/npm/simple-icons@latest/icons/claude.svg | #D97757 | 2026-11-02 | SVG mono |
| chatgpt | ChatGPT | chatgpt.svg | Simple Icons `openai` (jsDelivr) | https://cdn.jsdelivr.net/npm/simple-icons@latest/icons/openai.svg | (none in data; black mark) | 2026-11-02 | there is no `chatgpt` slug; the OpenAI mark is the ChatGPT mark. Trademark of OpenAI |

Licence note: Simple Icons paths are CC0 but the **trademarks belong to their owners** - used here only to identify the brand named in the video (nominative use); do not recolour/distort beyond the brand colour.

## Face-aware placement (v4.1)
The logo card is placed by `scripts/logo_place.py` using `faces.json` (never over the speaker's face; strict test + 10% DOM-box tolerance in `check_logo_faces.py`). The render gate fails if a logo card intersects the face. Never invent a logo: no real source => `NOT FOUND`, skip the beat.


## v4.2 note
`make_beats.py` now fetches missing logos itself (`brandLogos.autoFetch`: Simple Icons → svgl → unpkg mirror → favicon, via `scripts/fetch_logo.sh`), so Claude / TikTok no longer need a manual step; placement is strict (no 'least overlap' - a card that cannot avoid the real face is dropped and logged). Overlap threshold 6 px. Concept icons (not brands) are in `references/illustrations.md`.


## v4.3 - va chạm
Logo va chạm -> thử thời điểm `brandLogos.retryOffsetsSec` (<= `relocateMaxSec` sau lần nhắc đầu) và các slot khác trước khi bỏ. Dedupe: logo cùng thương hiệu với sticker/phần tử khác cùng thời điểm -> chỉ giữ logo.

## Hard rules / commands / thresholds (v4.4)
- Logo must be REAL (SVG or PNG >= 128 px from Simple Icons / svgl / Wikimedia / official kit); never draw one. Missing = `NOT FOUND` in the Registry (V15).
- Fetch: `scripts/fetch_logo.sh <slug> [simple-icons-slug] ...`; place: `scripts/logo_place.py` (strict, same face-aware card model as icons); gate: `python3 scripts/check_logo_faces.py`.
- v4.4: **never drop a logo for "no slot" before trying more**: `brandLogos.margin` relaxed, size ladder `brandLogos.ladder` (smaller rungs down to ~120 px), retry offsets `brandLogos.retryOffsetsSec` / `relocateMaxSec`. Drop only when every slot x size x time failed, and log every tried rung.
- Logo never overlaps face (> 10 % of the face box), captions, text-behind, CTA (6 px gate).
