#!/usr/bin/env python3
"""V04 caption-vs-face check on the RENDERED video, every frame of every caption span (v4.4).
  python3 scripts/check_caption_face.py VIDEO.mp4 [--boxes out/boxes.json] [--report out/caption_face.json] [--max 0.10] [--pad-top 0.12]

Why: the planning gate (faces.json sampled every 0.25 s + geometry model) reported 0 for a caption that brushed the forehead for 11 % of the
face at 12.33 s (v4.3 check). Here the face is detected (YuNet, same model as detect_faces.py) on the real output frame, the caption box is the real
DOM box of that frame (check_overlaps.mjs -> out/boxes.json, captions measured on EVERY frame), the face box is extended upward by --pad-top of its
height (YuNet boxes start at the brows: forehead/hair are part of the face for this rule). Frames where no face is found borrow the nearest detected
face within 0.3 s. Fails (exit 1) when any frame covers more than --max of the face area. JSON: {frames_checked, worst:{frame,t,pct}, violations:[{from,to,max_pct}]}"""
import argparse, json, os, sys
import cv2, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
MODEL = os.path.join(ROOT, 'assets', 'models', 'face_detection_yunet_2023mar.onnx')
ap = argparse.ArgumentParser(); ap.add_argument('video'); ap.add_argument('--boxes', default='out/boxes.json'); ap.add_argument('--report', default='out/caption_face.json')
ap.add_argument('--max', type=float, default=None); ap.add_argument('--pad-top', type=float, default=None); ap.add_argument('--cfg', default=os.path.join(ROOT, 'style.config.json'))
a = ap.parse_args()
V = json.load(open(a.cfg, encoding='utf-8')).get('verify', {}).get('captionFace', {})
MAXF = a.max if a.max is not None else V.get('maxFaceOverlap', 0.10); PAD = a.pad_top if a.pad_top is not None else V.get('foreheadPadR', 0.12)
B = json.load(open(a.boxes)); fps = B.get('fps', 30)
caps = {}
for b in B['boxes']:
    if b['n'] == 'caption': caps.setdefault(b['f'], []).append(b['r'])
cap = cv2.VideoCapture(a.video); W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)); vfps = cap.get(cv2.CAP_PROP_FPS) or fps
det = cv2.FaceDetectorYN.create(MODEL, '', (320, 320), 0.6, 0.3, 5000)
SW = 640; sc = SW / W; SH = int(round(H * sc)); det.setInputSize((SW, SH))
faces = {}; res = []; f = 0; last_f = max(caps) if caps else -1
while f <= last_f:
    ok, img = cap.read()
    if not ok: break
    if f in caps:
        _, d = det.detect(cv2.resize(img, (SW, SH)))
        if d is not None and len(d):
            k = max(range(len(d)), key=lambda i: d[i][2] * d[i][3]); x, y, w, h = [float(v) / sc for v in d[k][:4]]
            if w > 0.08 * W: faces[f] = [x, y - PAD * h, x + w, y + h]
    f += 1
frames = sorted(caps); got = sorted(faces)
def face_at(fr):
    if fr in faces: return faces[fr]
    if not got: return None
    n = min(got, key=lambda g: abs(g - fr)); return faces[n] if abs(n - fr) <= 0.3 * fps else None
viol = []; worst = dict(frame=None, t=None, pct=0.0); n = 0
for fr in frames:
    fb = face_at(fr)
    if not fb: continue
    n += 1; area = max(1.0, (fb[2] - fb[0]) * (fb[3] - fb[1]))
    for r in caps[fr]:
        ox = min(r[2], fb[2]) - max(r[0], fb[0]); oy = min(r[3], fb[3]) - max(r[1], fb[1])
        pct = (ox * oy / area) if ox > 0 and oy > 0 else 0.0
        if pct > worst['pct']: worst = dict(frame=fr, t=round(fr / fps, 2), pct=round(pct, 4))
        if pct > MAXF and ox > 6 and oy > 6:
            if viol and fr - viol[-1]['f1'] <= 3: viol[-1]['f1'] = fr; viol[-1]['max_pct'] = max(viol[-1]['max_pct'], round(100 * pct, 1))
            else: viol.append(dict(f0=fr, f1=fr, max_pct=round(100 * pct, 1)))
rep = dict(video=a.video, rule='V04', frames_with_caption=len(frames), frames_checked=n, face_detected=len(got), max_allowed_pct=round(100 * MAXF, 1), pad_top=PAD, worst=worst,
           violations=[dict(from_s=round(v['f0'] / fps, 2), to_s=round(v['f1'] / fps, 2), max_pct=v['max_pct']) for v in viol], pass_=not viol)
os.makedirs(os.path.dirname(os.path.abspath(a.report)), exist_ok=True); json.dump(rep, open(a.report, 'w'), indent=1)
print(json.dumps(rep, ensure_ascii=False)); sys.exit(1 if viol else 0)
