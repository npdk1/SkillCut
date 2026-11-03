#!/usr/bin/env python3
"""Vietnamese key-phrase extraction for on-screen titles (used by make_beats.py).

Transcript tokens are SYLLABLES ("trình", "bày"), so cutting "bày một vấn" out of a sentence looks like a bug on screen.
This module groups syllables into WORDS (pyvi `ViTokenizer` when installed:  pip install pyvi ; otherwise a built-in
compound list from style.config.json -> autoBeats.phrases.compounds) and returns only COMPLETE phrases:
  - start and end on a content word (never nói / rằng / là / thì / mà / cái / một ... or a light verb such as làm / có / được)
  - no stop word inside (only `link` words once, `droppable` classifiers are skipped in the displayed text)
  - never crosses punctuation or a pause > pauseSec, every syllable ASR p >= minP
  - minWords..maxWords syllables (default 2..5), <= maxChars
No candidate -> the caller must create no beat.
"""
import re, unicodedata

def strict(s):
    """lower-case NFC without punctuation - diacritics are KEPT ('nhất' != 'nhật')."""
    return unicodedata.normalize('NFC', re.sub(r'[^\w]', '', s.lower()))

_vit = None
def _pyvi():
    global _vit
    if _vit is None:
        try:
            from pyvi import ViTokenizer
            _vit = ViTokenizer
        except Exception:
            _vit = False
    return _vit or None

def segmenter_name():
    return 'pyvi' if _pyvi() else 'builtin-compounds (pip install pyvi for better word segmentation)'

def _units_from_groups(words, groups, pause):
    out = []; k = 0
    for g in groups:
        ws = words[k:k + g]; k += g
        prev = words[k - g - 1] if k - g - 1 >= 0 else None
        brk = prev is None or bool(re.search(r'[,.;:!?…]$', prev['w'])) or (ws[0]['s'] - prev['e'] > pause)
        out.append(dict(ws=ws, s=ws[0]['s'], e=ws[-1]['e'], syl=[strict(w['w']) for w in ws], brk=brk,
                        punct=bool(re.search(r'[,.;:!?…]$', ws[-1]['w'])), p=min(w.get('p', 1.0) for w in ws),
                        raw=' '.join(re.sub(r'^[\W_]+|[\W_]+$', '', w['w']) for w in ws)))
    return out

def to_units(words, compounds=(), pause=0.45):
    """consecutive syllable-words (one sentence) -> word units"""
    if not words: return []
    clean = [re.sub(r'^[\W_]+|[\W_]+$', '', w['w']) or w['w'] for w in words]
    groups = None
    vt = _pyvi()
    if vt and all(' ' not in c for c in clean):
        try:
            toks = vt.tokenize(' '.join(clean)).split()
            g = [len(t.split('_')) for t in toks]
            flat = [x for t in toks for x in t.split('_')]
            if sum(g) == len(clean) and [strict(x) for x in flat] == [strict(c) for c in clean]:
                groups = g
        except Exception:
            groups = None
    if groups is None: groups = [1] * len(words)
    comp = {tuple(strict(x) for x in c.split()) for c in compounds}
    maxn = max((len(c) for c in comp), default=1)
    # merge adjacent single groups that form a listed compound (works with/without pyvi)
    syl = [strict(c) for c in clean]
    merged = []; k = 0; gi = 0
    starts = []
    for g in groups: starts.append(k); k += g
    i = 0
    while i < len(groups):
        done = False
        if groups[i] == 1:
            for n in range(maxn, 1, -1):
                if i + n <= len(groups) and all(groups[i + j] == 1 for j in range(n)) and tuple(syl[starts[i + j]] for j in range(n)) in comp:
                    merged.append(n); i += n; done = True; break
        if not done: merged.append(groups[i]); i += 1
    return _units_from_groups(words, merged, pause)

class Phraser:
    def __init__(self, cfg):
        self.c = cfg
        self.stop = {strict(x) for x in cfg['stop']}
        self.light = {strict(x) for x in cfg['light']}
        self.link = {strict(x) for x in cfg['link']}
        self.drop = {strict(x) for x in cfg['droppable']}
        self.neg = {strict(x) for x in cfg.get('negators', [])}   # a phrase directly after one of these keeps it ('không tốn thêm token' must not become 'Tốn thêm token')
        self.noend = {strict(x) for x in cfg.get('noEnd', [])}   # verbs/auxiliaries that need an object: a phrase must not END on them ('Hệ thống gây')
        self.comp = cfg.get('compounds', [])
        self.minW, self.maxW = cfg.get('minWords', 2), cfg.get('maxWords', 5)
        self.maxChars, self.minP, self.pause = cfg.get('maxChars', 26), cfg.get('minP', 0.6), cfg.get('pauseSec', 0.45)

    def units(self, words): return to_units(words, self.comp, self.pause)
    def is_stop(self, u): return all(s in self.stop for s in u['syl'])
    def is_light(self, u): return all(s in self.light for s in u['syl'])
    def is_drop(self, u): return len(u['syl']) == 1 and u['syl'][0] in self.drop
    def is_link(self, u): return len(u['syl']) == 1 and u['syl'][0] in self.link
    def content(self, u):
        if self.is_stop(u) or self.is_light(u) or self.is_drop(u): return False
        if u['p'] < self.minP: return False
        raw = u['raw']
        return len(re.sub(r'[^\w]', '', raw)) >= 2 or raw.isdigit()

    def candidates(self, units, t_lo=-1e9, t_hi=1e9, max_words=None, max_chars=None):
        """all complete phrases inside units (list from units()), best-first by (score desc, start asc)"""
        maxW = max_words or self.maxW; maxC = max_chars or self.maxChars
        n = len(units); res = []
        for i in range(n):
            if not self.content(units[i]) or units[i]['s'] < t_lo: continue
            nsyl = 0; links = 0
            for j in range(i, n):
                u = units[j]
                if j > i and (u['brk'] or units[j - 1]['punct']): break
                if u['e'] > t_hi: break
                nsyl += len(u['syl'])
                if nsyl > maxW + 2: break
                if j > i:
                    if self.is_link(u): links += 1
                    if links > 1: break
                    if not (self.content(u) or self.is_drop(u) or self.is_link(u)): break
                if not self.content(u): continue            # end unit must be content
                if u['syl'][-1] in self.noend and not (j == n - 1 or u['punct']): continue
                shown = [x for x in units[i:j + 1] if not (self.is_drop(x) and x is not units[i])]
                syl_shown = sum(len(x['syl']) for x in shown)
                text = ' '.join(x['raw'] for x in shown)
                if i > 0 and not units[i]['brk'] and not units[i - 1]['punct'] and len(units[i - 1]['syl']) == 1 and units[i - 1]['syl'][0] in self.neg and len(text) + len(units[i - 1]['raw']) + 1 <= maxC + 6:
                    text = units[i - 1]['raw'] + ' ' + text
                if syl_shown < self.minW or syl_shown > maxW or len(text) > maxC: continue
                left_ok = i == 0 or units[i]['brk'] or units[i - 1]['punct'] or not self.content(units[i - 1])
                right_ok = j == n - 1 or units[j]['punct'] or units[j + 1]['brk'] or not (self.content(units[j + 1]) or self.is_drop(units[j + 1]) or self.is_link(units[j + 1]))
                score = min(syl_shown, 4) + (0.8 if left_ok and right_ok else 0) + (0.2 if left_ok else 0) - 0.4 * links
                res.append(dict(score=score, i=i, j=j, text=text[:1].upper() + text[1:], s=units[i]['s'], e=units[j]['e'], words=syl_shown))
        res.sort(key=lambda r: (-r['score'], r['s']))
        return res

    def best(self, units, **kw):
        c = self.candidates(units, **kw)
        return c[0] if c else None

    def pick_many(self, units, k, t_lo=-1e9, t_hi=1e9, min_gap=0.5, **kw):
        """up to k non-overlapping phrases, returned in time order"""
        chosen = []
        for c in self.candidates(units, t_lo, t_hi, **kw):
            if any(not (c['e'] <= x['s'] - 0.05 or c['s'] >= x['e'] + 0.05) or abs(c['s'] - x['s']) < min_gap for x in chosen): continue
            if any(re.sub(r'\W', '', c['text'].lower()) in re.sub(r'\W', '', x['text'].lower()) or re.sub(r'\W', '', x['text'].lower()) in re.sub(r'\W', '', c['text'].lower()) for x in chosen): continue
            chosen.append(c)
            if len(chosen) >= k: break
        return sorted(chosen, key=lambda r: r['s'])
