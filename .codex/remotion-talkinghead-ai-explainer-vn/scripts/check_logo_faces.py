#!/usr/bin/env python3
"""Element-vs-face part of the overlap gate (called by check_overlaps.mjs).
usage: check_logo_faces.py [public/project] [boxes.json]
 - brand-logo cards (from beats.json x/y/scale)  : ANY overlap with the real face box FAILS (> 6 px, the one pipeline threshold)
 - DOM boxes sampled during the render (boxes.json: title, rec, chips, prompt, comment, big-word, sticker): FAIL when they cover more than
   `tolerance` (default 10 %) of the face box. The face box is the real detection (faces.json) incl. framing zoom / punch overshoot, NOT expanded.
prints JSON {checked, violations:[...]}; exit 1 on any violation."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import logo_place
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'public', 'project')
boxes_p = sys.argv[2] if len(sys.argv) > 2 else None
TOL = 0.10
OVL = 6   # px, same as LayoutCollisionGuard OVL_PX
CFG = json.load(open(os.path.join(ROOT, 'style.config.json'), encoding='utf-8'))
J = lambda n, dflt=None: json.load(open(os.path.join(d, n), encoding='utf-8')) if os.path.exists(os.path.join(d, n)) else dflt
beats = (J('beats.json', {}) or {}).get('beats', []); probe = J('probe.json', {}); edl = J('edl.json', {}) or {}
segs = edl.get('segments')
faces = logo_place.load_faces(os.path.join(d, 'faces.json'))
ci = logo_place.canvas_info(CFG, probe)
LY = ci['prof']; LG = dict(size=round(LY['logo']['size'] * ci['u']), nameFont=round(LY['logo']['nameFont'] * ci['u']))
out, n = [], 0
for b in beats:
    if b.get('type') not in ('brand-logo', 'illustration'): continue      # v4.2: illustration cards use the same card model and the same zero-overlap rule
    n += 1
    fr = logo_place.face_rect(faces, segs, CFG, ci, b['t0'], b['t1']) if faces else None
    if not fr: continue
    cw, ch = logo_place.card_size(b.get('name') or b.get('label', ''), ci, b.get('scale', 1.0), LG)
    if b.get('x') is not None: x0, y0 = b['x'] * ci['W'] - cw / 2, b['y'] * ci['H']
    else: x0, y0 = (ci['W'] - cw) / 2, LY['logo']['yR'] * ci['H']
    ox = min(x0 + cw, fr[2]) - max(x0, fr[0]); oy = min(y0 + ch, fr[3]) - max(y0, fr[1])
    if ox > OVL and oy > OVL:
        out.append(dict(kind='logo', name=b.get('name') or b.get('label', ''), btype=b['type'], t0=b['t0'], t1=b['t1'], overlapPct=round(100 * ox * oy / max(1, (fr[2] - fr[0]) * (fr[3] - fr[1]))), box=[round(x0), round(y0), round(x0 + cw), round(y0 + ch)], face=[round(v) for v in fr]))
if boxes_p and faces and segs:
    fps = 30 if probe.get('fpsIsVariable') or probe.get('fps', 30) < 20 else round(probe['fps'])
    starts = []; c = 0.0
    for s in segs:
        starts.append((c, s)); c += (s['srcOut'] - s['srcIn']) / (s.get('speed') or 1)
    def src_t(tout):
        for c0, s in reversed(starts):
            if tout >= c0 - 1e-6: return s['srcIn'] + (tout - c0) * (s.get('speed') or 1)
        return tout
    agg = {}
    for bx in json.load(open(boxes_p)):
        n += 1
        ts = src_t(bx['f'] / fps)
        fr = logo_place.face_rect(faces, segs, CFG, ci, ts, ts)
        if not fr: continue
        r = bx['r']; ox = min(r[2], fr[2]) - max(r[0], fr[0]); oy = min(r[3], fr[3]) - max(r[1], fr[1])
        if ox <= 0 or oy <= 0: continue
        frac = ox * oy / max(1, (fr[2] - fr[0]) * (fr[3] - fr[1]))
        lim = 0.0 if bx['n'] in ('brand-logo', 'illustration') else TOL
        if frac > lim and (ox > OVL and oy > OVL):
            a = agg.setdefault(bx['n'], [])
            if a and bx['f'] - a[-1]['f1'] <= 8: a[-1]['f1'] = bx['f']; a[-1]['max'] = max(a[-1]['max'], round(frac * 100))
            else: a.append(dict(f0=bx['f'], f1=bx['f'], max=round(frac * 100)))
    for name, rs in agg.items():
        for r in rs: out.append(dict(kind='face', name=name, outFrom=round(r['f0'] / fps, 2), outTo=round(r['f1'] / fps, 2), overlapPct=r['max']))
print(json.dumps(dict(checked=n, violations=out), ensure_ascii=False))
sys.exit(1 if out else 0)
