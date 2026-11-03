#!/usr/bin/env python3
"""Face-aware placement of the brand-logo card (used by make_beats.py; mirrors assets/layouts.ts + VideoLayer.tsx geometry).

faces.json (scripts/detect_faces.py) holds the speaker's face box per sample as fractions of the SOURCE frame.
Here that box is mapped to OUTPUT-CANVAS pixels through the same transform the composition applies
(cover / blurfill fit, segment framing zoom wide/mid/tight, punch overshoot, zoom origin), unioned over the beat's
interval, expanded (hair above, chin/neck below) and the card is put in the first FREE slot:
above the head, right, left or below the chin (above the caption zone). Never overlapping the face; else a corner.
"""
import json, os
import cv2, numpy as np

def load_faces(path):
    try:
        d = json.load(open(path, encoding='utf-8'))
        return d if d.get('samples') else None
    except Exception:
        return None

def canvas_info(CFG, probe):
    """python port of buildLayout() (only the parts needed for geometry)"""
    o = (probe or {}).get('original', probe or {})
    ew = (o.get('effective') or {}).get('width', 1080); eh = (o.get('effective') or {}).get('height', 1920)
    orient = o.get('orientation') or ('portrait' if eh > ew else 'landscape')
    reframe = (probe or {}).get('reframe') or 'none'
    aspect = o.get('aspect') or ew / eh
    vertical = orient == 'portrait' or reframe != 'none'
    key = 'vertical' if orient == 'portrait' else ('horizontal' if orient == 'landscape' else 'square')
    if reframe != 'none' and orient != 'portrait': key += '-to-vertical'
    prof_name = 'horizontal' if key == 'horizontal' else 'square' if key == 'square' else 'vertical'
    prof = CFG['layout'][prof_name]; RF = CFG['layout']['reframe']
    S = 1080 if (vertical or min(ew, eh) >= 720) else 720;   # v4.3: vertical canvas is always 1080x1920 (mirror of assets/layouts.ts)
    Lg = 1920 if S == 1080 else 1280
    W, H = (S, Lg) if vertical else ((Lg, S) if key == 'horizontal' else (S, S))
    u = S / 1080
    fg = dict(x=0, y=0, w=W, h=H); fit = 'cover'
    if key.endswith('-to-vertical'):
        if reframe == 'crop': fit = 'crop'
        else:
            fit = 'blurfill'; fh = round(W / aspect)
            fg = dict(x=0, y=round((H - fh) / 2 + H * RF['fgYShiftR']), w=W, h=fh)
    fgScale = fg['w'] / ew if fit == 'blurfill' else max(W / ew, H / eh)
    maxZoom = max(1.0, min(prof['maxZoom'], RF['qualityCap'] / fgScale))
    capY = round(H * prof['caption']['bottomYr'])
    if fit == 'blurfill': capY = min(round(fg['y'] + fg['h'] + (H - fg['y'] - fg['h']) * 0.42), round(H * 0.7))
    return dict(W=W, H=H, u=u, fit=fit, fg=fg, ew=ew, eh=eh, focusX=(probe or {}).get('cropFocusX', 0.5) or 0.5, maxZoom=maxZoom, prof=prof, capY=capY)

def to_canvas(fb, z, ci):
    """fb = (x0,y0,x1,y1) fractions of the source frame -> canvas px after zoom z"""
    W, H = ci['W'], ci['H']
    if ci['fit'] == 'blurfill':
        fg = ci['fg']
        pts = [(fg['x'] + fb[0] * fg['w'], fg['y'] + fb[1] * fg['h']), (fg['x'] + fb[2] * fg['w'], fg['y'] + fb[3] * fg['h'])]
        ox, oy = fg['x'] + fg['w'] / 2, fg['y'] + fg['h'] / 2
    else:
        s = max(W / ci['ew'], H / ci['eh']); dw, dh = ci['ew'] * s, ci['eh'] * s
        offx, offy = (W - dw) * ci['focusX'], (H - dh) * 0.5
        pts = [(offx + fb[0] * dw, offy + fb[1] * dh), (offx + fb[2] * dw, offy + fb[3] * dh)]
        ox, oy = ci['focusX'] * W, 0.4 * H
    return [ox + (pts[0][0] - ox) * z, oy + (pts[0][1] - oy) * z, ox + (pts[1][0] - ox) * z, oy + (pts[1][1] - oy) * z]

def face_rect(faces, segs, CFG, ci, t0, t1):
    """union (canvas px) of the main face over the source interval [t0,t1]; None when no face data"""
    if not faces: return None
    lv = CFG['framing']['levels']; pu = CFG['framing']['punch']['overshoot']
    pad = 0.3
    ss = [s for s in faces['samples'] if t0 - pad <= s['t'] <= t1 + pad and s.get('main')]
    if not ss:   # nearest sample within 1.5 s
        near = [s for s in faces['samples'] if s.get('main') and abs(s['t'] - (t0 + t1) / 2) <= 1.5]
        ss = sorted(near, key=lambda s: abs(s['t'] - (t0 + t1) / 2))[:1]
    if not ss: return None
    R = None
    for s in ss:
        m = s['main']; fb = (m['x'], m['y'], m['x'] + m['w'], m['y'] + m['h']) if 'w' in m else tuple(m)
        seg = next((g for g in (segs or []) if g['srcIn'] - 0.05 <= s['t'] <= g['srcOut'] + 0.05), None)
        zs = [1.0]
        if seg:
            level = lv.get(seg.get('framing') or 'wide', 1.0)
            req = level
            if seg.get('zoom'): req = max(seg['zoom'].get('from', level), seg['zoom'].get('to', level))
            base = min(max(level, req), ci['maxZoom'])
            zs = [min(level, ci['maxZoom']), base]
            if seg.get('punch') or (seg.get('framing') or 'wide') != 'wide': zs.append(min(base * pu, ci['maxZoom'] * pu))
        for z in zs:
            r = to_canvas(fb, z, ci)
            R = r if R is None else [min(R[0], r[0]), min(R[1], r[1]), max(R[2], r[2]), max(R[3], r[3])]
    return R

def expand(R, ex, ci):
    w, h = R[2] - R[0], R[3] - R[1]
    return [max(0, R[0] - ex['x'] * w), max(0, R[1] - ex['up'] * h), min(ci['W'], R[2] + ex['x'] * w), min(ci['H'], R[3] + ex['down'] * h)]

def card_size(name, ci, k, LG, pill=False):
    S = LG['size']                                   # LG is already in canvas px (buildLayout V())
    nf = LG['nameFont']
    if pill:                                         # v4.3 ladder last rung: compact icon+label pill (mirrors Beats.tsx Illustration pill / assets/zones.ts)
        ph = 0.5 * S
        return ph * 0.9 + len(name) * nf * 0.58 + 30 * ci['u'], ph
    cw = max(S * k, len(name) * nf * k * 0.58) + 16 * ci['u']
    ch = (S + nf * 1.7) * k
    return cw, ch

def overlap(a, b, m=0):
    return min(a[2], b[2]) - max(a[0], b[0]) > m and min(a[3], b[3]) - max(a[1], b[1]) > m

def place(face, others, name, ci, PL, LG, safe, cap_top, strict=False, last_side=None):
    """-> dict(cx, top, scale, mode, rect) ; cx/top in px. face: expanded canvas-px rect or None; others: rects to avoid softly"""
    W, H = ci['W'], ci['H']; m = PL.get('marginPx', 24) * ci['u']
    top_lim = max(H * PL.get('topLimitR', 0.095), safe['top'])
    xl, xr = safe['left'], W - safe['right']
    prefer = PL.get('prefer', ['above', 'right', 'left', 'below'])
    def corner(k):
        cw, ch = card_size(name, ci, k, LG)
        side = PL.get('fallbackCorner', 'top-right')
        cx = xr - cw / 2 if 'right' in side else xl + cw / 2
        top = top_lim if 'top' in side else cap_top - ch
        return dict(cx=cx, top=top, scale=k, mode='corner:' + side, rect=[cx - cw / 2, top, cx + cw / 2, top + ch], free=False)
    if not face:
        return corner(min(PL.get('scales', [1.0]))) | dict(mode='corner (no face data)')
    cands = []
    LD = PL.get('ladder') or {}
    scales = list(PL.get('scales', [1.0, 0.85, 0.72, 0.6])) + (list(LD.get('smallScales', [0.8, 0.72, 0.686])) if LD.get('enabled', False) else [])
    def add_c(cx, top, cw, ch, k, mode, pill=False):
        rect = [cx - cw / 2, top, cx + cw / 2, top + ch]
        if cx - cw / 2 < xl - 1 or cx + cw / 2 > xr + 1 or top < top_lim - 1 or top + ch > cap_top + 1: return
        if overlap(rect, face): return
        free = not any(overlap(rect, o, 6) for o in others)
        cands.append(dict(cx=cx, top=top, scale=k, mode=mode, rect=rect, free=free, pill=pill))
    def slots(cw, ch, k, mode_pre, pill=False):
        """v4.3 ladder rung 2: slots beside the shoulder / top corners below the safe area / above the captions (any x edge), face-free"""
        rows = []
        y_lo, y_hi = max(top_lim, face[1] + (face[3] - face[1]) * 0.5), cap_top - ch
        if y_hi >= y_lo: rows += [y_lo + (y_hi - y_lo) * f for f in (0.0, 0.35, 0.7, 1.0)]
        rows += [top_lim, y_hi]
        for side in ('left', 'right'):
            cx = xl + cw / 2 if side == 'left' else xr - cw / 2
            for top in rows: add_c(cx, top, cw, ch, k, f'{mode_pre}{side}-edge', pill)
    for k in scales:
        cw, ch = card_size(name, ci, k, LG)
        fcx = (face[0] + face[2]) / 2; fcy = (face[1] + face[3]) / 2
        cx_c = min(max(fcx, xl + cw / 2), xr - cw / 2)
        for mode in prefer:
            if mode == 'above':
                top = face[1] - m - ch; cx = cx_c
                if top < top_lim: continue
            elif mode == 'below':
                top = face[3] + m; cx = cx_c
                if top + ch > cap_top: continue
            elif mode in ('right', 'left'):
                cx = face[2] + m + cw / 2 if mode == 'right' else face[0] - m - cw / 2
                if cx + cw / 2 > xr or cx - cw / 2 < xl: continue
                top = min(max(top_lim, fcy - ch / 2), cap_top - ch)
                if top < top_lim: continue
            else: continue
            add_c(cx, top, cw, ch, k, mode)
        if LD.get('enabled', False): slots(cw, ch, k, 'slot:')
    if LD.get('enabled', False) and LD.get('pill', True):          # last rung: compact icon+label pill (k = 1 pill units)
        pw, ph = card_size(name, ci, 1.0, LG, pill=True)
        slots(pw, ph, 1.0, 'pill:', True)
    # v4.4 SIDE CHOICE: the icon is NOT pinned to one slot. Among the free candidates of the largest scale that fits, take the side (left / right of the face) with the
    # MORE free room, and alternate with the previous icon (`last_side`) when the other side fits too. Records side + free px on both sides (verified.md V11).
    fcx_ = (face[0] + face[2]) / 2; free_l = face[0] - xl; free_r = xr - face[2]
    sd_ = lambda c: ('left' if c['cx'] < fcx_ else 'right')
    def decorate(c, why):
        c['side'] = sd_(c); c['freeLeftPx'] = round(free_l); c['freeRightPx'] = round(free_r); c['sideReason'] = why; return c
    fr_ = [c for c in cands if c['free']]
    if fr_:
        pool = [c for c in fr_ if c['scale'] == fr_[0]['scale']]
        by_side = {}
        for c in pool: by_side.setdefault(sd_(c), c)         # first (= most preferred mode) free candidate on each side
        if PL.get('sideMode', 'balanced') == 'balanced' and by_side:
            want = 'left' if free_l >= free_r else 'right'
            why = f'{want} has more free room (L {free_l:.0f}px / R {free_r:.0f}px)'
            if last_side == want and len(by_side) > 1:
                want = 'right' if want == 'left' else 'left'; why = f'alternate: previous icon was on the {last_side} and the {want} side fits too (L {free_l:.0f}px / R {free_r:.0f}px)'
            if want not in by_side:
                want = next(iter(by_side)); why = f'only the {want} side has a free slot (L {free_l:.0f}px / R {free_r:.0f}px)'
            return decorate(by_side[want], why)
        return decorate(pool[0], 'first free slot in prefer order')
    if cands: return decorate(cands[0], 'no overlay-free slot: least-bad candidate')
    if strict: return None        # v4.2: the render gate rejects a card on the face -> no 'least overlap' fallback, the caller drops the beat
    # no clean slot around the face (a big close-up): take the corner / smallest card that overlaps the (expanded) face LEAST, not a fixed corner
    def area(r1, r2): return max(0, min(r1[2], r2[2]) - max(r1[0], r2[0])) * max(0, min(r1[3], r2[3]) - max(r1[1], r2[1]))
    best = None
    for k in PL.get('scales', [1.0, 0.85, 0.72, 0.6]):
        cw, ch = card_size(name, ci, k, LG)
        for side in ('top-left', 'top-right', 'bottom-left', 'bottom-right'):
            cx = xr - cw / 2 if 'right' in side else xl + cw / 2
            top = top_lim if 'top' in side else cap_top - ch
            if top < top_lim - 1 or top + ch > cap_top + 1: continue
            rect = [cx - cw / 2, top, cx + cw / 2, top + ch]
            key = (round(area(rect, face) / (cw * ch), 2), not all(not overlap(rect, o, 6) for o in others), -k, side != PL.get('fallbackCorner', 'top-right'))
            if best is None or key < best[0]: best = (key, dict(cx=cx, top=top, scale=k, mode='corner:' + side + ' (least face overlap %.0f%%)' % (key[0] * 100), rect=rect, free=False))
    return best[1] if best else corner(min(PL.get('scales', [0.6])))


# ======================================================================================================================================================
# v4.4.1  PERSON-MASK SLOTS (verified.md V22): the icon side is chosen from the REAL per-frame person matte over the icon's WHOLE time window, not from the face box.
# Candidate slots on BOTH sides (top corner beside/above the head, right/left edge, 'hug' = just outside the body at that height = shoulder slots), sizes down to
# ~120 px; >= clearPx from person / face / captions / other overlays on every frame. Alternates sides; if the preferred side is not free the reason is recorded.
# ======================================================================================================================================================
def mask_slots_place(U, ds, face, others, name, ci, PL, LG, safe, cap_top, last_side=None, scales=None):
    """U: (H/ds, W/ds) float union (max over the icon window) of the DILATED person matte in canvas space. -> dict like place() (+ side, sideReason, *_why) or None.
    Every candidate rect is tested against U (so >= the dilation + `clearPx` from the person on EVERY frame), the expanded face, `others` (6 px) and the caption top."""
    W, H = ci['W'], ci['H']; clear = PL.get('maskClearPx', 6) * ci['u']
    top_lim = max(H * PL.get('topLimitR', 0.095), safe['top']); xl, xr = safe['left'], W - safe['right']
    occ = (U > 0.25)
    if clear > 0:
        kk = max(0, int(round(clear / ds)))
        if kk: occ = cv2.dilate(occ.astype(np.uint8), np.ones((2 * kk + 1, 2 * kk + 1), np.uint8)) > 0
    hh, ww = occ.shape
    def person_hit(r):
        x0, y0, x1, y1 = max(0, int(r[0] / ds)), max(0, int(r[1] / ds)), min(ww, int(np.ceil(r[2] / ds))), min(hh, int(np.ceil(r[3] / ds)))
        return int(occ[y0:y1, x0:x1].sum()) if x1 > x0 and y1 > y0 else 0
    ys, xs = np.where(U > 0.25)
    # free px on each side of the person over the usable band (shoulder height .. above the captions)
    band = occ[int(top_lim / ds):int(cap_top / ds)]
    cols = np.where(band.any(axis=0))[0] if band.size else np.array([])
    fcx = (face[0] + face[2]) / 2 if face else W / 2
    free_l = (cols.min() * ds - xl) if len(cols) else fcx - xl; free_r = (xr - (cols.max() + 1) * ds) if len(cols) else xr - fcx
    if scales is None:
        scales = list(PL.get('scales', [1.12, 1.03, 0.95, 0.9])) + list((PL.get('ladder') or {}).get('smallScales', [0.8, 0.72, 0.686]))
    fcy = (face[1] + face[3]) / 2 if face else H * 0.25
    def cands(side, k):
        cw, ch = card_size(name, ci, k, LG); out = []; why = dict(person=0, overlay=0, bounds=0, face=0)
        ytop = [top_lim + (cap_top - ch - top_lim) * f for f in np.linspace(0, 1, 12)] if cap_top - ch > top_lim else [top_lim]
        edge_cx = xl + cw / 2 if side == 'left' else xr - cw / 2
        for top in ytop:
            xs_ = [edge_cx]
            # hug: just outside the person's silhouette for the rows this card covers (shoulder slot)
            r0, r1 = max(0, int(top / ds)), min(hh, int(np.ceil((top + ch) / ds)))
            band_ = occ[r0:r1]; cc = np.where(band_.any(axis=0))[0] if band_.size else []
            if len(cc):
                hug = (cc.min() * ds - 2 - cw / 2) if side == 'left' else ((cc.max() + 1) * ds + 2 + cw / 2)
                xs_.append(hug)
            for cx in xs_:
                rect = [cx - cw / 2, top, cx + cw / 2, top + ch]
                if rect[0] < xl - 1 or rect[2] > xr + 1 or rect[1] < top_lim - 1 or rect[3] > cap_top + 1: why['bounds'] += 1; continue
                if face and overlap(rect, face): why['face'] += 1; continue
                if person_hit(rect): why['person'] += 1; continue
                if any(overlap(rect, o, 6) for o in others): why['overlay'] += 1; continue
                out.append(dict(cx=cx, top=top, scale=k, rect=rect, kind='corner' if abs(cx - edge_cx) < 1 else 'shoulder-hug', dist=abs((top + ch / 2) - fcy) + 0.25 * abs(cx - fcx)))
        return out, why
    pref = 'right' if last_side in (None, 'left') else 'left'
    if last_side is None: pref = 'right' if free_r >= free_l else 'left'
    order = [pref, 'left' if pref == 'right' else 'right']
    tried = {}
    for si, side in enumerate(order):
        tried[side] = []
        for k in scales:
            c, why = cands(side, k)
            tried[side].append((k, why))
            if c:
                best = min(c, key=lambda z: z['dist'])
                px = round(LG['size'] * k * 0.7)
                if si == 0 and last_side is None: why_s = f'first icon: {side} has more free room (L {free_l:.0f}px / R {free_r:.0f}px)'
                elif si == 0: why_s = f'alternate: previous icon was on the {last_side}; {side} slot free over the whole window ({best["kind"]}, ~{px}px, >= {PL.get("maskClearPx", 6)}px clear of person/face/captions/overlays)'
                else:
                    r_ = tried[order[0]]; why_s = f'{order[0]} NOT free for the whole window at any size {r_[0][0]}..{r_[-1][0]} ({_why_sum(r_)}); {side} slot free ({best["kind"]}, ~{px}px)'
                best.update(mode=f'mask-slot:{side}:{best["kind"]}', free=True, side=side, freeLeftPx=round(free_l), freeRightPx=round(free_r), sideReason=why_s, maskChecked=True)
                return best
    return dict(none=True, why='; '.join(f'{s}: ' + _why_sum(tried[s]) for s in order), freeLeftPx=round(free_l), freeRightPx=round(free_r))

def _why_sum(rows):
    tot = dict(person=0, overlay=0, bounds=0, face=0)
    for _, w in rows:
        for k in tot: tot[k] += w[k]
    return ', '.join(f'{k} {v}' for k, v in tot.items() if v) or 'no candidate'

def person_union(project_dir, CFG, ci, fps, segs, video, a, z, tool, ds=4, step=2, dilate_px=8):
    """per-frame person matte over source window [a, z] -> union in canvas space at 1/ds (masks cached in <project>/masks/_ill_<a>_<z>/, small + unrefined = fast)"""
    import subprocess, sys as _sys, json as _j
    sys_path = os.path.dirname(os.path.abspath(__file__))
    if sys_path not in _sys.path: _sys.path.insert(0, sys_path)
    import tbs_place
    s = max(0.0, round(a - 0.1, 3)); e = round(z + 0.1, 3); mid = f'_ill_{int(round(a * 100))}_{int(round(z * 100))}'
    out = os.path.join(project_dir, 'masks', mid); mj = os.path.join(out, 'mask.json')
    if not os.path.exists(mj):
        cmd = ([tool] if os.access(tool, os.X_OK) else [_sys.executable, tool]) + [video, '--start', str(s), '--end', str(e), '--out', out, '--size', '320', '--no-refine', '--no-analyze']
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode or not os.path.exists(mj): return None
    stage = tbs_place.Stage(project_dir, CFG, ci, fps, segs)
    st, zs, idx = stage.stack(dict(id=mid, maskStart=s, t0=a, t1=z), ds=ds, step=step, dilate_px=dilate_px, blockers=False)
    return st.max(axis=0)
