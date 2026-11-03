#!/usr/bin/env bash
# v4.2: fetch a REAL open-license concept icon (never a blank placeholder).
# usage: scripts/fetch_icon.sh <concept-slug> <set:name> [<set:name> ...] [--color #ffffff] [--dir public/project/illustrations]
# sets, tried in the order given:  lucide:<name> (ISC)  tabler:<name> (MIT, outline)  ph:<name> (Phosphor, MIT)  mi:<name> (Material Symbols, Apache-2.0)  iconify:<prefix>/<name> (any Iconify set - check its licence)
# writes <dir>/<concept-slug>.svg recoloured to --color (default white: the card is dark) and appends the source + licence to <dir>/icons.json
# exit 0 = file written, 3 = no source had the icon (the caller then falls back to a hand-drawn SVG composition: assets/illustrations/*.svg)
set -uo pipefail
SLUG="$1"; shift
COLOR="#ffffff"; DIR="public/project/illustrations"; CANDS=()
while [ $# -gt 0 ]; do case "$1" in --color) COLOR="$2"; shift 2;; --dir) DIR="$2"; shift 2;; *) CANDS+=("$1"); shift;; esac; done
mkdir -p "$DIR"; OUT="$DIR/$SLUG.svg"; TMP="$(mktemp)"
get() { curl -fsSL --max-time 20 "$1" -o "$TMP" 2>/dev/null && grep -q "<svg" "$TMP"; }
for c in "${CANDS[@]}"; do
  set="${c%%:*}"; name="${c#*:}"; url=""; lic=""
  case "$set" in
    lucide) url="https://cdn.jsdelivr.net/npm/lucide-static@latest/icons/$name.svg"; lic="Lucide (ISC)";;
    tabler) url="https://cdn.jsdelivr.net/npm/@tabler/icons@latest/icons/outline/$name.svg"; lic="Tabler Icons (MIT)";;
    ph) url="https://api.iconify.design/ph/$name.svg?color=%23ffffff&height=256"; lic="Phosphor Icons (MIT) via Iconify";;
    mi) url="https://api.iconify.design/material-symbols/$name.svg?color=%23ffffff&height=256"; lic="Material Symbols (Apache-2.0) via Iconify";;
    iconify) url="https://api.iconify.design/$name.svg?color=%23ffffff&height=256"; lic="Iconify set $name (check the set licence)";;
    *) continue;;
  esac
  if get "$url"; then
    python3 - "$TMP" "$OUT" "$COLOR" <<'PY'
import re, sys
s = open(sys.argv[1], encoding='utf-8').read(); col = sys.argv[3]
s = re.sub(r'currentColor', col, s, flags=re.I); s = re.sub(r'(?i)#fff(fff)?\b', col, s)
m = re.search(r'<svg\b[^>]*>', s)
tag = re.sub(r'\s(width|height)\s*=\s*"[^"]*"', '', m.group(0)); tag = tag.replace('<svg', '<svg width="256" height="256"', 1)
s = s[:m.start()] + tag + s[m.end():]
open(sys.argv[2], 'w', encoding='utf-8').write(s)
PY
    python3 - "$DIR/icons.json" "$SLUG" "$c" "$url" "$lic" <<'PY'
import json, os, sys
p, slug, c, url, lic = sys.argv[1:]
d = json.load(open(p)) if os.path.exists(p) else {}
d[slug] = dict(icon=c, url=url, license=lic); json.dump(d, open(p, 'w'), indent=1, ensure_ascii=False)
PY
    echo "icon $SLUG <- $c ($lic)"; rm -f "$TMP"; exit 0
  fi
done
rm -f "$TMP"; echo "fetch_icon: none of [${CANDS[*]}] resolved for $SLUG" >&2; exit 3
