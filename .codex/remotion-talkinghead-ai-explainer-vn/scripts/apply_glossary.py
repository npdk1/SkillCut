#!/usr/bin/env python3
"""Apply the glossary + the built-in ASR fixes to an EXISTING project without re-running whisper / make_edl:
  - public/project/glossary.txt ('wrong => Right' lines)  PLUS style.config.json textCleanup.asrFixes / properAliases / contextFixes ('xửa từng' -> 'sửa từng', 'claw' -> Claude near tech words, 'hấp' -> 'hợp' after kết/phù/tích ...)
  - words.json   (backup kept as words.pre_glossary.json the first time)
  - captions.json (word texts inside every page/line; timing untouched)  <- v4.2: captions get the SAME cleanup as the words, whether or not a glossary.txt exists
Then re-run make_beats.py (it also re-applies the glossary on load, so beat headlines/lines are corrected too).
usage: python3 scripts/apply_glossary.py [public/project] [--glossary FILE]"""
import argparse, json, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from text_cleanup import load_glossary, reapply_glossary, canon_pairs, apply_canon, apply_context, merge_numbers, ROOT, CFG

ap = argparse.ArgumentParser(); ap.add_argument('proj', nargs='?', default='public/project'); ap.add_argument('--glossary')
a = ap.parse_args()
gp = a.glossary or os.path.join(a.proj, 'glossary.txt')
gl = load_glossary(gp)
asr = {' '.join(k.split()) for k in CFG.get('asrFixes', {})}
pairs = [x for x in canon_pairs(gl) if ' '.join(x[0]) in gl or ' '.join(x[0]) in asr or x[0][0] in CFG.get('properAliases', {})]
if not pairs and not CFG.get('contextFixes'): sys.exit(f'no glossary / asrFixes / contextFixes entries (glossary file: {gp})')
wp = os.path.join(a.proj, 'words.json')
if os.path.exists(wp):
    segs = json.load(open(wp, encoding='utf-8')); new, n = reapply_glossary(segs, gp)
    if n:
        bk = os.path.join(a.proj, 'words.pre_glossary.json')
        if not os.path.exists(bk): shutil.copy(wp, bk)
        json.dump(new, open(wp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'words.json: {n} word(s) fixed')
cp = os.path.join(a.proj, 'captions.json'); nc = 0
if os.path.exists(cp):
    pages = json.load(open(cp, encoding='utf-8'))
    for pg in pages:
        ws = [w for ln in pg['lines'] for w in ln['words']]
        flat = [dict(w) for w in ws]; st = {}
        fixed = apply_context(apply_canon(flat, pairs, st), st) if flat else flat
        if len(fixed) != len(ws):
            print(f'  skip page (token count changed) {" ".join(w["w"] for w in ws)}: fix words.json and re-run make_edl.py'); continue
        for x, y in zip(ws, fixed):
            if x['w'] != y['w']: x['w'] = y['w']; nc += 1
    for pg in pages:                                    # v4.3: 'Opus 5 .5' -> 'Opus 5.5' inside every caption page (merge keeps the span t0..t1)
        flat = [(ln, w) for ln in pg['lines'] for w in ln['words']]
        for ln in pg['lines']:
            before = len(ln['words']); ln['words'] = merge_numbers(ln['words'], 't0', 't1'); nc += before - len(ln['words'])
    json.dump(pages, open(cp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'captions.json: {nc} word(s) fixed')
