#!/usr/bin/env python3
"""
MANDATORY STEP 0 - orientation / format probe.  NO editing is allowed before public/project/probe.json exists.

  python3 scripts/probe_video.py /path/to/raw.mp4 [--target native|vertical] [--reframe blurfill|crop|none] [--focus-x 0.5] [--out public/project]

What it does
  1. ffprobe the raw file: stored size, rotation (display matrix / rotate tag), SAR/DAR, fps (r_frame_rate vs avg_frame_rate -> VFR flag),
     duration, codec, audio presence.
  2. Computes the EFFECTIVE size (after rotation and SAR), aspect, orientation and the layout key (decision table in
     references/orientation-layouts.md; same rule as assets/layouts.ts chooseLayoutKey()).
  3. If the file needs normalising (rotation != 0, SAR != 1, VFR, odd codec) it is re-encoded to public/project/raw.mp4:
     autorotate + square pixels + constant fps + H.264 yuv420p + keyframe every 1s (so OffthreadVideo seeks are exact).
     Otherwise it is copied to public/project/raw.<ext>.
  4. Writes public/project/probe.json (this is the gate: make_edl.py and the Remotion composition refuse to run without it).
"""
import argparse, json, math, os, shutil, subprocess, sys


def run(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


def frac(s, default=0.0):
    try:
        a, b = s.split('/')
        return float(a) / float(b) if float(b) else default
    except Exception:
        try:
            return float(s)
        except Exception:
            return default


def ffprobe(path):
    return json.loads(run(['ffprobe', '-v', 'error', '-print_format', 'json', '-show_format', '-show_streams', path]))


def analyse(path):
    d = ffprobe(path)
    v = next((s for s in d['streams'] if s['codec_type'] == 'video'), None)
    if v is None:
        sys.exit('ERROR: no video stream in ' + path)
    has_audio = any(s['codec_type'] == 'audio' for s in d['streams'])
    w, h = int(v['width']), int(v['height'])
    rot = 0
    for sd in v.get('side_data_list', []) or []:
        if 'rotation' in sd:
            rot = int(round(float(sd['rotation'])))  # ffprobe: counter-clockwise degrees (e.g. -90 for a phone portrait clip)
    if 'rotate' in (v.get('tags') or {}):
        rot = -int(float(v['tags']['rotate']))
    rot_cw = (-rot) % 360  # normalised clockwise rotation that must be APPLIED
    sar = frac(v.get('sample_aspect_ratio', '1:1').replace(':', '/'), 1.0) or 1.0
    if sar <= 0:
        sar = 1.0
    ew, eh = (h, w) if rot_cw in (90, 270) else (w, h)
    ew = int(round(ew * sar)) if abs(sar - 1) > 0.005 else ew
    avg, rfr = frac(v.get('avg_frame_rate', '0/1')), frac(v.get('r_frame_rate', '0/1'))
    fps = avg or rfr or 30.0
    vfr = bool(rfr and avg and abs(rfr - avg) / max(rfr, 1) > 0.02)
    dur = float(v.get('duration') or d['format'].get('duration') or 0)
    aspect = ew / eh
    orient = 'portrait' if aspect < 0.95 else 'landscape' if aspect > 1.05 else 'square'
    return dict(codec=v['codec_name'], hasAudio=has_audio, durationSec=round(dur, 3), fps=round(fps, 3), fpsIsVariable=vfr,
                stored=dict(width=w, height=h), rotationDeg=rot_cw, sar=round(sar, 4), effective=dict(width=ew, height=eh),
                aspect=round(aspect, 4), orientation=orient, dar=v.get('display_aspect_ratio'), pixFmt=v.get('pix_fmt'))


def layout_key(orientation, reframe):  # == chooseLayoutKey() in assets/layouts.ts
    if orientation == 'portrait':
        return 'vertical'
    if orientation == 'landscape':
        return 'horizontal' if reframe == 'none' else 'horizontal-to-vertical'
    return 'square' if reframe == 'none' else 'square-to-vertical'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('video')
    ap.add_argument('--target', choices=['native', 'vertical'], default='native',
                    help='native: keep the raw ratio (16:9 stays 16:9). vertical: landscape/square raw becomes a 9:16 canvas (TikTok/Reels/Shorts).')
    ap.add_argument('--reframe', choices=['blurfill', 'crop', 'none'], default=None, help='only for --target vertical (default blurfill)')
    ap.add_argument('--focus-x', type=float, default=0.5, help='0..1 horizontal focus when --reframe crop')
    ap.add_argument('--out', default='public/project')
    ap.add_argument('--no-normalize', action='store_true', help='do not re-encode even when needed (not recommended)')
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    src = analyse(a.video)
    needs = src['rotationDeg'] != 0 or abs(src['sar'] - 1) > 0.005 or src['fpsIsVariable'] or src['codec'] not in ('h264',)
    if a.target == 'native' or src['orientation'] == 'portrait':
        reframe = 'none'
    else:
        reframe = a.reframe or 'blurfill'
    dest_ext = '.mp4'
    dest = os.path.join(a.out, 'raw' + dest_ext)

    if needs and not a.no_normalize:
        fps = 30 if (src['fpsIsVariable'] or src['fps'] < 20 or src['fps'] > 60) else round(src['fps'])
        vf = ['scale=trunc(iw*sar/2)*2:trunc(ih/2)*2', 'setsar=1', f'fps={fps}'] if abs(src['sar'] - 1) > 0.005 else [f'fps={fps}', 'setsar=1']
        cmd = ['ffmpeg', '-y', '-v', 'error', '-i', a.video, '-vf', ','.join(vf), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '17', '-pix_fmt', 'yuv420p',
               '-g', str(fps), '-keyint_min', str(fps), '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', dest]  # ffmpeg autorotates by default
        print('normalising ->', dest, ' '.join(cmd))
        subprocess.run(cmd, check=True)
        final = analyse(dest)
        normalized = True
    else:
        if os.path.abspath(a.video) != os.path.abspath(dest):
            shutil.copyfile(a.video, dest)
        final = analyse(dest)
        normalized = False

    probe = dict(version=1, gate='passed', file='project/raw' + dest_ext, normalized=normalized, original=src,
                 codec=final['codec'], hasAudio=final['hasAudio'], durationSec=final['durationSec'], fps=final['fps'],
                 fpsIsVariable=final['fpsIsVariable'], stored=final['stored'], rotationDeg=final['rotationDeg'], sar=final['sar'],
                 effective=final['effective'], aspect=final['aspect'], orientation=final['orientation'],
                 needsNormalize=False if normalized else needs, reframe=reframe, cropFocusX=a.focus_x,
                 layoutKey=layout_key(final['orientation'], reframe))
    if probe['needsNormalize']:
        print('WARNING: file still needs normalising (--no-normalize). Rotation/SAR/VFR will produce wrong geometry.', file=sys.stderr)
    if not probe['hasAudio']:
        print('NOTE: raw has no audio stream - transcript/silence steps will be skipped, captions need a manual script.')
    path = os.path.join(a.out, 'probe.json')
    json.dump(probe, open(path, 'w'), indent=2, ensure_ascii=False)
    e = probe['effective']
    print(f"OK probe.json: {e['width']}x{e['height']} {probe['orientation']} fps={probe['fps']} dur={probe['durationSec']}s audio={probe['hasAudio']} layout={probe['layoutKey']} reframe={reframe}")
    print('->', path)


if __name__ == '__main__':
    main()
