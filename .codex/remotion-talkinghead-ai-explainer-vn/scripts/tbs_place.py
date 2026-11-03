#!/usr/bin/env python3
"""text-behind-speaker PLACEMENT SEARCH + OCCLUSION GATE (v4.2).

Rule (AGENTS.md -> references/text-behind.md): the AI must verify the speaker with the person masks and
put the text ONLY in empty background space. The mask of every frame of the beat is warped through the SAME framing zoom the
composition applies (wide/mid/tight + punch overshoot, origin focusX/40%), then candidate placements are scanned:
   line      one line, any x / y / size
   split     words on either side of the head (left group | right group, same size, same row)
   stack     2-3 stacked lines (left / centre / right aligned), any x / y / size
   wrap      v4.4: line 1 behind the crown + line 2 on its own row just below in the nearest free background (never drops words)
   short     OFF in v4.4 (autoBeats.textBehind.allowShortPhase=false): a phrase is never cut down to a fragment
Readability = share of the glyph ink NOT covered by the person alpha.  Required: mean >= MEAN_MIN (0.90) AND worst frame >= WORST_MIN (0.80).
Nothing passes -> the caller must fall back to a normal headline / other style (never render occluded text).

CANONICAL MEASUREMENT = the shared render tool /workspace/render-env/bin/text_occlusion.py (glyph-accurate, exit code 3 when > 10 % of the ink is hidden).
It works in MASK space, so this module first writes COMPOSITION-space masks (every mask warped through that frame's framing zoom) to
out/tbs_canvas/<id>/ and calls the tool on those: tune step (make_masks.py) and gate (--check, render.sh) both use it. The in-house
raster search below only GENERATES candidates (line / split / stack / short, align, size) and pre-filters them; if text_occlusion.py is
missing it falls back to its own numbers at the same threshold (<= 10 % occluded).
usage (CLI check of beats.json, used by render.sh):  python3 scripts/tbs_place.py --check public/project
"""
import glob, itertools, json, math, os, re, sys
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
MEAN_MIN, WORST_MIN = 0.90, 0.80
DS = 4

def cfg():
    return json.load(open(os.path.join(ROOT, 'style.config.json'), encoding='utf-8'))

def find_font(name):
    c = glob.glob(os.path.expanduser('~/.fonts/' + name)) + glob.glob('/usr/share/fonts/**/' + name, recursive=True)
    return c[0] if c else None

def ease_out_cubic(x):
    x = min(1.0, max(0.0, x)); return 1 - (1 - x) ** 3

# ------------------------------------------------------------------ framing zoom (python port of VideoLayer.zoomAt) ------------------
def zoom_at(seg, frame_in_seg, dur_frames, CFG, max_zoom):
    lv = CFG['framing']['levels']; fr = seg.get('framing') or 'wide'
    level = lv.get(fr, 1.0)
    z = seg.get('zoom')
    req = z['from'] + (z['to'] - z['from']) * (frame_in_seg / max(1, dur_frames)) if z else level
    base = min(req, max_zoom)
    if seg.get('punch') is False or (fr == 'wide' and not seg.get('punch')): return base
    p = CFG['framing']['punch']
    k = 1 + (p['overshoot'] - 1) * (1 - ease_out_cubic(frame_in_seg / p['settleFrames']))
    return min(base * k, max_zoom * p['overshoot'])

class Stage:
    """canvas geometry + EDL segments + masks of one beat, warped to canvas pixels at 1/ds"""
    def __init__(self, d, CFG, ci, fps, segs):
        self.d, self.CFG, self.ci, self.fps, self.segs = d, CFG, ci, fps, segs or []
        self.W, self.H = ci['W'], ci['H']

    def zoom_for_src_frame(self, sf):
        for s in self.segs:
            a, b = s['srcIn'] * self.fps, s['srcOut'] * self.fps
            if a - 0.5 <= sf < b + 0.5:
                sp = s.get('speed') or 1
                durf = max(1, round((s['srcOut'] - s['srcIn']) / sp * self.fps))
                return zoom_at(s, (sf - round(s['srcIn'] * self.fps)) / sp, durf, self.CFG, self.ci['maxZoom'])
        if self.segs:        # v4.3: a frame inside the (short) cut gap a text-behind window spans -> the zoom of the nearest segment (same framing by construction)
            n = min(self.segs, key=lambda s: min(abs(sf - s['srcIn'] * self.fps), abs(sf - s['srcOut'] * self.fps)))
            return self.zoom_for_src_frame(round(n['srcIn'] * self.fps) + 0.5) if abs(sf - n['srcOut'] * self.fps) > abs(sf - n['srcIn'] * self.fps) else self.zoom_for_src_frame(n['srcOut'] * self.fps - 0.6)
        return 1.0

    def stack(self, beat, ds=DS, step=2, dilate_px=4, blockers=True, track=None, rng=None):
        """float32 (N, H/ds, W/ds) person alpha in CANVAS space for the visible frames of the beat (every `step` frames) + the zoom list"""
        mdir = os.path.join(self.d, 'masks', beat['id']); meta = json.load(open(os.path.join(mdir, 'mask.json')))
        fps = self.fps; first = math.ceil(float(beat.get('maskStart', meta['start'])) * fps - 1e-9)
        cw, ch = int(meta['width']), int(meta['height']); W, H = self.W, self.H
        s = max(W / cw, H / ch); offx = (W - cw * s) * self.ci['focusX']; offy = (H - ch * s) * 0.5
        ox, oy = self.ci['focusX'] * W, 0.4 * H
        out, zs, idx = [], [], []
        a, b = round(beat['t0'] * fps), round(beat['t1'] * fps)
        if rng: a, b = rng                                                    # source-frame range override (crown series over ALL mask frames)
        for sf in range(a, b, step):
            k = sf - first
            fn = os.path.join(mdir, f'mask_{k:05d}.png')
            if k < 0 or not os.path.exists(fn): continue
            z = self.zoom_for_src_frame(sf)
            m = cv2.imread(fn, cv2.IMREAD_GRAYSCALE)
            # mask px -> canvas px: p' = o + (off + s*p - o) * z   (then /ds)
            M = np.array([[s * z / ds, 0, (ox + (offx - ox) * z) / ds], [0, s * z / ds, (oy + (offy - oy) * z) / ds]], np.float32)
            w = cv2.warpAffine(m, M, (W // ds, H // ds), flags=cv2.INTER_AREA if s * z / ds < 1 else cv2.INTER_LINEAR, borderValue=0)
            out.append(w.astype(np.float32) / 255.0); zs.append(z); idx.append(sf)
        st = np.stack(out) if out else np.zeros((1, H // ds, W // ds), np.float32)
        if dilate_px and ds:
            kk = max(1, int(round(dilate_px / ds))); ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * kk + 1, 2 * kk + 1))
            st = np.stack([cv2.dilate(f, ker) for f in st])
        for r in (beat.get('_blockers') or []) if blockers else []:           # v4.2: other beats that share the window (chips, prompt, logo ...) count as "occupied" like the person does
            x0, y0, x1, y1 = [int(max(0, v)) for v in (r[0] * W / ds, r[1] * H / ds, math.ceil(r[2] * W / ds), math.ceil(r[3] * H / ds))]
            st[:, y0:y1, x0:x1] = 1.0
        if track is not None:      # v4.3 crown tracking: shift every frame by -dy[k] so the HEAD stands still (a static text box there = text that follows the crown in the real frame)
            for i_, sf in enumerate(idx):
                dy = track[min(max(sf - first, 0), len(track) - 1)] / ds
                if abs(dy) > 1e-3: st[i_] = cv2.warpAffine(st[i_], np.array([[1, 0, 0], [0, 1, -dy]], np.float32), (st.shape[2], st.shape[1]), flags=cv2.INTER_LINEAR, borderValue=0)
        return st, zs, idx

# ------------------------------------------------------------------ text raster (same metrics as the browser) --------------------------
class Typeset:
    def __init__(self, CFG):
        T = CFG['beats']['textBehind']; self.lh = T['lineHeight']; self.ls = CFG['fonts']['letterSpacingEm']
        self.fontfile = find_font(CFG['autoBeats']['textBehind'].get('tuneFont', 'BeVietnamPro-ExtraBold.ttf')) or find_font('BeVietnamPro-ExtraBold.ttf')
        if not self.fontfile: raise SystemExit('tbs_place: BeVietnamPro-ExtraBold.ttf not found')
        self.fonts = {}
    def font(self, px):
        px = max(4, int(round(px)))
        if px not in self.fonts: self.fonts[px] = ImageFont.truetype(self.fontfile, px)
        return self.fonts[px]
    def line_w(self, text, px):
        f = self.font(px); return f.getlength(text) + self.ls * px * len(text)
    def raster(self, text, px, align, scale):
        """alpha raster (at 1/scale) of the item at font size px (canvas px); returns (alpha, off_x, off_y, anchor-relative):
        off_x/off_y = position of the raster's top-left relative to (anchor_x, line-box-top) in canvas px"""
        lines = text.upper().split('\n'); f = self.font(px)
        asc, desc = f.getmetrics(); lh = px * self.lh
        widths = [self.line_w(l, px) for l in lines]; Wt = max(widths)
        pad = int(px * 0.3); Hbox = lh * len(lines)
        im = Image.new('L', (int(Wt + 2 * pad), int(Hbox + 2 * pad)), 0); dr = ImageDraw.Draw(im)
        for i, l in enumerate(lines):
            base = pad + i * lh + (lh - (asc + desc)) / 2 + asc
            x0 = pad + {'l': 0, 'c': (Wt - widths[i]) / 2, 'r': Wt - widths[i]}[align]
            for ch in l:                                     # per-glyph so letter-spacing is honoured
                dr.text((x0, base), ch, font=f, fill=255, anchor='ls'); x0 += f.getlength(ch) + self.ls * px
        a = np.asarray(im); ys, xs = np.where(a > 100)
        x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
        a = a[y0:y1, x0:x1]
        # ink-box top-left relative to the anchor: anchor_x is left edge / centre / right edge of the text block
        anchor_in_im = pad + {'l': 0, 'c': Wt / 2, 'r': Wt}[align]
        off_x = x0 - anchor_in_im; off_y = y0 - pad
        sm = cv2.resize(a, (max(1, int(round(a.shape[1] / scale))), max(1, int(round(a.shape[0] / scale)))), interpolation=cv2.INTER_AREA)
        return sm.astype(np.float32) / 255.0, off_x, off_y, (a.shape[1], a.shape[0])

    def glyphs(self, text, px, align, scale=1.0):
        """v4.3.2 PER-GLYPH rasters of an item (same layout/metrics as raster()): list of dict(ch, line, a, gx, gy) - `a` = float alpha of ONE character at 1/scale,
        (gx, gy) = its top-left in cells of 1/scale RELATIVE TO THE ITEM'S INK-BOX TOP-LEFT (the same origin as raster()'s ink box / item['ink'][:2])."""
        lines = text.upper().split('\n'); f = self.font(px)
        asc, desc = f.getmetrics(); lh = px * self.lh
        widths = [self.line_w(l, px) for l in lines]; Wt = max(widths); pad = int(px * 0.3)
        raw = []
        for i, l in enumerate(lines):
            base = pad + i * lh + (lh - (asc + desc)) / 2 + asc
            x0 = pad + {'l': 0, 'c': (Wt - widths[i]) / 2, 'r': Wt - widths[i]}[align]
            for ch in l:
                adv = f.getlength(ch) + self.ls * px
                if ch.strip():
                    l_, t_, r_, b_ = f.getbbox(ch, anchor='ls'); gw, gh = int(r_ - l_) + 4, int(b_ - t_) + 4
                    im = Image.new('L', (gw, gh), 0); ImageDraw.Draw(im).text((-l_ + 2, -t_ + 2), ch, font=f, fill=255, anchor='ls')
                    a = np.asarray(im); ys, xs = np.where(a > 100)
                    if len(xs): raw.append((ch, i, a, x0 + l_ - 2, base + t_ - 2, x0 + l_ - 2 + xs.min(), base + t_ - 2 + ys.min()))
                x0 += adv
        if not raw: return []
        X0 = min(r[5] for r in raw); Y0 = min(r[6] for r in raw); out = []
        for ch, i, a, gx, gy, _, _ in raw:
            if scale == 1: sm = a.astype(np.float32) / 255.0; ox, oy = int(round(gx - X0)), int(round(gy - Y0))
            else:
                sm = cv2.resize(a, (max(1, int(round(a.shape[1] / scale))), max(1, int(round(a.shape[0] / scale)))), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
                ox, oy = int(round((gx - X0) / scale)), int(round((gy - Y0) / scale))
            out.append(dict(ch=ch, line=i, a=sm, gx=ox, gy=oy))
        return out

def occl(stack, tmpl, ix, iy):
    """per-frame share of the template ink covered by person alpha when the template's top-left sits at cell (ix, iy)"""
    h, w = tmpl.shape; N, H, W = stack.shape
    x0, y0, x1, y1 = max(ix, 0), max(iy, 0), min(ix + w, W), min(iy + h, H)
    s = float(tmpl.sum())
    if x1 <= x0 or y1 <= y0: return np.ones(N)
    t = tmpl[y0 - iy:y1 - iy, x0 - ix:x1 - ix]
    o = (stack[:, y0:y1, x0:x1] * t[None]).sum(axis=(1, 2)) / s
    return np.clip(o + (1 - float(t.sum()) / s), 0, 1)

def measure_items(stack, items, ds, TS, W):
    """exact occlusion of a set of placed items: returns (mean_readable, worst_readable, per_item_mean_readable)"""
    num = np.zeros(stack.shape[0]); den = 0.0; per = []
    for it in items:
        px = it['size'] * W
        t, ox, oy, _ = TS.raster(it['text'], px, it['align'], ds)
        ix = int(round((it['x'] * W + ox) / ds)); iy = int(round((it['y_px'] + oy) / ds))
        o = occl(stack, t, ix, iy); s = float(t.sum()); num += o * s; den += s; per.append(float(1 - o.mean()))
    o = num / max(den, 1e-9)
    return float(1 - o.mean()), float(1 - o.max()), per

def glyph_min_visible(stack, glyphs, ix, iy):
    """low-res (search) test: per glyph the WORST-frame visible share (1 - covered) for an item whose ink-box top-left sits at cell (ix, iy). -> (min_vis, [(ch, min_vis)])"""
    per = []
    for g_ in glyphs:
        o = occl(stack, g_['a'], ix + g_['gx'], iy + g_['gy']); per.append((g_['ch'], float(1 - o.max())))
    return (min(v for _, v in per) if per else 1.0), per

def glyph_visibility(canvas_dir, item, dy, ka, kb, TS, W, min_vis=0.70):
    """v4.3.2 PER-GLYPH GATE (own script - Render's text_occlusion.py has no --max-glyph yet). Every glyph of `item` is rasterised alone at full resolution (ink-box top-left = item['ink'][:2],
    moved by dy[k] px per mask frame k) and measured against the composition-space masks canvas_dir/mask_<k>.png for k in [ka, kb): visible share = 1 - covered share of THAT glyph's ink.
    -> dict(min_vis, worst=dict(ch, frame, line, vis), per_glyph=[{ch, line, min_vis, frame}], ok = min_vis >= min_vis, frames)"""
    gl = TS.glyphs(item['text'], item['size'] * W, item['align'], 1.0); ink = item['ink']
    per = [dict(ch=g_['ch'], line=g_['line'], min_vis=1.0, frame=None) for g_ in gl]; frames = 0
    for k in range(max(0, ka), kb):
        fn = os.path.join(canvas_dir, f'mask_{k:05d}.png')
        if not os.path.exists(fn): continue
        m = cv2.imread(fn, cv2.IMREAD_GRAYSCALE)
        if m is None: continue
        m = m.astype(np.float32) / 255.0; Hh, Ww = m.shape; frames += 1
        d_ = int(round(dy[min(k, len(dy) - 1)])) if len(dy) else 0
        for pi, g_ in enumerate(gl):
            a = g_['a']; x0 = int(round(ink[0])) + g_['gx']; y0 = int(round(ink[1])) + d_ + g_['gy']; h_, w_ = a.shape
            xa, ya, xb, yb = max(x0, 0), max(y0, 0), min(x0 + w_, Ww), min(y0 + h_, Hh)
            if xb <= xa or yb <= ya: continue
            t = a[ya - y0:yb - y0, xa - x0:xb - x0]; cov = float((m[ya:yb, xa:xb] * t).sum() / max(float(a.sum()), 1e-9))
            v = 1.0 - min(1.0, cov)
            if v < per[pi]['min_vis']: per[pi]['min_vis'] = round(v, 4); per[pi]['frame'] = k
    if not per: return dict(min_vis=1.0, worst=None, per_glyph=[], ok=True, frames=frames)
    w = min(per, key=lambda r: r['min_vis'])
    return dict(min_vis=w['min_vis'], worst=dict(ch=w['ch'], frame=w['frame'], line=w['line'], vis=w['min_vis']), per_glyph=per, ok=w['min_vis'] >= min_vis - 1e-6, frames=frames)

TOOL_CANDIDATES = ['/workspace/render-env/bin/text_occlusion.py']
def occlusion_tool():
    import shutil
    for t in [os.environ.get('TEXT_OCCLUSION')] + TOOL_CANDIDATES + [shutil.which('text_occlusion.py')]:
        if t and os.path.exists(t): return t
    return None

def write_canvas_masks(stage, beat, out_dir, track=None):
    """masks/<id>/mask_%05d.png (source-frame space) -> out_dir/mask_%05d.png in COMPOSITION space (same names, same mask.json),
    each warped through that source frame's framing zoom, so text_occlusion.py measures what the viewer sees."""
    src = os.path.join(stage.d, 'masks', beat['id']); meta = json.load(open(os.path.join(src, 'mask.json')))
    fps = stage.fps; first = math.ceil(float(beat.get('maskStart', meta['start'])) * fps - 1e-9)
    stamp = os.path.join(out_dir, 'mask.json')
    key = dict(meta, _zoomKey=[round(stage.zoom_for_src_frame(first + k), 4) for k in range(0, int(meta['count']), 3)], _canvas=[stage.W, stage.H], _blk=beat.get('_blockers') or [], _trk=(None if track is None else [round(float(v), 1) for v in track[::2]]))
    if os.path.exists(stamp):
        try:
            if json.load(open(stamp)) == key: return out_dir
        except Exception: pass
    os.makedirs(out_dir, exist_ok=True)
    cw, ch = int(meta['width']), int(meta['height']); W, H = stage.W, stage.H
    s = max(W / cw, H / ch); offx = (W - cw * s) * stage.ci['focusX']; offy = (H - ch * s) * 0.5; ox, oy = stage.ci['focusX'] * W, 0.4 * H
    for k in range(int(meta['count'])):
        fn = os.path.join(src, f'mask_{k:05d}.png')
        if not os.path.exists(fn): continue
        z = stage.zoom_for_src_frame(first + k)
        m = cv2.imread(fn, cv2.IMREAD_GRAYSCALE)
        M = np.array([[s * z, 0, ox + (offx - ox) * z], [0, s * z, oy + (offy - oy) * z]], np.float32)
        wm = cv2.warpAffine(m, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=0)
        for r in beat.get('_blockers') or []: wm[int(r[1] * H):int(math.ceil(r[3] * H)), int(r[0] * W):int(math.ceil(r[2] * W))] = 255
        if track is not None and abs(track[min(k, len(track) - 1)]) > 0.05:
            wm = cv2.warpAffine(wm, np.array([[1, 0, 0], [0, 1, -float(track[min(k, len(track) - 1)])]], np.float32), (W, H), flags=cv2.INTER_LINEAR, borderValue=0)
        cv2.imwrite(os.path.join(out_dir, f'mask_{k:05d}.png'), wm)
    json.dump(key, open(stamp, 'w'))
    return out_dir

def _init_glyph_max():
    global GLYPH_MAX
    try: g = cfg()['autoBeats']['textBehind'].get('tuneGlyphMinVisible', 0.70)
    except Exception: g = 0.70
    GLYPH_MAX = round(1 - g, 4) if g > 0 else None

def tool_has_flag(flag):
    """does Render's text_occlusion.py know this flag (e.g. --min-occlusion)? cached"""
    import subprocess
    tool = occlusion_tool()
    if not tool: return False
    if flag not in _FLAGS:
        try: _FLAGS[flag] = flag in subprocess.run([tool, '--help'], capture_output=True, text=True).stdout
        except Exception: _FLAGS[flag] = False
    return _FLAGS[flag]
_FLAGS = {}
_init_glyph_max()

def tool_measure(canvas_dir, item, beat):
    """text_occlusion.py --box on one item (ink box in canvas px). returns dict(max, mean) of the OCCLUDED share, or None when the tool is missing"""
    import subprocess
    tool = occlusion_tool()
    if not tool: return None
    x, y, w, h = item['ink']
    cmd = [tool, canvas_dir, '--box', f'{x:.1f},{y:.1f},{w:.1f},{h:.1f}', '--text', item['text'], '--range', f'{beat["t0"]},{beat["t1"]}', '--no-fail-exit']
    if tool_has_flag('--max-glyph') and GLYPH_MAX is not None: cmd += ['--max-glyph', str(GLYPH_MAX)]
    if tool_has_flag('--min-occlusion') and beat.get('_minOcc'): cmd += ['--min-occlusion', str(beat['_minOcc'])]   # same flag name as Render's tool; the pass/fail of the band is decided below from occlusion_mean/max
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode not in (0, 3): return None
    try: j = json.loads(r.stdout)
    except Exception: return None
    return dict(max=float(j['occlusion_max']), mean=float(j['occlusion_mean']), frames=j.get('frames'), glyph_max=j.get('glyph_occlusion_max'), pass_glyph=j.get('pass_glyph'), worst_glyph=j.get('worst_glyph'))

def verify_external(canvas_dir, items, beat, max_occ):
    """-> (ok, mean_readable, worst_readable) over all items by the canonical tool; (None, ...) when unavailable"""
    ms_, mx_ = [], []
    for it in items:
        r = tool_measure(canvas_dir, it, beat)
        if r is None: return None, None, None
        ms_.append(r['mean']); mx_.append(r['max'])
    return all(m <= max_occ for m in mx_), 1 - max(ms_), 1 - max(mx_)

def person_occlusion(person_dir, items, beat):
    """mean occluded share by the PERSON alone (no blocker rects) of the most-covered item, by text_occlusion.py; None when the tool is missing"""
    vals = []
    for it in items:
        r = tool_measure(person_dir, it, dict(beat, _minOcc=0))
        if r is None: return None
        vals.append(r['mean'])
    return max(vals) if vals else 0.0


# ------------------------------------------------------------------ v4.3 crown tracking ---------------------------------------------------
def crown_series(stage, beat, head=None, ds=DS):
    """crown_y (canvas px, top-most person row near the head columns) for EVERY mask frame k of the beat (zoom-aware: canvas-space masks).
    -> dict(raw=[px], smooth=[px], first=k0). `head` = [x0,y0,x1,y1] canvas px (union of the head over the beat) or None -> centre third of the frame.
    Smoothing: 5-frame median -> zero-phase EMA (alpha 0.4, forward+backward) -> velocity cap (autoBeats.textBehind.trackMaxVelR * H per frame)."""
    mdir = os.path.join(stage.d, 'masks', beat['id']); meta = json.load(open(os.path.join(mdir, 'mask.json')))
    fps = stage.fps; first = math.ceil(float(beat.get('maskStart', meta['start'])) * fps - 1e-9); n = int(meta['count'])
    stk, zs, idx = stage.stack(beat, ds=ds, step=1, dilate_px=0, blockers=False, rng=(first, first + n))
    W, H = stage.W, stage.H; P = stage.CFG['autoBeats'].get('textBehind', {})
    if head: hx0, hx1 = head[0] - 0.08 * W, head[2] + 0.08 * W
    else: hx0, hx1 = 0.3 * W, 0.7 * W
    c0, c1 = max(0, int(hx0 / ds)), min(stk.shape[2], int(hx1 / ds) + 1)
    raw = np.full(n, np.nan)
    for f, sf in zip(stk, idx):
        cnt = (f[:, c0:c1] > 0.5).sum(axis=1); rows = np.where(cnt >= 3)[0]
        if len(rows): raw[sf - first] = rows[0] * ds
    ok = ~np.isnan(raw)
    if ok.sum() < 3: return dict(raw=[0.0] * n, smooth=[0.0] * n, first=first, ok=False)
    raw = np.interp(np.arange(n), np.where(ok)[0], raw[ok])
    med = np.array([np.median(raw[max(0, i - 2):i + 3]) for i in range(n)])
    al = P.get('trackEma', 0.4)
    fw = med.copy()
    for i in range(1, n): fw[i] = al * med[i] + (1 - al) * fw[i - 1]
    bw = fw.copy()
    for i in range(n - 2, -1, -1): bw[i] = al * fw[i] + (1 - al) * bw[i + 1]
    vmax = P.get('trackMaxVelR', 0.012) * H; sm = bw.copy()
    for i in range(1, n): sm[i] = sm[i - 1] + max(-vmax, min(vmax, bw[i] - sm[i - 1]))
    return dict(raw=[float(v) for v in raw], smooth=[float(v) for v in sm], first=first, ok=True)

def track_dy(cs, ka, kb, clamp=None):
    """per-mask-frame y offset (canvas px, + = down) relative to the crown's median over the window [ka, kb)"""
    sm = np.array(cs['smooth']); ref = float(np.median(sm[max(0, ka):max(ka + 1, kb)]))
    d = sm - ref
    if clamp: d = np.clip(d, -clamp, clamp)
    return [float(v) for v in d], ref

def head_motion(cs, ka, kb):
    """px range of the RAW crown over the window = how much a static text would be hit"""
    r = np.array(cs['raw'][max(0, ka):max(ka + 1, kb)]); return float(r.max() - r.min()) if len(r) else 0.0

def track_entries(item, dy, ka, kb, first_pad=0):
    """[frame,x,y,w,h,text] keyframes (canvas px, ink box of ONE item moving with the crown) for text_occlusion.py --track"""
    x, y, w, h = item['ink']
    return [dict(frame=int(k), x=round(x, 1), y=round(y + dy[min(k, len(dy) - 1)], 1), w=round(w, 1), h=round(h, 1), text=item['text']) for k in range(max(0, ka), kb)]

def tool_track(canvas_dir, item, dy, ka, kb, beat, save=None, min_occ=None):
    """text_occlusion.py --track (Render's tool): occlusion max/mean over the frames for ONE moving item. -> dict(max, mean, behind_ratio, pass_max, pass_min, worst_frames) or None"""
    import subprocess, tempfile
    tool = occlusion_tool()
    if not tool or not tool_has_flag('--track'): return None
    ent = track_entries(item, dy, ka, kb)
    fn = save or tempfile.mktemp(suffix='.json', prefix='tbs_track_')
    json.dump(ent, open(fn, 'w'), ensure_ascii=False)
    cmd = [tool, canvas_dir, '--track', fn, '--text', item['text'], '--max-occlusion', str(1 - WORST_MIN_T), '--no-fail-exit']
    if tool_has_flag('--max-glyph') and GLYPH_MAX is not None: cmd += ['--max-glyph', str(GLYPH_MAX)]
    if min_occ: cmd += ['--min-occlusion', str(min_occ)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if save is None:
        try: os.remove(fn)
        except OSError: pass
    try: j = json.loads(r.stdout)
    except Exception: return None
    return dict(max=float(j['occlusion_max']), mean=float(j['occlusion_mean']), behind_ratio=j.get('behind_ratio'), pass_max=j.get('pass_max'), pass_min=j.get('pass_min'), worst=j.get('worst_frames'), glyph_max=j.get('glyph_occlusion_max'), pass_glyph=j.get('pass_glyph'), worst_glyph=j.get('worst_glyph'), raw=j)
WORST_MIN_T = 0.90
GLYPH_MAX = None      # v4.3.2: text_occlusion.py --max-glyph (per-character rule: no glyph more than 30 % covered on any frame); set from autoBeats.textBehind.tuneGlyphMinVisible by cfg()

def beat_track(b, stage):
    """-> (dy px list per mask index, ka, kb) for a beat that stores `track` (fractions of H); constant 0 track for a static beat"""
    meta = json.load(open(os.path.join(stage.d, 'masks', b['id'], 'mask.json'))); fps = stage.fps
    first = math.ceil(float(b.get('maskStart', meta['start'])) * fps - 1e-9); n = int(meta['count'])
    dy = [v * stage.H for v in b['track']] if b.get('track') else [0.0] * n
    return dy, max(0, round(b['t0'] * fps) - first), min(n, round(b['t1'] * fps) - first)

def export_tracks(d, b, stage):
    """public/project/tbs_track_<id>[_i].json = [{frame,x,y,w,h,text}] per item: the EXACT file `text_occlusion.py MASKDIR --track FILE --text ... --require-behind` takes. -> list of paths"""
    dy, ka, kb = beat_track(b, stage); paths = []
    for i, it in enumerate(b.get('items') or []):
        fn = os.path.join(d, f'tbs_track_{b["id"]}' + (f'_{i}' if len(b['items']) > 1 else '') + '.json')
        json.dump(track_entries(dict(it, ink=it['ink']), dy, ka, kb), open(fn, 'w'), ensure_ascii=False, indent=0); paths.append(fn)
    return paths

def suggest_candidate(stab_dir, text, TS, W, H, beat, min_occ, max_occ, min_scale=0.35):
    """Render's `text_occlusion.py --suggest WxH --text ... --require-behind` on a (crown-stabilised) mask dir -> candidate dict like search() produces, or None.
    The tool tries 1 line / balanced 2-line stack and returns `text` (may contain \n): that exact string is rendered."""
    import subprocess
    tool = occlusion_tool()
    if not tool or not tool_has_flag('--suggest'): return None
    px0 = 0.30 * W; t, ox, oy, (iw, ih) = TS.raster(text.upper(), px0, 'c', 1)
    cmd = [tool, stab_dir, '--suggest', f'{iw}x{ih}', '--text', text.upper(), '--font', TS.fontfile, '--range', f'{beat["t0"]},{beat["t1"]}', '--max-occlusion', str(max_occ),
           '--min-occlusion', str(min_occ), '--min-scale', str(min_scale), '--require-behind']
    if tool_has_flag('--max-glyph') and GLYPH_MAX is not None: cmd += ['--max-glyph', str(GLYPH_MAX)]      # v4.3.2: the tool rejects placements that swallow a letter
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0: return dict(_none=True, reason=f'text_occlusion.py --suggest exit {r.returncode} (no placement meets max-occlusion / min-occlusion / max-glyph)')
    try: j = json.loads(r.stdout)
    except Exception: return None
    j = j.get('suggest', j) or {}                      # the tool nests the placement under "suggest"
    if not j.get('behind_effect', False) or 'x' not in j: return dict(_none=True, reason=j.get('reason') or 'no placement tucks behind the crown within the glyph / occlusion limits')
    txt = (j.get('text') or text).upper(); px = px0 * float(j['scale'])
    _t, ox2, oy2, (iw2, ih2) = TS.raster(txt, px, 'c', 1)
    cx = j['x'] + j['w'] / 2.0; top = j['y'] - oy2
    it = dict(text=txt, align='c', size=round(px / W, 5), x=round(cx / W, 5), y=round(top / H, 5), y_px=top, ink=[round(cx - iw2 / 2.0, 1), round(float(j['y']), 1), iw2, ih2])
    return dict(items=[it], layout=('stack' if '\n' in txt else 'line'), shortened=False, mean=1 - float(j.get('occlusion_mean', 0)), worst=1 - float(j.get('occlusion_max', 0)), score=9.0, suggested=True)


# ------------------------------------------------------------------ phrase lint (verified.md V09 / V10) ------------------------------------------------
def phrase_words(text):
    return [w for w in re.sub(r'[^\w\s]', ' ', (text or '').upper().replace('\n', ' ')).split() if w]

def lint_phrase(text, P=None, CFG=None):
    """-> (ok, [problems]). A text-behind phrase must be complete in meaning: not a lone fragment ('TRIỂN'), not starting/ending on a function word."""
    CFG = CFG or cfg(); P = P or CFG['autoBeats'].get('textBehind', {})
    ph = CFG['autoBeats'].get('phrases', {})
    ws = phrase_words(text); problems = []
    if not ws: return False, ['empty phrase']
    singles = {x.upper() for x in P.get('completeSingleWords', [])}
    if len(ws) == 1 and ws[0] not in singles: problems.append(f'lone fragment "{ws[0]}" (a single word must be listed in autoBeats.textBehind.completeSingleWords; prefer a full phrase such as "TRIỂN KHAI", "CƠ HỘI")')
    edge = {x.upper() for x in (ph.get('stop', []) + ph.get('light', []) + P.get('badEdgeWords', []))}
    if len(ws) > 1 and ws[0] in edge: problems.append(f'starts on a function word "{ws[0]}"')
    if len(ws) > 1 and ws[-1] in {x.upper() for x in P.get('badEdgeWords', [])}: problems.append(f'ends on a function word "{ws[-1]}"')
    return not problems, problems

def lint_beat(b, P=None, CFG=None):
    """-> list of problems for one beat: phrase lint + 'no word dropped' (the words of all items == the words of the phrase) + wrap geometry"""
    probs = list(lint_phrase(b.get('text', ''), P, CFG)[1])
    if b.get('items'):
        got = [w for it in b['items'] for w in phrase_words(it['text'])]; want = phrase_words(b.get('text', ''))
        if got != want: probs.append(f'words dropped/changed: phrase {want} vs rendered {got}')
        if len(b['items']) == 2 and b.get('_layout') == 'wrap' and not (b['items'][1]['y'] > b['items'][0]['y']): probs.append('wrap: line 2 is not below line 1')
    return probs

# ------------------------------------------------------------------ candidate search ------------------------------------------------
def groupings(words, max_groups):
    n = len(words)
    for k in range(1, min(n, max_groups) + 1):
        for cuts in itertools.combinations(range(1, n), k - 1):
            b = (0,) + cuts + (n,)
            yield [' '.join(words[b[i]:b[i + 1]]) for i in range(k)]

def search(stack, head, beat, TS, W, H, P, log=None, min_occ=None, pstack=None):
    """returns (candidates best-first, tried); each = dict(items, mean, worst, layout, shortened, score) already passing the in-house >=90 % / >=80 % test. P = autoBeats.textBehind knobs"""
    ds = DS; mean = stack.mean(axis=0); umax = stack.max(axis=0); pstack = stack if pstack is None else pstack; pmean = pstack.mean(axis=0); words = beat['text'].replace('\n', ' ').split()
    top_min, bot_max = P.get('tuneMinTopR', 0.065), P.get('tuneMaxBottomR', 0.58)
    xmin_r, xmax_r = P.get('tuneSafeX', [0.02, 0.98])
    sizes_r = [r for r in P.get('tuneSizesR', [0.30, 0.26, 0.23, 0.20, 0.18, 0.16, 0.145, 0.13, 0.12, 0.11])]   # font px / canvas W
    min_occ = P.get('tuneMinOcclusion', 0.0) if min_occ is None else min_occ     # v4.3: the text must sit PARTLY behind the crown (mean occlusion >= min_occ), not 300 px above it
    mean_thr = 1 - P.get('tuneMinReadable', MEAN_MIN); worst_thr = 1 - P.get('tuneWorstFrameMin', WORST_MIN)
    hx0, hy0, hx1, hy1 = head                                   # canvas px, union of the speaker's face over the beat
    hcx, hcy = (hx0 + hx1) / 2, (hy0 + hy1) / 2
    maxw = P.get('tuneMaxWidthR', 0.97) * W
    cands = []                                                  # (score, items, mean, worst, layout)
    def place_block(text, px, align, strict=True, need_behind=True, yr=None, ref_cx=None, topk=None):
        """all valid top-left cells for one block, best first (cost: near the head, near centre, high up). yields (cost, ix, iy, off_x, off_y, occ_mean_map)"""
        t, ox, oy, (iw, ih) = TS.raster(text, px, align, ds)
        th, tw = t.shape
        if tw * ds > maxw + 2: return None
        cc = cv2.matchTemplate(mean, t, cv2.TM_CCORR) / max(float(t.sum()), 1e-9)       # mean occlusion at every top-left cell
        ys0 = int(top_min * H / ds); ys1 = int(bot_max * H / ds) - th
        if yr: ys0 = max(ys0, int(yr[0] / ds)); ys1 = min(ys1, int(yr[1] / ds))          # v4.4 wrap: line 2 only in the band just under line 1
        xs0 = int(xmin_r * W / ds); xs1 = int(xmax_r * W / ds) - tw
        if ys1 < ys0 or xs1 < xs0: return None
        sub = cc[ys0:ys1 + 1, xs0:xs1 + 1]
        cu = (cv2.matchTemplate(umax, t, cv2.TM_CCORR) / max(float(t.sum()), 1e-9))[ys0:ys1 + 1, xs0:xs1 + 1]   # occlusion if the person were everywhere she ever is (upper bound of the worst frame)
        subp = (cv2.matchTemplate(pmean, t, cv2.TM_CCORR) / max(float(t.sum()), 1e-9))[ys0:ys1 + 1, xs0:xs1 + 1]   # occlusion by the PERSON only (other elements in the window do not count as 'behind the head')
        lo_ = (subp >= min_occ) if need_behind else np.ones_like(subp, dtype=bool)      # line 2 of a wrap does NOT have to touch the head, only be readable
        ok = np.argwhere((sub <= mean_thr * 0.95) & lo_ & (cu <= worst_thr))         # guaranteed pass
        if len(ok) == 0: ok = np.argwhere((sub <= mean_thr * 0.95) & lo_ & (cu <= worst_thr * 3.5))   # may pass: verified exactly per frame
        if len(ok) == 0 and min_occ <= 0: ok = np.argwhere((sub <= mean_thr * 0.85) & (cu <= worst_thr * 3.5))
        if len(ok) == 0: return None
        yy, xx = ok[:, 0] + ys0, ok[:, 1] + xs0
        cxp = (xx + tw / 2) * ds; cyp = (yy + th / 2) * ds
        cost = P.get('wCentre', 0.5) * np.abs(cxp - W / 2) / W + P.get('wHead', 1.0) * np.hypot((cxp - hcx) / W, (cyp - hcy) / H) + P.get('wHigh', 0.2) * (yy * ds / H)
        if ref_cx is not None: cost = np.abs(cxp - ref_cx) / W + 0.3 * (yy * ds - (yr[0] if yr else 0)) / H          # wrap line 2: stay centred under line 1, as close as possible
        elif min_occ > 0 and need_behind: cost = cost + P.get('wOcc', 2.0) * np.abs(subp[ok[:, 0], ok[:, 1]] - P.get('tuneTargetOcclusion', 0.06))   # aim for the middle of the 3-10 % band
        order = np.argsort(cost)[:(topk or P.get('tuneTopK', 25))]
        return t, ox, oy, [(float(cost[i]), int(xx[i]), int(yy[i])) for i in order]
    def mk_item(text, px, align, ix, iy, ox, oy):
        ax = ix * ds - ox; top = iy * ds - oy
        _t, _ox, _oy, (iw, ih) = TS.raster(text, px, align, ds)
        return dict(text=text.upper(), align=align, size=round(px / W, 5), x=round(ax / W, 5), y=round(top / H, 5), y_px=top, ink=[round(ix * ds, 1), round(iy * ds, 1), iw, ih])
    def consider(items, layout):
        m, w, per = measure_items(stack, items, ds, TS, W)
        mp = measure_items(pstack, items[:1] if layout == 'wrap' else items, ds, TS, W)[0] if min_occ > 0 else 1.0      # wrap: the 3-10 % behind-the-crown rule is about line 1; line 2 only has to be readable
        gmin = P.get('tuneGlyphMinVisible', 0.70)
        if gmin > 0 and m >= 1 - mean_thr and w >= 1 - worst_thr:           # v4.3.2: no letter may be swallowed - every glyph >= 70 % visible on EVERY frame (pre-filter with a 2 % margin; make_masks re-checks at full resolution)
            for it_ in items:
                gl_ = TS.glyphs(it_['text'], it_['size'] * W, it_['align'], ds)
                ix_ = int(round(it_['ink'][0] / ds)); iy_ = int(round(it_['ink'][1] / ds))
                if glyph_min_visible(stack, gl_, ix_, iy_)[0] < gmin + 0.02: return None
        if m >= 1 - mean_thr and w >= 1 - worst_thr and (1 - mp) >= min_occ - 0.002:
            sz = min(i['size'] for i in items); lines = sum(i['text'].count('\n') + 1 for i in items)
            return m, w, sz
        return None
    tried = 0
    # v4.4: NEVER cut a phrase down to one fragment ('TRIỂN' out of 'TRIỂN KHAI'): the `short` phase is OFF unless the longest word is itself a complete word (completeSingleWords)
    shorts = [w_ for w_ in (sorted(words, key=lambda x: -len(x))[:1] if len(words) > 1 else []) if P.get('allowShortPhase', False) and w_.upper() in {x.upper() for x in P.get('completeSingleWords', [])}]
    for phase, texts in (('full', [beat['text'].replace('\n', ' ')]), ('short', shorts)):
        results = []
        for sr in sizes_r:
            px = sr * W
            if phase == 'full':
                # 1) one line (any x/y) 2) stacked lines 3) split left|right of the head
                for g in groupings(words, 3):
                    if len(g) == 1:
                        for al in ('c',):
                            r = place_block(g[0], px, al)
                            if not r: continue
                            t, ox, oy, pos = r
                            for cost, ix, iy in pos:
                                it = [mk_item(g[0], px, al, ix, iy, ox, oy)]; tried += 1; ev = consider(it, 'line')
                                if ev: results.append((sr * 1.0 - cost * 0.25, 'line', it, ev)); break
                    else:
                        stacked = '\n'.join(g)
                        for al in ('c', 'l', 'r'):
                            r = place_block(stacked, px, al)
                            if not r: continue
                            t, ox, oy, pos = r
                            for cost, ix, iy in pos:
                                it = [mk_item(stacked, px, al, ix, iy, ox, oy)]; tried += 1; ev = consider(it, 'stack')
                                if ev: results.append((sr * 1.0 - 0.04 * (len(g) - 1) - cost * 0.25, 'stack', it, ev)); break
                        if len(g) == 2 and P.get('wrapEnabled', True):
                            # v4.4 WRAP: line 1 tucked behind the crown, line 2 on its own row just below, in the nearest free background (beside the head / shoulders) - never drop words
                            r1 = place_block(g[0], px, 'c', topk=10)
                            if r1:
                                t1_, ox1, oy1, pos1 = r1; done_w = False
                                for cost1, ix1, iy1 in pos1[:8]:
                                    y_lo = (iy1 + t1_.shape[0]) * ds + P.get('wrapGapR', 0.010) * H; y_hi = y_lo + P.get('wrapMaxDropR', 0.09) * H
                                    r2 = place_block(g[1], px, 'c', need_behind=False, yr=(y_lo, y_hi), ref_cx=(ix1 + t1_.shape[1] / 2) * ds, topk=8)
                                    if not r2: continue
                                    t2_, ox2, oy2, pos2 = r2
                                    for cost2, ix2, iy2 in pos2:
                                        it = [mk_item(g[0], px, 'c', ix1, iy1, ox1, oy1), mk_item(g[1], px, 'c', ix2, iy2, ox2, oy2)]
                                        tried += 1; ev = consider(it, 'wrap')
                                        if ev: results.append((sr * 1.0 - P.get('wrapPenalty', 0.02) - (cost1 + cost2) * 0.125, 'wrap', it, ev)); done_w = True; break
                                    if done_w: break
                        if len(g) == 2:                                          # split: g[0] left of the head | g[1] right of the head, same row
                            rl = place_block(g[0], px, 'r'); rr = place_block(g[1], px, 'l')
                            if not rl or not rr: continue
                            tl, oxl, oyl, posl = rl; tr, oxr, oyr, posr = rr
                            done = False
                            for costl, ixl, iyl in posl:
                                for costr, ixr, iyr in posr:
                                    if abs(iyl - iyr) * ds > 0.02 * H: continue
                                    it = [mk_item(g[0], px, 'r', ixl, iyl, oxl, oyl), mk_item(g[1], px, 'l', ixr, iyr, oxr, oyr)]
                                    if it[0]['x'] * W > it[1]['x'] * W - 0.02 * W: continue
                                    iy_px = int(round((it[0]['y_px'] + it[1]['y_px']) / 2)); dy = [iy_px - x['y_px'] for x in it]; it[0]['ink'][1] += dy[0]; it[1]['ink'][1] += dy[1]; it[0]['y_px'] = it[1]['y_px'] = iy_px; it[0]['y'] = it[1]['y'] = round(iy_px / H, 5)
                                    tried += 1; ev = consider(it, 'split')
                                    if ev: results.append((sr * 1.0 - 0.02 - (costl + costr) * 0.125, 'split', it, ev)); done = True; break
                                if done: break
            else:
                r = place_block(texts[0], px, 'c')
                if not r: continue
                t, ox, oy, pos = r
                for cost, ix, iy in pos:
                    it = [mk_item(texts[0], px, 'c', ix, iy, ox, oy)]; tried += 1; ev = consider(it, 'short')
                    if ev: results.append((sr * 1.0 - 0.1 - cost * 0.25, 'short', it, ev)); break
        if results:
            comfort = P.get('tuneComfortSizeR', 0.13)          # v4.4: a one-liner squeezed below the comfort size loses to a wrap/stack with bigger type (a phone viewer must read it)
            results = [(r[0] - P.get('comfortPenalty', 2.0) * max(0.0, comfort - min(i['size'] for i in r[2])), *r[1:]) for r in results]
            results.sort(key=lambda r: -r[0])
            return [dict(items=r[2], mean=r[3][0], worst=r[3][1], layout=r[1], shortened=(phase == 'short'), score=r[0]) for r in results[:P.get('tuneVerify', 14)]], tried
    return [], tried

def head_box(faces, segs, CFG, ci, t0, t1):
    import logo_place
    fr = logo_place.face_rect(faces, segs, CFG, ci, t0, t1)
    return fr

def recheck(beat, d, CFG, ci, fps, segs):
    """independent re-measure of a stored placement at 1/2 resolution (render gate). returns (mean_readable, worst_readable)"""
    st = Stage(d, CFG, ci, fps, segs); stk, zs, _ = st.stack(beat, ds=2, step=1)
    TS = Typeset(CFG); W = ci['W']
    items = []
    for it in beat['items']:
        it = dict(it); it['y_px'] = it['y'] * ci['H']; items.append(it)
    m, w, per = measure_items(stk, items, 2, TS, W)
    return m, w, stk.shape[0]

if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == '--lint-phrase':
        ok_, pr_ = lint_phrase(sys.argv[2]); print(json.dumps(dict(text=sys.argv[2], ok=ok_, problems=pr_), ensure_ascii=False)); sys.exit(0 if ok_ else 1)
    if len(sys.argv) >= 3 and sys.argv[1] == '--check':
        import logo_place
        d = sys.argv[2]; CFG = cfg(); P = CFG['autoBeats']['textBehind']
        if '--min-occlusion' in sys.argv: P = dict(P, tuneMinOcclusion=float(sys.argv[sys.argv.index('--min-occlusion') + 1]))     # override of autoBeats.textBehind.tuneMinOcclusion
        J = lambda n: json.load(open(os.path.join(d, n), encoding='utf-8')) if os.path.exists(os.path.join(d, n)) else {}
        beats = [b for b in J('beats.json').get('beats', []) if b.get('type') == 'text-behind-speaker']
        probe = J('probe.json'); edl = J('edl.json'); ci = logo_place.canvas_info(CFG, probe); fps = edl.get('source', {}).get('fps') or probe.get('fps', 30)
        mean_min, worst_min = P.get('tuneMinReadable', MEAN_MIN), P.get('tuneWorstFrameMin', WORST_MIN)
        bad = []; st = Stage(d, CFG, ci, fps, edl.get('segments')) if beats else None
        for b in beats:
            if not b.get('items'): print(f'FAIL {b["id"]}: no verified placement (items) - run make_masks.py'); bad.append(b['id']); continue
            canvas = None
            if occlusion_tool():                              # canonical: Render's text_occlusion.py on composition-space masks (<= 10 % occluded)
                try: canvas = write_canvas_masks(st, b, os.path.join(d, '..', '..', 'out', 'tbs_canvas', b['id']))
                except Exception as e: print(f'  (canvas masks failed: {e}; using the in-house recheck)')
            ok_ = None; occp = None
            if canvas:
                try: occp = None if b.get('track') else person_occlusion(write_canvas_masks(st, dict(b, _blockers=[]), os.path.join(d, '..', '..', 'out', 'tbs_canvas', b['id'] + '_person')), b['items'], b)
                except Exception as e: print(f'  (person-only masks failed: {e})')
                if b.get('track') and tool_has_flag('--track'):         # v4.3 crown-tracked text: the same thresholds, measured on the MOVING boxes by text_occlusion.py --track
                    dy_, ka_, kb_ = beat_track(b, st); mx_, mn_ = 0.0, 0.0
                    for it_ in b['items']:
                        r_ = tool_track(canvas, it_, dy_, ka_, kb_, b)
                        if r_ is None: mx_ = mn_ = 1.0; break
                        mx_, mn_ = max(mx_, r_['max']), max(mn_, r_['mean'])
                    ok_, m, w = mx_ <= 1 - worst_min + 1e-6, 1 - mn_, 1 - mx_
                    pc_ = write_canvas_masks(st, dict(b, _blockers=[]), os.path.join(d, '..', '..', 'out', 'tbs_canvas', b['id'] + '_person'))
                    pm_ = [tool_track(pc_, it_, dy_, ka_, kb_, b) for it_ in b['items']]
                    occp = max(r_['mean'] for r_ in pm_) if all(pm_) else None
                else: ok_, m, w = verify_external(canvas, b['items'], b, 1 - worst_min)
                src = 'text_occlusion.py'
                if ok_ is not None: ok_ = ok_ and m >= mean_min - 0.005 and w >= worst_min - 0.005
            if ok_ is None:
                m, w, n = recheck(b, d, CFG, ci, fps, edl.get('segments')); ok_ = m >= mean_min - 0.005 and w >= worst_min - 0.005; src = 'tbs_place fallback (text_occlusion.py not found)'
            gmin_ = P.get('tuneGlyphMinVisible', 0.70); gl_min, gl_worst = 1.0, None; tool_gl = []                         # v4.3.2 per-glyph gate (every letter >= 70 % visible on every frame)
            if canvas and gmin_ > 0:
                try:
                    TSg = Typeset(CFG); dyg, kag, kbg = beat_track(b, st)
                    for it_ in b['items']:
                        gv_ = glyph_visibility(canvas, it_, dyg, kag, kbg, TSg, ci['W'], gmin_)
                        if gv_['min_vis'] < gl_min: gl_min, gl_worst = gv_['min_vis'], gv_['worst']
                        rt_ = tool_track(canvas, it_, dyg, kag, kbg, b) if tool_has_flag('--max-glyph') else None      # canonical: text_occlusion.py --track --max-glyph (exit 5 rule)
                        if rt_ and rt_.get('glyph_max') is not None:
                            tool_gl.append(rt_.get('pass_glyph') is not False)
                            if 1 - rt_['glyph_max'] < gl_min: gl_min, gl_worst = 1 - rt_['glyph_max'], dict(ch=str((rt_.get('worst_glyph') or {}).get('char', '?')), frame=(rt_.get('worst_glyph') or {}).get('frame'))
                            if rt_.get('pass_glyph') is False: gl_min = min(gl_min, 1 - rt_['glyph_max'] - 1e-6)
                    if (not all(tool_gl)) if tool_gl else (gl_min < gmin_ - 1e-6): ok_ = False      # Render's --max-glyph verdict is canonical; the in-house number is the fallback when the tool lacks the flag
                except Exception as e: print(f'  (glyph gate failed to run: {e})')
            need_occ = b.get('_minOcc', P.get('tuneMinOcclusion', 0.0)) if '--min-occlusion' not in sys.argv else P['tuneMinOcclusion']
            occ_pers = occp if occp is not None else 1 - m
            occ_ok = occ_pers >= need_occ - 0.005                  # v4.3: mean occlusion >= min (3 %): the text really sits behind the head (waived per beat with _minOcc: 0 when no spot allows it)
            if need_occ and not occ_ok: ok_ = False
            print(f'{"OK  " if ok_ else "FAIL"} {b["id"]} "{b["text"]}" readable mean {m*100:.1f}% worst-frame {w*100:.1f}% = occluded mean {(1-m)*100:.1f}% max {(1-w)*100:.1f}% (speaker alone: mean {occ_pers*100:.1f}%) [{src}] (need readable >= {mean_min*100:.0f}% / {worst_min*100:.0f}% and occluded mean >= {need_occ*100:.0f}%{"" if occ_ok or not need_occ else " - NOT behind the head"}) | glyph min visible {gl_min*100:.1f}%{"" if gl_min >= gmin_ - 1e-6 else " < " + format(gmin_*100, ".0f") + "% - LETTER HIDDEN: '" + str((gl_worst or {}).get("ch")) + "' frame " + str((gl_worst or {}).get("frame"))}')
            if not ok_: bad.append(b['id'])
        os.makedirs(os.path.join(d, '..', '..', 'out'), exist_ok=True)
        json.dump(dict(failed=bad, checked=len(beats)), open(os.path.join(d, '..', '..', 'out', 'tbs_gate.json'), 'w'))
        print(f'text-behind readability gate: {"FAILED " + ",".join(bad) if bad else "passed"} ({len(beats)} beat(s))')
        sys.exit(1 if bad else 0)
