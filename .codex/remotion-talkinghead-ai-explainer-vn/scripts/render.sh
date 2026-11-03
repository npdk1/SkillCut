#!/usr/bin/env bash
# Render + force a standard yuv420p (limited range, bt709) file.
# Why: Remotion with jpeg frames (fast) yields h264 tagged yuvj420p (full range) even with --pixel-format=yuv420p;
# some players/TikTok uploaders treat that badly. The second pass converts range properly (no colour shift) and tags bt709.
# usage: scripts/render.sh [out.mp4] [composition]
set -euo pipefail
OUT="${1:-out/final.mp4}"; COMP="${2:-TalkingHead}"
mkdir -p "$(dirname "$OUT")"
TMP="${OUT%.mp4}.rawframes.mp4"
# mandatory gates (v4.2) - the render never starts while one fails:
#  1. overlap gate: ANY caption / title / beat element / illustration / brand-logo box overlap > 6px (both axes), or an element/logo/caption covering > 10% of the speaker's face
#  2. text-behind readability gate: every text-behind-speaker beat >= 90% readable on average and on its worst frame, measured with Render's text_occlusion.py (<= 10% occluded)
# When a gate fails, scripts/autofix_overlaps.py repairs beats.json (caption->top / move the CTA / re-slot logos; only decorative beats are dropped, never the closing CTA) and the gates re-run (max 3 rounds). No hand edits, no skip flag.
REPORT="$(dirname "$OUT")/overlaps.json"
# v4.4 PROFILE: every stage is timed -> out/render_profile.json (v4.3 vertical took 9m44s for 41s: gates re-decoded + re-blurred the footage on every round, default concurrency 4 of 8 cores).
# Fixes: gate render = REMOTION_GATE=1 (no video decode/blur), blurred backdrop at 1/4 size, --concurrency=${RENDER_CONCURRENCY:-6}.
PROF="$(dirname "$OUT")/render_profile.json"; T_ALL=$(date +%s.%N); declare -A STAGE
tick() { local n=$(date +%s.%N); STAGE[$1]=$(python3 -c "print(round($n-$T_LAST,1))"); T_LAST=$n; }
T_LAST=$T_ALL
CONC="${RENDER_CONCURRENCY:-6}"
# v4.3: text-behind beats WITHOUT verified masks/placement used to fall back to a plain headline in silence. Now: build the masks here (make_masks.py), and if that is impossible say so LOUDLY.
# v4.4 SPEED: Remotion seeks the raw for every frame; a raw with a keyframe every ~8 s decodes ~240 frames per seek (the v4.3 9m44s). Re-encode ONLY if the GOP is > 1 s (idempotent).
python3 scripts/ensure_keyframes.py public/project/raw.mp4 --max-gop-sec 1.0 >&2 || echo "[render.sh] ensure_keyframes failed - render will be slow" >&2
tick keyframes
need_masks=$(python3 - <<'PY'
import json, os, sys
try: B = json.load(open('public/project/beats.json', encoding='utf-8')).get('beats', [])
except Exception: sys.exit(0)
miss = [b['id'] for b in B if b.get('type') == 'text-behind-speaker' and (not b.get('items') or not os.path.exists(os.path.join('public/project/masks', b['id'], 'mask.json')))]
print(' '.join(miss))
PY
)
if [ -n "$need_masks" ]; then
  echo "[render.sh] text-behind beat(s) [$need_masks] have no person masks / verified placement -> running scripts/make_masks.py now" >&2
  if ! python3 scripts/make_masks.py public/project; then
    {
      echo "################################################################################"
      echo "# WARNING: text-behind-speaker beat(s) [$need_masks] have NO masks (make_masks.py failed)."
      echo "# They will NOT be 'behind the speaker': the gate turns them into a plain headline (big-word)."
      echo "# Fix: set PERSON_MASK=/path/to/person_mask.py and run: python3 scripts/make_masks.py public/project"
      echo "# (set STRICT_TBS=1 to make this an error)"
      echo "################################################################################"
    } >&2
    if [ "${STRICT_TBS:-0}" = "1" ]; then echo "RENDER ABORTED: STRICT_TBS=1 and text-behind masks are missing." >&2; exit 1; fi
  fi
fi
tick masks
ok=0
for round in 1 2 3 4; do      # rounds 1-3: gate -> autofix; round 4 = the final gate run on the result of autofix round 3 (check only)
  g1=0; g2=0
  python3 scripts/tbs_place.py --check public/project || g1=1
  node scripts/check_overlaps.mjs public/project --report "$REPORT" || g2=1
  if [ "$g1$g2" = "00" ]; then ok=1; break; fi
  if [ "$round" = 4 ]; then break; fi
  echo "gate failed (round $round) -> autofix" >&2
  python3 scripts/autofix_overlaps.py public/project --report "$REPORT" --round "$round" || echo "autofix round $round: nothing it can change" >&2
done
tick gates
if [ "$ok" != 1 ]; then echo "RENDER ABORTED: gates still failing after 3 autofix rounds (see $REPORT and out/autofix.json) - there is no skip flag. Exit 2." >&2; exit 2; fi
npx remotion render src/index.ts "$COMP" "$TMP" --pixel-format=yuv420p --crf=16 --concurrency="$CONC"
tick remotion_render
ffmpeg -v error -y -i "$TMP" -vf "scale=in_range=pc:out_range=tv:flags=accurate_rnd+full_chroma_int,format=yuv420p" \
  -c:v libx264 -preset medium -crf 14 -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv \
  -c:a copy -movflags +faststart "$OUT"
rm -f "$TMP"
tick ffmpeg_reencode
{ printf '{"concurrency": %s, "stages_sec": {' "$CONC"; first=1; for k in "${!STAGE[@]}"; do [ $first = 1 ] || printf ', '; printf '"%s": %s' "$k" "${STAGE[$k]}"; first=0; done; printf '}, "total_sec": %s, "out": "%s"}\n' "$(python3 -c "import time;print(round(time.time()-$T_ALL,1))")" "$OUT"; } > "$PROF"; cat "$PROF"
ffprobe -v error -select_streams v:0 -show_entries stream=pix_fmt,color_range -of csv=p=0 "$OUT"
