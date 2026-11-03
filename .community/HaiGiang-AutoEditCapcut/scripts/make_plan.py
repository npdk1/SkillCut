"""Start an edit plan from the timed shot list. Claude then adds music, sfx and text cues to it.

usage: python3 make_plan.py --shots work/timing/shots_timed.json --manifest work/shots/manifest.json \
          --vo "<media folder>/<Video Name> voiceover.wav" --words work/timing/words.json --out work/edit_plan.json \
          [--canvas 9:16] [--lang vi] [--font-device "<real path of BeVietnamPro-Bold.ttf>"] \
          [--map LOCAL_PREFIX DEVICE_PREFIX]...

--map tells the builder where each folder you read here lives on the viewer's computer (real paths), e.g.
   --map "<media folder as seen here>/" "/Users/sam/Movies/CapCut Automation/Emu War/"
   --map "<sounds folder as seen here>/" "/Users/sam/Documents/Sound Library/"
(more can be added to "path_map" later; Windows paths are fine: "C:/Users/sam/Videos/CapCut Automation/Emu War/").
--vo must be the voiceover copy INSIDE the media folder (the one the viewer imports), not the work copy.
--canvas    16:9 (default), 9:16 for TikTok / Reels / Shorts, 1:1, 4:5.
--lang vi   Vietnamese captions: the plan gets a "font" entry for the bundled Be Vietnam Pro (CapCut's default
            font has no Vietnamese tone marks). --font-device is where that .ttf sits on the viewer's computer
            (put a copy next to the video's media folder, in "CapCut Automation/_fonts/").
"""
import argparse
import os
import common as C
import textfit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--shots', required=True)
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--vo', required=True)
    ap.add_argument('--words', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--canvas', default=None)
    ap.add_argument('--lang', default=None)
    ap.add_argument('--font-device', default=None)
    ap.add_argument('--font-file', default=None, help='local copy of the caption font (default: bundled Be Vietnam Pro for vi)')
    ap.add_argument('--map', nargs=2, action='append', default=[], metavar=('LOCAL', 'DEVICE'))
    a = ap.parse_args()
    timed = C.load_json(a.shots)
    man = {m['n']: m for m in C.load_json(a.manifest)}
    canvas = None
    shots = []
    for i, r in enumerate(timed['shots']):
        m = man.get(r['n'])
        if not m:
            C.die(f"no image for shot {r['n']} in the manifest")
        shots.append({'n': r['n'], 'file': m['jpg'], 'analysis': m['png'], 'zoom': 'in' if i % 2 == 0 else 'out'})
        if m.get('w') and canvas is None:
            canvas = [m['w'], m['h']]
    cw, ch = C.canvas_size(a.canvas or canvas)
    if canvas and tuple(canvas) != (cw, ch):
        C.die(f'the images are {canvas[0]}x{canvas[1]} but --canvas is {cw}x{ch}: re-run prep_images.py normalize --canvas')
    lang = a.lang
    if not lang:
        txt = os.path.join(os.path.dirname(os.path.abspath(a.words)), 'words.txt')
        lang = 'vi' if os.path.exists(txt) and 'lang: vi' in open(txt, encoding='utf-8').readline() else 'en'
    plan = {
        'fps': timed.get('fps', 30),
        'end': timed['end'],
        'canvas': [cw, ch],
        'lang': lang,
        'words': os.path.abspath(a.words),
        'shots_file': os.path.abspath(a.shots),
        'path_map': [[os.path.abspath(l) + ('/' if l.endswith(('/', '\\')) else ''), d] for l, d in a.map],
        'vo': {'file': os.path.abspath(a.vo)},
        'zoom': {'per_sec': 0.011, 'min': 0.015, 'max': 0.045},
        'shots': shots,
        'music': [],
        'sfx': [],
        'text': [],
    }
    if lang == 'vi' or a.font_file:
        f = {'file': os.path.abspath(a.font_file or textfit.VI_FONT)}
        if a.font_device:
            f['device'] = a.font_device
        plan['font'] = f
    C.save_json(a.out, plan)
    print(f'{len(shots)} shots on a {cw}x{ch} canvas, lang {lang} -> {a.out}. '
          f'Next: add music, sfx and text cues (see references/capcut-edit.md).')
    if 'font' in plan and 'device' not in plan['font']:
        print('NOTE: add "device" to "font" (the real path of the .ttf on the viewer\'s computer) or a path_map entry '
              'that covers it; otherwise the builder puts it in "_fonts" next to the media folder.')


if __name__ == '__main__':
    main()
