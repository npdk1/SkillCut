#!/usr/bin/env python3
"""Clean a words.json transcript (list of {start,end,text,words:[{w,s,e,p}]}).
 - drops stray tokens: LAUGHS / MUSIC / [Music] / (cười) / CJK-Hangul-Kana-Thai-Arabic-Cyrillic characters / known hallucination phrases
 - collapses a word repeated >= N times in a row (whisper loops)
 - hallucination phrases are only dropped when the segment ALSO carries bad whisper metadata (no_speech/avg_logprob) and is not flagged energetic/suspect by transcribe.py
 - ALL-CAPS words -> lower case (keepCaps stay; low-probability all-caps gibberish is dropped), Title-Case shouting runs (>=3 capitalised words in a row) -> lower case
 - proper nouns (config textCleanup.properNouns + glossary): diacritics-less / wrongly cased 'sai gon' -> 'Sài Gòn' (multi-word by accent-folded match, single words exact)
 - per-video glossary file (public/project/glossary.txt or --glossary): 'wrong => Right' lines or JSON; wins over brand/properNouns
 - sentence case: first word after . ? ! … (and the first word of the file) is capitalised
 - adjacent duplicate proper words ('Gòn Gòn') collapsed
 - applies the brand-name correction dictionary in style.config.json -> textCleanup.brand (multi-word keys allowed, case-insensitive,
   corrected spans keep the first word's timing and share the span's time range)
Usage: python3 scripts/text_cleanup.py public/project/words.json [-o public/project/words.json] [--report]
Also importable: from text_cleanup import clean_segments
"""
import argparse, json, os, re, sys, unicodedata


def fold(s):
    s = unicodedata.normalize('NFD', s.replace('đ', 'd').replace('Đ', 'D'))
    return re.sub(r'[^a-z0-9]+', '', ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn').lower())


HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
_ALL = json.load(open(os.path.join(ROOT, 'style.config.json'), encoding='utf-8'))
CFG = _ALL['textCleanup']
HC = _ALL.get('transcribe', {}).get('hallucination', {})

SCRIPT_RANGES = {
    'CJK': [(0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0xF900, 0xFAFF), (0x20000, 0x2A6DF)],
    'Hangul': [(0xAC00, 0xD7AF), (0x1100, 0x11FF), (0x3130, 0x318F)],
    'Kana': [(0x3040, 0x30FF), (0x31F0, 0x31FF)],
    'Thai': [(0x0E00, 0x0E7F)],
    'Arabic': [(0x0600, 0x06FF), (0x0750, 0x077F)],
    'Cyrillic': [(0x0400, 0x04FF)],
}

def in_dropped_script(ch):
    o = ord(ch)
    for name in CFG['dropScripts']:
        for a, b in SCRIPT_RANGES.get(name, []):
            if a <= o <= b:
                return True
    return False

def clean_token(w, stats, prob=1.0):
    orig = w
    if CFG.get('dropBracketed'):
        w = re.sub(r'\[[^\]]*\]|\([^)]*\)|\{[^}]*\}', '', w)
    w = ''.join(ch for ch in w if not in_dropped_script(ch) and ch not in CFG['dropSymbols'])
    bare = re.sub(r'[^\wÀ-ỹ]', '', w)
    if bare.upper() in {t.upper() for t in CFG['dropTokens']} and (bare.isupper() or w.startswith('[')):
        w = ''
    w = w.strip().lstrip('-–—')
    if CFG.get('dropPunctOnly') and w and not re.search(r'[\wÀ-ỹ]', w):
        w = ''
    if w and prob < CFG.get('minWordProb', 0):
        w = ''
    caps = CFG.get('dropAllCapsNoise'); ac = CFG.get('allCapsToSentence', {})
    if w:
        letters = re.sub(r'[^A-Za-zÀ-ỹ]', '', w)
        keep = {k.upper() for k in (caps or {}).get('keepCaps', [])} | {k.upper() for k in ac.get('keepCaps', [])}
        if len(letters) >= 2 and letters.isupper() and letters.upper() not in keep:
            # gibberish only when whisper itself was unsure; confident ALL-CAPS words are real shouting/headline text -> lower-cased
            if caps and len(letters) >= caps['minLetters'] and prob < CFG.get('allCapsKeepProb', 0.5):
                w = ''
            elif len(letters) >= ac.get('minLetters', 2):
                w = w.lower()
    if w != orig:
        stats['tokens_changed'] = stats.get('tokens_changed', 0) + 1
    return w

def norm(s):
    return re.sub(r'[^\wÀ-ỹ]', '', s.lower())

def apply_brand(words, stats):
    pairs = sorted(((k.split(), v.split()) for k, v in CFG['brand'].items()), key=lambda kv: -len(kv[0]))
    out, i = [], 0
    while i < len(words):
        hit = None
        for k, v in pairs:
            seg = words[i:i + len(k)]
            if len(seg) == len(k) and all(norm(a['w']) == norm(b) for a, b in zip(seg, k)):
                hit = (k, v, seg); break
        if not hit:
            out.append(words[i]); i += 1; continue
        k, v, seg = hit
        t0, t1, p = seg[0]['s'], seg[-1]['e'], min(x.get('p', 1.0) for x in seg)
        step = (t1 - t0) / len(v)
        for j, tok in enumerate(v):
            trail = re.search(r'[.,!?…]+$', seg[-1]['w']) if j == len(v) - 1 else None
            lead_upper = seg[0]['w'][:1].isupper() and j == 0 and tok[:1].islower() and tok not in CFG['brandCaseKeep']
            tok2 = (tok[:1].upper() + tok[1:]) if lead_upper else tok
            out.append(dict(w=tok2 + (trail.group(0) if trail else ''), s=round(t0 + j * step, 3), e=round(t0 + (j + 1) * step, 3), p=p))
        stats['brand_fixes'] = stats.get('brand_fixes', 0) + 1
        stats.setdefault('brand_log', []).append(' '.join(x['w'] for x in seg) + ' -> ' + ' '.join(v))
        i += len(k)
    return out

def collapse(words, stats):
    n = CFG.get('collapseRepeats', 3)
    out = []
    for w in words:
        if len(out) >= n - 1 and all(norm(x['w']) == norm(w['w']) for x in out[-(n - 1):]) and norm(w['w']):
            stats['repeats_dropped'] = stats.get('repeats_dropped', 0) + 1
            out[-1]['e'] = w['e']
            continue
        out.append(w)
    return out

def load_glossary(path):
    g = {}
    if not path or not os.path.exists(path):
        return g
    txt = open(path, encoding='utf-8').read().strip()
    if txt.startswith('{'):
        return json.loads(txt)
    for ln in txt.splitlines():
        ln = ln.split('#', 1)[0].strip()
        if '=>' in ln:
            k, v = ln.split('=>', 1)
            if k.strip() and v.strip():
                g[k.strip()] = v.strip()
        elif ln:
            g[ln] = ln                      # a bare line = canonical spelling to enforce (case/diacritics)
    return g


def canon_pairs(glossary):
    """[(key_tokens, canonical_tokens, exact)]: multi-word keys match accent-folded, single-word keys match lower-case exactly (avoids 'hue' -> 'Huế')."""
    pairs = []
    for name in CFG.get('properNouns', []):
        pairs.append((name, name))
    for k, v in list(CFG.get('properAliases', {}).items()) + list(CFG.get('asrFixes', {}).items()):
        pairs.append((k, v))
    for k, v in glossary.items():
        pairs.append((k, v))
    out = {}
    for k, v in pairs:                       # later entries (glossary) override
        kt = k.split()
        out[(len(kt), tuple(fold(t) if len(kt) > 1 else t.lower() for t in kt))] = (kt, v.split(), len(kt) == 1)
    return sorted(out.values(), key=lambda x: -len(x[0]))


def apply_context(words, stats):
    """v4.2: context-gated ASR fixes (config textCleanup.contextFixes): {w, to, near:[...], within:N} or {w, to, prev:[...]}. 'claw' -> Claude only when tech words are near,
    'hấp' -> 'hợp' only after kết/phù/tích...; a word is never changed when the context does not fit."""
    rules = CFG.get('contextFixes', [])
    if not rules: return words
    out = [dict(w) for w in words]
    for i, w in enumerate(out):
        core = re.sub(r'[.,!?…;:]+$', '', w['w']); trail = w['w'][len(core):]
        for r in rules:
            if norm(core) != norm(r['w']): continue
            n = r.get('within', 6); win = [fold(re.sub(r'[^\w]', '', x['w'])) for x in out[max(0, i - n):i] + out[i + 1:i + 1 + n]]
            ok = True
            if r.get('near'): ok = any(fold(k) in win for k in r['near'])
            if ok and r.get('prev'): ok = i > 0 and fold(re.sub(r'[^\w]', '', out[i - 1]['w'])) in [fold(k) for k in r['prev']]
            if ok and r.get('next'): ok = i + 1 < len(out) and fold(re.sub(r'[^\w]', '', out[i + 1]['w'])) in [fold(k) for k in r['next']]
            if ok:
                to = r['to'];  w['w'] = (to[:1].upper() + to[1:] if core[:1].isupper() and not r.get('keepCase') else to) + trail
                stats['context_fixes'] = stats.get('context_fixes', 0) + 1; break
    return out


AMBIG = {norm(k): v for k, v in CFG.get('ambiguousWords', {}).items() if not k.startswith('_')}

def ambiguous_ok(words, i, w, rule):
    """config textCleanup.ambiguousWords: {"mai": {"requireCap": true, "near": [...], "within": 12, "notNext": [...]}}. A glossary / alias entry for a COMMON Vietnamese word
    ('mai' = tomorrow / a name) is applied only when the token is capitalised (when requireCap), no `notNext` word follows and a `near` word (AI tool/brand) is within `within` words."""
    core = re.sub(r'[.,!?…;:]+$', '', w['w'])
    if rule.get('requireCap', True) and not core[:1].isupper(): return False
    n = rule.get('within', 12); win = [fold(re.sub(r'[^\w]', '', x['w'])) for x in words[max(0, i - n):i] + words[i + 1:i + 1 + n]]
    if i + 1 < len(words) and fold(re.sub(r'[^\w]', '', words[i + 1]['w'])) in [fold(k) for k in rule.get('notNext', [])]: return False
    if any(fold(k) in win for k in rule.get('near', [])) if rule.get('near') else True: return True
    # v4.4 (v4.3 check: clips without an AI-tool word near 'Mai' kept 'Mai'): NAME VOTE - a capitalised token that is followed by a subject marker (sẽ / đã / đang / hoàn toàn / là ...)
    # at least `nameVote.minHits` times in the transcript is the speaker's / tool's NAME, not 'tomorrow' (a capitalised 'Mai' after 'ngày' / before 'sau' is already excluded above).
    nv = rule.get('nameVote') or {}
    if nv.get('enabled', False):
        mk = {fold(x) for x in nv.get('markers', [])}; tgt = fold(core)
        hits = sum(1 for j in range(len(words) - 1) if fold(re.sub(r'[^\w]', '', words[j]['w'])) == tgt and re.sub(r'[.,!?…;:]+$', '', words[j]['w'])[:1].isupper() and fold(re.sub(r'[^\w]', '', words[j + 1]['w'])) in mk)
        return hits >= nv.get('minHits', 2) and fold(re.sub(r'[^\w]', '', words[i + 1]['w'])) in mk if i + 1 < len(words) else False
    return False

NUM_TECH = {'opus', 'sonnet', 'haiku', 'claude', 'gpt', 'gemini', 'llama', 'qwen', 'grok', 'deepseek', 'v', 'version', 'phien', 'ban', 'iphone', 'ios', 'android', 'python', 'node', 'o', 'r'}

def merge_numbers(words, key_s='s', key_e='e'):
    """v4.3: ASR spacing 'Opus 5 .5' / 'Opus 5 . 5' / 'GPT 4 ,5' -> 'Opus 5.5'. Merges a bare number with a following '.N' / ',N' token (always: a token that STARTS with a separator
    glued to digits is a decimal), and 'N' '.' 'N' only when the word before is a model/version word. Timing: first start .. last end. Works on words with w/s/e or w/t0/t1."""
    ks, ke = (key_s, key_e) if words and key_s in words[0] else ('t0', 't1')
    out, i = [], 0
    while i < len(words):
        w = words[i]; core = re.sub(r'[.,!?…;:]+$', '', w['w'])
        nxt = words[i + 1] if i + 1 < len(words) else None
        if re.fullmatch(r'\d+', core) and nxt is not None:
            m = re.fullmatch(r'[.,](\d+)([.,!?…;:]*)', nxt['w'])
            prev = fold(re.sub(r'[^\w]', '', out[-1]['w'])) if out else ''
            if m:
                out.append(dict(w, w=core + '.' + m.group(1) + m.group(2), **{ke: nxt[ke]})); i += 2; continue
            n2 = words[i + 2] if i + 2 < len(words) else None
            if n2 is not None and re.fullmatch(r'[.,]', nxt['w']) and re.fullmatch(r'\d+[.,!?…;:]*', n2['w']) and (prev in NUM_TECH or len(core) <= 2):
                out.append(dict(w, w=core + '.' + n2['w'], **{ke: n2[ke]})); i += 3; continue
        out.append(w); i += 1
    return out

def apply_canon(words, pairs, stats):
    out, i = [], 0
    while i < len(words):
        hit = None
        for kt, vt, single in pairs:
            seg = words[i:i + len(kt)]
            if len(seg) != len(kt):
                continue
            if single:
                ok = norm(seg[0]['w']) == norm(kt[0])
                if ok and norm(kt[0]) in AMBIG: ok = ambiguous_ok(words, i, seg[0], AMBIG[norm(kt[0])])    # v4.3: 'Mai' is a common Vietnamese word/name -> only in an AI-tool/name context
            else:
                ok = all(fold(x['w']) == fold(t) for x, t in zip(seg, kt))
            if ok:
                hit = (kt, vt, seg); break
        if not hit:
            out.append(words[i]); i += 1; continue
        kt, vt, seg = hit
        trail = re.search(r'[.,!?…;:]+$', seg[-1]['w'])
        trail = trail.group(0) if trail else ''
        if len(vt) == len(seg):                               # same token count: keep every word's own timing
            for j, x in enumerate(seg):
                nw = vt[j]
                t_j = re.search(r'[.,!?…;:]+$', x['w'])
                if nw != re.sub(r'[.,!?…;:]+$', '', x['w']):
                    stats['proper_fixes'] = stats.get('proper_fixes', 0) + 1
                out.append(dict(x, w=nw + (t_j.group(0) if t_j else '')))
        else:                                                 # unequal: NO word may be dropped or repeated - spread the span over all canonical tokens
            t0, t1 = seg[0]['s'], seg[-1]['e']
            wts = [max(1, len(t)) for t in vt]
            acc, cur = sum(wts), t0
            mp = round(sum(x.get('p', 1.0) for x in seg) / len(seg), 3)
            for j, tok in enumerate(vt):
                nxt = t1 if j == len(vt) - 1 else round(cur + (t1 - t0) * wts[j] / acc, 3)
                out.append(dict(seg[min(j, len(seg) - 1)], w=tok + (trail if j == len(vt) - 1 else ''), s=round(cur, 3), e=round(nxt, 3), p=mp))
                cur = nxt
            stats['proper_fixes'] = stats.get('proper_fixes', 0) + 1
            stats['canon_resized'] = stats.get('canon_resized', 0) + 1
        i += len(kt)
    return out


def dedupe_proper(words, stats):
    out = []
    for w in words:
        if out and CFG.get('dedupeAdjacentProper') and norm(out[-1]['w']) == norm(w['w']) and w['w'][:1].isupper() and norm(w['w']):
            out[-1]['e'] = w['e']; out[-1]['w'] = out[-1]['w'].rstrip('.,') + (re.search(r'[.,!?…]+$', w['w']).group(0) if re.search(r'[.,!?…]+$', w['w']) else '')
            stats['proper_dupes'] = stats.get('proper_dupes', 0) + 1
            continue
        out.append(w)
    return out


def unshout(all_words, protected, stats):
    """lower-case runs of >=3 Title-Case words (whisper 'Title Case Everything'), except protected canonical words"""
    i, n = 0, len(all_words)
    while i < n:
        j = i
        while j < n and all_words[j]['w'][:1].isupper() and not all_words[j]['w'].isupper():
            j += 1
        if j - i >= 3:
            for k in range(i, j):
                bare = re.sub(r'[.,!?…;:]+$', '', all_words[k]['w'])
                if bare not in protected and k > i:
                    all_words[k]['w'] = bare.lower() + all_words[k]['w'][len(bare):]
                    stats['titlecase_lowered'] = stats.get('titlecase_lowered', 0) + 1
        i = max(j, i + 1)


def sentence_case(all_words, protected, stats):
    start = True
    for w in all_words:
        if start and w['w'][:1].islower():
            w['w'] = w['w'][:1].upper() + w['w'][1:]
            stats['sentence_caps'] = stats.get('sentence_caps', 0) + 1
        start = bool(re.search(r'[.!?…]$', w['w']))


def clean_segments(segs, glossary_path=None):
    stats = {}
    res = []
    gl = load_glossary(glossary_path if glossary_path is not None else os.path.join(ROOT, CFG.get('glossaryFile', '')) if CFG.get('glossaryFile') else None)
    if gl:
        stats['glossary_entries'] = len(gl)
    pairs = canon_pairs(gl)
    phrases = [fold(h) for h in CFG.get('dropHallucinations', [])] + [fold(h) for h in HC.get('phrases', [])]
    for sg in segs:
        f = fold(sg.get('text', ''))
        if any(h and h in f for h in phrases):
            has_meta = 'ns' in sg or 'lp' in sg
            bad = sg.get('ns', 0) >= HC.get('maxNoSpeech', 0.6) or sg.get('lp', 0) <= HC.get('minAvgLogprob', -1.0) or sg.get('cr', 0) >= HC.get('maxCompression', 2.4)
            if (not has_meta and CFG.get('dropHallucinations')) or (has_meta and bad and not sg.get('suspect')):
                stats['segments_dropped_hallucination'] = stats.get('segments_dropped_hallucination', 0) + 1
                continue
        ws = []
        for w in sg.get('words', []):
            t = clean_token(w['w'], stats, w.get('p', 1.0))
            if t:
                ws.append(dict(w, w=t))
        ws = collapse(apply_brand(ws, stats), stats)
        if gl:
            ws = apply_canon(ws, [x for x in pairs if (' '.join(x[0]) in gl)], stats)
        ws = apply_canon(ws, [x for x in pairs if ' '.join(x[0]) not in gl], stats) if CFG.get('properNouns') else ws
        ws = merge_numbers(apply_context(dedupe_proper(ws, stats), stats))
        if not ws:
            stats['segments_empty'] = stats.get('segments_empty', 0) + 1
            continue
        res.append(dict(sg, start=ws[0]['s'], end=ws[-1]['e'], text=' '.join(x['w'] for x in ws), words=ws))
    if CFG.get('sentenceCase', True):
        flat = [w for sg in res for w in sg['words']]
        protected = set(CFG.get('properNouns', []) and [t for n in CFG['properNouns'] for t in n.split()]) | {t for v in gl.values() for t in v.split()} | set(CFG.get('brandCaseKeep', [])) | {t for v in CFG['brand'].values() for t in v.split()}
        unshout(flat, protected, stats)
        sentence_case(flat, protected, stats)
        for sg in res:
            sg['text'] = ' '.join(x['w'] for x in sg['words'])
    return res, stats


def reapply_glossary(segs, glossary_path=None):
    """Idempotent glossary-only pass over already transcribed segments (words.json). make_edl.py (captions) and make_beats.py (beat headlines/lines)
    call this on load, so a glossary.txt edited AFTER transcription still fixes captions and beat text without re-running whisper. Returns (segs, n_fixed)."""
    gl = load_glossary(glossary_path if glossary_path is not None else os.path.join(ROOT, CFG.get('glossaryFile', '')) if CFG.get('glossaryFile') else None)
    if not gl and not CFG.get('asrFixes') and not CFG.get('contextFixes'):
        return segs, 0
    pairs = canon_pairs(gl); asr = {' '.join(k.split()) for k in CFG.get('asrFixes', {})}; gp = [x for x in pairs if ' '.join(x[0]) in gl or ' '.join(x[0]) in asr]
    stats, out = {}, []
    for sg in segs:
        ws = sg.get('words')
        if not ws:
            out.append(sg); continue
        ws2 = [dict(w) for w in ws]
        for w in ws2:                                         # accept both {w,s,e} and {word,start,end}
            if 'w' not in w and 'word' in w: w['w'] = w['word']
        nw = merge_numbers(apply_context(apply_canon(ws2, gp, stats), stats))
        out.append(dict(sg, words=nw, text=' '.join(x['w'] for x in nw)))
    return out, stats.get('proper_fixes', 0) + stats.get('context_fixes', 0)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('words'); ap.add_argument('-o', '--out'); ap.add_argument('--report', action='store_true'); ap.add_argument('--glossary')
    a = ap.parse_args()
    segs = json.load(open(a.words, encoding='utf-8'))
    res, stats = clean_segments(segs, glossary_path=a.glossary)
    json.dump(res, open(a.out or a.words, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(stats, ensure_ascii=False, indent=1) if a.report else 'cleaned: ' + json.dumps({k: v for k, v in stats.items() if k != 'brand_log'}, ensure_ascii=False))
