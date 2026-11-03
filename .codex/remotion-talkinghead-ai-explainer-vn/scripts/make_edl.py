#!/usr/bin/env python3
"""
HIGHLIGHT + TIGHTEN stage.  raw footage + transcript  ->  edl.json (+ captions.json, beats.suggested.json, edl_report.md)

  python3 scripts/make_edl.py --words public/project/words.json [--raw public/project/raw.mp4] [--out public/project]

Refuses to run unless public/project/probe.json exists and says gate=passed (see scripts/probe_video.py).
All thresholds / weights / keywords come from style.config.json -> tighten.*  (the reference's pacing is in framing.* and cuts.targetPacing).

Pipeline
  1 silencedetect (ffmpeg) + 100 ms RMS energy of the raw audio
  2 words -> phrases (break at pauses >= caption.pageRules.breakOnGapSec or at transcript segment ends)
  3 fillers trimmed / filler-only phrases dropped; repeat takes (similar text) -> keep the LAST take
  4 rubric score 0..1 per phrase (hookiness, information, energy, clarity, emotion, novelty, payoff; weights in config)
  5 keep / drop by thresholds, with continuity rule; then clamp to the soft target window (never padded, never forced to raw length)
  6 jump-cut pads, merge tiny gaps, split too-long segments at the biggest internal pause
  7 optional HOOK REORDER: the best short phrase (score >= hookAbove) is moved to the front
  8 framing cycle (wide/mid/tight) assigned per segment from framing.* ; captions paged by caption.pageRules
Output length = sum(kept segments) / speed. It is a RESULT, not an input.
"""
import argparse, difflib, json, math, os, re, subprocess, sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, 'style.config.json')))
T = CFG['tighten']; PR = CFG['caption']['pageRules']; FR = CFG['framing']


def die(msg):
    print('ERROR:', msg, file=sys.stderr); sys.exit(2)


def load_probe(out):
    p = os.path.join(out, 'probe.json')
    if not os.path.exists(p):
        die(f'{p} not found. STEP 0 is mandatory: python3 scripts/probe_video.py <raw video>  (no editing before the probe exists)')
    probe = json.load(open(p))
    if probe.get('gate') != 'passed':
        die('probe.json does not carry gate=passed. Re-run scripts/probe_video.py.')
    if probe.get('needsNormalize'):
        die('probe says the raw still needs normalising (rotation/SAR/VFR). Re-run probe_video.py without --no-normalize.')
    return probe


def norm(s):
    return re.sub(r'[^\wÀ-ỹ ]+', '', s.lower()).strip()


# ---------- audio analysis ----------
def silences(raw):
    n, d = T['silence']['noiseDb'], T['silence']['minSilenceSec']
    r = subprocess.run(['ffmpeg', '-v', 'info', '-i', raw, '-af', f'silencedetect=n={n}dB:d={d}', '-f', 'null', '-'], capture_output=True, text=True)
    st = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', r.stderr)]
    en = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', r.stderr)]
    return list(zip(st, en + [float('inf')] * (len(st) - len(en))))


def energy_curve(raw):
    """RMS per 100 ms (0..1). Needs numpy; falls back to a flat curve."""
    try:
        import numpy as np
    except ImportError:
        print('numpy missing -> energy feature disabled (pip install numpy)'); return None
    pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', raw, '-ac', '1', '-ar', '8000', '-f', 's16le', '-'], capture_output=True).stdout
    a = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768
    hop = 800
    n = len(a) // hop
    if n == 0:
        return None
    rms = np.sqrt((a[: n * hop].reshape(n, hop) ** 2).mean(1))
    return rms.tolist()


def window_energy(curve, t0, t1):
    if not curve:
        return 0.5
    i0, i1 = int(t0 * 10), max(int(t1 * 10), int(t0 * 10) + 1)
    seg = curve[i0:i1] or [0]
    return sum(seg) / len(seg)


# ---------- transcript -> phrases ----------
def phrases_from(words_json):
    ws = []
    for seg in words_json:
        for w in seg.get('words', []):
            ws.append(dict(w=w.get('w') or w.get('word', ''), s=w.get('s', w.get('start')), e=w.get('e', w.get('end')), p=w.get('p', 1.0), seg_end=False))
        if ws:
            ws[-1]['seg_end'] = True
    out, cur = [], []
    for w in ws:
        if cur and (w['s'] - cur[-1]['e'] >= PR['breakOnGapSec'] or cur[-1]['seg_end']):
            out.append(cur); cur = []
        cur.append(w)
    if cur:
        out.append(cur)
    # a phrase longer than 14 words is split at its LARGEST internal pause (never at an arbitrary word count)
    final = []
    for p in out:
        while len(p) > 14:
            k = max(range(5, len(p) - 4), key=lambda i: p[i]['s'] - p[i - 1]['e'])
            final.append(p[:k]); p = p[k:]
        final.append(p)
    res, sent = [], 0
    for p in final:
        ends = bool(re.search(r'[.!?…]["»”)]*$', p[-1]['w'])) or p[-1]['seg_end']
        res.append(dict(words=p, start=p[0]['s'], end=p[-1]['e'], text=' '.join(x['w'] for x in p), sent=sent, sentEnd=ends))
        if ends:
            sent += 1
    return res


def trim_fillers(ph):
    fill = set(T['fillers'])
    ws = ph['words']
    while ws and norm(ws[0]['w']) in fill:
        ws = ws[1:]
    while ws and norm(ws[-1]['w']) in fill:
        ws = ws[:-1]
    if not ws:
        return None
    ph = dict(ph); ph['words'] = ws; ph['start'], ph['end'] = ws[0]['s'], ws[-1]['e']; ph['text'] = ' '.join(x['w'] for x in ws)
    return ph


# ---------- rubric ----------
def score_phrases(phs, curve, total):
    W = T['rubric']['weights']
    hk, pk = T['rubric']['hookKeywords'], T['rubric']['payoffKeywords']
    en = [window_energy(curve, p['start'], p['end']) for p in phs]
    srt = sorted(en)
    p90 = srt[int(len(srt) * 0.9)] if srt else 1
    p90 = p90 or 1
    target_wps = CFG['cuts']['targetPacing']['wordsPerSecTarget']
    for i, p in enumerate(phs):
        t = norm(p['text']); nw = len(p['words']); dur = max(0.2, p['end'] - p['start'])
        f = {}
        f['hookiness'] = min(1, 0.55 * any(k in t for k in hk) + 0.2 * ('?' in p['text'] or '!' in p['text']) + 0.25 * (nw <= 8) + (0.1 if i < 2 else 0))
        content = [w for w in p['words'] if len(norm(w['w'])) > 3 or re.search(r'\d|[A-Z]', w['w'])]
        f['information'] = min(1, len(content) / max(1, nw) * 1.3)
        f['energy'] = min(1, en[i] / p90)
        conf = sum(w.get('p', 1.0) for w in p['words']) / nw
        wps = nw / dur
        f['clarity'] = max(0, min(1, conf * (1 - min(0.5, abs(wps - target_wps) / (target_wps * 2)))))
        f['emotion'] = min(1, 0.5 * ('!' in p['text']) + 0.5 * f['energy'] + 0.2 * any(k in t for k in ('quá', 'rất', 'cực', 'siêu', 'tuyệt', 'đỉnh')))
        sim = 0
        for q in phs[:i]:
            sim = max(sim, difflib.SequenceMatcher(None, t, norm(q['text'])).ratio())
        f['novelty'] = 1 - sim
        f['payoff'] = min(1, 0.7 * any(k in t for k in pk) + (0.3 if p['start'] > 0.85 * total else 0))
        p['features'] = {k: round(v, 3) for k, v in f.items()}
        p['score'] = round(sum(W[k] * f[k] for k in W), 3)
    return phs


def mark_repeats(phs, thr=None):
    """repeat take = a phrase followed (within 8 phrases / 25 s) by a near-identical one; the LAST take survives.
    Similarity is on WORD tokens: char-level ratios flagged 'lựa chọn thứ nhất là đi cao tốc' vs 'lựa chọn thứ hai là đi quốc lộ' as repeats."""
    thr = thr if thr is not None else T['repeat']['similarity']
    dropped = set()
    toks = [[norm(w['w']) for w in p['words'] if norm(w['w'])] for p in phs]
    for i, a in enumerate(phs):
        for j in range(i + 1, min(len(phs), i + 8)):
            if len(toks[i]) >= 3 and difflib.SequenceMatcher(None, toks[i], toks[j]).ratio() >= thr and phs[j]['start'] - a['end'] < 25:
                dropped.add(i); break
    return dropped


# ---------- main ----------
def fit_target(a):
    """v4.3 --target-sec: re-run this script with a speech budget until the kept length (incl. pads/pauses) is within tol of the target."""
    budget = a.target_sec * 0.9; best = None
    base = [sys.executable, os.path.abspath(__file__), '--words', a.words, '--out', a.out] + (['--raw', a.raw] if a.raw else []) + (['--preset', a.preset] if a.preset else []) + (['--no-hook-reorder'] if a.no_hook_reorder else [])
    for it in range(8):
        r = subprocess.run(base + ['--_budget', f'{budget:.2f}'], capture_output=True, text=True)
        if r.returncode:
            print(r.stdout + r.stderr, file=sys.stderr); return r.returncode
        kept = json.load(open(os.path.join(a.out, 'edl.json')))['stats']['keptSec']
        print(f'  --target-sec {a.target_sec:g}: iteration {it + 1} budget {budget:.1f}s -> kept {kept:.1f}s')
        if best is None or abs(kept - a.target_sec) < abs(best[0] - a.target_sec): best = (kept, budget)
        if abs(kept - a.target_sec) <= a.tol: print(r.stdout.strip().splitlines()[-1]); return 0
        budget = max(5.0, budget + (a.target_sec - kept) * 0.8)
    r = subprocess.run(base + ['--_budget', f'{best[1]:.2f}'], capture_output=True, text=True)
    print(f'WARNING: could not reach {a.target_sec:g}s +-{a.tol:g}s (best {best[0]:.1f}s: not enough usable material?)'); print(r.stdout.strip().splitlines()[-1]); return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--words', required=True); ap.add_argument('--raw', default=None); ap.add_argument('--out', default='public/project')
    ap.add_argument('--preset', choices=['light', 'normal', 'tight'], default=None, help='aggressiveness (default tighten.preset = normal: keep ~70-85 percent of the raw length)')
    ap.add_argument('--no-hook-reorder', action='store_true'); ap.add_argument('--keep-all', action='store_true', help='skip rubric dropping (only silence/filler/repeat)')
    ap.add_argument('--target-sec', type=float, default=None, help='v4.3: aim for this OUTPUT length (e.g. 60): best-scoring whole sentences are kept until the kept length is within --tol seconds (iterates internally)')
    ap.add_argument('--tol', type=float, default=2.0, help='tolerance for --target-sec (default 2s)')
    ap.add_argument('--_budget', type=float, default=None, help=argparse.SUPPRESS)
    a = ap.parse_args()
    if a.target_sec and a._budget is None:
        sys.exit(fit_target(a))
    probe = load_probe(a.out)
    PRE_NAME = a.preset or T.get('preset', 'normal'); PRE = T['presets'][PRE_NAME]
    raw = a.raw or os.path.join(a.out, '..', probe['file'].replace('project/', 'project/'))
    raw = raw if os.path.exists(raw) else os.path.join(a.out, 'raw.mp4')
    fps = probe['fps']; dur = probe['durationSec']
    words_json = json.load(open(a.words))
    try:
        from text_cleanup import reapply_glossary
        words_json, _nfix = reapply_glossary(words_json)    # glossary.txt applies before captions are built
        if _nfix: print(f'glossary: {_nfix} word(s) corrected before building captions')
    except ImportError:
        pass

    curve = energy_curve(raw) if probe['hasAudio'] and os.path.exists(raw) else None
    sil = silences(raw) if probe['hasAudio'] and os.path.exists(raw) else []

    dropped = []
    restored = []
    phs = []
    for ph in phrases_from(words_json):
        t = trim_fillers(ph)
        if t is None:
            dropped.append(dict(srcIn=round(ph['start'], 3), srcOut=round(ph['end'], 3), reason='filler', note=ph['text'])); continue
        if t['start'] - ph['start'] > 0.05:
            dropped.append(dict(srcIn=round(ph['start'], 3), srcOut=round(t['start'], 3), reason='filler', note='leading filler'))
        phs.append(t)
    score_phrases(phs, curve, dur)
    rep = mark_repeats(phs, PRE['repeatSimilarity'])

    R = dict(T['rubric'], keepAbove=PRE['keepAbove'], dropBelow=PRE['dropBelow'])
    keep = []
    for i, p in enumerate(phs):
        if i in rep:
            dropped.append(dict(srcIn=round(p['start'], 3), srcOut=round(p['end'], 3), reason='repeat-take', note=p['text'])); keep.append(False); continue
        keep.append(a.keep_all or p['score'] >= R['keepAbove'])
    # continuity: borderline phrases survive when both neighbours survive
    for i, p in enumerate(phs):
        if not keep[i] and i not in rep and p['score'] >= R['dropBelow'] and 0 < i < len(phs) - 1 and keep[i - 1] and keep[i + 1]:
            keep[i] = True
    # SENTENCE RULE: never cut mid-sentence. A sentence is kept when >= 50% of its (non-repeat) words were kept.
    by_sent = defaultdict(list)
    for i, p in enumerate(phs):
        if i not in rep:
            by_sent[p['sent']].append(i)
    for sid, idxs in by_sent.items():
        tot = sum(len(phs[i]['words']) for i in idxs); kp = sum(len(phs[i]['words']) for i in idxs if keep[i])
        decision = kp * 2 >= tot
        for i in idxs:
            keep[i] = decision
    # RETENTION FLOOR: whole sentences (never mid-sentence) are put back, best score first, until kept speech >= preset retention[0] of the raw length
    rmin, rmax = PRE['retention']
    if a._budget:
        # v4.3 --target-sec: keep the best whole sentences (duration-weighted mean score) until the speech budget is used up
        sc_ = {sid: sum(phs[i]['score'] * (phs[i]['end'] - phs[i]['start']) for i in idxs) / max(1e-6, sum(phs[i]['end'] - phs[i]['start'] for i in idxs)) for sid, idxs in by_sent.items()}
        # concept bonus: sentences that SAY an illustration concept (customer-talk, sales, money, ...) win over equally-scored filler, so the cut has material for >= 4 icons
        _cb = CFG.get('tighten', {}).get('conceptBonus', 0.35); _cons = CFG.get('autoBeats', {}).get('illustration', {}).get('concepts', [])
        _nrm = lambda x: x.lower()
        for sid, idxs in by_sent.items():
            _t = _nrm(' '.join(phs[i]['text'] for i in idxs)); _n = sum(1 for c in _cons if any(_nrm(k_) in _t for k_ in c.get('keywords', [])))
            sc_[sid] += _cb * min(3, _n)
        keep = [False] * len(phs); used = 0.0
        for sid in sorted(sc_, key=lambda k: -sc_[k]):
            span = sum(phs[i]['end'] - phs[i]['start'] for i in by_sent[sid])
            if used + span > a._budget and used > 0:
                continue
            for i in by_sent[sid]: keep[i] = True
            used += span
    if not a.keep_all and not a._budget:
        spans = lambda idxs: sum(phs[i]['end'] - phs[i]['start'] for i in idxs)
        kept_sec = spans([i for i in range(len(phs)) if keep[i]])
        cand = sorted(((max(phs[i]['score'] for i in idxs), sid, idxs) for sid, idxs in by_sent.items() if not any(keep[i] for i in idxs)), key=lambda x: -x[0])
        for sc, sid, idxs in cand:
            if kept_sec >= rmin * dur:
                break
            for i in idxs:
                keep[i] = True
            kept_sec += spans(idxs)
            restored.append((sid, round(sc, 2)))
    for i, p in enumerate(phs):
        if not keep[i] and i not in rep:
            low_energy = p['features']['energy'] < 0.25
            dropped.append(dict(srcIn=round(p['start'], 3), srcOut=round(p['end'], 3), reason='low-energy' if low_energy else 'off-topic', note=f"score {p['score']} {p['text']}"))
    kept = [p for i, p in enumerate(phs) if keep[i]]
    if not kept:
        die('rubric dropped everything - lower tighten.rubric.keepAbove in style.config.json or use --keep-all')

    # soft target window
    tgt = T['target']; maxsec = min(tgt['maxSec'], dur * rmax)
    if a._budget: maxsec = 1e9   # budget already bounds the length
    total = sum(p['end'] - p['start'] for p in kept)
    while total > maxsec and len(kept) > 3:
        w = min(range(len(kept)), key=lambda i: kept[i]['score'])
        sid = kept[w]['sent']
        for p in [q for q in kept if q['sent'] == sid]:
            kept.remove(p); total -= p['end'] - p['start']
            dropped.append(dict(srcIn=round(p['start'], 3), srcOut=round(p['end'], 3), reason='over-window', note=f"over {PRE_NAME} retention window ({maxsec:.0f}s), score {p['score']}"))

    # jump-cut segments
    J = T['jumpCut']
    allw = sorted((w for ph in phs for w in ph['words']), key=lambda w: w['s'])
    def pad_in(t):   # never reach back into the previous word
        prev = [w['e'] for w in allw if w['e'] <= t + 1e-6 and w['s'] < t - 1e-6]
        return max(0, t - J['padInSec'], (prev[-1] + 0.02) if prev and prev[-1] < t else 0)
    def pad_out(t):  # never reach into the next word
        nxt = [w['s'] for w in allw if w['s'] >= t - 1e-6 and w['e'] > t + 1e-6]
        return min(dur, t + J['padOutSec'], (nxt[0] - 0.02) if nxt and nxt[0] > t else dur)
    segs = []
    for p in kept:
        s, e = pad_in(p['start']), pad_out(p['end'])
        if segs and s - segs[-1]['srcOut'] <= J['mergeGapSec']:
            segs[-1]['srcOut'] = e; segs[-1]['phr'].append(p)
        else:
            segs.append(dict(srcIn=s, srcOut=e, phr=[p]))
    # too long -> split at biggest internal gap
    out = []
    for sg in segs:
        stack = [sg]
        while stack:
            c = stack.pop(0)
            if c['srcOut'] - c['srcIn'] <= J['maxSegmentSec'] or len(c['phr']) < 2:
                out.append(c); continue
            gaps = [(c['phr'][i + 1]['start'] - c['phr'][i]['end'], i) for i in range(len(c['phr']) - 1)]
            sent_gaps = [g for g in gaps if c['phr'][g[1]]['sentEnd']]   # prefer a SENTENCE boundary, else the biggest pause
            _, k = max(sent_gaps or gaps)
            L = dict(srcIn=c['srcIn'], srcOut=pad_out(c['phr'][k]['end']), phr=c['phr'][: k + 1])
            R2 = dict(srcIn=pad_in(c['phr'][k + 1]['start']), srcOut=c['srcOut'], phr=c['phr'][k + 1:])
            stack = [L, R2] + stack
    segs = out
    # too short -> merge into the neighbour
    i = 0
    while i < len(segs):
        if segs[i]['srcOut'] - segs[i]['srcIn'] < J['minSegmentSec'] and len(segs) > 1:
            j = i + 1 if i + 1 < len(segs) else i - 1
            lo, hi = sorted((i, j))
            segs[lo] = dict(srcIn=segs[lo]['srcIn'], srcOut=segs[hi]['srcOut'], phr=segs[lo]['phr'] + segs[hi]['phr'])
            del segs[hi]; i = 0; continue
        i += 1

    # hook reorder
    H = T['hook']
    for sg in segs:
        sg['score'] = max(p['score'] for p in sg['phr'])
    hook_idx = 0
    if H['allowReorder'] and not a.no_hook_reorder:
        cands = [(p['score'], si, p) for si, sg in enumerate(segs) for p in sg['phr'] if p['score'] >= H['minHookScore'] and (p['end'] - p['start']) <= H['maxHookSec'] and p['features']['hookiness'] >= 0.5 and p['sentEnd'] and sum(1 for q in phs if q['sent'] == p['sent']) == 1]
        if cands:
            _, si, hp = max(cands, key=lambda x: x[0])
            if si != 0 or segs[0]['phr'][0] is not hp:
                new = dict(srcIn=pad_in(hp['start']), srcOut=pad_out(hp['end']), phr=[hp], score=hp['score'], reorderedHook=True)
                if not H['repeatHookInBody']:
                    host = segs[si]
                    # cut the hook phrase out of its original segment (split into before/after)
                    before = [p for p in host['phr'] if p['end'] <= hp['start']]
                    after = [p for p in host['phr'] if p['start'] >= hp['end']]
                    repl = []
                    if before: repl.append(dict(srcIn=host['srcIn'], srcOut=pad_out(before[-1]['end']), phr=before, score=max(p['score'] for p in before)))
                    if after: repl.append(dict(srcIn=pad_in(after[0]['start']), srcOut=host['srcOut'], phr=after, score=max(p['score'] for p in after)))
                    segs[si:si + 1] = repl
                segs.insert(0, new)

    # GUARANTEE: no two segments share raw time. Neighbouring pads are clipped to the midpoint of the gap between the words; a segment that
    # became shorter than minSegmentSec after clipping is merged into its source-order neighbour.
    segs = [sg for sg in segs if sg['srcOut'] > sg['srcIn']]
    order = sorted(range(len(segs)), key=lambda i: segs[i]['srcIn'])
    for a_, b_ in zip(order, order[1:]):
        A, Bq = segs[a_], segs[b_]
        if A['srcOut'] > Bq['srcIn'] - 1e-6:
            if A['phr'] and Bq['phr']:
                lo, hi = A['phr'][-1]['end'], Bq['phr'][0]['start']
                mid = (lo + hi) / 2 if hi >= lo else Bq['srcIn']
            else:
                mid = (A['srcOut'] + Bq['srcIn']) / 2
            A['srcOut'] = min(A['srcOut'], mid); Bq['srcIn'] = max(Bq['srcIn'], A['srcOut'])
    for i_, (x, y) in enumerate(zip(sorted(segs, key=lambda q: q['srcIn']), sorted(segs, key=lambda q: q['srcIn'])[1:])):
        assert x['srcOut'] <= y['srcIn'] + 1e-6, f"overlap {x['srcOut']} > {y['srcIn']}"
    # roles, framing, ids
    cycle = FR['cycle']; ci = 0; since = 0.0; edl_segs = []
    for n, sg in enumerate(segs):
        d = sg['srcOut'] - sg['srcIn']
        framing_changed = False
        if n > 0 and since >= FR['framingChangeEverySec'][0]:
            ci = (ci + 1) % len(cycle); since = 0.0; framing_changed = True
        since += d
        texts = ' '.join(p['text'] for p in sg['phr']); tn = norm(texts)
        role = 'hook' if n == 0 else 'cta' if (n == len(segs) - 1 and any(k in tn for k in T['rubric']['payoffKeywords'])) else 'payoff' if any(k in tn for k in T['rubric']['payoffKeywords']) else 'body'
        labels = [k for k, v in max(sg['phr'], key=lambda p: p['score'])['features'].items() if v >= 0.6]
        edl_segs.append(dict(id=f's{n:02d}', srcIn=round(sg['srcIn'], 3), srcOut=round(sg['srcOut'], 3), role=role,
                             reason=('reordered hook; ' if sg.get('reorderedHook') else '') + (', '.join(labels) or 'continuity'), score=round(sg['score'], 3),
                             framing=cycle[ci], punch=bool(framing_changed or n == 0 and cycle[ci] != 'wide'), transitionIn='cut'))
    # ---- PACING: visual cut / punch-in points INSIDE long kept segments (no speech is dropped; the source stays contiguous) ----
    cap_segs = [dict(x) for x in edl_segs]                  # captions are built on the speech segments (a caption page may then span a visual cut: that is fine, source time is continuous)
    VC = FR.get('visualCuts', {})
    n_visual = 0
    if VC.get('enabled', True):
        kw = sorted((w for p_ in kept for w in p_['words']), key=lambda w: w['s'])
        final_segs = []
        for sg in edl_segs:
            d = sg['srcOut'] - sg['srcIn']
            if d <= VC['triggerSec']:
                final_segs.append(sg); continue
            inner = [w for w in kw if sg['srcIn'] + 0.05 <= w['s'] and w['e'] <= sg['srcOut'] + 0.05]
            cands = []                                      # (time, quality): a word boundary, better when it is a pause / phrase end / punctuation
            for a_, b_ in zip(inner, inner[1:]):
                gap = b_['s'] - a_['e']
                q = min(gap, 0.5) * 2 + (1.0 if re.search(r'[,;.!?…]$', a_['w']) else 0) + (0.6 if a_.get('_pe') else 0) - (0.8 if norm(b_['w']) in {norm(x) for x in PR.get('functionWordsStartLine', [])} and False else 0)
                cands.append((round((a_['e'] + b_['s']) / 2, 3), q))
            n_pieces = max(2, round(d / VC['everySec']))
            cuts, last = [], sg['srcIn']
            for k in range(1, n_pieces):
                ideal = sg['srcIn'] + d * k / n_pieces
                ok = [c for c in cands if abs(c[0] - ideal) <= VC['searchSec'] and c[0] - last >= VC['minPieceSec'] and sg['srcOut'] - c[0] >= VC['minPieceSec']]
                if not ok: continue
                best = max(ok, key=lambda c: (c[1] - abs(c[0] - ideal) * 0.8, -abs(c[0] - ideal)))
                cuts.append(best[0]); last = best[0]
            if not cuts:
                final_segs.append(sg); continue
            edges = [sg['srcIn']] + cuts + [sg['srcOut']]
            for k in range(len(edges) - 1):
                piece = dict(sg, srcIn=round(edges[k], 3), srcOut=round(edges[k + 1], 3))
                if k > 0:
                    piece.update(role='body' if sg['role'] != 'cta' else 'cta', reason=sg['reason'] + '; visual cut at a word boundary (pacing)', visualCut=True, transitionIn='cut', punch=True)
                    n_visual += 1
                final_segs.append(piece)
        prev = None
        for sg in final_segs:                               # framing must change at every visual cut (that is the whole point), following the reference cycle
            if prev is not None and sg['framing'] == prev['framing']:
                start = cycle.index(prev['framing']) if prev['framing'] in cycle else 0
                sg['framing'] = next((cycle[(start + j) % len(cycle)] for j in range(1, len(cycle) + 1) if cycle[(start + j) % len(cycle)] != prev['framing']), 'mid')
                sg['punch'] = True
            prev = sg
        for n_, sg in enumerate(final_segs):
            sg['id'] = f's{n_:02d}'
        edl_segs = final_segs
    # silence stats
    cut_sil = sum(min(e, dur) - s for s, e in sil)
    total_out = sum(s['srcOut'] - s['srcIn'] for s in edl_segs)
    edl = dict(version=1, source=dict(file=probe['file'], fps=fps, durationSec=dur), target=dict(minSec=tgt['minSec'], maxSec=round(maxsec, 1), ratio=round(total_out / dur, 3), preset=PRE_NAME, retention=PRE['retention'], restoredSentences=len(restored), speechRetention=round(sum(p['end'] - p['start'] for p in kept) / dur, 3)),
               segments=edl_segs, dropped=sorted(dropped, key=lambda d: d['srcIn']),
               stats=dict(rawSec=dur, keptSec=round(total_out, 2), segments=len(edl_segs), speechSegments=len(cap_segs), visualCuts=n_visual, avgShotSec=round(total_out / len(edl_segs), 2), silenceSecDetected=round(cut_sil, 2),
                          wordsPerSec=round(sum(len(p['words']) for p in kept) / max(1, total_out), 2),
                          referenceAvgShotSec=CFG['cuts']['targetPacing']['avgShotSec']))
    os.makedirs(a.out, exist_ok=True)
    json.dump(edl, open(os.path.join(a.out, 'edl.json'), 'w'), indent=2, ensure_ascii=False)

    # captions (source time, per kept segment, never across a cut)
    pages = []
    first = True
    skip = set(T['fillers'])
    DANGLING = {'các', 'những', 'một', 'cái', 'của', 'và', 'là', 'thì', 'mà', 'với', 'để', 'cho', 'ở', 'trong', 'khi', 'nếu', 'vì'}   # a whisper segment ending on these is mid-phrase: do not break the caption there
    FW = {norm(x) for x in PR.get('functionWordsStartLine', [])}
    MINW, MAXW, MAXC = PR.get('minWordsPerLine', 2), PR['maxWordsPerLine'], PR['maxCharsPerLine']
    gap_break = PR.get('breakOnGapSec', 0.25)
    MERGE_GAP = PR.get('mergeGapMaxSec', 0.6)          # NEVER merge two chunks/pages separated by a longer silence
    CHUNK_MAX = PR.get('chunkMaxSec', PR['maxPageSec'])  # ... or into something longer than this

    def can_join(A, B):
        return 0 <= B[0]['s'] - A[-1]['e'] <= MERGE_GAP and B[-1]['e'] - A[0]['s'] <= CHUNK_MAX

    def natural_chunks(ws):
        ch, cur = [], []
        for k, w in enumerate(ws):
            cur.append(w)
            end_punct = bool(re.search(r'[,;.!?…]$', w['w'])) or (bool(w.get('_pe')) and norm(w['w']) not in DANGLING)
            gap = (ws[k + 1]['s'] - w['e']) if k + 1 < len(ws) else 9
            if end_punct or gap >= gap_break:
                ch.append(cur); cur = []
        if cur: ch.append(cur)
        # merge chunks shorter than MINW words into a neighbour (prefer the next; the last one joins the previous) while the result stays <= 2 lines
        cap_w = MAXW * PR['maxLinesPerPage']
        k = 0
        while k < len(ch):
            if len(ch[k]) < MINW and len(ch) > 1:
                j = k + 1 if k + 1 < len(ch) else k - 1
                lo, hi = sorted((k, j))
                if len(ch[lo]) + len(ch[hi]) <= cap_w and can_join(ch[lo], ch[hi]):
                    ch[lo] = ch[lo] + ch[hi]; del ch[hi]; k = 0; continue
            k += 1
        return ch

    def split_lines(ch):
        """balanced lines of MINW..MAXW words (and <= MAXC chars); the break prefers to sit BEFORE a function word (và / thì / là / của ...)"""
        n = len(ch)
        if n <= MAXW and len(' '.join(x['w'] for x in ch)) <= MAXC:
            return [ch]
        k = max(math.ceil(n / MAXW), math.ceil(len(' '.join(x['w'] for x in ch)) / MAXC))
        k = min(k, max(1, n // MINW))
        lines, i0 = [], 0
        for li in range(k):
            left = k - li
            if left == 1:
                lines.append(ch[i0:]); break
            ideal = i0 + round((n - i0) / left)
            lo, hi = max(i0 + MINW, ideal - 1), min(n - MINW * (left - 1), ideal + 1, i0 + MAXW)
            opts = [c for c in range(lo, hi + 1) if len(' '.join(x['w'] for x in ch[i0:c])) <= MAXC] or [max(i0 + 1, min(ideal, i0 + MAXW))]
            c = next((c for c in sorted(opts, key=lambda c: abs(c - ideal)) if c < n and norm(ch[c]['w']) in FW), min(opts, key=lambda c: abs(c - ideal)))
            lines.append(ch[i0:c]); i0 = c
        return [l for l in lines if l]

    for p_ in kept:
        if p_['words']:
            p_['words'][-1]['_pe'] = True                  # phrase end = natural caption boundary (pause or whisper segment end)
    for sg in cap_segs:
        ws = [w for p in kept for w in p['words'] if w['s'] >= sg['srcIn'] - 0.05 and w['e'] <= sg['srcOut'] + 0.05 and norm(w['w']) not in skip]
        pgs = []                                             # each page = list of lines (word lists)
        for ch in natural_chunks(ws):
            ls = split_lines(ch)
            cur, cur_t = [], None
            for ln in ls:
                if len(cur) >= PR['maxLinesPerPage'] or (cur and ln[-1]['e'] - cur[0][0]['s'] > PR['maxPageSec']):
                    pgs.append(cur); cur = []
                cur.append(ln)
            if cur: pgs.append(cur)
        # a page that is a single 1-word line merges into its neighbour's last line (no orphan words)
        k = 0
        while k < len(pgs):
            j = (k - 1 if k > 0 else k + 1) if len(pgs) > 1 else k
            if len(pgs[k]) == 1 and len(pgs[k][0]) < MINW and len(pgs) > 1 and can_join(*((pgs[j][-1], pgs[k][0]) if j < k else (pgs[k][0], pgs[j][0]))):
                tgt_p = pgs[j]
                if j < k: tgt_p[-1] = tgt_p[-1] + pgs[k][0]
                else: tgt_p[0] = pgs[k][0] + tgt_p[0]
                del pgs[k]; k = 0; continue
            k += 1
        # list-like runs ('Dầu Dây, / Phan Thiết,'): two tiny single-line pages in a row become one 2-line page
        k = 0
        while k + 1 < len(pgs):
            A_, B_ = pgs[k], pgs[k + 1]
            if len(A_) == 1 and len(B_) == 1 and A_[0][-1]['e'] - A_[0][0]['s'] < PR['minPageSec'] and B_[0][0]['s'] - A_[0][-1]['e'] < 0.35 and len(A_[0]) + len(B_[0]) <= 2 * MAXW:
                pgs[k] = [A_[0], B_[0]]; del pgs[k + 1]
            else:
                k += 1
        for pi, lines in enumerate(pgs):
            t0, t1 = lines[0][0]['s'], lines[-1][-1]['e']
            if t1 - t0 < PR['minPageSec'] and pi + 1 < len(pgs):
                t1 = min(t0 + PR['minPageSec'], pgs[pi + 1][0][0]['s'])
            t1 = max(t1, lines[-1][-1]['e']) if pi + 1 >= len(pgs) else max(t1, min(lines[-1][-1]['e'], pgs[pi + 1][0][0]['s']))
            kw = any(k in norm(' '.join(w['w'] for l in lines for w in l)) for k in T['rubric']['hookKeywords'])
            size = 'hero' if first else 'normal'
            styled = []
            for li, ln in enumerate(lines):
                st = PR['line1Style'] if li == 0 else PR['line2Style']
                if len(lines) == 1:
                    st = 'pill' if (first or (kw and PR['pillStyleForKeyword'])) else 'white'
                styled.append(dict(style=st, t0=round(ln[0]['s'], 3), words=[dict(w=w['w'], t0=round(w['s'], 3), t1=round(w['e'], 3)) for w in ln]))
            pages.append(dict(t0=round(t0, 3), t1=round(min(t1, sg['srcOut']), 3), lines=styled, size=size))
            first = False
    json.dump(pages, open(os.path.join(a.out, 'captions.json'), 'w'), indent=2, ensure_ascii=False)

    # beat suggestions (NOT applied automatically: the editor/agent confirms against the transcript)
    sug = [dict(type='stars', t0=edl_segs[0]['srcIn'], t1=min(edl_segs[0]['srcOut'], edl_segs[0]['srcIn'] + 1.5))]
    for sg in edl_segs:
        if sg['role'] == 'cta':
            sug.append(dict(type='comment-box', t0=max(sg['srcIn'], sg['srcOut'] - 2.0), t1=sg['srcOut'], typed='tham khảo', bubble='tham khảo'))
    json.dump(dict(beats=sug, captionAnchor=[]), open(os.path.join(a.out, 'beats.suggested.json'), 'w'), indent=2, ensure_ascii=False)

    rep = ['# EDL report', '', f"raw {dur:.1f}s -> kept {total_out:.1f}s ({total_out / dur:.0%} incl. pauses/pads, spoken phrases {sum(p['end'] - p['start'] for p in kept) / dur:.0%}; preset {PRE_NAME}, target {PRE['retention'][0]:.0%}-{PRE['retention'][1]:.0%}), {len(edl_segs)} segments, avg {total_out / len(edl_segs):.1f}s (reference avg {CFG['cuts']['targetPacing']['avgShotSec']}s)", '',
           '| seg | src in-out | role | framing | score | why |', '|---|---|---|---|---|---|']
    rep += [f"| {s['id']} | {s['srcIn']:.2f}-{s['srcOut']:.2f} | {s['role']} | {s['framing']} | {s['score']} | {s['reason']} |" for s in edl_segs]
    rep += ['', '## Dropped', '| src in-out | reason | note |', '|---|---|---|'] + [f"| {d['srcIn']:.2f}-{d['srcOut']:.2f} | {d['reason']} | {d.get('note', '')[:70]} |" for d in edl['dropped']]
    open(os.path.join(a.out, 'edl_report.md'), 'w').write('\n'.join(rep))
    print(f"OK edl.json [{PRE_NAME}]: kept {total_out:.1f}s of {dur:.1f}s in {len(edl_segs)} segments; {len(pages)} caption pages; report -> {a.out}/edl_report.md")


if __name__ == '__main__':
    main()
