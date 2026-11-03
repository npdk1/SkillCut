#!/usr/bin/env python3
"""v4.4 evidence bundle (verified.md V18 / V19). One command after every render:

  python3 scripts/make_evidence.py --video out/final.mp4 --prefix out/final [--project public/project] [--out-dir out]

writes, named after the output (<prefix> = path without .mp4):
  <prefix>_contact.jpg                 1 fps contact sheet, every tile stamped with its OUTPUT time (V18)
  <prefix>_still_<tbsId>.jpg           one still per text-behind beat at the middle of the beat (shows the 2-line wrap) (V06/V10)
  <prefix>_still_ill<k>_<concept>_<side>.jpg   one still per icon beat, middle of the beat (V11/V13)
  <prefix>_beats.json  <prefix>_icons.json  <prefix>_tbs.json (+ <prefix>_tbs_track_<id>[_i].json)   (tbs_manifest.py: command + command_person_only, person-only numbers)
"""
import argparse, json, math, os, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tbs_manifest
from PIL import Image, ImageDraw, ImageFont

ap = argparse.ArgumentParser(); ap.add_argument('--video', required=True); ap.add_argument('--prefix'); ap.add_argument('--project', default='public/project'); ap.add_argument('--out-dir', default='out')
ap.add_argument('--cols', type=int, default=10); ap.add_argument('--tile-w', type=int, default=216)
a = ap.parse_args(); P = a.prefix or os.path.splitext(a.video)[0]
def jl(p, d=None):
    try: return json.load(open(p, encoding='utf-8'))
    except Exception: return d
edl = jl(os.path.join(a.project, 'edl.json'), {}); mp = tbs_manifest.out_map(edl)
dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', a.video], capture_output=True, text=True).stdout.strip() or 0)
def still(t, path, w=None):
    cmd = ['ffmpeg', '-v', 'error', '-y', '-ss', f'{max(0, min(t, dur - 0.05)):.3f}', '-i', a.video, '-frames:v', '1', '-q:v', '2'] + (['-vf', f'scale={w}:-2'] if w else []) + [path]
    subprocess.run(cmd, check=True)
# contact sheet
n = int(math.ceil(dur)); tw = a.tile_w; tmp = P + '_tiles'; os.makedirs(tmp, exist_ok=True)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', a.video, '-vf', f'fps=1,scale={tw}:-2', '-q:v', '3', os.path.join(tmp, 't_%04d.jpg')], check=True)
tiles = sorted(os.listdir(tmp)); th = Image.open(os.path.join(tmp, tiles[0])).size[1]; cols = a.cols; rows = int(math.ceil(len(tiles) / cols))
sheet = Image.new('RGB', (cols * tw, rows * th), (20, 20, 20)); d = ImageDraw.Draw(sheet)
try: font = ImageFont.truetype(os.path.expanduser('~/.fonts/BeVietnamPro-Bold.ttf'), 22)
except Exception: font = ImageFont.load_default()
for i, f in enumerate(tiles):
    x, y = (i % cols) * tw, (i // cols) * th; sheet.paste(Image.open(os.path.join(tmp, f)), (x, y)); d.rectangle([x, y, x + 74, y + 28], fill=(0, 0, 0)); d.text((x + 4, y + 2), f'{i}s', fill=(255, 235, 59), font=font)
sheet.save(P + '_contact.jpg', quality=88); shutil.rmtree(tmp)
# manifests + stills
man = tbs_manifest.build(a.project, a.out_dir, a.video, None, P + '_tbs.json')
for b in man['beats']:
    t = (b['output_window_s'][0] + b['output_window_s'][1]) / 2; still(t, f'{P}_still_{b["id"]}.jpg'); b['still'] = os.path.basename(f'{P}_still_{b["id"]}.jpg')
json.dump(man, open(P + '_tbs.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
B = jl(os.path.join(a.project, 'beats.json'), {}); beats = B.get('beats', [])
icons = []; k = 0
for bt in beats:
    if bt.get('type') != 'illustration': continue
    k += 1; t0, t1 = mp(bt['t0']), mp(bt['t1']); t = (t0 + t1) / 2 if t0 is not None and t1 is not None else (t0 or 0)
    fn = f'{os.path.basename(P)}_still_ill{k}_{bt["concept"]}_{bt.get("side", "na")}.jpg'; still(t, os.path.join(os.path.dirname(P) or '.', fn))
    icons.append(dict(k=k, concept=bt['concept'], side=bt.get('side'), source_t=bt['t0'], output_t=t0, output_end=t1, free_left_px=bt.get('_freeLeftPx'), free_right_px=bt.get('_freeRightPx'), side_reason=bt.get('_sideReason'),
                      source=bt.get('source'), icon=bt.get('icon'), scale=bt.get('scale'), still=fn, why=bt.get('_why')))
json.dump(icons, open(P + '_icons.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
B2 = dict(B); B2['_output_times'] = {'note': 'beat t0/t1 are SOURCE seconds; output seconds from edl.json (cumulative)', 'map': [[s['srcIn'], s['srcOut']] for s in edl.get('segments', [])]}
json.dump(B2, open(P + '_beats.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(dict(contact=P + '_contact.jpg', tbs=[b['still'] for b in man['beats']], icons=[i['still'] for i in icons], duration=dur)))
