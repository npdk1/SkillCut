#!/usr/bin/env python3
"""Find screen-recording / screen-filmed / document-like windows in a video (no ML, numpy + ffmpeg only).
  python3 scripts/detect_screen_broll.py public/project/raw.mp4 [--out public/project/screen_broll.json] [--print]
Per sampled frame (style.config.json -> screenBroll): flat = share of 8x8 blocks with luma std < flatStd (UI chrome, documents, empty panels),
axis = share of gradient energy that is horizontal/vertical (text lines, boxes, window edges), luma = mean brightness 0-1.
screen := (flat >= minFlat AND axis >= minAxis AND (luma >= minLuma OR flat >= minFlatDark))  OR  (bright filmed screen: flat >= minFlatBright AND axis >= minAxisBright AND luma >= minLumaBright).   Natural footage (road, faces, rooms) is textured
(low flat) and its edges are diagonal/curved (low axis). Windows shorter than minWindowSec are dropped; gaps <= mergeGapSec are bridged.
Output: {"windows":[{t0,t1,meanFlat,meanAxis,meanLuma}], "frames":[...]}. make_beats.py turns every window into
captionAnchor {anchor:'top', variant:'dark'} (dark pill caption at the top, as the reference does over screen b-roll) and uses the best window's
frame as the editor/phone placeholder image. [E] heuristic - always eyeball with --print; tune thresholds per channel.
"""
import argparse, json, os, subprocess, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(HERE, '..', 'style.config.json'), encoding='utf-8'))['screenBroll']


def features(g):
    h, w = g.shape
    hb, wb = h // 8, w // 8
    blocks = g[:hb * 8, :wb * 8].reshape(hb, 8, wb, 8).std(axis=(1, 3))
    flat = float((blocks < CFG['flatStd']).mean())
    gx = np.abs(np.diff(g, axis=1))[:-1, :]; gy = np.abs(np.diff(g, axis=0))[:, :-1]
    mask = (gx + gy) > 18                      # only real edges
    if mask.sum() < 20:
        axis = 0.0 if flat < 0.9 else 1.0      # almost no edges at all: blank panel
    else:
        ratio = np.maximum(gx, gy)[mask] / (gx[mask] + gy[mask] + 1e-6)
        axis = float((ratio > 0.8).mean())     # edge pixels whose gradient is (almost) purely horizontal OR vertical
    return flat, axis, float(g.mean() / 255)


def detect(video, fps=None):
    fps = fps or CFG['fps']; W = CFG['width']
    probe = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'json', video], capture_output=True, text=True, check=True).stdout)['streams'][0]
    H = int(round(W * probe['height'] / probe['width'] / 8)) * 8
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', video, '-an', '-vf', f'fps={fps},scale={W}:{H},format=gray', '-f', 'rawvideo', '-'], capture_output=True, check=True).stdout
    n = len(raw) // (W * H)
    frames = []
    for i in range(n):
        g = np.frombuffer(raw, dtype=np.uint8, count=W * H, offset=i * W * H).reshape(H, W).astype(np.float32)
        flat, axis, luma = features(g)
        is_screen = (flat >= CFG['minFlat'] and axis >= CFG['minAxis'] and (luma >= CFG['minLuma'] or flat >= CFG['minFlatDark'])) or \
                    (flat >= CFG['minFlatBright'] and axis >= CFG['minAxisBright'] and luma >= CFG['minLumaBright'])
        frames.append(dict(t=round(i / fps, 2), flat=round(flat, 2), axis=round(axis, 2), luma=round(luma, 2), screen=bool(is_screen)))
    wins, cur = [], None
    for f in frames:
        if f['screen']:
            if cur and f['t'] - cur['t1'] <= CFG['mergeGapSec'] + 1 / fps:
                cur['t1'] = f['t']; cur['fr'].append(f)
            else:
                if cur: wins.append(cur)
                cur = dict(t0=f['t'], t1=f['t'], fr=[f])
    if cur: wins.append(cur)
    out = []
    for w in wins:
        t1 = w['t1'] + 1 / fps
        if t1 - w['t0'] >= CFG['minWindowSec']:
            fr = w['fr']
            out.append(dict(t0=round(w['t0'], 2), t1=round(t1, 2), meanFlat=round(float(np.mean([x['flat'] for x in fr])), 2), meanAxis=round(float(np.mean([x['axis'] for x in fr])), 2), meanLuma=round(float(np.mean([x['luma'] for x in fr])), 2)))
    return out, frames


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('video'); ap.add_argument('--out', default='public/project/screen_broll.json'); ap.add_argument('--print', action='store_true')
    a = ap.parse_args()
    wins, frames = detect(a.video)
    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
    json.dump(dict(video=os.path.basename(a.video), params=CFG, windows=wins, frames=frames), open(a.out, 'w'), indent=1)
    print(f'{len(wins)} screen-like window(s): ' + ', '.join(f"{w['t0']}-{w['t1']}s" for w in wins))
    if a.print:
        for f in frames: print(f"{f['t']:6.2f} flat={f['flat']:.2f} axis={f['axis']:.2f} luma={f['luma']:.2f} {'SCREEN' if f['screen'] else ''}")
