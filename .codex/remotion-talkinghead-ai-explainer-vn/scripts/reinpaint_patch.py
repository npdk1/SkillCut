#!/usr/bin/env python3
"""v4.4 patch handling for a raw whose burned-in subtitles were removed (verified.md V21).

  detect : python3 scripts/reinpaint_patch.py detect  <clean.mp4> [--orig original.mp4] [--out patch.json]
           finds rectangles that are visibly "blurred / smeared" in the raw. With --orig it is exact (|clean - orig| over time). Without it, a
           low-gradient test is used: rectangle-ish regions whose gradient energy is far below the median of the same rows, stable across frames.
  fill   : python3 scripts/reinpaint_patch.py fill <orig.mp4> <out.mp4> --audio <clean.mp4> [--mask-from-color teal] [--frames A:B]
           re-inpaints every frame of the ORIGINAL (with the burned-in pill) with an edge-directed fill (below) instead of a blur. Writes <out>.json manifest.
  still  : python3 scripts/reinpaint_patch.py still <video.mp4> <t_sec> <out.jpg> [--box x0,y0,x1,y1]   (before/after crops)

Fill model (per column of the hole): choose the edge direction s (px shift per px of height) that best matches the pixels just ABOVE and just BELOW the hole,
interpolate along that line (so vertical + diagonal edges - arm, shirt panel, collar - continue through the hole instead of being smeared), then add camera-like
grain with the std measured around the hole, and feather the border by 3 px so no line is visible. Everything is in the manifest (box, rows, method).
"""
import sys, json, argparse, subprocess, os
import numpy as np, cv2

def pill_mask(f, y0=1100, y1=1450, dil=17):
    """burned-in 'pill' = solid saturated teal box with white text; closed + filled + dilated"""
    roi = f[y0:y1]; hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    t = ((hsv[..., 0] > 70) & (hsv[..., 0] < 95) & (hsv[..., 1] > 150) & (hsv[..., 2] > 100)).astype(np.uint8)
    t = cv2.morphologyEx(t, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
    cn, _ = cv2.findContours(t, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    m = np.zeros_like(t); cv2.drawContours(m, cn, -1, 1, -1)
    m = cv2.dilate(m, np.ones((dil, dil), np.uint8))
    full = np.zeros(f.shape[:2], np.uint8); full[y0:y1] = m
    return full

class Filler:
    """static-mask filler (the burned-in pill never moves). low = per-column linear interpolation between the rows just above / below the hole
    (vertical edges continue straight through it), detail = high-pass of the row-REFLECTED surroundings, grain, then a Poisson blend into the frame."""
    def __init__(self, hole, sigma_lo=3.0, ds=4, feather=3):
        self.hole = hole.astype(np.uint8); H, W = hole.shape; self.sigma = sigma_lo; self.ds = ds
        ys, xs = np.where(hole > 0); self.Y0, self.Y1, self.X0, self.X1 = int(ys.min()) - 40, int(ys.max()) + 41, int(xs.min()) - 40, int(xs.max()) + 41
        self.Y0 = max(self.Y0, 0); self.X0 = max(self.X0, 0); self.Y1 = min(self.Y1, H); self.X1 = min(self.X1, W)
        src_r = np.tile(np.arange(H)[:, None], (1, W)); src_r = src_r.copy()
        for c in range(W):
            r = np.where(hole[:, c] > 0)[0]
            if not len(r): continue
            a, b = r[0], r[-1]; mid = (a + b) / 2
            for y in range(a, b + 1):
                src_r[y, c] = a - 1 - (y - a) if y < mid else b + 1 + (b - y)
        self.top = np.full(W, -1); self.bot = np.full(W, -1)
        for c in range(W):
            r = np.where(hole[:, c] > 0)[0]
            if len(r): self.top[c], self.bot[c] = r[0], r[-1]
        yy = np.arange(H)[:, None]; L = (self.bot - self.top + 1)[None, :].astype(np.float32)
        self.t = np.clip((yy - self.top[None, :] + 0.5) / np.maximum(L, 1), 0, 1).astype(np.float32)
        self.src_r = np.clip(src_r, 0, H - 1); self.cols = np.tile(np.arange(W)[None, :], (H, 1))
        hm = self.hole[self.Y0:self.Y1, self.X0:self.X1].astype(np.float32)
        self.alpha = np.clip(cv2.GaussianBlur(hm, (0, 0), feather) * 1.6 - 0.3, 0, 1)[..., None]
    def fill(self, f, rng, sig=None):
        Y0, Y1, X0, X1 = self.Y0, self.Y1, self.X0, self.X1; hole = self.hole
        roi = f[Y0:Y1, X0:X1]; hm = hole[Y0:Y1, X0:X1]
        # low-frequency = per-column linear interpolation between the (lightly smoothed) rows just above and below the hole: vertical edges continue,
        # and there is no mid-line seam (Telea meets in the middle and leaves one)
        W = f.shape[1]; g = 2; bnd = 5
        cols = np.arange(W); cc = cols[self.top >= 0]
        T = np.zeros((W, 3), np.float32); B = np.zeros((W, 3), np.float32)
        for k in range(1, bnd + 1):
            T[cc] += f[self.top[cc] - g - k, cc]; B[cc] += f[np.minimum(self.bot[cc] + g + k, f.shape[0] - 1), cc]
        T /= bnd; B /= bnd
        T = cv2.GaussianBlur(T[None], (7, 1), 0)[0]; B = cv2.GaussianBlur(B[None], (7, 1), 0)[0]
        lowF = T[None, :, :] * (1 - self.t[..., None]) + B[None, :, :] * self.t[..., None]
        low = lowF[Y0:Y1, X0:X1]
        # detail = high-pass of the frame (hole already replaced by `low`, so the burned-in colour never leaks), REFLECTED across the hole border: no DC step at the
        # reflection seam because the high-pass is taken BEFORE reflecting
        base = roi.astype(np.float32).copy(); base[hm > 0] = low[hm > 0]
        hpF = base - cv2.GaussianBlur(base, (0, 0), self.sigma)
        full_hp = np.zeros(f.shape, np.float32); full_hp[Y0:Y1, X0:X1] = hpF
        det = full_hp[self.src_r[Y0:Y1, X0:X1], self.cols[Y0:Y1, X0:X1]]
        res = low + det * 0.45
        if sig is None: sig = self.sig_ring(f)
        n = cv2.GaussianBlur(rng.standard_normal(res.shape[:2]).astype(np.float32), (0, 0), 0.6); n *= (sig * 0.45) / max(float(n.std()), 1e-3)
        res = res + n[..., None]
        res8 = np.clip(res, 0, 255).astype(np.uint8)
        # Poisson (gradient-domain) blend: the border of the filled area takes the colour of the real pixels around it, so there is no tone seam / line
        m = (hm > 0).astype(np.uint8) * 255; m = cv2.erode(m, np.ones((3, 3), np.uint8))
        out = f.copy(); dst = roi.copy()
        blended = cv2.seamlessClone(res8, dst, m, (res8.shape[1] // 2, res8.shape[0] // 2), cv2.NORMAL_CLONE)
        out[Y0:Y1, X0:X1] = blended
        return out
    def sig_ring(self, f):
        return 2.0

def fill_frame(f, hole, rng, flr=[None]):
    if flr[0] is None or flr[0].hole.shape != hole.shape: flr[0] = Filler(hole)
    return flr[0].fill(f, rng)

def cmd_fill(a):
    """Re-fill the static subtitle-remnant pill of the ORIGINAL video, frame-synchronous with the existing cleaned file (--audio = that file:
    its audio is copied and its frame count is the length cap, so words.json / edl.json / beats stay valid)."""
    W, H = 1080, 1920
    cap = cv2.VideoCapture(a.orig); ok, f0 = cap.read()
    mask = pill_mask(f0)
    ys, xs = np.where(mask > 0); box = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
    ref_n = int(subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_packets', '-show_entries', 'stream=nb_read_packets', '-of', 'csv=p=0', a.audio]).split()[0])
    rd = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', a.orig, '-vf', 'fps=30', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-'], stdout=subprocess.PIPE, bufsize=W * H * 3 * 4)
    tmp = a.out + '.v.mp4'
    wr = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', '30', '-i', '-', '-c:v', 'libx264', '-crf', '15', '-preset', 'fast', '-pix_fmt', 'yuv420p', tmp], stdin=subprocess.PIPE)
    rng = np.random.default_rng(7); n = 0
    while n < ref_n:
        b = rd.stdout.read(W * H * 3)
        if len(b) < W * H * 3: break
        f = np.frombuffer(b, np.uint8).reshape(H, W, 3).copy()
        wr.stdin.write(fill_frame(f, mask, rng).tobytes()); n += 1
        if n % 500 == 0: print(n, flush=True)
    rd.kill(); wr.stdin.close(); wr.wait()
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp, '-i', a.audio, '-map', '0:v', '-map', '1:a?', '-c', 'copy', a.out], check=True)   # no -shortest: keep every video frame
    os.remove(tmp)
    json.dump(dict(tool='scripts/reinpaint_patch.py fill',
                   method='per-frame fill of the static subtitle-remnant pill: per-column linear interpolation of the 5-row bands just outside the hole (low frequency) '
                          '+ reflected high-pass detail (sigma 3, x0.45) + matched grain + Poisson seamlessClone (NORMAL_CLONE)',
                   source=a.orig, audio_from=a.audio, frames=n, reference_frames=ref_n, patch_box_xyxy=box,
                   mask='teal pill (HSV h70-95 s>150 v>100) closed+filled+dilated 17 px, static over the whole video', out=os.path.abspath(a.out)), open(a.out + '.json', 'w'), indent=1)
    print('done', n, box)

def _rows_of(flat, box):
    """Split a patch box into stacked rows by the horizontal extent of its flat mask (a step in width = another subtitle row)."""
    x0, y0, x1, y1 = box; sub = flat[y0:y1, x0:x1] > 0; ext = []
    for r in range(sub.shape[0]):
        xs = np.where(sub[r])[0]; ext.append((xs.min(), xs.max()) if len(xs) > 20 else None)
    rows, cur = [], None
    for r, e in enumerate(ext):
        if e is None: continue
        if cur and abs(e[0] - cur['a']) < 12 and abs(e[1] - cur['b']) < 12: cur['y1'] = y0 + r + 1
        else:
            if cur and cur['y1'] - cur['y0'] >= 12: rows.append(cur)
            cur = dict(y0=y0 + r, y1=y0 + r + 1, a=int(e[0]), b=int(e[1]))
    if cur and cur['y1'] - cur['y0'] >= 12: rows.append(cur)
    return [dict(x0=x0 + r['a'], x1=x0 + r['b'] + 1, y0=r['y0'], y1=r['y1']) for r in rows]

def cmd_detect(a):
    """Find leftover subtitle-removal patches. Mode A (--orig given): temporal mean |clean - original| > 30 -> exact patch pixels.
    Mode B (no original): a blur/fill patch is an AXIS-ALIGNED RECTANGLE that is static over time and whose noise/texture level is flat and
    different from its surroundings: the temporal mean of the high-pass energy shows it as a rectangle with four long straight edges, which
    moving people / furniture never produce. Rows (stacked patches) are split by their width steps."""
    cap = cv2.VideoCapture(a.clean); n = int(cap.get(7)); acc = None; k = 0
    o = cv2.VideoCapture(a.orig) if a.orig else None
    for i in np.linspace(20, n - 20, a.samples).astype(int):
        cap.set(1, int(i)); ok, f = cap.read()
        if not ok: continue
        if o is not None:
            o.set(1, int(i)); ok2, g0 = o.read()
            if not ok2: continue
            d = cv2.GaussianBlur(np.abs(f.astype(np.float32) - g0.astype(np.float32)).mean(2), (0, 0), 2)
        else:
            g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32)
            d = cv2.GaussianBlur(np.abs(g - cv2.GaussianBlur(g, (0, 0), 1.2)), (0, 0), 4)
        acc = d if acc is None else acc + d; k += 1
    acc /= k; rects = []
    if o is not None:
        flat = (acc > 30).astype(np.uint8)
    else:
        flat = np.zeros(acc.shape, np.uint8); H_, W_ = acc.shape; BW, ST = 120, 40; found = []
        rel = lambda v, lv: abs(v - lv) / max(lv, 0.25)
        for xa in range(0, W_ - BW + 1, ST):                  # column bands: a flat plateau with a sharp step at its top and bottom
            P = cv2.GaussianBlur(np.median(acc[:, xa:xa + BW], axis=1).reshape(-1, 1), (1, 0), 2).ravel(); yu = 14
            while yu < H_ - 40:
                if rel(P[yu + 8], P[yu - 10]) > 0.25:
                    lv = float(np.median(P[yu + 8:yu + 18])); ye = yu + 8
                    while ye < H_ - 14 and rel(P[ye], lv) < 0.2: ye += 1
                    if 25 <= ye - yu <= 130 and rel(P[ye + 8], lv) > 0.2: found.append((xa, yu, ye)); yu = ye
                yu += 1
        used = set()
        for k_, (xa, yu, ye) in enumerate(found):              # same y-range in >= 5 consecutive bands (>= 280 px wide) = static rectangle, not a person/furniture edge
            if k_ in used: continue
            grp = [k_]
            for k2, (xb, yu2, ye2) in enumerate(found):
                if k2 != k_ and k2 not in used and abs(yu2 - yu) < 14 and abs(ye2 - ye) < 14: grp.append(k2)
            xs_ = sorted(found[g][0] for g in grp)
            if len(grp) >= 4 and xs_[-1] + BW - xs_[0] >= 400 and all(b - a_ <= 3 * ST for a_, b in zip(xs_, xs_[1:])):   # >= 4 bands, >= 400 px wide, gaps <= 2 bands
                used.update(grp); flat[yu:ye, xs_[0]:xs_[-1] + BW] = 1
    m = cv2.morphologyEx(flat, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    cn, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in cn:
        x, y, w, h = cv2.boundingRect(c)
        if w * h >= 3000 and w >= 40 and h >= 25:
            rects.append(dict(x0=x, y0=y, x1=x + w, y1=y + h, fill_ratio=round(float(cv2.contourArea(c)) / (w * h), 2), rows=_rows_of(m, (x, y, x + w, y + h))))
    rects.sort(key=lambda r: -(r['x1'] - r['x0']) * (r['y1'] - r['y0']))
    res = dict(video=a.clean, samples=k, mode='diff-vs-original' if o is not None else 'EXPERIMENTAL static-rectangle candidates (noise-energy plateaus) - confirm by eye; use --orig when the removal step kept the source', patches=rects)
    json.dump(res, open(a.out, 'w'), indent=1); print(json.dumps(res)[:900])

def cmd_still(a):
    cap = cv2.VideoCapture(a.video); cap.set(cv2.CAP_PROP_POS_MSEC, a.t * 1000); ok, f = cap.read()
    x0, y0, x1, y1 = [int(v) for v in a.box.split(',')]
    cv2.imwrite(a.out, f[y0:y1, x0:x1], [cv2.IMWRITE_JPEG_QUALITY, 92])

if __name__ == '__main__':
    p = argparse.ArgumentParser(); sp = p.add_subparsers(dest='cmd', required=True)
    d = sp.add_parser('detect'); d.add_argument('clean'); d.add_argument('--orig'); d.add_argument('--out', default='patch.json'); d.add_argument('--samples', type=int, default=40)
    fl = sp.add_parser('fill'); fl.add_argument('orig'); fl.add_argument('out'); fl.add_argument('--audio', required=True); 
    st = sp.add_parser('still'); st.add_argument('video'); st.add_argument('t', type=float); st.add_argument('out'); st.add_argument('--box', default='0,1100,1080,1400')
    a = p.parse_args(); {'detect': cmd_detect, 'fill': cmd_fill, 'still': cmd_still}[a.cmd](a)
