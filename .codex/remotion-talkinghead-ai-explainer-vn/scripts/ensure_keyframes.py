#!/usr/bin/env python3
"""v4.4 render-speed fix (profile of the v4.3 vertical render: 9m44s for 41 s vs ~4 min in v4.2).
ROOT CAUSE: Remotion's <OffthreadVideo> extracts every output frame with its own ffmpeg seek. A phone raw with one keyframe every ~8 s (22 keyframes in 171 s) makes every
seek decode up to ~240 frames of 1080x1920 -> ~10x slower. FIX: before the render, make sure the raw has a keyframe at least every `--max-gop-sec` (default 1.0 s).
If not, re-encode ONLY the video (libx264 -g 30 -keyint_min 30, crf 14, same fps/size/pix_fmt; audio copied) to a temp file and swap it in; the original is kept as raw.orig.mp4.
usage: python3 scripts/ensure_keyframes.py [public/project/raw.mp4] [--max-gop-sec 1.0]   -> prints JSON {"max_gop_sec": .., "reencoded": bool, "sec": ..}"""
from fractions import Fraction
import argparse, json, os, shutil, subprocess, sys, time
ap = argparse.ArgumentParser(); ap.add_argument('raw', nargs='?', default='public/project/raw.mp4'); ap.add_argument('--max-gop-sec', type=float, default=1.0); ap.add_argument('--check-only', action='store_true')
a = ap.parse_args()
def gop(p):
    o = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-skip_frame', 'nokey', '-show_entries', 'frame=pts_time', '-of', 'csv=p=0', p], capture_output=True, text=True).stdout.split()
    t = [float(x.strip(',')) for x in o if x.strip(',').replace('.', '', 1).isdigit()]
    d = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p], capture_output=True, text=True).stdout.strip()
    end = float(d) if d else (t[-1] if t else 0)
    return max([b - a_ for a_, b in zip(t, t[1:] + [end])] or [end]), len(t)
g, n = gop(a.raw); res = dict(raw=a.raw, max_gop_sec=round(g, 2), keyframes=n, reencoded=False)
if g > a.max_gop_sec + 1e-6 and not a.check_only:
    t0 = time.time(); tmp = a.raw[:-4] + '.kf.mp4'; orig = a.raw[:-4] + '.orig.mp4'
    fps = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=r_frame_rate', '-of', 'csv=p=0', a.raw], capture_output=True, text=True).stdout.strip()
    r = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', a.raw, '-map', '0:v:0', '-map', '0:a?', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '14', '-g', str(max(1, int(float(Fraction(fps or '30/1')) * a.max_gop_sec))),
                        '-keyint_min', '1', '-sc_threshold', '0', '-pix_fmt', 'yuv420p', '-c:a', 'copy', '-movflags', '+faststart', tmp], capture_output=True, text=True)
    if r.returncode: print(r.stderr, file=sys.stderr); sys.exit(1)
    if not os.path.exists(orig): shutil.move(a.raw, orig)
    shutil.move(tmp, a.raw); g2, n2 = gop(a.raw); res.update(reencoded=True, max_gop_sec_after=round(g2, 2), keyframes_after=n2, sec=round(time.time() - t0, 1), original=orig)
print(json.dumps(res))
