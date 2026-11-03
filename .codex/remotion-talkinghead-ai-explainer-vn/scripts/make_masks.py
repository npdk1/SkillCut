#!/usr/bin/env python3
"""Person mattes for every `text-behind-speaker` beat (only the frames of the beat are processed, cached by range).
usage: make_masks.py [public/project]   (beats.json + probe.json + raw video inside)
The matting tool is `person_mask.py` (rembg u2net_human_seg + guided-filter refinement + temporal smoothing). Looked up in: env PERSON_MASK,
style.config.json autoBeats.textBehind.tool, /workspace/render-env/bin/person_mask.py, `person_mask.py` on PATH.
Writes public/project/masks/<id>/mask_%05d.png (+ mask.json) and stores `maskStart` (source seconds of mask_00000) in beats.json."""
import json, os, shutil, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'public', 'project')
CFG = json.load(open(os.path.join(ROOT, 'style.config.json'), encoding='utf-8'))
TB = CFG['autoBeats'].get('textBehind', {})
bp = os.path.join(d, 'beats.json'); data = json.load(open(bp, encoding='utf-8'))
probe = json.load(open(os.path.join(d, 'probe.json'), encoding='utf-8'))
video = os.path.join(d, os.path.basename(probe['file']))
tool = next((t for t in [os.environ.get('PERSON_MASK'), TB.get('tool'), '/workspace/render-env/bin/person_mask.py', shutil.which('person_mask.py')] if t and os.path.exists(t)), None)
todo = [b for b in data['beats'] if b['type'] == 'text-behind-speaker']
if todo and not tool: sys.exit('make_masks: person_mask.py not found (set PERSON_MASK=/path/to/person_mask.py)')
dur = float((probe.get('original') or {}).get('durationSec') or probe.get('durationSec') or 1e9)
for b in todo:
    s = max(0.0, round(b['t0'] - TB.get('padBeforeSec', 0.15), 3)); e = min(dur, round(b['t1'] + TB.get('padAfterSec', 0.3), 3))
    out = os.path.join(d, 'masks', b['id']); mj = os.path.join(out, 'mask.json')
    ok = False
    if os.path.exists(mj):
        m = json.load(open(mj)); ok = abs(m.get('start', -1) - s) < 0.01 and abs(m.get('end', -1) - e) < 0.01
    if not ok:
        shutil.rmtree(out, ignore_errors=True)
        cmd = [tool] if os.access(tool, os.X_OK) else [sys.executable, tool]
        r = subprocess.run(cmd + [video, '--start', str(s), '--end', str(e), '--out', out], capture_output=True, text=True)
        if r.returncode: sys.exit(f'make_masks: person_mask failed for {b["id"]}:\n{r.stderr[-800:]}')
        print(f'mask {b["id"]}: {s}-{e}s', file=sys.stderr)
    b['maskStart'] = s; b['maskDir'] = f'project/masks/{b["id"]}'

# ---- v4.2 placement search: verify the speaker (person masks, warped through the framing zoom) and put the text ONLY in empty background space ----
# readability >= tuneMinReadable (0.90) on average AND >= tuneWorstFrameMin (0.80) on the worst frame; nothing passes -> beat.fallback (make_beats/render turn it into a normal headline).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tbs_place, logo_place
import numpy as np
J = lambda n: json.load(open(os.path.join(d, n), encoding='utf-8')) if os.path.exists(os.path.join(d, n)) else {}
edl = J('edl.json'); ci = logo_place.canvas_info(CFG, probe); fps = (edl.get('source') or {}).get('fps') or probe.get('fps') or 30
fps = 30 if probe.get('fpsIsVariable') or fps < 20 else fps
segs = edl.get('segments'); TS = tbs_place.Typeset(CFG); stage = tbs_place.Stage(d, CFG, ci, fps, segs)
MAX_OCC = 1 - TB.get('tuneWorstFrameMin', 0.9)       # the shared gate: <= 10 % of the glyph ink hidden on the WORST frame
OUTD = os.path.join(d, '..', '..', 'out', 'tbs_canvas')
def head_of(stk, W, H):
    m = stk.mean(axis=0); ys, xs = np.where(m[: int(H * 0.5 / tbs_place.DS)] > 0.4)
    return [xs.min() * tbs_place.DS, ys.min() * tbs_place.DS, xs.max() * tbs_place.DS, ys.max() * tbs_place.DS] if len(xs) else [W * .35, H * .12, W * .65, H * .3]
def verify_tracked(bb, c, dy, ka, kb, mo, tag):
    """CANONICAL gate for a candidate (v4.3): Render's text_occlusion.py --track on the composition-space masks (person + other beats' boxes): worst frame <= 10 % hidden, mean <= 10 %;
    and --track on the person-only masks: mean occlusion >= mo (the text really tucks behind the head). Every item of the candidate is measured. -> (ok, readable_mean, readable_worst, person_mean) or None if the tool lacks --track"""
    canvas = tbs_place.write_canvas_masks(stage, bb, os.path.join(OUTD, bb['id']))                       # REAL composition-space masks: the text box moves, the masks do not
    pcanvas = tbs_place.write_canvas_masks(stage, dict(bb, _blockers=[]), os.path.join(OUTD, bb['id'] + '_person'))
    mx_, mn_, pm_ = 0.0, 0.0, 0.0; tg_, tw_, tp_ = 0.0, None, True
    for it in c['items']:
        r = tbs_place.tool_track(canvas, it, dy, ka, kb, bb); rp = tbs_place.tool_track(pcanvas, it, dy, ka, kb, bb)
        if r is None or rp is None: return None
        mx_, mn_, pm_ = max(mx_, r['max']), max(mn_, r['mean']), max(pm_, rp['mean'])
        if r.get('glyph_max') is not None:                                              # Render's text_occlusion.py --max-glyph (canonical)
            tp_ = tp_ and (bool(r['pass_glyph']) if r.get('pass_glyph') is not None else r['glyph_max'] <= (tbs_place.GLYPH_MAX or 0.30) + 1e-6)
            if r['glyph_max'] >= tg_: tg_, tw_ = r['glyph_max'], r.get('worst_glyph')
    gmin = TB.get('tuneGlyphMinVisible', 0.70); gv = 1.0; gw = None             # v4.3.2: per-glyph rule, exact (full resolution, own script): no letter more than 30 % covered on any frame
    if gmin > 0:
        for it in c['items']:
            r_ = tbs_place.glyph_visibility(canvas, it, dy, ka, kb, TS, ci['W'], gmin)
            if r_['min_vis'] < gv: gv, gw = r_['min_vis'], r_['worst']
    if tw_ is not None: gv, gw = min(gv, 1 - tg_), (tw_ if (1 - tg_) <= gv + 1e-9 else gw)     # the tool's number wins when it is the worse one
    c['glyphMin'] = gv; c['glyphWorst'] = gw; c['glyphTool'] = tg_ if tw_ is not None else None
    ok = mx_ <= MAX_OCC + 1e-6 and (1 - mn_) >= TB.get('tuneMinReadable', 0.9) and (mo <= 0 or pm_ >= mo - 0.002) and gv >= gmin - 0.003 and tp_
    if not ok and gv < gmin - 1e-6: print(f'  tune {bb["id"]} candidate "{c["items"][0]["text"].replace(chr(10), "|")}" rejected: glyph "{(gw or {}).get("ch") or (gw or {}).get("char")}" only {gv:.0%} visible on frame {(gw or {}).get("frame")} (< {gmin:.0%})', file=sys.stderr)
    if os.environ.get('TBS_DEBUG'): print(f'  [dbg] {bb["id"]} {c.get("layout")} {[i["text"] for i in c["items"]]!r} size {c["items"][0]["size"]} ink {c["items"][0]["ink"]} occ max {mx_:.3f} mean {mn_:.3f} person mean {pm_:.3f} glyphmin {gv:.3f} tool_glyph_max {tg_:.3f} pass_tool {tp_} -> ok {ok}', file=sys.stderr)
    return ok, 1 - mn_, 1 - mx_, pm_

def attempt(b, win, use_track, cs, mo):
    """one try: window `win` (source s), tracked or static. Candidate generators: (1) Render's --suggest --require-behind on the crown-stabilised masks, (2) the in-house search. -> best dict or None"""
    W, H = ci['W'], ci['H']; fps_ = fps
    bb = dict(b, t0=win[0], t1=win[1]); ka = max(0, round(win[0] * fps_) - cs['first']); kb = min(len(cs['raw']), round(win[1] * fps_) - cs['first'])
    dy, ref = tbs_place.track_dy(cs, ka, kb, clamp=TB.get('trackClampR', 0.10) * H) if use_track else ([0.0] * len(cs['raw']), 0.0)
    trk = dy if use_track else None; tag = '_trk' if use_track else '_st'
    stk, zs, idx = stage.stack(bb, ds=tbs_place.DS, step=2, track=trk)
    pstk = stage.stack(bb, ds=tbs_place.DS, step=2, blockers=False, track=trk)[0] if b.get('_blockers') else stk
    head = head_of(stk, W, H)
    bb['_minOcc'] = mo; cands = []
    if tbs_place.tool_has_flag('--suggest') and tbs_place.occlusion_tool():
        stab = tbs_place.write_canvas_masks(stage, bb, os.path.join(OUTD, b['id'] + tag + '_stab'), track=dy if use_track else None)
        sc = tbs_place.suggest_candidate(stab, b['text'].replace('\n', ' '), TS, W, H, bb, mo, MAX_OCC)
        if sc and not sc.get('_none'): cands.append(sc)
        elif sc: print(f'  tune {b["id"]} suggest ({"tracked" if use_track else "static"}, {win[0]:.2f}-{win[1]:.2f}s): no behind placement - {str(sc.get("reason"))[:120]}', file=sys.stderr)
    c2, tried = tbs_place.search(stk, head, bb, TS, W, H, TB, min_occ=mo, pstack=pstk); cands += c2
    if os.environ.get('TBS_DEBUG'): print(f'  [dbg] search {win} -> {len(c2)} cands: ' + ', '.join(f'{c["layout"]}@{c["items"][0]["size"]}' for c in c2), file=sys.stderr)
    for c in cands:
        v = verify_tracked(bb, c, dy if use_track else [0.0] * len(cs['raw']), ka, kb, mo, tag)
        if v is None: c['tool'] = 'tbs_place (text_occlusion.py --track unavailable)'; c.update(occP=None); return dict(c, win=win, dy=dy, ka=ka, kb=kb, tracked=use_track, ref=ref, tried=tried)
        if v[0]: c.update(mean=v[1], worst=v[2], occP=v[3], tool='text_occlusion.py --track' + (' (crown-tracked)' if use_track else ' (static)')); return dict(c, win=win, dy=dy, ka=ka, kb=kb, tracked=use_track, ref=ref, tried=tried)
    return None

def tune(b):
    W, H = ci['W'], ci['H']
    stk0, zs, idx = stage.stack(b, ds=tbs_place.DS, step=2)
    head0 = head_of(stk0, W, H)
    cs = tbs_place.crown_series(stage, b, head0)
    ka0 = max(0, round(b['t0'] * fps) - cs['first']); kb0 = min(len(cs['raw']), round(b['t1'] * fps) - cs['first'])
    motion = tbs_place.head_motion(cs, ka0, kb0)
    MIN_OCC = TB.get('tuneMinOcclusion', 0.03)
    wins = [(b['t0'], b['t1'])]
    # fallback order (v4.3): crown-TRACKED behind -> a window of the same beat with less head motion -> skip + log (headline). Sub-windows: >= minHoldSec, lowest crown motion first
    L = max(TB.get('tbsMinHoldSec', TB.get('minHoldSec', 1.4)), 0.65 * (b['t1'] - b['t0'])); st_ = b['t0']; subs = []
    while st_ + L <= b['t1'] + 1e-6:
        a_ = max(0, round(st_ * fps) - cs['first']); z_ = min(len(cs['raw']), round((st_ + L) * fps) - cs['first']); subs.append((tbs_place.head_motion(cs, a_, z_), (round(st_, 2), round(st_ + L, 2)))); st_ += 0.25
    subs.sort(); wins += [w for _, w in subs if abs(w[0] - b['t0']) > 0.01 or abs(w[1] - b['t1']) > 0.01][:3]
    modes = [True, False] if (TB.get('trackEnabled', True) and cs['ok'] and motion >= TB.get('trackMinMotionPx', 20)) else [False]
    best = None; log_ = []
    for w in wins:
        for ut in modes:
            best = attempt(b, w, ut, cs, MIN_OCC)
            log_.append(f'{w[0]:.2f}-{w[1]:.2f}s {"tracked" if ut else "static"}: {"OK" if best else "no"}')
            if best: break
        if best: break
    if not best:
        b['fallback'] = 'headline'; b.pop('items', None); b['_readable'] = [0, 0]
        print(f'tune {b["id"]} "{b["text"]}": NO behind placement (3-10 % occluded, readable >= {TB.get("tuneMinReadable", .9):.0%} mean/worst) - head motion {motion:.0f}px; tried {" | ".join(log_)} -> SKIPPED as text-behind, becomes a plain headline', file=sys.stderr)
        b['_fallbackFrom'] = 'text-behind-speaker'; b['text'] = b['text'].upper().replace('\n', ' '); b['type'] = 'big-word'
        for k in ('y', 'h', 'maskDir', 'maskStart', 'anim', 'id', '_minOcc', 'items', 'track'): b.pop(k, None)
        return
    its = [{k: v for k, v in i.items() if k != 'y_px'} for i in best['items']]
    probs_ = tbs_place.lint_beat(dict(b, items=its, _layout=best['layout']), TB, CFG)       # v4.4 (verified.md V09/V10): complete phrase, no word dropped, line 2 below line 1
    if probs_:
        b['fallback'] = 'headline'; b.pop('items', None); b['_readable'] = [0, 0]
        print(f'tune {b["id"]} "{b["text"]}": placement rejected by the phrase lint: {"; ".join(probs_)} -> headline', file=sys.stderr)
        b['_fallbackFrom'] = 'text-behind-speaker'; b['text'] = b['text'].upper().replace('\n', ' '); b['type'] = 'big-word'
        for k in ('y', 'h', 'maskDir', 'maskStart', 'anim', 'id', '_minOcc', 'items', 'track'): b.pop(k, None)
        return
    b.pop('fallback', None)
    b['items'] = its; b['t0'], b['t1'] = round(best['win'][0], 2), round(best['win'][1], 2); b['_minOcc'] = MIN_OCC
    if best['tracked']:
        b['track'] = [round(v / H, 5) for v in best['dy']]; b['trackRef'] = round(best['ref'], 1)      # fraction of H per mask index (the component adds track[maskIndex] * H to every item's y)
    else: b.pop('track', None); b.pop('trackRef', None)
    b['y'] = min(i['y'] for i in its)
    b['_readable'] = [round(best['mean'], 3), round(best['worst'], 3)]; b['_occlusion'] = [round(1 - best['mean'], 3), round(1 - best['worst'], 3)]; b['_occlusionSpeaker'] = round(best['occP'] if best.get('occP') is not None else 1 - best['mean'], 3)
    b['phrase'] = ' '.join(tbs_place.phrase_words(b['text'])); n_lines_ = sum(i['text'].count('\n') + 1 for i in its)
    if n_lines_ > 1: b['_wrap'] = dict(lines=n_lines_, layout=best['layout'], words=[i['text'].replace('\n', ' / ') for i in its], reason='the phrase did not fit one line behind the crown within the 3-10 % / 70 % glyph rules -> wrapped onto line 2 (no word dropped)')
    else: b.pop('_wrap', None)
    b['_glyphMin'] = round(best.get('glyphMin', 1.0), 3); b['_glyphWorst'] = best.get('glyphWorst'); b['_layout'] = best['layout']; b['_tool'] = best['tool']; b['_tracked'] = bool(best['tracked']); b['_headMotionPx'] = round(motion)
    print(f'tune {b["id"]} "{" / ".join(i["text"].replace(chr(10), "|") for i in its)}": {best["layout"]}{" (Render suggest)" if best.get("suggested") else ""} {"CROWN-TRACKED" if best["tracked"] else "static"} window {b["t0"]}-{b["t1"]}s size {its[0]["size"]:.3f}W readable mean {best["mean"]:.3f} worst {best["worst"]:.3f}, min glyph visible {best.get("glyphMin", 1):.3f}, behind (speaker alone) {b["_occlusionSpeaker"]:.3f} [{best["tool"]}] (head motion {motion:.0f}px)', file=sys.stderr)
for b in todo:
    tune(b)
for b in todo:
    if b.get('items'):
        for fn in tbs_place.export_tracks(d, b, stage): print(f'track exported: {fn}', file=sys.stderr)
json.dump(data, open(bp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
bad = [b for b in todo if b.get('fallback')]
print(f'masks ready for {len(todo)} beat(s); {len(bad)} fell back to a headline (nothing in the empty background reached the readability threshold)')
