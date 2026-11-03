#!/usr/bin/env python3
"""Create placeholder media for beats (public/project/editor.png = fake editor window, phone.png = fake phone screen) when missing.
Used by topic-card / info-scene `media`. Replace with a real screenshot / screen recording any time (same file name).
  python3 scripts/make_placeholders.py [--dir public/project] [--force] [--from-video raw.mp4 --at 12.5]   # --from-video: crop a real frame instead
"""
import argparse, os, subprocess, sys, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, 'style.config.json'), encoding='utf-8'))
ap = argparse.ArgumentParser(); ap.add_argument('--dir', default=os.path.join(ROOT, 'public/project')); ap.add_argument('--force', action='store_true')
ap.add_argument('--from-video'); ap.add_argument('--at', type=float, default=0)
a = ap.parse_args(); os.makedirs(a.dir, exist_ok=True)
ed, ph = os.path.join(a.dir, 'editor.png'), os.path.join(a.dir, 'phone.png')
if a.from_video:
    for out in (ed, ph):
        if a.force or not os.path.exists(out):
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(a.at), '-i', a.from_video, '-frames:v', '1', out], check=True)
    sys.exit(0)
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    for out, size in ((ed, '1280x800'), (ph, '540x1080')):
        if a.force or not os.path.exists(out):
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f'color=c=0x1c1c22:s={size}', '-frames:v', '1', out], check=True)
    print('PIL missing: plain placeholders written'); sys.exit(0)
acc = CFG.get('palette', {}).get('accent', '#f5d90a') if isinstance(CFG.get('palette'), dict) else '#f5d90a'


def font(sz):
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', '/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf'):
        if os.path.exists(p): return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


def editor():
    W, H = 1280, 800
    im = Image.new('RGB', (W, H), (28, 28, 34)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 44], fill=(20, 20, 25))
    for i, c in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))): d.ellipse([16 + i * 26, 14, 30 + i * 26, 28], fill=c)
    d.text((W // 2 - 60, 12), 'Editor (placeholder)', fill=(170, 170, 180), font=font(18))
    d.rectangle([40, 70, 880, 470], fill=(12, 12, 16), outline=(70, 70, 80), width=2)      # canvas
    d.text((330, 250), 'PREVIEW', fill=(90, 90, 100), font=font(48))
    d.rectangle([910, 70, 1240, 470], fill=(24, 24, 30), outline=(70, 70, 80), width=2)    # layers panel
    for i, n in enumerate(('Title', 'Caption', 'Video', 'Audio')):
        d.rectangle([925, 90 + i * 52, 1225, 130 + i * 52], fill=(40, 40, 50)); d.text((940, 99 + i * 52), n, fill=(200, 200, 210), font=font(18))
    d.rectangle([40, 500, 1240, 780], fill=(20, 20, 26), outline=(70, 70, 80), width=2)    # timeline
    cols = [(245, 217, 10), (90, 160, 255), (120, 200, 120), (230, 120, 120)]
    for r in range(4):
        x = 70
        for k in range(3 + r % 2):
            w = 120 + (k * 97 + r * 53) % 200
            d.rectangle([x, 520 + r * 62, x + w, 560 + r * 62], fill=cols[r]); x += w + 14
    d.line([420, 500, 420, 780], fill=(255, 80, 80), width=3)
    im.save(ed)


def phone():
    W, H = 540, 1080
    im = Image.new('RGB', (W, H), (14, 14, 18)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([20, 20, W - 20, H - 20], 48, fill=(24, 24, 32), outline=(80, 80, 90), width=3)
    d.text((W // 2 - 90, H // 2 - 20), 'PHONE (placeholder)', fill=(110, 110, 120), font=font(22))
    for i, y in enumerate((880, 930, 980)): d.rounded_rectangle([60, y, 60 + 280 - i * 40, y + 20], 8, fill=(60, 60, 72))
    im.save(ph)


for path, fn in ((ed, editor), (ph, phone)):
    if a.force or not os.path.exists(path):
        fn(); print('wrote', path)
    else:
        print('exists', path)
