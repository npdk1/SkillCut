#!/usr/bin/env python3
"""v4.2 gate-driven auto-repair: read the overlap-gate report (out/overlaps.json) and change public/project/beats.json so the NEXT gate run passes - no hand edits.
  round 1: caption-vs-element  -> pin the caption to the top for that beat when the element sits in the lower part of the frame, else drop the beat
  round 2+: every remaining pair / face-cover -> drop the lower-priority beat (priority = autoBeats.collision.priority)
  v4.3: PROTECTED beats (autoBeats.collision.protected = the closing CTA comment-box) are NEVER dropped: the caption is pinned to the top, else the CTA is MOVED (`dy`, away from the other box / the face); only the
  other (decorative) beat may be dropped. Brand logos + illustration cards are RE-SLOTTED / RE-TIMED with the face-aware placer before they are dropped. Canvas height comes from logo_place.canvas_info (not the probe height).
  Exit codes: 0 = changed something, 3 = nothing left to fix. render.sh turns "still failing after 3 rounds" into a non-zero exit that stops the render.
Text-behind-speaker beats that fell back are big-words; they follow the same rules. Every change is logged to out/autofix.json (nothing silent).
usage: python3 scripts/autofix_overlaps.py [public/project] [--report out/overlaps.json] [--round N]  -> exit 0 = changed something, 3 = nothing left to fix"""
import argparse, json, os, sys
ap = argparse.ArgumentParser(); ap.add_argument('proj', nargs='?', default='public/project'); ap.add_argument('--report', default='out/overlaps.json'); ap.add_argument('--round', type=int, default=1)
a = ap.parse_args()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, 'style.config.json'), encoding='utf-8'))
PRIO = CFG['autoBeats'].get('collision', {}).get('priority', [])
rep = json.load(open(a.report)); bp = os.path.join(a.proj, 'beats.json'); data = json.load(open(bp, encoding='utf-8')); beats = data['beats']
edl = json.load(open(os.path.join(a.proj, 'edl.json'))) if os.path.exists(os.path.join(a.proj, 'edl.json')) else None
sys.path.insert(0, os.path.join(ROOT, 'scripts')); import logo_place
PROBE = json.load(open(os.path.join(a.proj, 'probe.json'))) if os.path.exists(os.path.join(a.proj, 'probe.json')) else {}
CI = logo_place.canvas_info(CFG, PROBE); H = CI['H']; W = CI['W']      # v4.3: canvas px (1080x1920 for every vertical output), NOT the source height (a 16:9 source is 608/720 high)
PROTECTED = set(CFG['autoBeats'].get('collision', {}).get('protected', ['comment-box']))
FACES = logo_place.load_faces(os.path.join(a.proj, 'faces.json'))
GT = {'chips': 'chip-stack', 'prompt': 'prompt-box', 'comment': 'comment-box', 'title': 'title-burst', 'timeline': 'title-burst', 'rec': 'title-burst', 'star': 'stars', 'sticker': 'sticker',
      'big-word': 'big-word', 'brand-logo': 'brand-logo', 'name': 'brand-logo', 'logo': 'brand-logo', 'avatar-chain': 'avatar-chain', 'info-card': 'info-scene', 'info-header': 'info-scene',
      'topic-header': 'topic-card', 'topic-line': 'topic-card', 'tbs-text': 'text-behind-speaker', 'ff-device': 'framed-focus', 'ff-head': 'framed-focus', 'ff-line': 'framed-focus',
      'illustration': 'illustration', 'illu': 'illustration', 'caption': 'caption'}
def to_src(t):
    if not edl: return t
    c = 0.0
    for s in edl['segments']:
        d = (s['srcOut'] - s['srcIn']) / s.get('speed', 1)
        if c - 1e-6 <= t <= c + d + 1e-6: return s['srcIn'] + (t - c) * s.get('speed', 1)
        c += d
    return t
def active(ty, t0, t1):
    ts = to_src(t0); te = to_src(t1)
    return [b for b in beats if b['type'] == ty and b['t0'] - 0.3 <= te and ts <= b['t1'] + 0.3 and '_autofixDropped' not in b]

def box_gap(r, o):    # vertical overlap (px) of two [l,t,r,b] boxes, <=0 when clear
    return min(r[3], o[3]) - max(r[1], o[1])
DY_TYPES = ('comment-box', 'prompt-box', 'chip-stack', 'title-burst')
def move_cta(b, mine, other, sign_hint=None):
    """v4.3: shift a protected CTA by `dy` (fraction of canvas H) until it clears `other` (+ margin); cumulative, max |dy| 0.30. -> True when changed"""
    if b['type'] not in DY_TYPES: return False                 # only components that read `dy` can be moved (Beats.tsx: chips, prompt, title, comment)
    old = b.get('dy', 0) or 0
    if mine and other:
        need = (box_gap(mine, other) + 14) / H
        down = (mine[1] + mine[3]) / 2 >= (other[1] + other[3]) / 2          # CTA lower than the other box -> go further down, else up
        dy = old + (need if down else -need)
    else:
        dy = old + (sign_hint or 1) * 0.06
    dy = round(max(-0.30, min(0.30, dy)), 3)
    if abs(dy - old) < 1e-3: return False
    b['dy'] = dy; log.append(dict(action='moveCTA', beat=b['type'], t0=b['t0'], t1=b['t1'], dy=dy)); print(f"autofix: MOVE {b['type']} {b['t0']}-{b['t1']}s dy {old:+.3f} -> {dy:+.3f} (never dropped)"); return True
def pin_caption_top(t0, t1, why):
    ex = data.setdefault('captionAnchor', [])
    if any(e['anchor'] == 'top' and e['t0'] <= t0 + 0.01 and e['t1'] >= t1 - 0.01 for e in ex): return False
    ex.append(dict(t0=t0, t1=t1, anchor='top', _why=f"autofix: {why}")); log.append(dict(action='captionTop', t0=t0, t1=t1, why=why)); print(f"autofix: caption -> top {t0}-{t1}s ({why})"); return True
BUSY = ('title-burst', 'chip-stack', 'prompt-box', 'comment-box', 'avatar-chain', 'info-scene', 'topic-card', 'framed-focus', 'broll', 'sticker', 'big-word', 'text-behind-speaker')
def relocate_card(b, boxes):
    """v4.3: brand-logo / illustration collided -> same-time slot search around the reported obstacle boxes + the face (all slots x all scales), then other times
    (only where no other overlay is on screen). True = moved (never dropped before this ran)"""
    illu = b['type'] == 'illustration'; name = b.get('label') if illu else b.get('name')
    PL = CFG['autoBeats']['illustration']['placement'] if illu else CFG['brandLogos']['placement']
    LG = dict(size=round(CFG['layout'][('horizontal' if CI.get('prof') is CFG['layout']['horizontal'] else 'vertical')]['logo']['size'] * CI['u']), nameFont=round(CFG['layout'][('horizontal' if CI.get('prof') is CFG['layout']['horizontal'] else 'vertical')]['logo']['nameFont'] * CI['u']))
    sfr = CI['prof'].get('safe') or CFG['layout']['vertical']['safe']
    sfp = dict(top=H * sfr['topR'], left=W * sfr['leftR'], right=W * sfr['rightR'], bottom=H * sfr['bottomR'])
    segs = edl['segments'] if edl else None
    dur = b['t1'] - b['t0']; tried = []
    for off in [0.0, 0.4, 0.8, 1.2, 1.6, -0.2]:
        t0, t1 = round(b['t0'] + off, 2), round(b['t1'] + off, 2)
        if off and any(o is not b and o['type'] in BUSY and o['t0'] < t1 + 0.1 and t0 - 0.1 < o['t1'] and '_autofixDropped' not in o for o in beats): continue
        fr = logo_place.face_rect(FACES, segs, CFG, CI, t0, t1) if FACES and segs else None
        fx = logo_place.expand(fr, PL.get('faceExpand', {'x': 0.2, 'up': 0.45, 'down': 0.2}), CI) if fr else None
        obst = [list(x) for x in boxes] if off == 0 else []
        pl = logo_place.place(fx, obst, name, CI, PL, LG, sfp, CI['capY'] - PL.get('captionGapR', 0.045) * H, strict=bool(fx))
        if pl is None or (obst and not pl.get('free', True)): continue
        nx, ny = round(pl['cx'] / W, 4), round(pl['top'] / H, 4)
        if off == 0 and abs(nx - (b.get('x') or 0)) < 1e-3 and abs(ny - (b.get('y') or 0)) < 1e-3 and pl['scale'] == b.get('scale') and bool(pl.get('pill')) == bool(b.get('pill')): continue
        if off and any(o is not b and o['type'] in BUSY for o in beats if False): continue
        b.update(x=nx, y=ny, scale=pl['scale']); b['t0'], b['t1'] = t0, t1
        if pl.get('pill'): b['pill'] = True
        else: b.pop('pill', None)
        log.append(dict(action='relocate', beat=b['type'], name=name, off=off, x=nx, y=ny, scale=pl['scale'], mode=pl.get('mode'))); print(f"autofix: RELOCATE {b['type']} {name}: {pl.get('mode')} x{pl['scale']} at {t0}-{t1}s (offset {off:+.1f}s)"); return True
    return False
issues = []
for o in rep.get('overlaps', []):
    x, y = [p.strip() for p in o['pair'].split(' x ')]
    issues.append(dict(a=GT.get(x, x), b=GT.get(y, y), t0=o['outFrom'], t1=o['outTo'], boxA=o.get('boxA'), boxB=o.get('boxB'), why=o['pair']))
for v in rep.get('logoOverFace', []):
    if v['kind'] == 'logo': issues.append(dict(a=v.get('btype', 'brand-logo'), b='face', t0=v['t0'], t1=v['t1'], src=True, why=f"logo {v['name']} covers face {v['overlapPct']}%", name=v['name']))
    else: issues.append(dict(a=GT.get(v['name'], v['name']), b='face', t0=v['outFrom'], t1=v['outTo'], why=f"{v['name']} covers {v['overlapPct']}% of the face"))
log = []
tg = 'out/tbs_gate.json'
if os.path.exists(tg):        # text-behind readability gate failed -> that beat becomes a normal headline (never render occluded text)
    for bid in json.load(open(tg)).get('failed', []):
        b = next((x for x in beats if x.get('id') == bid), None)
        if b: b.update(type='big-word', text=b['text'].replace('\n', ' ').upper(), _fallbackFrom='text-behind-speaker'); [b.pop(k, None) for k in ('items', 'y', 'h', 'maskDir', 'maskStart', 'anim', 'id', '_readable', '_layout', '_tool', '_blockers')]; log.append(dict(action='tbs->headline', beat=bid, why='readability gate failed')); print(f'autofix: text-behind {bid} failed readability -> normal headline')
    os.remove(tg)
def drop(b, why):
    if b.get('_autofixDropped'): return
    if b['type'] in PROTECTED:
        log.append(dict(action='refused-drop', beat=b['type'], t0=b['t0'], t1=b['t1'], why=why)); print(f"autofix: REFUSED to drop protected {b['type']} {b['t0']}-{b['t1']}s ({why}) - move it / the caption instead"); return
    b['_autofixDropped'] = why; log.append(dict(action='drop', beat=b['type'], t0=b['t0'], t1=b['t1'], why=why)); print(f"autofix: DROP {b['type']} {b['t0']}-{b['t1']}s: {why}")
for it in issues:
    if it.get('src'):
        cands = [b for b in beats if b['type'] == it['a'] and (b.get('name') or b.get('label')) == it.get('name') and b['t0'] - 0.3 <= it['t1'] and it['t0'] <= b['t1'] + 0.3 and not b.get('_autofixDropped')]
    else:
        names = [t for t in (it['a'], it['b']) if t not in ('caption', 'face')]
        cands = [b for n in names for b in active(n, it['t0'], it['t1'])]
    if not cands and it['a'] == 'caption' and it['b'] == 'face' and a.round <= 2:      # plain caption over a big close-up face (no beat involved): pin that caption window to the top
        ex = data.setdefault('captionAnchor', []); ts_, te_ = round(to_src(it['t0']) - 0.12, 2), round(to_src(it['t1']) + 0.12, 2)
        cp_ = os.path.join(sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('-') else 'public/project', 'captions.json')
        if os.path.exists(cp_):       # anchors are matched on the PAGE midpoint -> cover the whole page(s) touching the window
            pg = [q for q in json.load(open(cp_, encoding='utf-8')) if q['t0'] <= te_ and ts_ <= q['t1']]
            if pg: ts_, te_ = round(min(q['t0'] for q in pg) - 0.01, 2), round(max(q['t1'] for q in pg) + 0.01, 2)
        if not any(e['anchor'] == 'top' and e['t0'] <= ts_ + 0.01 and e['t1'] >= te_ - 0.01 for e in ex):
            ex.append(dict(t0=ts_, t1=te_, anchor='top', _why=f"autofix: {it['why']}")); log.append(dict(action='captionTop', beat='caption', t0=ts_, t1=te_, why=it['why'])); print(f"autofix: caption -> top {ts_}-{te_}s ({it['why']})"); continue
    if not cands: print(f"autofix: no beat found for {it['why']} @ {it['t0']}-{it['t1']}s (output time) - nothing to change"); continue
    if 'caption' in (it['a'], it['b']) and a.round <= 1 and len(cands) == 1 and it.get('boxA'):
        b = cands[0]; bx = it['boxA'] if it['a'] != 'caption' else it['boxB']
        if bx[1] > 0.35 * H:       # element in the lower part -> caption to the top is a clear spot
            ex = data.setdefault('captionAnchor', [])
            if not any(e['anchor'] == 'top' and e['t0'] <= b['t0'] + 0.01 and e['t1'] >= b['t1'] - 0.01 for e in ex):
                ex.append(dict(t0=b['t0'], t1=b['t1'], anchor='top', _why=f"autofix: {it['why']}")); log.append(dict(action='captionTop', beat=b['type'], t0=b['t0'], t1=b['t1'], why=it['why'])); print(f"autofix: caption -> top during {b['type']} {b['t0']}-{b['t1']}s ({it['why']})")
                continue
    # ---- v4.3: protected CTA / cards: move, re-slot, re-time - then (only for non-protected beats) drop ----
    prot = [b for b in cands if b['type'] in PROTECTED]
    cap_involved = 'caption' in (it['a'], it['b'])
    def other_box(me_type):
        if not (it.get('boxA') and it.get('boxB')): return None, None
        return (it['boxA'], it['boxB']) if it['a'] == me_type else (it['boxB'], it['boxA'])
    if prot:
        cta = prot[0]; mine, oth_ = other_box(cta['type'])
        if cap_involved:
            ts_, te_ = round(cta['t0'] - 0.05, 2), round(cta['t1'] + 0.05, 2)
            if a.round <= 1 and pin_caption_top(ts_, te_, it['why']): continue                 # 1) the caption moves up out of the CTA's way
            if move_cta(cta, mine, oth_, sign_hint=-1): continue                                # 2) else the CTA moves (never dropped)
            if pin_caption_top(ts_, te_, it['why']): continue
            print(f"autofix: PROTECTED {cta['type']} still collides with the caption after caption->top and dy={cta.get('dy', 0)}: gate will fail the render"); continue
        if it['b'] == 'face' or it['a'] == 'face':
            if move_cta(cta, None, None, sign_hint=(1 if a.round % 2 else -1)): continue
        else:
            if move_cta(cta, mine, oth_): continue
            others = [b for b in cands if b['type'] not in PROTECTED]        # the OTHER element yields
            if others: drop(max(others, key=lambda b: PRIO.index(b['type']) if b['type'] in PRIO else 99), f"gate: {it['why']} vs protected CTA @ {it['t0']}-{it['t1']}s (round {a.round})"); continue
        print(f"autofix: PROTECTED {cta['type']}: nothing movable left for {it['why']} - the gate will fail the render (CTA is never dropped)"); continue
    cards = [b for b in cands if b['type'] in ('brand-logo', 'illustration')]
    if cards and a.round <= 3:
        c0 = cards[0]; oth_boxes = [bx for bx in (it.get('boxA'), it.get('boxB')) if bx and bx is not (it.get('boxA') if it['a'] == c0['type'] else it.get('boxB'))]
        if relocate_card(c0, oth_boxes): continue
    nonprot = [b for b in cands if b['type'] not in PROTECTED]
    lo = max(nonprot or cands, key=lambda b: PRIO.index(b['type']) if b['type'] in PRIO else 99)
    drop(lo, f"gate: {it['why']} @ {it['t0']}-{it['t1']}s (round {a.round})")
data['beats'] = [b for b in beats if not b.get('_autofixDropped')]
data.setdefault('_autofix', []).extend(log)
json.dump(data, open(bp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
os.makedirs('out', exist_ok=True); json.dump(log, open('out/autofix.json', 'w'), indent=1, ensure_ascii=False)
sys.exit(0 if log else 3)
