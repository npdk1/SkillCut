#!/usr/bin/env bash
# Fetch the REAL logo of a brand into public/project/logos/<slug>.svg|png  (never invents one: exit 1 when every source fails).
#   scripts/fetch_logo.sh <slug> [simple-icons-slug] [domain] [svgl-query...]
#   e.g. scripts/fetch_logo.sh stripe            scripts/fetch_logo.sh chatgpt openai chatgpt.com "ChatGPT" "OpenAI"
# v4.2: make_beats.py now CALLS this script itself for every mentioned brand without a file (brandLogos.autoFetch), passing slug + `si` (Simple Icons slug) + `domain` from style.config.json.
# Order (SKILL.md 'BRAND LOGOS'): Simple Icons (jsDelivr, then cdn.simpleicons.org) -> svgl.app -> favicon 256 (last resort).
# Wikimedia Commons / the official press kit are manual steps (see references/brand-logos.md) - try them yourself when this script exits 1.
# Prints one line:  <slug> <file> <source> <url> <hex-color>   -> copy it into references/brand-logos.md 'Registry'.
set -u
slug="$1"; si="${2:-$1}"; domain="${3:-}"; shift $(( $# >= 3 ? 3 : $# )) 2>/dev/null
OUT="${LOGO_DIR:-public/project/logos}"; mkdir -p "$OUT"; tmp="$(mktemp)"; UA="SkillCut/1.0 (logo fetch)"
ok_svg() { head -c 20000 "$1" | grep -qi '<svg' && ! grep -qi '<script' "$1" && [ "$(wc -c <"$1")" -gt 100 ]; }
done_svg() { sed -E 's/ on[a-z]+="[^"]*"//g' "$tmp" > "$OUT/$slug.svg"; col="$(grep -oiE '(fill|stop-color)="#[0-9a-f]{6}"' "$OUT/$slug.svg" | grep -viE '#(ffffff|000000)' | head -1 | grep -oiE '#[0-9a-f]{6}')"; echo "$slug $OUT/$slug.svg $1 $2 ${col:-${3:-#FFFFFF}}"; rm -f "$tmp"; exit 0; }
hex="$(curl -fsS -m 25 -A "$UA" https://cdn.jsdelivr.net/npm/simple-icons@latest/data/simple-icons.json 2>/dev/null | python3 -c "import sys,json
try:
  d=json.load(sys.stdin); print(next((i['hex'] for i in d if i['slug']=='$si'),''))
except Exception: print('')")"
# 1) Simple Icons: monochrome path -> inject the brand fill
u="https://cdn.jsdelivr.net/npm/simple-icons@latest/icons/$si.svg"
if curl -fsS -m 25 -A "$UA" -o "$tmp" "$u" 2>/dev/null && ok_svg "$tmp"; then
  [ -n "$hex" ] && sed -i -E "0,/<svg /s//<svg fill=\"#$hex\" /" "$tmp"; done_svg simpleicons "$u" "#${hex:-FFFFFF}"; fi
u="https://unpkg.com/simple-icons@latest/icons/$si.svg"          # v4.2: second mirror (a CDN hiccup used to leave Claude / TikTok 'MISSING')
if curl -fsSL -m 25 -A "$UA" -o "$tmp" "$u" 2>/dev/null && ok_svg "$tmp"; then
  [ -n "$hex" ] && sed -i -E "0,/<svg /s//<svg fill=\"#$hex\" /" "$tmp"; done_svg simpleicons-unpkg "$u" "#${hex:-FFFFFF}"; fi
u="https://cdn.simpleicons.org/$si"
if curl -fsSL -m 25 -A "$UA" -o "$tmp" "$u" 2>/dev/null && ok_svg "$tmp"; then done_svg simpleicons-cdn "$u" "#${hex:-FFFFFF}"; fi
# 2) svgl.app
for q in "$slug" "$@"; do
  route="$(curl -fsS -m 25 -A "$UA" -G --data-urlencode "search=$q" https://api.svgl.app 2>/dev/null | python3 -c "import sys,json
try:
  d=json.load(sys.stdin); r=d[0]['route']; print(r if isinstance(r,str) else r.get('light') or r.get('dark'))
except Exception: print('')")"
  if [ -n "$route" ] && curl -fsSL -m 25 -A "$UA" -o "$tmp" "$route" 2>/dev/null && ok_svg "$tmp"; then done_svg svgl "$route" "#FFFFFF"; fi
done
# 3) favicon (last resort, raster)
if [ -n "$domain" ]; then
  u="https://www.google.com/s2/favicons?domain=$domain&sz=256"
  if curl -fsSL -m 25 -A "$UA" -o "$tmp" "$u" 2>/dev/null && [ "$(wc -c <"$tmp")" -gt 600 ] && head -c 4 "$tmp" | grep -q PNG; then mv "$tmp" "$OUT/$slug.png"; echo "$slug $OUT/$slug.png favicon $u #FFFFFF"; exit 0; fi
fi
rm -f "$tmp"; echo "NOT FOUND: $slug (tried simple-icons, svgl, favicon) - try Wikimedia Commons / the official press kit by hand; never invent a logo" >&2; exit 1
