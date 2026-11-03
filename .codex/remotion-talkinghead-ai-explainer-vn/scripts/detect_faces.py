#!/usr/bin/env python3
"""FACE BOXES of the speaker -> public/project/faces.json   (used by make_beats.py to keep brand-logo cards OFF the face)

  python3 scripts/detect_faces.py public/project/raw.mp4 [--out public/project/faces.json] [--every 0.25] [--edl public/project/edl.json]

* Samples the SOURCE video every --every seconds (ffmpeg, auto-rotation, 640 px wide), detects faces with OpenCV
  YuNet (assets/models/face_detection_yunet_2023mar.onnx, bundled) and falls back to Haar cascades (frontalface_alt2/default/profile) per frame.
* Boxes are stored as FRACTIONS of the displayed source frame (x, y, w, h in 0..1), source-time `t` (same time base as words.json / beats.json).
* Only the largest face per frame is kept as `main` (talking head); `faces` has all of them. Frames with no detection get `main: null`; make_beats fills gaps from neighbours (<= 1.5 s).
* Cached: re-running with an existing faces.json that matches the video (size/duration) is a no-op unless --force.
Needs: pip install opencv-python-headless (4.x; 5.x ships no Haar data, YuNet still works), ffmpeg.
"""
import argparse, glob, json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(os.path.dirname(HERE), 'assets', 'models', 'face_detection_yunet_2023mar.onnx')


def probe(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height:format=duration', '-of', 'json', path], capture_output=True, text=True)
    j = json.loads(r.stdout)
    return float(j['format']['duration']), j['streams'][0]['width'], j['streams'][0]['height']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('video'); ap.add_argument('--out'); ap.add_argument('--every', type=float, default=0.25)
    ap.add_argument('--force', action='store_true'); ap.add_argument('--min-score', type=float, default=0.6); ap.add_argument('--min-w', type=float, default=0.08, help='ignore faces narrower than this fraction of the frame width (screens/posters/false hits)')
    a = ap.parse_args()
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.video)), 'faces.json')
    dur, sw, sh = probe(a.video)
    if os.path.exists(out) and not a.force:
        try:
            old = json.load(open(out))
            if abs(old.get('duration', -1) - dur) < 0.05 and old.get('every') == a.every:
                print(f'faces.json up to date: {out}'); return
        except Exception:
            pass
    try:
        import cv2
    except ImportError:
        sys.exit('opencv missing: pip install opencv-python-headless')
    tmp = tempfile.mkdtemp(prefix='faces_')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', a.video, '-vf', f'fps=1/{a.every},scale=640:-2', '-q:v', '2', os.path.join(tmp, 'f%06d.jpg')], check=True)
    frames = sorted(glob.glob(os.path.join(tmp, 'f*.jpg')))
    yun = None
    if hasattr(cv2, 'FaceDetectorYN') and os.path.exists(MODEL):
        yun = cv2.FaceDetectorYN.create(MODEL, '', (640, 640), a.min_score, 0.3, 5000)
    casc = []
    try:
        for n in ('haarcascade_frontalface_alt2.xml', 'haarcascade_frontalface_default.xml', 'haarcascade_profileface.xml'):
            p = os.path.join(cv2.data.haarcascades, n)
            if os.path.exists(p): casc.append(cv2.CascadeClassifier(p))
    except Exception:
        pass
    samples, n_yunet, n_haar = [], 0, 0
    for k, fp in enumerate(frames):
        img = cv2.imread(fp)
        if img is None: continue
        h, w = img.shape[:2]
        faces = []
        if yun is not None:
            yun.setInputSize((w, h))
            _, det = yun.detect(img)
            if det is not None:
                faces = [dict(x=float(d[0]) / w, y=float(d[1]) / h, w=float(d[2]) / w, h=float(d[3]) / h, score=round(float(d[14]), 3), by='yunet') for d in det]
                n_yunet += 1
        if not faces and casc:
            g = cv2.equalizeHist(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
            for c in casc:
                r = c.detectMultiScale(g, 1.1, 5, minSize=(max(24, w // 12), max(24, w // 12)))
                if len(r):
                    faces = [dict(x=float(x) / w, y=float(y) / h, w=float(fw) / w, h=float(fh) / h, score=0.5, by='haar') for x, y, fw, fh in r]
                    n_haar += 1; break
        faces = [f for f in faces if a.min_w <= f['w'] <= 0.9]
        faces.sort(key=lambda f: -(f['w'] * f['h']))
        samples.append(dict(t=round(k * a.every + a.every / 2, 3), main=faces[0] if faces else None, faces=faces))
    for fp in frames:
        try: os.remove(fp)
        except OSError: pass
    try: os.rmdir(tmp)
    except OSError: pass
    got = sum(1 for s in samples if s['main'])
    json.dump(dict(version=1, source=os.path.basename(a.video), duration=dur, width=sw, height=sh, every=a.every, method='yunet+haar-fallback' if yun is not None else 'haar',
                   stats=dict(samples=len(samples), withFace=got, yunet=n_yunet, haar=n_haar), samples=samples), open(out, 'w'), ensure_ascii=False)
    print(f'OK {out}: faces in {got}/{len(samples)} samples (yunet {n_yunet}, haar-fallback {n_haar})')


if __name__ == '__main__':
    main()
