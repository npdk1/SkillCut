#!/usr/bin/env python3
"""clean_burned_captions.py - remove the SOURCE video's burned-in caption boxes (e.g. the green TikTok subtitle box) frame by frame.

Why (v4.4, user feedback "white blurred box behind the subtitle"): the v4.3 demo source (raw_clean_*.mp4) was cleaned with ONE fixed
mask (union of the caption box of frame 30) and a column-interpolated fill, so every frame had a smeared, pale rectangle exactly where the
captions are drawn. Rule: clean ONLY the pixels the caption box really covers in THAT frame (per-frame colour mask), nothing in frames
without a box, then let the template draw its own captions (no background box, see references/captions.md).

usage: clean_burned_captions.py in.mp4 out.mp4 [--hue 70,95] [--sat-min 150] [--val-min 100] [--roi 0.45,0.80] [--min-area 4000] [--radius 5]
  --report out.json   frames cleaned / skipped
Audio is copied unchanged (timing identical -> words.json / transcript stay valid).
"""
import argparse, json, subprocess, sys, time
import cv2, numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('src'); ap.add_argument('dst')
ap.add_argument('--hue', default='70,95'); ap.add_argument('--sat-min', type=int, default=150); ap.add_argument('--val-min', type=int, default=100)
ap.add_argument('--roi', default='0.45,0.80', help='vertical band (fractions of H) where the burned caption lives')
ap.add_argument('--min-area', type=int, default=4000); ap.add_argument('--radius', type=int, default=5)
ap.add_argument('--report', default=None)
a = ap.parse_args()
h0, h1 = [int(x) for x in a.hue.split(',')]; r0, r1 = [float(x) for x in a.roi.split(',')]
pr = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,r_frame_rate', '-of', 'json', a.src]))['streams'][0]
W, H = int(pr['width']), int(pr['height']); n_, d_ = pr['r_frame_rate'].split('/'); fps = float(n_) / float(d_)
Y0, Y1 = int(H * r0), int(H * r1)
rd = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', a.src, '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-'], stdout=subprocess.PIPE, bufsize=W * H * 3 * 4)
tmp = a.dst + '.v.mp4'
wr = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', str(fps), '-i', '-', '-c:v', 'libx264', '-crf', '15', '-preset', 'fast', '-pix_fmt', 'yuv420p', tmp], stdin=subprocess.PIPE)
K = np.ones((25, 25), np.uint8); D = np.ones((9, 9), np.uint8)
n = cleaned = 0; t = time.time()
while True:
    b = rd.stdout.read(W * H * 3)
    if len(b) < W * H * 3: break
    f = np.frombuffer(b, np.uint8).reshape(H, W, 3).copy(); n += 1
    roi = f[Y0:Y1]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    g = ((hsv[..., 0] >= h0) & (hsv[..., 0] <= h1) & (hsv[..., 1] > a.sat_min) & (hsv[..., 2] > a.val_min)).astype(np.uint8)
    if g.sum() >= a.min_area:
        m = cv2.morphologyEx(g, cv2.MORPH_CLOSE, K)
        cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        m2 = np.zeros_like(m)
        for c in cnts:
            if cv2.contourArea(c) >= a.min_area: cv2.drawContours(m2, [c], -1, 1, -1)
        if m2.any():
            m2 = cv2.dilate(m2, D) * 255
            ys, xs = np.where(m2 > 0); y0, y1, x0, x1 = max(ys.min() - 12, 0), min(ys.max() + 13, roi.shape[0]), max(xs.min() - 12, 0), min(xs.max() + 13, W)
            crop = roi[y0:y1, x0:x1]
            filled = cv2.inpaint(crop, m2[y0:y1, x0:x1], a.radius, cv2.INPAINT_TELEA)
            soft = cv2.GaussianBlur((m2[y0:y1, x0:x1] / 255.0).astype(np.float32), (0, 0), 2.0)[..., None]
            roi[y0:y1, x0:x1] = np.clip(filled * soft + crop * (1 - soft), 0, 255).astype(np.uint8)
            cleaned += 1
    wr.stdin.write(f.tobytes())
    if n % 500 == 0: print(n, round(time.time() - t), flush=True)
wr.stdin.close(); wr.wait()
subprocess.check_call(['ffmpeg', '-v', 'error', '-y', '-i', tmp, '-i', a.src, '-map', '0:v', '-map', '1:a?', '-c', 'copy', '-movflags', '+faststart', a.dst])
import os; os.remove(tmp)
rep = {'frames': n, 'cleaned_frames': cleaned, 'seconds': round(time.time() - t, 1)}
print(json.dumps(rep))
if a.report: json.dump(rep, open(a.report, 'w'))
