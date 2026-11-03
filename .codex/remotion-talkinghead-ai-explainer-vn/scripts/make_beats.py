#!/usr/bin/env python3
"""AUTO BEAT PLAN: transcript (+ edl) -> public/project/beats.json   (times in SOURCE seconds, like the rest of the project data)

  python3 scripts/make_beats.py --words public/project/words.json [--edl public/project/edl.json] [--out public/project/beats.json] [--report]

Rules (style.config.json -> autoBeats) were derived from the reference's beat timeline; they look for keyword triggers in the transcript:
  stars (hook) | brand sticker | chip-stack (>=3 listed terms) | prompt-box ("đừng prompt ...") | info-scene (negatives / amounts)
  | title-burst ("render") | big-word (emphasis words, repeated key noun) + selection-box | topic-card | avatar-chain | skill sticker | comment-box CTA
No trigger -> no beat (nothing is invented). Text shown on screen is always copied from the spoken words (capitalised), never made up,
except documented fallbacks in config. beats.json is a PLAN: review it, delete/adjust anything; it is also the file the composition reads.
All beats get a `_why` field (rule + trigger word) for review; extra keys are ignored by the composition.
"""
import argparse, json, os, re, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vi_phrases, logo_place
CFG = json.load(open(os.path.join(ROOT, 'style.config.json'), encoding='utf-8'))
A = CFG['autoBeats']
CFG_IS = CFG.get('beats', {}).get('infoScene', {})


DANGLING = {'ra', 'không', 'khong', 'mà', 'và', 'thì', 'là', 'của', 'để', 'cho', 'với', 'nhưng', 'hoặc', 'hay', 'rồi', 'cũng', 'sẽ', 'đã', 'đang', 'có', 'những', 'các', 'một', 'như', 'này', 'nào', 'khi', 'nếu', 'vì', 'bởi', 'tại', 'ở', 'trong'}
def _fetch_logo(br, ldir):
    """run scripts/fetch_logo.sh for a mentioned brand with no logo file; returns the file path or None (a missing logo is reported, never faked)"""
    import subprocess
    sh = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fetch_logo.sh')
    if not os.path.exists(sh): return None
    args = ['bash', sh, br['slug'], br.get('si', br['slug']), br.get('domain', ''), br['name']]
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=90, env=dict(os.environ, LOGO_DIR=ldir))
    except Exception as e:
        print(f"logo fetch for {br['name']} failed to run: {e}", file=sys.stderr); return None
    line = (r.stdout or '').strip().split('\n')[-1].split()
    if r.returncode != 0 or len(line) < 5:
        print(f"logo fetch: NOT FOUND {br['name']} ({(r.stderr or '').strip()[-120:]})", file=sys.stderr); return None
    try:    # record in logos.json so the glow colour and the source are kept (references/brand-logos.md Registry)
        jp = os.path.join(ldir, 'logos.json'); d = json.load(open(jp, encoding='utf-8')) if os.path.exists(jp) else {}
        (d['brands'] if isinstance(d.get('brands'), dict) else d)[br['slug']] = dict(file=os.path.basename(line[1]), source=line[2], url=line[3], color=line[4])
        json.dump(d, open(jp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    except Exception: pass
    print(f"logo fetched: {br['name']} <- {line[2]} ({line[3]})", file=sys.stderr)
    return line[1] if os.path.exists(line[1]) else os.path.join(ldir, os.path.basename(line[1]))

def _reload_logo_meta(ldir):
    try:
        m = json.load(open(os.path.join(ldir, 'logos.json'), encoding='utf-8')); return m.get('brands', m) if isinstance(m, dict) else {}
    except Exception: return {}

def clean_sub(txt):
    """Never end a subline on a cut-off fragment ('không t') or a dangling function word; <2 words left -> no subline."""
    if not txt: return None
    toks = txt.strip().split()
    while toks:
        last = re.sub(r'[^\w]', '', toks[-1]).lower()
        if len(last) <= 1 and not last.isdigit() or last in DANGLING: toks.pop(); continue
        break
    out = ' '.join(toks).strip(' ,.;')
    return out if len(toks) >= 2 else None

def fold(s):
    s = unicodedata.normalize('NFD', s.replace('đ', 'd').replace('Đ', 'D'))
    s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn').lower()
    return re.sub(r'[^a-z0-9]+', '', s)


def cap(s):
    s = s.strip(' ,.;:!?…-')
    return s[:1].upper() + s[1:]


def load_words(path):
    ws, sents, cur = [], [], []
    _segs = json.load(open(path, encoding='utf-8'))
    try:
        from text_cleanup import reapply_glossary
        _segs, _nfix = reapply_glossary(_segs)         # glossary.txt applies BEFORE any beat text is built
        if _nfix: print(f'glossary: {_nfix} word(s) corrected before building beats')
    except ImportError:
        pass
    for seg in _segs:
        for w in seg.get('words', []):
            x = dict(w=w.get('w') or w.get('word', ''), s=float(w.get('s', w.get('start'))), e=float(w.get('e', w.get('end'))))
            x['f'] = fold(x['w'])
            if not x['f']:
                continue
            if cur and x['s'] - cur[-1]['e'] >= 0.6:
                sents.append(cur); cur = []
            cur.append(x); ws.append(x)
            if re.search(r'[.!?…]$', x['w']):
                sents.append(cur); cur = []
        if cur:
            sents.append(cur); cur = []
    return ws, [s for s in sents if s]


def find(ws, phrase, start=0):
    """index of the first occurrence of an (accent-folded, space separated) phrase in ws[start:], else -1"""
    toks = phrase.split()
    for i in range(start, len(ws) - len(toks) + 1):
        if all(ws[i + j]['f'] == toks[j] for j in range(len(toks))):
            return i
    return -1


def words_after(ws, i, n, skip=(), stop_punct=True):
    out = []
    for w in ws[i:]:
        if w['f'] in skip:
            continue
        out.append(w['w'])
        if len(out) >= n or (stop_punct and re.search(r'[,.;!?…]$', w['w'])):
            break
    return ' '.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--words', required=True); ap.add_argument('--edl'); ap.add_argument('--out', default='public/project/beats.json'); ap.add_argument('--report', action='store_true')
    ap.add_argument('--raw', help='source video (default: raw.mp4 next to --out): used for screen-b-roll detection and still frames')
    ap.add_argument('--screen', help='screen_broll.json (default: next to --out; auto-created from --raw when missing)')
    ap.add_argument('--no-generic', action='store_true', help='keyword rules only (no genre-agnostic fallback)')
    a = ap.parse_args()
    ws, sents = load_words(a.words)
    if not ws:
        sys.exit('no words')
    segs = json.load(open(a.edl))['segments'] if a.edl and os.path.exists(a.edl) else None
    t_end = ws[-1]['e']
    beats = []

    def add(b, why):
        b['_why'] = why; beats.append(b)

    def sent_of(w):
        return next(s for s in sents if w in s)

    # 1 stars hook
    add(dict(type='stars', t0=round(ws[0]['s'], 2), t1=round(ws[0]['s'] + A['hook']['starsSec'], 2)), 'hook: first sentence')

    # 2 brand sticker (first mention of each brand term; a shorter term inside an already-used longer one is skipped there)
    covered = set()
    for term in sorted(A['brand']['terms'], key=lambda t: -len(t)):
        n0 = len(term.split())
        i = next((j for j in range(len(ws)) if j not in covered and find(ws, term, j) == j), -1)
        if i < 0:
            continue
        covered.update(range(i, i + n0))
        # also mark every occurrence of the longer term as covered for shorter terms
        j0 = 0
        while True:
            j0 = find(ws, term, j0)
            if j0 < 0: break
            covered.update(range(j0, j0 + n0)); j0 += n0
        j = i + n0
        label = ' '.join(w['w'] for w in ws[i:j]).strip(' ,.')
        k = j; ver = ''
        while k < len(ws) and re.fullmatch(r'[\d.,]+', ws[k]['w'].strip()) and len(ver) < 6:
            ver += ws[k]['w'].strip(); k += 1
        ver = ver.strip('.,')
        label = label + (' ' + ver if ver else '')
        t = ws[i]['s']; d = A['brand']['stickerSec']
        if t < A['brand']['labelAboveMinSec']:
            add(dict(type='sticker', t0=round(t, 2), t1=round(t + d, 2), look='tile', brand=term), f'brand "{term}" early -> tile')
        else:
            hl = ' '.join(label.split()[1:]) or None
            b = dict(type='sticker', t0=round(t, 2), t1=round(t + d, 2), label=label, look='label-above', brand=term)
            if hl: b['hl'] = hl
            add(b, f'brand "{term}" -> label-above')

    # 3 chip-stack
    C = A['chips']; hits = []
    for it in C['lexicon']:
        for k in it['keys']:
            i = find(ws, k)
            if i >= 0:
                hits.append((ws[i]['s'], i, it, len(k.split()))); break
    hits.sort(key=lambda h: h[0])
    best = []
    for x in range(len(hits)):
        grp = [h for h in hits[x:] if h[0] - hits[x][0] <= C['windowSec']]
        if len(grp) > len(best):
            best = grp
    if len(best) >= C['minItems']:
        items = []
        for t, i, it, nk in best:
            sub = words_after(ws, i + nk, C['subWords'], skip=set(C['subSkip']))
            if items and t - items[-1]['t'] < 0.6: continue
            items.append(dict(t=round(t, 2), title=it['title'], sub=sub.strip(' ,.;'), icon=it['icon']))
        add(dict(type='chip-stack', t0=round(best[0][0] - 0.1, 2), t1=round(best[-1][0] + C['holdSec'] + 1.2, 2), items=items), f'{len(items)} listed terms within {C["windowSec"]}s')

    # 4 prompt-box
    P = A['promptBox']
    for trig in P['triggers']:
        i = find(ws, trig)
        if i < 0:
            continue
        s = sent_of(ws[i]); si = s.index(ws[i])
        if any(find(s, n) >= 0 for n in P['negators']):
            rest = [w for w in s[si + 1:] if w['f'] not in ('nua', 'di', 'ai')]
            txt = cap(' '.join(w['w'] for w in rest[:6])) if rest else P['fallbackText']
            t0 = ws[i]['s'] - 0.4; t1 = s[-1]['e'] + P['holdAfterSec']
            add(dict(type='prompt-box', t0=round(t0, 2), t1=round(t1, 2), text=txt + '...', strikeAt=round(max(t0 + 0.8, s[-1]['e'] + P['strikeOffsetSec']), 2)), f'"{trig}" + negator in sentence')
            break

    # 5 info-scene: negatives list
    N = A['infoNegative']; neg = []
    for t in N['terms']:
        i = find(ws, ' '.join(t))
        if i >= 0:
            neg.append((ws[i]['s'], i, t))
    def hl_time(word_s, t0):
        """headline appears headlineLeadSec BEFORE its first word (so it is fully visible when spoken) but never before scene t0 + headlineMinAfterHeaderSec"""
        lead = CFG_IS.get('headlineLeadSec', 0.1); mn = CFG_IS.get('headlineMinAfterHeaderSec', 0.3)
        return round(max(word_s - lead, t0 + mn), 2)
    neg.sort()
    # "tốn thời gian VÀ token" -> second card "Tốn token" (verb repeated from the first term)
    if neg:
        i0 = neg[0][1] + len(' '.join(neg[0][2]).split())
        if i0 + 1 < len(ws) and ws[i0]['f'] in N.get('andContinuation', []) and not any(ws[i0 + 1]['f'] == n[2][-1] for n in neg[1:]):
            neg.append((ws[i0 + 1]['s'], i0 + 1, ['__and__', ws[i0 + 1]['f']]))
    if len(neg) >= N['minTerms']:
        t_first, i0 = neg[0][0], neg[0][1]
        sc0 = sent_of(ws[i0])
        pre = [w for w in sc0 if w['e'] <= t_first + 0.01][-N['headerWords']:]
        header = ' '.join(w['w'] for w in pre).strip(' ,.') if pre else ''
        cards = []
        verb = ws[i0]['w']
        for tt, i, t in neg[:3]:
            if t[0] == '__and__':
                cards.append(dict(t=round(tt, 2), text=cap(verb + ' ' + ws[i]['w']), strike=True))
            else:
                cards.append(dict(t=round(tt, 2), text=cap(' '.join(w['w'] for w in ws[i:i + len(' '.join(t).split()) + (1 if len(t) == 1 else 0)])), strike=True))
        sc = sent_of(ws[neg[-1][1]])
        # scene runs to the end of the sentence that contains the "replacement" (headline) when there is one
        tail = ws[ws.index(sc[-1]):]
        t_e = sc[-1]['e']
        info = dict(type='info-scene', t0=round(pre[0]['s'] if pre else t_first - 0.5, 2), t1=0, header=header, cards=cards)
        for trig in N['headlineAfter']:
            i = find(ws, trig, ws.index(sc[0]))
            if i >= 0:
                k = i + len(trig.split())
                while k < len(ws) and ws[k]['f'] in ('mot', 'cai', 'nhung', 'cac'): k += 1
                info['headline'] = dict(t=hl_time(ws[k]['s'], info['t0']), text=words_after(ws, k, N['headlineWords']).strip(' ,.'))
                t_e = max(t_e, sent_of(ws[k])[-1]['e'])
                break
        for trig in N['pillAfter']:
            i = find(ws, trig)
            if i >= 0:
                info['pill'] = dict(t=round(ws[i]['s'], 2), text=cap(' '.join(w['w'] for w in ws[i:i + len(trig.split())]) + ' ' + ' '.join(w['w'] for w in sent_of(ws[i])[-2:]).strip(' ,.'))); t_e = max(t_e, sent_of(ws[i])[-1]['e']); break
        info['t1'] = round(t_e + 0.1, 2)
        add(info, f'{len(neg)} negative terms')

    # 6 info-scene: amounts ("chỉ mất ...")
    M = A['infoAmount']
    for trig in M['triggers']:
        i = find(ws, trig)
        if i < 0: continue
        s = sent_of(ws[i]); si = s.index(ws[i]); n0 = len(trig.split())
        rest = s[si + n0:]
        if not rest: continue
        head = ' '.join(w['w'] for w in ws[i:i + n0]).strip(' ,')
        head = cap(head)
        hl_txt = words_after(ws, i + n0, 3)
        cards = []
        base = ws.index(s[0]); span = ws[base:base + len(s) + 20]
        text, pos = '', []
        for w in span:
            pos.append(len(text)); text += w['w'] + ' '
        for mm in re.finditer(r'(nửa tiếng|nửa giờ|\d+(?:\s*[-–]?\s*\d+)?\s*(?:phút|giờ|tiếng|ngày|giây))', text):
            wi = max(k for k, p_ in enumerate(pos) if p_ <= mm.start())
            cards.append(dict(t=round(span[wi]['s'], 2), text=re.sub(r'\s*[-–]?\s*(?=\d)', lambda q: '-' if q.group(0).strip() else ' ', cap(mm.group(1).strip())) if False else re.sub(r'(\d)\s+(\d)', r'\1-\2', mm.group(1).strip())))
        cards = cards[:M['cardMax']]
        for k, cd in enumerate(cards):
            if k: cd['accent'] = True
        if cards:
            add(dict(type='info-scene', t0=round(ws[i]['s'] - 0.2, 2), t1=round(cards[-1]['t'] + 1.3, 2), header=head, headline=dict(t=hl_time(ws[i + n0]['s'], ws[i]['s'] - 0.2), text=hl_txt), cards=cards), f'amount trigger "{trig}"')
        break

    # 7 title-burst   (v4.1: title = a COMPLETE key phrase near the trigger, never the 3 syllables before it)
    T = A['titleBurst']
    PH = vi_phrases.Phraser(A['phrases'])
    for trig in T['triggers']:
        i = find(ws, trig)
        if i < 0: continue
        s = sent_of(ws[i]); st = s.index(ws[i])
        su = PH.units(s)
        near = [c for c in PH.candidates(su, t_lo=ws[i]['s'] - 3.0, t_hi=ws[i]['e'] + 3.0, max_words=4) if c['s'] <= ws[i]['e'] and c['e'] >= ws[i]['s'] - 0.05] \
            or PH.candidates(su, t_lo=ws[i]['s'] - 3.0, t_hi=ws[i]['e'] + 3.0, max_words=4)
        if not near:
            print(f'title-burst "{trig}" skipped: no complete key phrase near the trigger', file=sys.stderr); break
        tp = near[0]
        rest = PH.best([u for u in su if u['s'] >= tp['e'] - 0.01], max_words=5)
        t0 = max(ws[0]['s'], tp['s'] - 0.1)
        add(dict(type='title-burst', t0=round(t0, 2), t1=round(t0 + T['holdSec'], 2), title=tp['text'], sub=(rest['text'] if rest else None), rec='REC', timeline=True, _recSrcT=round(t0, 2)), f'trigger "{trig}"')
        break

    # 8 big-word: emphasis + key noun
    W = A['bigWord']
    for e in W['emphasis']:
        i = next((j for j, w in enumerate(ws) if w['w'].lower().strip(' ,.!?…') == e), -1)
        if i >= 0 and ws[i]['s'] > ws[0]['s'] + 2:
            add(dict(type='big-word', t0=round(ws[i]['s'] - 0.3, 2), t1=round(ws[i]['s'] + W['holdSec'], 2), text=ws[i]['w'].strip(' ,.!?') + '!', sparkles=True), f'emphasis "{e}"')
            break
    for kn in W['keyNouns']:
        idx = [j for j, w in enumerate(ws) if w['f'] == fold(kn)]
        if len(idx) >= 2:
            t = ws[idx[-1]]['s']
            add(dict(type='big-word', t0=round(t - 0.3, 2), t1=round(t + W['holdSec'] + 1.0, 2), text=kn), f'key noun "{kn}" x{len(idx)}')
            if W['selectionBoxForKeyNoun']:
                add(dict(type='selection-box', t0=round(t + 0.7, 2), t1=round(t + W['holdSec'] + 1.0, 2), label=kn, size=W['selectionSize']), 'selection box on key noun')

    # 9 topic-card
    Tc = A['topicCard']; last = -99; used = 0; taken = [(b['t0'], b['t1']) for b in beats if b['type'] in ('info-scene', 'title-burst')]
    for s in sents:
        if used >= Tc['maxCount']: break
        if s[0]['s'] - last < Tc['minGapSec'] or s[0]['s'] < ws[0]['s'] + 2.5: continue
        txt = ' '.join(w['f'] for w in s)
        trig = next((t for t in Tc['triggers'] if find(s, t) >= 0), None)
        if not trig: continue
        t0, t1 = s[0]['s'], min(s[-1]['e'] + 0.4, s[0]['s'] + Tc['maxSec'])
        if t1 - t0 < Tc['minSec']: t1 = t0 + Tc['minSec']
        if any(t0 < b1 and b0 < t1 for b0, b1 in taken): continue
        su = PH.units(s)
        picks = PH.pick_many(su, Tc['maxLines'] + 1, t_lo=s[0]['s'] - 0.01, t_hi=t1 + 0.2, min_gap=0.4)
        if len(picks) < 2: continue                      # no complete phrases -> no card (v4.1)
        phone = any(find(s, k) >= 0 for k in Tc['phoneKeys'])
        lines = []
        for li, ph_ in enumerate(picks[1:Tc['maxLines'] + 1]):
            ln = dict(t=round(ph_['s'], 2), text=ph_['text'])
            if li == 0 and not phone: ln['pill'] = True
            elif li % 2 == 1: ln['hl'] = True
            lines.append(ln)
        header = picks[0]['text']
        add(dict(type='topic-card', t0=round(t0, 2), t1=round(t1, 2), header=header, media=dict(src='project/phone.png' if phone else 'project/editor.png', kind='phone' if phone else 'window'), lines=lines), f'topic trigger "{trig}"')
        taken.append((t0, t1)); last = t1; used += 1

    # 10 avatar chain   (v4.1: needs a real "AI replaces you" context - a bare 'thay thế' is not enough)
    Av = A['avatarChain']
    _st = lambda x: unicodedata.normalize('NFC', re.sub(r'[^\w]', '', x))
    brand_first = {fold(t.split()[0]) for t in A['brand']['terms']}
    def av_context(i, n0):
        """(ok, why): AI side named near the trigger and the trigger is not negated by lowercase 'ai' (= nobody)"""
        s_ = sent_of(ws[i]); si = s_.index(ws[i])
        if any(_st(w['w']) == 'ai' and not w['w'].strip(' ,.!?…;:').isupper() for w in s_[max(0, si - Av.get('negationWindow', 4)):si + n0 + Av.get('negationWindow', 4)] if w is not ws[i]):
            return False, 'negated ("ai" = nobody)'
        tgt = ws[i]['s']
        for w in ws:
            if abs(w['s'] - tgt) > Av.get('contextSec', 4.0): continue
            raw = w['w'].strip(' ,.!?…;:')
            if raw in Av.get('aiTokens', ['AI']) or w['f'] in brand_first and w['w'][:1].isupper(): return True, f'AI side "{raw}"'
        return False, 'no AI / brand named near the trigger'
    for trig in Av['triggers']:
        n0 = len(trig.split()); j0 = 0; chosen = None
        while True:
            i = find(ws, trig, j0)
            if i < 0: break
            j0 = i + 1
            if trig.split()[-1] == 'ai':                   # "giao cho AI": the last word must be the capitalised AI
                if ws[i + n0 - 1]['w'].strip(' ,.!?…;:') not in Av.get('aiTokens', ['AI']): continue
                ok, why = True, 'AI is the trigger'
            else:
                ok, why = av_context(i, n0) if Av.get('contextRequired', True) else (True, 'context check off')
            if not ok:
                print(f'avatar-chain "{trig}" @ {ws[i]["s"]:.2f}s skipped: {why}', file=sys.stderr); continue
            chosen = (i, why); break
        if not chosen: continue
        i, why = chosen
        spoken = ' '.join(w['w'] for w in ws[i:i + n0]).strip(' ,.!?')
        su = PH.units(sent_of(ws[i + n0 - 1]))
        after = [u for u in su if u['s'] >= ws[i + n0 - 1]['e'] - 0.01]
        chip = None
        if trig.startswith('thay the') or trig.startswith('giao'):
            chip = spoken                                     # the action itself: "thay thế", "giao cho AI"
        else:                                                 # "thay mình <edit video>": the complete 1-2 content words that follow
            ph_ = [u for u in after[:3] if PH.content(u) and len(u['syl']) <= 3]
            if ph_:
                us = [ph_[0]] + ([ph_[1]] if len(ph_) > 1 and ph_[1] is after[1] and len(ph_[0]['syl']) + len(ph_[1]['syl']) <= 3 and not ph_[0]['punct'] else [])
                chip = ' '.join(u['raw'] for u in us)
            else: chip = spoken
        badge = next((' '.join(w['w'] for w in ws[j:j + len(k.split())]) for k in Av['badgeKeys'] for j in [find(ws, k)] if j >= 0), None)
        d = dict(type='avatar-chain', t0=round(ws[i]['s'] - 0.8, 2), t1=round(ws[i]['s'] - 0.8 + Av['holdSec'], 2), left=Av['left'], chip=chip.strip(' ,.'), right=Av['right'])
        if badge: d['badge'] = badge.strip(' ,.')
        add(d, f'trigger "{trig}" ({why})'); break

    # 11 skill sticker (label-right card) near the end
    Sk = A['skillSticker']
    for k in Sk['terms']:
        j = -1; st = 0
        while True:
            c_ = find(ws, k, st)
            if c_ < 0: break
            if ws[c_]['s'] > t_end * 0.6: j = c_; break
            st = c_ + 1
        if j < 0: continue
        n0 = len(k.split())
        sub = words_after(ws, j + n0, Sk['subWords'], skip=('de', 'cho', 'nay', 'nhe'), stop_punct=True)
        add(dict(type='sticker', t0=round(ws[j]['s'] - 0.2, 2), t1=round(ws[j]['s'] + Sk['holdSec'], 2), look='label-right', **({'label': cap(sub), 'sub': ' '.join(w['w'] for w in ws[j:j + n0]).strip(' ,.'), 'icon': 'bolt'} if sub else {'label': ' '.join(w['w'] for w in ws[j:j + n0]).strip(' ,.'), 'icon': 'bolt'})), f'skill term "{k}" in last 40%')
        break

    # 12 CTA
    Cc = A['cta']
    for trig in Cc['triggers']:
        i = find(ws, trig)
        if i < 0: continue
        s = sent_of(ws[i]); typed = None
        for k in Cc['typedFrom']:
            j = find(s, k)
            if j >= 0:
                typed = ' '.join(w['w'] for w in s[j:j + len(k.split())]).strip(' ,.'); break
        typed = typed or Cc['typedFallback']
        t0 = s[0]['s'] if Cc['holdFromSentenceStart'] else ws[i]['s'] - 1
        add(dict(type='comment-box', t0=round(t0, 2), t1=round(max(s[-1]['e'] + 0.2, t0 + 1.5), 2), typed=typed, bubble=typed), f'CTA trigger "{trig}"')
        break


    # ---- 13 GENERIC (genre-agnostic) fallback: runs for every video, keeps whatever the keyword rules already placed ----
    G = A.get('generic', {})
    pdir0 = os.path.dirname(os.path.abspath(a.out))
    raw_path = a.raw or next((os.path.join(pdir0, n) for n in ('raw.mp4', 'raw.mov', 'raw.mkv') if os.path.exists(os.path.join(pdir0, n))), None)
    probe_p = os.path.join(pdir0, 'probe.json')
    portrait = False; canvas_ar = 1.78
    if os.path.exists(probe_p):
        try:
            _o = json.load(open(probe_p)).get('original', {})
            portrait = _o.get('orientation') == 'portrait'; canvas_ar = float(_o.get('aspect') or canvas_ar)
        except Exception: pass
    kept_iv = [(x['srcIn'], x['srcOut']) for x in segs] if segs else [(0, t_end + 1)]
    in_kept = lambda t: any(i0 - 0.05 <= t <= i1 + 0.05 for i0, i1 in kept_iv)
    t_last = max(i1 for _, i1 in kept_iv) if segs else t_end
    t_last = min(t_last, t_end + 0.3)
    busy = lambda t0, t1, types=None: any(b['t0'] - G.get('avoidNearSec', 1.2) < t1 and t0 < b['t1'] + G.get('avoidNearSec', 1.2) for b in beats if types is None or b['type'] in types)
    fullscreen_busy = lambda t0, t1: any(b['t0'] < t1 and t0 < b['t1'] for b in beats if b['type'] in ('info-scene', 'topic-card', 'framed-focus'))
    gen_report = []
    still_jobs = []
    if G.get('enabled', True) and not a.no_generic:
        FUNC = {fold(x) for x in ('và', 'thì', 'là', 'của', 'để', 'mà', 'nhưng', 'hoặc', 'với', 'ở', 'trong', 'rồi', 'sau', 'khi', 'nếu', 'vì', 'nên', 'cho', 'từ', 'đến', 'ra', 'về', 'các', 'những', 'một', 'cái', 'này', 'đó', 'kia', 'thế', 'cũng', 'đã', 'sẽ', 'đang', 'có', 'không', 'rất', 'như', 'bạn', 'mình', 'chúng', 'ta', 'tôi', 'em', 'anh', 'chị', 'ông', 'bà')}
        # v4.1: superlatives are matched WITH diacritics (fold() made 'cập nhật' == 'nhất', 'đang' == 'đáng', 'chat' == 'chất')
        sup = [tuple(vi_phrases.strict(t) for t in x.split()) for x in G['superlatives']]
        sadj = {vi_phrases.strict(x) for x in G.get('superlativeAdj', [])}
        scmp = {vi_phrases.strict(x) for x in G.get('comparatives', ['hơn'])}
        smul = {vi_phrases.strict(x) for x in G.get('multipliers', ['gấp'])}
        sint = {vi_phrases.strict(x) for x in ('quá', 'lắm', 'thật', 'vô cùng')}
        stw = [vi_phrases.strict(w['w']) for w in ws]
        units = {fold(x) for x in G['units']}
        starts = set()
        for sn in sents: starts.add(id(sn[0]))
        scored = []
        for i, w in enumerate(ws):
            raw_w = w['w'].strip(' ,.!?…;:')
            sc, kind = 0.0, None
            if re.fullmatch(r'\d[\d.,]*%?', raw_w) and not (ws[i - 1]['f'] in ('quoc', 'lo') if i else False):
                sc += 2.0; kind = 'number'
                if i + 1 < len(ws) and ws[i + 1]['f'] in units: sc += 1.0
            span = None
            for tup in sup:
                n0 = len(tup)
                if tuple(stw[i:i + n0]) == tup and not (tup[-1] == 'nhất' and i + n0 < len(ws) and stw[i + n0] == 'là'):     # 'nhất là' = 'especially', not a superlative
                    sc += 2.0; kind = kind or 'superlative'; span = (i, i + n0 - 1)
                    if stw[i + n0 - 1] != 'nhất' and i + n0 < len(ws) and stw[i + n0] in sadj and ws[i + n0]['s'] - ws[i + n0 - 1]['e'] < 0.3: span = (i, i + n0)   # 'siêu nhanh', 'cực kỳ đẹp'
                    break
            if kind != 'superlative' and stw[i] in sadj and i + 1 < len(ws) and stw[i + 1] in sint:        # '<adj> quá/lắm'
                sc += 2.0; kind = 'superlative'; span = (i, i + 1)
            if kind != 'superlative' and stw[i] in scmp and i + 1 < len(ws) and stw[i + 1] in sadj:        # 'hơn <adj>'
                sc += 2.0; kind = 'superlative'; span = (i, i + 1)
            if kind not in ('superlative', 'number') and stw[i] in smul and i + 2 < len(ws) and re.fullmatch(r'\d+', stw[i + 1]) and stw[i + 2] == 'lần':   # 'gấp 10 lần'
                sc += 2.0; kind = 'superlative'; span = (i, i + 2)
            if raw_w[:1].isupper() and id(w) not in starts and not re.search(r'[.!?…]$', ws[i - 1]['w'] if i else '.') and w['f'] not in FUNC and len(raw_w) > 1:
                sc += 1.5; kind = kind or 'proper'
            if w['w'].endswith('!'): sc += 1.0; kind = kind or 'exclaim'
            if w.get('p', 1) < G.get('bigWordMinP', 0.6): continue          # low-confidence word: never a big-word candidate
            if kind == 'proper' and sc <= 1.5 + 1e-9:
                # a 1-syllable proper noun is usually a fragment of a longer name ('Nội' of Hà Nội, 'Mai', 'Hành'): needs a capitalised neighbour or >= bigWordMinProperChars letters
                nb = [ws[j] for j in (i - 1, i + 1) if 0 <= j < len(ws)]
                has_cap_nb = any(n_['w'].strip(' ,.!?…;:')[:1].isupper() and n_['f'] not in FUNC and n_.get('p', 1) >= G.get('bigWordMinP', 0.6) for n_ in nb)
                if len(raw_w) < G.get('bigWordMinProperChars', 7) and not has_cap_nb: continue
            if sc > 0: scored.append(dict(i=i, sc=sc, kind=kind, span=span))
        by_i = {x['i']: x for x in scored}

        def span_of(x):
            i = x['i']; lo = hi = i
            if x['kind'] == 'proper':
                while lo > 0 and by_i.get(lo - 1, {}).get('kind') == 'proper': lo -= 1
                while hi + 1 < len(ws) and by_i.get(hi + 1, {}).get('kind') == 'proper': hi += 1
                lo = max(lo, hi - G['bigWordMaxWords'] + 1)
            elif x['kind'] == 'number':
                if hi + 1 < len(ws) and ws[hi + 1]['f'] in units: hi += 1
                else:
                    while hi + 1 < len(ws) and hi - lo < 2 and ws[hi + 1]['f'] not in FUNC and len(' '.join(w['w'] for w in ws[lo:hi + 2])) <= G['bigWordMaxChars']: hi += 1
            else:
                if x.get('span'): lo, hi = x['span']
                if x['kind'] == 'superlative' and stw[lo] == 'nhất' and lo > 0 and stw[lo - 1] in sadj and ws[lo]['s'] - ws[lo - 1]['e'] < 0.3: lo -= 1   # '<adj> nhất'
                elif x['kind'] != 'superlative' and lo > 0 and ws[lo - 1]['f'] not in FUNC and ws[lo]['s'] - ws[lo - 1]['e'] < 0.3: lo -= 1
            txt = ' '.join(w['w'] for w in ws[lo:hi + 1]).strip(' ,.!?…;:')
            letters = len(re.sub(r'[^\w]', '', txt))
            if any(w.get('p', 1) < G.get('bigWordMinP', 0.6) for w in ws[lo:hi + 1]) or (x['kind'] != 'number' and letters < G.get('bigWordMinChars', 4)) \
               or (x['kind'] == 'proper' and hi == lo and letters < G.get('bigWordMinProperChars', 7)):
                txt = ''                                        # fragment / 1-syllable / low-confidence: rejected by the caller (-> next candidate)
            if x['kind'] == 'superlative' and lo == hi and stw[lo] == 'nhất': txt = ''      # bare 'nhất' without its adjective says nothing
            if x['kind'] == 'superlative' and lo == hi and stw[lo] == 'nhất': txt = ''      # bare 'nhất' without its adjective says nothing
            return lo, hi, txt

        # (a) big-word on the strongest keyword roughly every bigWordEverySec (kind-balanced: a proper noun only wins when nothing better is in the window)
        lo_s, hi_s = G['bigWordEverySec']; cursor = ws[0]['s'] + 3.0; placed = 0
        existing_bw = [b['t0'] for b in beats if b['type'] == 'big-word']
        while cursor < t_last - 2.0:
            win = [x for x in scored if cursor <= ws[x['i']]['s'] <= cursor + (hi_s - lo_s + 4) and in_kept(ws[x['i']]['s']) and x['sc'] >= G['bigWordMinScore']
                   and not any(abs(ws[x['i']]['s'] - t) < lo_s * 0.6 for t in existing_bw) and not busy(ws[x['i']]['s'] - 0.3, ws[x['i']]['s'] + W['holdSec'], ('big-word', 'title-burst')) and not fullscreen_busy(ws[x['i']]['s'] - 0.3, ws[x['i']]['s'] + W['holdSec'])]
            if not win:
                cursor += lo_s * 0.5; continue
            best = None
            for x in sorted(win, key=lambda x: (-(x['sc'] + (0.4 if x['kind'] != 'proper' else 0)), ws[x['i']]['s'])):
                l0, h0, txt = span_of(x)
                if txt and len(txt) <= G['bigWordMaxChars'] + 6: best = x; break
            if best is None: cursor += lo_s * 0.5; continue
            t = ws[l0]['s']
            add(dict(type='big-word', t0=round(t - 0.25, 2), t1=round(t + W['holdSec'], 2), text=txt.upper() if False else txt, sparkles=best['kind'] in ('superlative', 'exclaim')), f'generic big-word ({best["kind"]}, score {best["sc"]:.1f})')
            existing_bw.append(t); placed += 1; gen_report.append(('big-word', txt)); cursor = t + lo_s
        # (b) topic / title cards at sentence-GROUP boundaries (a long pause, or a group already >= groupMinSec long)
        groups, cur_g = [], []
        for sn in sents:
            if cur_g and (sn[0]['s'] - cur_g[-1][-1]['e'] >= G['groupGapSec'] or (cur_g[-1][-1]['e'] - cur_g[0][0]['s'] >= G['groupMinSec'] and re.search(r'[.!?…]$', cur_g[-1][-1]['w']))):
                groups.append(cur_g); cur_g = []
            cur_g.append(sn)
        if cur_g: groups.append(cur_g)
        used_cards = sum(1 for b in beats if b['type'] in ('topic-card', 'info-scene'))
        taken_full = [(b['t0'], b['t1']) for b in beats if b['type'] in ('info-scene', 'topic-card', 'framed-focus', 'title-burst')]
        for gi, g in enumerate(groups):
            first_s = g[0]
            if gi == 0 or used_cards >= G['topicCardMax'] or first_s[0]['s'] < ws[0]['s'] + G['topicCardFirstAfterSec'] or not in_kept(first_s[0]['s']):
                continue
            txt_words = [w for sn in g[:2] for w in sn]
            t0 = first_s[0]['s']; t1 = min(t0 + G['topicCardMaxSec'], txt_words[-1]['e'] + 0.4); t1 = max(t1, t0 + G['topicCardMinSec'])
            if any(t0 < b1 + 0.8 and b0 - 0.8 < t1 for b0, b1 in taken_full) or (t1 > t_last + 0.3) or (G['cta']['alwaysAtEnd'] and t1 > t_last - G['cta']['holdSec'] - 0.2):
                continue
            # v4.1: card / title text = complete key phrases (never mid-sentence chunks); no good phrase -> no card
            gu = []
            for sn in g[:2]: gu += PH.units(sn)
            phrases = PH.pick_many(gu, Tc['maxLines'] + 1, t_lo=t0 - 0.01, t_hi=t1 - 0.3, min_gap=0.5)
            tb_ok = gi >= 1 and G['titleBurst']['enabled'] and (t_end - ws[0]['s']) >= G['titleBurst']['minVideoSec'] and not any(b['type'] == 'title-burst' for b in beats) and not any(b['type'] == 'big-word' and b['t0'] < t0 + T['holdSec'] and t0 < b['t1'] for b in beats)
            minL = 1 + G.get('topicCardMinLines', 2)
            if len(phrases) < (1 if tb_ok else minL):
                continue
            if tb_ok:
                # the title is the best-scoring complete phrase of the first ~searchSec seconds of the group (earliest on ties), the sub the best one after it
                near = [c for c in PH.candidates(gu, t_lo=t0 - 0.01, t_hi=t0 + A['phrases'].get('searchSec', 5.0), max_words=4, max_chars=22) if c['score'] >= A['phrases'].get('titleMinScore', 0)]
                if near:
                    tp = near[0]
                    rest = PH.best([u for u in gu if u['s'] >= tp['e'] - 0.01 and u['s'] <= tp['e'] + 4.0], max_words=5) if G['titleBurst']['sub'] else None
                    tt0 = max(t0, tp['s'] - 0.15)
                    if not any(tt0 < b1 + 0.8 and b0 - 0.8 < tt0 + T['holdSec'] for b0, b1 in taken_full) and not any(b['type'] == 'big-word' and b['t0'] < tt0 + T['holdSec'] and tt0 < b['t1'] for b in beats):
                        add(dict(type='title-burst', t0=round(tt0, 2), t1=round(tt0 + T['holdSec'], 2), title=tp['text'], sub=(rest['text'] if rest else None), rec='REC', timeline=True, _recSrcT=round(tt0, 2)), f'generic: first topic change (group {gi + 1}) -> title-burst "{tp["text"]}" (phrase score {tp["score"]:.1f})')
                        taken_full.append((tt0, tt0 + T['holdSec'])); gen_report.append(('title-burst', tp['text'])); continue
                if len(phrases) < minL: continue
            if len(phrases) < minL: continue
            header = phrases[0]['text']
            lines = []
            for li, ph_ in enumerate(phrases[1:Tc['maxLines'] + 1]):
                ln = dict(t=round(ph_['s'], 2), text=ph_['text'])
                if li == 0: ln['pill'] = True
                elif li % 2 == 1: ln['hl'] = True
                lines.append(ln)
            n_cards = sum(1 for b in beats if b['type'] == 'topic-card')
            src = f'project/still_{n_cards + 1}.jpg'
            still_jobs.append((src, round(t0 + 0.6, 2)))
            add(dict(type='topic-card', t0=round(t0, 2), t1=round(t1, 2), header=header, media=dict(src=src, kind='phone' if portrait else 'window'), lines=lines), f'generic: topic change at sentence-group boundary {gi + 1}')
            taken_full.append((t0, t1)); used_cards += 1; gen_report.append(('topic-card', header))
        # (c) CTA comment-box at the end ALWAYS (unless a CTA keyword rule already placed one)
        if G['cta']['alwaysAtEnd'] and not any(b['type'] == 'comment-box' for b in beats):
            c0 = max(ws[0]['s'], t_last - G['cta']['holdSec'])
            add(dict(type='comment-box', t0=round(c0, 2), t1=round(t_last, 2), typed=G['cta']['typed'], bubble=G['cta']['bubble']), 'generic: CTA at the end (always)')
            gen_report.append(('comment-box', G['cta']['typed']))

    # overlay beats must not sit on top of the generic full-screen cards / title
    for b in [b for b in beats if b['type'] == 'big-word' and str(b.get('_why', '')).startswith('generic')]:
        if any(o['type'] in ('topic-card', 'info-scene', 'framed-focus') and o['t0'] < b['t1'] and b['t0'] < o['t1'] for o in beats):
            beats.remove(b)

    # ---- screen-recording b-roll windows -> dark top caption (captionAnchor) ----
    screen_wins = []
    sp = a.screen or os.path.join(pdir0, 'screen_broll.json')
    if A.get('captionAnchorDefaults', {}).get('autoDetectScreenBroll', True):
        if not os.path.exists(sp) and raw_path and os.path.exists(raw_path):
            import subprocess as _sp
            _sp.run([sys.executable, os.path.join(ROOT, 'scripts', 'detect_screen_broll.py'), raw_path, '--out', sp], check=False, capture_output=True)
        if os.path.exists(sp):
            screen_wins = json.load(open(sp)).get('windows', [])

    # ---- screen model shared by brand-logo placement and the collision pass (canvas fractions) ----
    probe_full = {}
    try: probe_full = json.load(open(probe_p))
    except Exception: pass
    ci = logo_place.canvas_info(CFG, probe_full)
    orient = 'vertical' if ci['W'] < ci['H'] else ('square' if ci['W'] == ci['H'] else 'horizontal')
    LY = ci['prof']
    Hd = 1920.0 if orient == 'vertical' else 1080.0; Wd = 1080.0 if orient != 'horizontal' else 1920.0     # design px (style.config.json layout.* values)

    def rects_of(b):
        """screen rectangles as fractions of the canvas, incl. the face-aware vertical shift `dy` (title: only the title block, the timeline stays)"""
        rs = rects_base(b); dy = b.get('dy', 0) or 0
        if not dy: return rs
        if b['type'] == 'title-burst': return [(r[0], r[1] + dy, r[2], r[3] + dy) if i == 0 else r for i, r in enumerate(rs)]
        return [(r[0], r[1] + dy, r[2], r[3] + dy) for r in rs]

    def rects_base(b):
        """screen rectangles (x0, y0, x1, y1) as fractions of the canvas that a beat covers"""
        ty = b['type']; sf = LY['safe']
        if ty == 'title-burst':
            t_ = LY['title']; r = [(t_['xR'], t_['recYR'] - 0.01, 1 - sf['rightR'], t_['yR'] + (t_['font'] * 1.15 + (t_['subFont'] * 1.2 if b.get('sub') else 0)) / Hd)]
            if b.get('timeline'): r.append((0.5 - t_['timelineWR'] / 2, t_['timelineYR'], 0.5 + t_['timelineWR'] / 2, t_['timelineYR'] + t_['timelineH'] / Hd))
            return r
        if ty in ('big-word', 'selection-box'): return [(0.05, LY['bigWord']['yR'], 0.95, LY['bigWord']['yR'] + LY['bigWord']['font'] * 1.2 / Hd + (0.03 if ty == 'selection-box' else 0))]
        if ty == 'prompt-box': p_ = LY['prompt']; return [(p_['xR'], p_['yR'], p_['xR'] + p_['wR'], p_['yR'] + p_['h'] / Hd)]
        if ty == 'comment-box': c_ = LY['comment']; return [(c_['xR'], c_['yR'] + min(0, c_['bubbleDyR']), c_['xR'] + c_['wR'], c_['yR'] + c_['h'] / Hd)]
        if ty == 'chip-stack':
            c_ = LY['chips']; n_ = len(b.get('items', [])); rows = -(-n_ // max(1, c_['cols'])); cw_ = c_['w'] / Wd if 'w' in c_ else c_['wR']
            return [(c_['xR'], c_['yR'], min(1.0, c_['xR'] + min(n_, c_['cols']) * (cw_ + c_['gapX'] / Wd)), c_['yR'] + rows * (c_['h'] + c_['gapY']) / Hd)]
        if ty == 'sticker': st_ = LY['sticker']; return [(0.0, min(st_['yR'], st_['topYr'], st_['cardYr']), 1.0, max(st_['yR'], st_['topYr'], st_['cardYr']) + st_['size'] / Hd + 0.03)]
        if ty == 'avatar-chain': return [(0.05, 0.80, 0.95, 0.89)]
        if ty == 'brand-logo':
            if 'x' in b and 'y' in b:
                cw_, ch_ = logo_place.card_size(b['name'], ci, b.get('scale', 1.0), LGpx)
                return [(b['x'] - cw_ / 2 / ci['W'], b['y'], b['x'] + cw_ / 2 / ci['W'], b['y'] + ch_ / ci['H'])]
            lg_ = LY['logo']; return [(0.5 - lg_['size'] / 2 / Wd, lg_['yR'], 0.5 + lg_['size'] / 2 / Wd, lg_['yR'] + (lg_['size'] + lg_['nameFont'] * 1.7) / Hd)]
        if ty == 'stars': y_ = CFG['beats']['stars']['yRatio']; return [(0.05, y_, 0.95, y_ + 0.07)]
        if ty in ('info-scene', 'topic-card', 'broll', 'framed-focus'): return [(0.0, 0.0, 1.0, 1.0)]
        if ty == 'text-behind-speaker':
            if b.get('items'): return [(it['ink'][0] / ci['W'], it['ink'][1] / ci['H'], (it['ink'][0] + it['ink'][2]) / ci['W'], (it['ink'][1] + it['ink'][3]) / ci['H']) for it in b['items'] if it.get('ink')]    # v4.2: the real ink boxes chosen by make_masks tune
            return [(0.0, b.get('y', 0.3), 1.0, b.get('y', 0.3) + b.get('h', 0.2))]
        if ty == 'illustration':
            if 'x' in b and 'y' in b:
                cw_, ch_ = logo_place.card_size(b.get('label', ''), ci, b.get('scale', 1.0), LGpx, bool(b.get('pill')))
                return [(b['x'] - cw_ / 2 / ci['W'], b['y'], b['x'] + cw_ / 2 / ci['W'], b['y'] + ch_ / ci['H'])]
            lg_ = LY['logo']; return [(0.5 - lg_['size'] / 2 / Wd, lg_['yR'], 0.5 + lg_['size'] / 2 / Wd, lg_['yR'] + (lg_['size'] + lg_['nameFont'] * 1.7) / Hd)]
        return []
    LGpx = dict(size=round(LY['logo']['size'] * ci['u']), nameFont=round(LY['logo']['nameFont'] * ci['u']))

    # ---- FACES (cached public/project/faces.json): used by brand-logo placement AND by the face-aware shift of titles / chips / prompt / comment ----
    FP = A.get('facePlacement', {})
    faces_all = None
    if FP.get('enabled', True) or CFG.get('brandLogos', {}).get('placement', {}).get('enabled', True):
        fpath_all = os.path.join(pdir0, 'faces.json')
        if not os.path.exists(fpath_all) and raw_path and os.path.exists(raw_path):
            import subprocess as _sp
            r_ = _sp.run([sys.executable, os.path.join(ROOT, 'scripts', 'detect_faces.py'), raw_path, '--out', fpath_all], check=False, capture_output=True, text=True)
            if r_.returncode != 0: print('face detection failed (needs: pip install opencv-python-headless==4.10.0.84): ' + ((r_.stderr or '').strip().splitlines() or ['?'])[-1] + ' -> no face-aware placement (corner fallback for logos)', file=sys.stderr)
        faces_all = logo_place.load_faces(fpath_all)
        if not faces_all: print('no faces.json -> titles/chips/logos are NOT face-aware', file=sys.stderr)

    # ---- v4.1  SCENE STYLES: framed-focus (device mock-up) + text-behind-speaker --------------------------------------------------
    FF = A.get('framedFocus', {}); TBc = A.get('textBehind', {})
    if FF.get('enabled', True) and FF.get('convertTopicCards', True):
        # a topic-card whose media is only a placeholder / still of the footage itself becomes a framed-focus (the speaker IS the media); real screenshots keep the card
        n_ff = 0
        for b in list(beats):
            if b['type'] != 'topic-card': continue
            src = (b.get('media') or {}).get('src', '')
            real = os.path.exists(os.path.join(pdir0, os.path.basename(src))) and not os.path.basename(src).startswith('still_') and os.path.basename(src) not in ('phone.png', 'editor.png')
            if real: continue
            dev = FF.get('devices', ['phone', 'window'])[n_ff % len(FF.get('devices', ['phone', 'window']))]; n_ff += 1
            lines = [dict(t=l['t'], text=l['text'], pill=bool(l.get('pill'))) for l in b['lines'][:2]]
            if lines and not any(l['pill'] for l in lines): lines[0]['pill'] = bool(FF.get('firstLinePill', False))
            t0_, t1_, hd_ = b['t0'], b['t1'], b.get('header') or ''; b.clear(); b.update(type='framed-focus', t0=t0_, t1=t1_, header=hd_, lines=lines, device=dev, _why=f'converted from topic-card (media = placeholder/still of the footage): speaker framed in a {dev} mock-up')
            still_jobs[:] = [j for j in still_jobs if j[0] != src]
    if FF.get('enabled', True) and FF.get('extraEverySec') and (t_end - ws[0]['s']) >= TBc.get('minVideoSec', 15):
        # more framed-focus moments (~1 per extraEverySec s): the first two complete phrases of a sentence = header (white) + highlighted line (yellow pill)
        e_lo, e_hi = FF['extraEverySec']; busy_ = ('title-burst', 'chip-stack', 'prompt-box', 'comment-box', 'avatar-chain', 'info-scene', 'topic-card', 'framed-focus', 'broll', 'brand-logo')
        ffs = sorted([b['t1'] for b in beats if b['type'] == 'framed-focus']); n_x = sum(1 for b in beats if b['type'] == 'framed-focus')
        last_ff = ws[0]['s'] - e_lo
        for sn in sents:
            t0 = round(sn[0]['s'], 2)
            if t0 - last_ff < e_lo or t0 < ws[0]['s'] + FF.get('firstAfterSec', 14) or not in_kept(t0): continue
            if any(abs(t0 - b['t0']) < e_lo and b['type'] == 'framed-focus' for b in beats): continue
            t1 = round(t0 + FF.get('holdSec', 3.4), 2)
            if t1 > t_last - (G['cta']['holdSec'] if G['cta'].get('alwaysAtEnd') else 0) - 0.4 or not in_kept(t1 - 0.1): continue
            if any(b['type'] in busy_ and b['t0'] < t1 + 0.5 and t0 - 0.5 < b['t1'] for b in beats): continue
            pk = PH.pick_many(PH.units(sn), 3, t_lo=t0 - 0.01, t_hi=t1 - 0.4, min_gap=0.3)
            if len(pk) < 2: continue
            n_x += 1; dev = FF.get('devices', ['phone', 'window'])[(n_x - 1) % len(FF.get('devices', ['phone', 'window']))]
            add(dict(type='framed-focus', t0=t0, t1=t1, header=pk[0]['text'], lines=[dict(t=round(pk[1]['s'], 2), text=pk[1]['text'], pill=True)], device=dev), f'framed-focus: key phrases of the sentence at {t0:.1f}s in a {dev} mock-up')
            last_ff = t1
    skips = []          # v4.2: every beat that was NOT made / dropped, with the reason (printed + public/project/beats_skips.json) - nothing is skipped silently
    def skip(kind, t, why):
        skips.append(dict(beat=kind, t=round(t, 2), why=why)); print(f'skip {kind} @ {t:.2f}s: {why}', file=sys.stderr)

    # ---- v4.4 PHONE / WINDOW FRAME CAP (verified.md V14): <= max(1, round(output seconds / 30)) framed-focus beats, never back-to-back (gap >= minGapSec) ----
    if FF.get('enabled', True):
        out_dur_ = sum(x['srcOut'] - x['srcIn'] for x in segs) if segs else (t_end - ws[0]['s'])
        cap_ff = max(1, int(out_dur_ // float(FF.get("perSec", 30)))) * int(FF.get('maxPerPeriod', 1)); min_gap_ff = float(FF.get('minGapSec', 15))
        def _out(t): return sum(max(0.0, min(t, x['srcOut']) - x['srcIn']) for x in segs) if segs else t        # source s -> output s (the gap is judged on the OUTPUT timeline)
        kept_ff = []
        for b in sorted([b for b in beats if b is not None and b['type'] == 'framed-focus'], key=lambda x: x['t0']):
            why_ = None
            if len(kept_ff) >= cap_ff: why_ = f'cap reached ({cap_ff} per {out_dur_:.0f}s of output; maxPerPeriod={FF.get("maxPerPeriod", 1)} per {FF.get("perSec", 30)}s)'
            elif kept_ff and _out(b['t0']) - _out(kept_ff[-1]['t1']) < min_gap_ff: why_ = f'only {_out(b["t0"]) - _out(kept_ff[-1]["t1"]):.1f}s after the previous phone/window frame (< minGapSec {min_gap_ff:.0f}s: never back-to-back)'
            if why_: beats.remove(b); skips.append(dict(beat='framed-focus', t=round(b['t0'], 2), why=f'"{b.get("header", "")}" dropped: {why_}'))
            else: kept_ff.append(b)
    if not (TBc.get('enabled', True)): skip('text-behind-speaker', 0, 'disabled in style.config.json autoBeats.textBehind.enabled')
    elif not faces_all: skip('text-behind-speaker', 0, 'no faces.json (run scripts/detect_faces.py) - cannot verify the speaker')
    elif (t_end - ws[0]['s']) < TBc.get('minVideoSec', 15): skip('text-behind-speaker', 0, f"video shorter than minVideoSec={TBc.get('minVideoSec', 15)}s")
    if TBc.get('enabled', True) and faces_all and (t_end - ws[0]['s']) >= TBc.get('minVideoSec', 15):
        T_ = CFG['beats']['textBehind']; ev_lo, ev_hi = TBc.get('everySec', [22, 30])
        # only beats that own the whole screen or the top text zone stop a text-behind beat; every other beat in the window (chips, prompt, logo, ...) becomes a BLOCKER
        # that the placement search keeps free (make_masks.py tune), so the beat triggers whenever there is a real empty spot.
        busy_types = ('info-scene', 'topic-card', 'framed-focus', 'broll', 'title-burst', 'big-word', 'selection-box')
        _pun = CFG['framing']['punch']['settleFrames'] / float(probe_full.get('fps') or 30)
        def steady(ts, te):
            """text-behind needs a CONSTANT framing zoom (the mask is warped through it): clip the window to ONE EDL segment, after the punch settle.
            v4.3: the window may SPAN a jump cut into the next segment(s) when their framing is the same, no zoom ramp, no punch and the kept gap is <= tbsMaxCutGapSec"""
            if not segs: return ts, te, ''
            for gi, sg in enumerate(segs):
                if sg['srcIn'] - 1e-3 <= ts < sg['srcOut']:
                    if sg.get('zoom'): return None, None, f"segment {sg['id']} has a zoom ramp (zoom not constant)"
                    a_ = max(ts, sg['srcIn'] + (_pun + 0.06 if (sg.get('punch') or sg.get('framing') in ('mid', 'tight')) else 0.0)); z_ = min(te, sg['srcOut'] - 0.04)
                    why = f"inside {sg['id']} ({sg.get('framing')})"; cur = sg; nj = 0
                    while z_ < te - 1e-3 and gi + 1 < len(segs):
                        nx = segs[gi + 1]
                        if nx['srcIn'] - cur['srcOut'] > TBc.get('tbsMaxCutGapSec', 0.6) or nx.get('framing') != cur.get('framing') or nx.get('zoom') or nx.get('punch'): break
                        gi += 1; cur = nx; nj += 1; z_ = min(te, nx['srcOut'] - 0.04); why += f" + {nx['id']} (spans {nj} jump cut{'s' if nj > 1 else ''}, same framing)"
                    return a_, z_, why
            return None, None, 'keyword time is inside a cut-out part'
        cands = []
        for sn in sents:
            for c in PH.candidates(PH.units(sn), max_words=TBc.get('maxWords', 3), max_chars=TBc.get('maxChars', 16)):
                if c['score'] >= TBc.get('minScore', 2.0): cands.append(c)
        if not cands: skip('text-behind-speaker', ws[0]['s'], f"no key phrase scored >= minScore {TBc.get('minScore', 2.0)}")
        n_tb = 0; start = ws[0]['s'] + TBc.get('firstAfterSec', 6); last_end = start - ev_lo
        for c in sorted(cands, key=lambda c: c['s']):
            if c['s'] < start or c['s'] - last_end < ev_lo: continue
            win = [x for x in cands if c['s'] <= x['s'] <= c['s'] + 6 and x['s'] - last_end >= ev_lo]
            best = max(win, key=lambda x: (x['score'], -x['s']))
            if best is not c: continue
            tag = f'"{best["text"]}"'
            t0 = round(max(ws[0]['s'], best['s'] - 0.1), 2); t1 = round(max(best['e'] + 1.0, t0 + TBc.get('holdSec', 2.2)), 2)
            a_, z_, why_ = steady(t0, t1)
            if a_ is None: skip('text-behind-speaker', best['s'], f'{tag}: {why_}'); continue
            t0, t1 = round(a_, 2), round(z_, 2)
            if t1 - t0 < TBc.get('tbsMinHoldSec', TBc.get('minHoldSec', 1.4)): skip('text-behind-speaker', best['s'], f"{tag}: only {t1 - t0:.2f}s of steady framing (one framing, jump cuts included) (< tbsMinHoldSec {TBc.get('tbsMinHoldSec', TBc.get('minHoldSec', 1.4))}s)"); continue
            if t1 > t_last - (G['cta']['holdSec'] if G['cta'].get('alwaysAtEnd') else 0) - 0.3: skip('text-behind-speaker', best['s'], f'{tag}: collides with the closing CTA'); continue
            if not in_kept(t0) or not in_kept(t1 - 0.1): skip('text-behind-speaker', best['s'], f'{tag}: window falls on a cut-out part'); continue
            bz = [b['type'] for b in beats if b['type'] in busy_types and b['t0'] < t1 + 0.4 and t0 - 0.4 < b['t1']]
            if bz: skip('text-behind-speaker', best['s'], f"{tag}: {', '.join(sorted(set(bz)))} owns the screen/top text zone in the same window"); continue
            fr = logo_place.face_rect(faces_all, segs, CFG, ci, t0, t1)
            if not fr: skip('text-behind-speaker', best['s'], f'{tag}: no face detected in the window'); continue
            words_ = best['text'].split()
            text = best['text'] if (len(words_) < 2 or len(best['text']) <= 12) else ' '.join(words_[:len(words_) // 2 + len(words_) % 2]) + '\n' + ' '.join(words_[len(words_) // 2 + len(words_) % 2:])
            n_tb += 1
            font = min(T_['fontPx'] * ci['u'], ci['W'] * T_['maxWidthR'] / (max(len(l) for l in text.split('\n')) * T_['glyphEm']))
            blockH = len(text.split('\n')) * font * T_['lineHeight']
            top = min(max(fr[1] - TBc.get('centerAboveFaceTopFaceH', 0.10) * (fr[3] - fr[1]) - blockH / 2, 0.045 * ci['H']), 0.5 * ci['H'])   # provisional: make_masks.py tune puts the real items into the empty space
            blk = [[round(v, 4) for v in r] for o in beats if o['type'] not in ('info-scene', 'topic-card', 'broll') and o['t0'] < t1 and t0 < o['t1'] for r in rects_of(o)]
            tb_ = dict(type='text-behind-speaker', id=f'tbs{n_tb}', t0=t0, t1=t1, text=text, y=round(top / ci['H'], 3), h=round(blockH / ci['H'], 3), color=('yellow' if n_tb % 2 == 0 else 'white'), anim=TBc.get('anims', ['slide', 'type'])[(n_tb - 1) % len(TBc.get('anims', ['slide', 'type']))])
            if blk: tb_['_blockers'] = blk
            add(tb_, f'text-behind-speaker: key phrase "{best["text"]}" (score {best["score"]:.1f}) {why_}')
            last_end = t1

    # ---- BRAND LOGOS: first mention of a well-known brand whose REAL logo file exists in public/project/logos/<slug>.(svg|png) ----
    BL = CFG.get('brandLogos', {})
    if BL.get('enabled', True) and BL.get('brands'):
        ldir = os.path.join(pdir0, 'logos')
        meta = {}
        try:
            _m = json.load(open(os.path.join(ldir, 'logos.json'), encoding='utf-8'))
            meta = _m.get('brands', _m) if isinstance(_m, dict) else {}
        except Exception:
            pass
        _strict = lambda x: unicodedata.normalize('NFC', re.sub(r'[^\w]', '', x.lower()))
        raw_t = [_strict(w['w']) for w in ws]
        found, missing = [], {}
        for br in BL['brands']:
            fn = next((os.path.join(ldir, br['slug'] + e) for e in ('.svg', '.png', '.webp', '.jpg') if os.path.exists(os.path.join(ldir, br['slug'] + e))), None)
            first = None
            for al in br['aliases']:
                toks = al.split()
                strict = any(ord(ch) > 127 for ch in al)
                fl = [fold(x) for x in toks]
                st = [_strict(x) for x in toks]
                n = len(toks)
                for i in range(len(ws) - n + 1):
                    ok = all((raw_t[i + k] == st[k]) if strict else (ws[i + k]['f'] == fl[k]) for k in range(n))
                    if not ok and n > 1 and not strict:
                        ok = ws[i]['f'] == ''.join(fl)                      # 'chatgpt' written as one word
                    if ok and br.get('caseSensitive') and not ws[i]['w'][:1].isupper(): ok = False
                    if ok and (first is None or ws[i]['s'] < first): first = ws[i]['s']; break
            if first is None: continue
            if not fn and BL.get('autoFetch', True):      # v4.2: the brand is MENTIONED but has no file -> fetch the real logo now (Simple Icons -> svgl -> favicon), never draw one
                fn = _fetch_logo(br, ldir); meta = _reload_logo_meta(ldir) if fn else meta
            if not fn: missing[br['name']] = round(first, 2); continue
            found.append((first, br, fn))
        found.sort(key=lambda x: x[0])
        PL = BL.get('placement', {})
        faces = faces_all
        last, nlogo = -1e9, 0
        for first, br, fn in found:
            if nlogo >= BL.get('maxPerVideo', 12) or not in_kept(first): continue
            at = max(first, last + BL.get('minGapSec', 4.0))        # max ~1 logo per minGapSec: a close second brand is delayed (<= maxDelaySec after its mention) instead of lost
            if at - first > BL.get('maxDelaySec', 2.0) or not in_kept(at):
                print(f"brand logo skipped (spacing): {br['name']} @ {first:.2f}s", file=sys.stderr); continue
            m = meta.get(br['slug'], {}) if isinstance(meta, dict) else {}
            t0 = round(max(ws[0]['s'], at - BL.get('leadSec', 0.1)), 2)
            hold_ = BL.get('holdSec', 2.0)
            # v4.3 DEDUPE: the same brand already shown at that moment by a sticker tile / avatar chain / chip / title -> no second logo (was: Claude logo + Claude sticker side by side)
            _bn = [fold(x) for x in [br['name']] + list(br.get('aliases', [])) if len(fold(x)) >= 3]
            def _brand_shown(a_, z_):
                for o in beats:
                    if o['type'] in ('brand-logo', 'stars') or not (o['t0'] < z_ + 0.4 and a_ - 0.4 < o['t1']): continue
                    vals = [o.get('brand'), o.get('label'), o.get('left'), o.get('right'), o.get('chip'), o.get('text'), o.get('title'), o.get('headline'), o.get('name')]
                    if any(isinstance(v_, str) and any(bn in fold(v_) for bn in _bn) for v_ in vals): return o
                return None
            dup_ = _brand_shown(t0, t0 + hold_)
            if dup_: skip('brand-logo', t0, f"{br['name']}: same brand already shown by a {dup_['type']} at {dup_['t0']:.1f}-{dup_['t1']:.1f}s (deduped)"); continue
            bl_ = dict(type='brand-logo', t0=t0, t1=round(t0 + hold_, 2), name=br['name'], logo='project/logos/' + os.path.basename(fn), color=(m.get('color') if isinstance(m, dict) else None) or br.get('color'))
            why_pl = ''
            if PL.get('enabled', True):
                sfp = dict(top=ci['H'] * LY['safe']['topR'], left=ci['W'] * LY['safe']['leftR'], right=ci['W'] * LY['safe']['rightR'], bottom=ci['H'] * LY['safe']['bottomR'])
                # v4.3: a logo that collides is RE-SLOTTED first (every slot x every scale in logo_place.place), then RE-TIMED (+0.4s steps after the mention, never over a full-screen scene / cut), only then dropped
                pl_ = None; tried_ = 0; fx = None; fb_ = None
                for pass_, ex_ in enumerate([PL.get('faceExpand', {'x': 0.2, 'up': 0.45, 'down': 0.2}), PL.get('relaxedFaceExpand')]):
                    if ex_ is None or pl_ is not None or fb_ is not None: break      # v4.4: pass 2 = smaller hair/chin margin + smaller scales (ladder) BEFORE dropping the logo
                    for off_ in [0.0] + list(BL.get('retryOffsetsSec', [0.4, 0.8, 1.2, 1.6, 2.0, 2.5, -0.15])):
                        tt = round(max(ws[0]['s'], t0 + off_), 2); zz = round(tt + hold_, 2)
                        if tt < first - 0.25 or tt - first > BL.get('relocateMaxSec', 2.6): continue
                        if not in_kept(tt) or not in_kept(zz - 0.1): continue
                        if any(o['type'] in ('info-scene', 'topic-card', 'broll', 'framed-focus') and o['t0'] < zz and tt < o['t1'] for o in beats): continue
                        if _brand_shown(tt, zz): continue
                        tried_ += 1
                        fr = logo_place.face_rect(faces, segs, CFG, ci, tt, zz)
                        fx_ = logo_place.expand(fr, ex_, ci) if fr else None
                        oth = [[r[0] * ci['W'], r[1] * ci['H'], r[2] * ci['W'], r[3] * ci['H']] for o in beats if o['type'] not in ('brand-logo', 'stars') and o['t0'] < zz and tt < o['t1'] and o['type'] not in ('info-scene', 'topic-card', 'broll') for r in rects_of(o)]
                        c_ = logo_place.place(fx_, oth, br['name'], ci, PL, LGpx, sfp, ci['capY'] - PL.get('captionGapR', 0.045) * ci['H'], strict=bool(fx_))
                        if c_ is None: continue
                        if c_.get('free', True) or not fx_: pl_, fx = c_, fx_; bl_['t0'], bl_['t1'] = tt, zz; why_pl = f'; re-timed {off_:+.2f}s (first slot/time collided)' if off_ else ''; why_pl += ' [relaxed face margin]' if pass_ else ''; break
                        if fb_ is None: fb_ = (c_, fx_, tt, zz, off_)       # face-clear but touching another beat: only if no free slot/time exists
                if pl_ is None and fb_ is not None:
                    pl_, fx, bl_['t0'], bl_['t1'] = fb_[0], fb_[1], fb_[2], fb_[3]; why_pl = f'; re-timed {fb_[4]:+.2f}s' if fb_[4] else ''
                if pl_ is None: skip('brand-logo', t0, f"{br['name']}: no slot clear of the speaker's face / other beats / full-screen scenes ({tried_} candidate times tried; 0 = every retry time was outside the kept cut or over a full-screen scene) - dropped, not 'least overlap'"); continue
                bl_.update(x=round(pl_['cx'] / ci['W'], 4), y=round(pl_['top'] / ci['H'], 4), scale=pl_['scale'])
                why_pl = f"; placed {pl_['mode']} x{pl_['scale']}" + ('' if fx else ' (face not found)') + why_pl
            add(bl_, f"brand logo: first mention of {br['name']} at {first:.2f}s" + why_pl)
            last = at; nlogo += 1
        if missing:
            print('BRAND LOGOS MISSING (mentioned but no file in public/project/logos/ - fetch the REAL logo first, see SKILL.md): ' + ', '.join(f'{k}@{v}s' for k, v in missing.items()), file=sys.stderr)

    # ---- ILLUSTRATIONS (v4.2): every pictureable concept in the speech gets a drawn icon (customer talk -> two people talking, sale -> tag/cart, money, growth, time, AI, learning, documents, jobs ...) ----
    IL = A.get('illustration', {}); REFRAMED = set()
    if IL.get('enabled', True) and IL.get('concepts'):
        import subprocess as _sp
        idir = os.path.join(os.path.dirname(os.path.abspath(a.out)), 'illustrations'); os.makedirs(idir, exist_ok=True)
        fb_dir = os.path.join(ROOT, 'assets', 'illustrations')
        hits = []
        for cpt in IL['concepts']:
            for kw in cpt['keywords']:
                raw_ = kw.split(); toks = [fold(x) for x in raw_]; n_ = len(toks)
                import unicodedata as _ud
                nrm = lambda t_: _ud.normalize('NFC', re.sub(r'[^\w]', '', t_))
                def _m(w_, k):      # ACCENT-SENSITIVE (folding would make 'bán' == 'bạn'), case-sensitive for capitalised keywords ('AI': Vietnamese 'ai' = 'who')
                    a_, b_ = nrm(w_['w']), nrm(raw_[k])
                    return a_ == b_ if b_ != b_.lower() else a_.lower() == b_
                for i in range(len(ws) - n_ + 1):
                    if all(_m(ws[i + k], k) for k in range(n_)): hits.append((ws[i]['s'], ws[i]['e'], cpt, kw))
        hits.sort(key=lambda h: h[0])
        # v4.5 DENSITY (verified.md V21): at most 1 icon per `secPerIcon` of OUTPUT time (<= 4 in 30 s, <= 8 in 60 s), >= minGapSec apart (output time), the same concept not
        # twice within sameConceptGapSec; when hits compete the higher `priority` concept wins (user's own example concepts customer-talk/sales = 10), then the higher `strength`, ties -> earlier; `density.gapMode` = start-to-start (default: starts >= minGapSec apart) or end-to-start (minGapSec clear + holdSec). Dropped hits are logged in the skip report.
        DN = IL.get('density', {})
        if DN.get('enabled', True) and hits:
            def _s2o(t_):
                if not segs: return t_
                c_ = 0.0
                for g_ in segs:
                    if g_['srcIn'] - 1e-6 <= t_ <= g_['srcOut'] + 1e-6: return c_ + (t_ - g_['srcIn']) / g_.get('speed', 1)
                    c_ += (g_['srcOut'] - g_['srcIn']) / g_.get('speed', 1)
                return None
            out_dur_ = sum((g_['srcOut'] - g_['srcIn']) / g_.get('speed', 1) for g_ in segs) if segs else (t_end - ws[0]['s'])
            cap_ = min(IL.get('maxPerVideo', 8), max(1, int(out_dur_ / DN.get('secPerIcon', 7.5) + 0.2)))
            IL['_densityCap'] = cap_; chosen_ = []
            def _viable(h_):        # same hard conditions the placement loop applies at the keyword time, so a hit that cannot be shown never uses up a density slot
                at_ = h_[0]; t0_ = round(max(ws[0]['s'], at_ - IL.get('leadSec', 0.1)), 2); t1_ = round(t0_ + IL.get('holdSec', 2.0), 2)
                if _s2o(at_) is None or not in_kept(at_): return False
                if segs:
                    sg_ = next((x for x in segs if x['srcIn'] - 0.15 <= at_ < x['srcOut']), None)
                    if not sg_ or round(min(t1_, sg_['srcOut'] - 0.05), 2) - round(max(t0_, sg_['srcIn']), 2) < IL.get('minHoldSec', 1.2): return False
                if any(o['type'] in ('info-scene', 'topic-card', 'broll', 'framed-focus') and o['t0'] < t1_ and t0_ < o['t1'] for o in beats): return False
                import unicodedata as _u3; nf3_ = lambda x: _u3.normalize('NFC', x.lower()); cf3_ = {nf3_(x) for k_ in h_[2]['keywords'] + [h_[2].get('label', '')] for x in k_.split() if len(x) >= 3}
                for o in beats:
                    if o.get('type') == 'text-behind-speaker':
                        tf3_ = {nf3_(x) for x in re.sub(r'\s+', ' ', o['text']).split() if len(x) >= 3}
                        if tf3_ & cf3_ and o['t0'] - IL.get('tbsConceptWindowSec', 8.0) < t0_ < o['t1'] + IL.get('tbsConceptWindowSec', 8.0): return False
                return True
            for h_ in sorted([h for h in hits if _viable(h)], key=lambda h: (-h[2].get('priority', 0), -h[2].get('strength', 5), h[0])):
                o_ = _s2o(h_[0]); cid_ = h_[2]['id']
                if len(chosen_) >= cap_: skip('illustration', h_[0], f"{cid_} (\"{h_[3]}\"): density cap {cap_} icons in {out_dur_:.0f}s (1 per {DN.get('secPerIcon', 7.5)}s) - kept the stronger concepts"); continue
                s2s_ = DN.get('gapMode', 'start-to-start') == 'start-to-start'; gap_need_ = DN.get('minGapSec', 5.0) + (0.0 if s2s_ else IL.get('holdSec', 2.0))
                bad_ = next((c_ for c_ in chosen_ if abs(o_ - _s2o(c_[0])) < gap_need_), None)
                if bad_: skip('illustration', h_[0], f"{cid_} (\"{h_[3]}\"): closer than {DN.get('minGapSec', 5.0)}s ({'start of one icon -> start of the next' if s2s_ else 'end of one icon -> start of the next'}) to the higher-priority/earlier {bad_[2]['id']} icon"); continue
                same_ = next((c_ for c_ in chosen_ if c_[2]['id'] == cid_ and abs(o_ - _s2o(c_[0])) < DN.get('sameConceptGapSec', 15.0)), None)
                if same_: skip('illustration', h_[0], f"{cid_} (\"{h_[3]}\"): same concept already shown {abs(o_ - _s2o(same_[0])):.0f}s away (< {DN.get('sameConceptGapSec', 15.0)}s)"); continue
                chosen_.append(h_)
            hits = sorted(chosen_, key=lambda h: h[0])
        PLI = dict(CFG.get('brandLogos', {}).get('placement', {}), **IL.get('placement', {}))
        sfp_i = dict(top=ci['H'] * LY['safe']['topR'], left=ci['W'] * LY['safe']['leftR'], right=ci['W'] * LY['safe']['rightR'], bottom=ci['H'] * LY['safe']['bottomR'])
        nil, last_i, used, il_prev, last_side_ = 0, -1e9, {}, None, None
        import shutil as _shm
        _pdir = os.path.dirname(os.path.abspath(a.out)); _pj = os.path.join(_pdir, 'probe.json'); _pr = json.load(open(_pj)) if os.path.exists(_pj) else {}
        _tool = next((t_ for t_ in [os.environ.get('PERSON_MASK'), CFG['autoBeats'].get('textBehind', {}).get('tool'), '/workspace/render-env/bin/person_mask.py', _shm.which('person_mask.py')] if t_ and os.path.exists(t_)), None)
        _vid = a.raw or os.path.join(_pdir, os.path.basename(_pr.get('file', 'raw.mp4')))
        MASKCTX = dict(ok=bool(_tool and os.path.exists(_vid)), dir=_pdir, video=_vid, tool=_tool, fps=30.0 if _pr.get('original', {}).get('fpsIsVariable') else float((_pr.get('original') or {}).get('fps') or 30.0))
        if not MASKCTX['ok']: print('ILLUSTRATIONS: person_mask.py / video not found -> side slots are chosen from the face box only (no per-frame person-mask check)', file=sys.stderr)
        for hs, he, cpt, kw in hits:
            at = hs
            if nil >= IL.get('maxPerVideo', 8): skip('illustration', at, f"{cpt['id']} (\"{kw}\"): maxPerVideo reached"); continue
            if not in_kept(at): skip('illustration', at, f"{cpt['id']} (\"{kw}\"): the word falls in a cut-out part"); continue
            if at - last_i < IL.get('minGapSec', 3.5): skip('illustration', at, f"{cpt['id']} (\"{kw}\"): within minGapSec of the previous illustration"); continue
            if used.get(cpt['id'], -1e9) + IL.get('sameConceptGapSec', 12) > at: skip('illustration', at, f"{cpt['id']} (\"{kw}\"): same concept shown {at - used[cpt['id']]:.0f}s ago"); continue
            t0 = round(max(ws[0]['s'], at - IL.get('leadSec', 0.1)), 2); t1 = round(t0 + IL.get('holdSec', 2.0), 2)
            if segs:                                        # keep the card inside its EDL segment so it never straddles a cut
                sg_ = next((x for x in segs if x['srcIn'] - 0.15 <= at < x['srcOut']), None)
                if not sg_: skip('illustration', at, f"{cpt['id']}: no EDL segment at {at}s"); continue
                t0 = round(max(t0, sg_['srcIn']), 2); t1 = round(min(t1, sg_['srcOut'] - 0.05), 2)
                if t1 - t0 < IL.get('minHoldSec', 1.2): skip('illustration', at, f"{cpt['id']} (\"{kw}\"): only {t1 - t0:.2f}s left in its segment"); continue
            # v4.3.2: an illustration and a text-behind never share a concept or a moment - the text-behind keeps the screen, the icon moves (out of its window +- tbsPadSec) or is dropped
            tbs_ = [o for o in beats if o is not None and o.get('type') == 'text-behind-speaker']
            if tbs_:
                pad_ = IL.get('tbsPadSec', 0.25); cwin_ = IL.get('tbsConceptWindowSec', 8.0)
                import unicodedata as _u2; nf_ = lambda x: _u2.normalize('NFC', x.lower()); cf_ = {nf_(x) for k_ in cpt['keywords'] + [cpt.get('label', '')] for x in k_.split() if len(x) >= 3}      # accent-SENSITIVE ('bán' != 'bản')
                drop_ = None
                for o in tbs_:
                    tf_ = {nf_(x) for x in re.sub(r'\s+', ' ', o['text']).split() if len(x) >= 3}
                    if tf_ & cf_ and o['t0'] - cwin_ < t0 < o['t1'] + cwin_: drop_ = f"same concept as the text-behind \"{o['text'].replace(chr(10), ' ')}\" ({o['id']}) - the text-behind keeps it"; break
                    if t0 < o['t1'] + pad_ and o['t0'] - pad_ < t1:                       # overlapping time: try to move it
                        if t0 < o['t0'] - pad_ and (o['t0'] - pad_) - t0 >= IL.get('minHoldSec', 1.2): t1 = round(o['t0'] - pad_, 2)
                        elif t1 > o['t1'] + pad_ and t1 - (o['t1'] + pad_) >= IL.get('minHoldSec', 1.2): t0 = round(o['t1'] + pad_, 2)
                        else: drop_ = f"overlaps the text-behind {o['id']} ({o['t0']}-{o['t1']}s) and no >= {IL.get('minHoldSec', 1.2)}s window is left around it"; break
                if drop_: skip('illustration', at, f"{cpt['id']} (\"{kw}\"): {drop_}"); continue
            if il_prev is not None and il_prev['t1'] > t0:   # a quick list ("giao tiếp, sale, tài liệu"): the new icon replaces the previous one in the same slot
                il_prev['t1'] = round(t0, 2)
            slug = cpt['id']; fn = os.path.join(idir, slug + '.svg'); src_ = None
            if not os.path.exists(fn) or not os.path.exists(os.path.join(idir, 'icons.json')) or slug not in json.load(open(os.path.join(idir, 'icons.json'))):
                if cpt.get('hand') and os.path.exists(os.path.join(fb_dir, cpt['hand'])) and cpt.get('handFirst'):
                    import shutil as _sh; _sh.copy(os.path.join(fb_dir, cpt['hand']), fn); ij = os.path.join(idir, 'icons.json'); dj = json.load(open(ij)) if os.path.exists(ij) else {}
                    dj[slug] = dict(icon='hand-drawn:' + cpt['hand'], license='original hand-drawn SVG composition (CC0)'); json.dump(dj, open(ij, 'w'), indent=1, ensure_ascii=False)
                else:
                    r_ = _sp.run(['bash', os.path.join(ROOT, 'scripts', 'fetch_icon.sh'), slug] + cpt['icons'] + ['--dir', idir, '--color', IL.get('iconColor', '#ffffff')], capture_output=True, text=True, cwd=ROOT)
                    if r_.returncode and cpt.get('hand') and os.path.exists(os.path.join(fb_dir, cpt['hand'])):
                        import shutil as _sh; _sh.copy(os.path.join(fb_dir, cpt['hand']), fn); ij = os.path.join(idir, 'icons.json'); dj = json.load(open(ij)) if os.path.exists(ij) else {}
                        dj[slug] = dict(icon='hand-drawn:' + cpt['hand'], license='original hand-drawn SVG composition (CC0)'); json.dump(dj, open(ij, 'w'), indent=1, ensure_ascii=False)
                    elif r_.returncode: skip('illustration', at, f"{cpt['id']}: no icon in {cpt['icons']} and no hand-drawn fallback"); continue
            src_ = json.load(open(os.path.join(idir, 'icons.json'))).get(slug, {})
            il_ = dict(type='illustration', t0=t0, t1=t1, concept=cpt['id'], label=cpt['label'], icon='project/illustrations/' + slug + '.svg', color=cpt.get('color', IL.get('color', '#ffd400')), source=f"{src_.get('icon')} - {src_.get('license')}")
            why_pl = ''
            if PLI.get('enabled', True):
                # v4.3: bigger icons (scales 1.12/1.03/0.95) fit fewer slots -> before dropping, RE-TIME the card (+0.3s steps after the keyword, -0.2s), staying inside kept video, one constant framing and clear of full-screen scenes
                pl_ = None; fx = None; fb_ = None; tried_ = 0; t0_o, t1_o = t0, t1
                reframed_ = None; LDl = PLI.get('ladder') or {}
                for rf_ in ([False, True] if (LDl.get('enabled') and LDl.get('reframe', True) and segs) else [False]):    # rung 5 (last): WIDEN the framing of the one segment the card sits in (tight/mid -> wide) so the face shrinks and a slot opens
                    for off_ in [0.0] + list(PLI.get('retryOffsetsSec', [0.3, 0.6, 0.9, 1.2, -0.2])):
                        a_ = round(max(ws[0]['s'], t0_o + off_), 2); z_ = round(a_ + (t1_o - t0_o), 2)
                        if not in_kept(a_) or not in_kept(z_ - 0.1): continue
                        if any(o['type'] in ('info-scene', 'topic-card', 'broll', 'framed-focus') and o['t0'] < z_ and a_ < o['t1'] for o in beats):
                            if off_ == 0.0: skip('illustration', at, f"{cpt['id']}: a full-screen scene is on screen"); tried_ = -1; break
                            continue
                        tried_ += 1
                        segs_u = segs
                        if rf_:
                            sg_ = next((g for g in segs if g['srcIn'] - 1e-3 <= a_ and z_ <= g['srcOut'] + 1e-3), None)
                            if not sg_ or (sg_.get('framing') or 'wide') == 'wide' or sg_.get('zoom') or any(o['type'] in ('brand-logo', 'illustration') and o['t0'] < sg_['srcOut'] and sg_['srcIn'] < o['t1'] for o in beats): continue
                            segs_u = [dict(g, framing='wide', punch=False) if g is sg_ else g for g in segs]
                        fr = logo_place.face_rect(faces_all, segs_u, CFG, ci, a_, z_) if faces_all else None
                        fx_ = logo_place.expand(fr, PLI.get('faceExpand', {'x': 0.2, 'up': 0.45, 'down': 0.2}), ci) if fr else None
                        oth = [[r[0] * ci['W'], r[1] * ci['H'], r[2] * ci['W'], r[3] * ci['H']] for o in beats if o['type'] not in ('stars',) and o['t0'] < z_ and a_ < o['t1'] and o['type'] not in ('info-scene', 'topic-card', 'broll') for r in rects_of(o)]
                        c_ = logo_place.place(fx_, oth, cpt['label'], ci, PLI, LGpx, sfp_i, ci['capY'] - PLI.get('captionGapR', 0.045) * ci['H'], strict=bool(fx_), last_side=last_side_)
                        mrej_ = None
                        if PLI.get('maskSlots', True) and fx_ and MASKCTX['ok'] and ci['fit'] != 'blurfill':
                            U_ = logo_place.person_union(MASKCTX['dir'], CFG, ci, MASKCTX['fps'], segs_u, MASKCTX['video'], a_, z_, MASKCTX['tool'])
                            if U_ is not None:
                                mp_ = logo_place.mask_slots_place(U_, 4, fx_, oth, cpt['label'], ci, PLI, LGpx, sfp_i, ci['capY'] - PLI.get('captionGapR', 0.045) * ci['H'], last_side=last_side_)
                                if mp_.get('none'):
                                    mrej_ = mp_
                                    # the legacy (face-box) slot is only kept when it is ALSO clear of the person matte on every frame; otherwise re-time / drop (never force overlap)
                                    occ_ = (U_ > 0.25); r_ = c_['rect'] if c_ else None
                                    hit_ = (c_ is None) or int(occ_[max(0, int((r_[1] - 6) / 4)):int(np.ceil((r_[3] + 6) / 4)), max(0, int((r_[0] - 6) / 4)):int(np.ceil((r_[2] + 6) / 4))].sum()) > 0
                                    if hit_: continue
                                    c_ = dict(c_, side=c_.get('side', 'left'), sideReason=(c_.get('sideReason', '') + f" | person-mask check: no mask slot free on either side ({mp_['why']}); legacy slot is clear of the person").strip(' |'), maskChecked=True)
                                else: c_ = mp_
                        if c_ is None or (fx_ and not c_.get('free', True)): continue
                        pl_, fx = c_, fx_; il_['t0'], il_['t1'] = a_, z_
                        if rf_: reframed_ = sg_['id']
                        break
                    if pl_ is not None or tried_ < 0: break
                if pl_ is None and tried_ < 0: continue
                if pl_ is None: skip('illustration', at, f"{cpt['id']}: no face-free, overlap-free slot at {tried_} tried times even after the whole ladder (big icon beside the face -> shoulder/edge/above-caption slots -> smaller icon down to ~120px -> compact pill) - dropped"); continue
                if il_['t0'] != t0: why_pl = f"; re-timed {il_['t0'] - t0:+.2f}s"
                il_.update(x=round(pl_['cx'] / ci['W'], 4), y=round(pl_['top'] / ci['H'], 4), scale=pl_['scale'])
                if pl_.get('side'): il_.update(side=pl_['side'], _freeLeftPx=pl_['freeLeftPx'], _freeRightPx=pl_['freeRightPx'], _sideReason=pl_['sideReason'], _personMaskChecked=bool(pl_.get('maskChecked'))); last_side_ = pl_['side']; why_pl = f"; placed {pl_['mode']} x{pl_['scale']}" + why_pl
                if reframed_:
                    for g in segs:
                        if g['id'] == reframed_: g['framing'] = 'wide'; g['punch'] = False; g['_reframedBy'] = 'illustration ladder'
                    REFRAMED.add(reframed_); why_pl += f' [ladder rung 5: segment {reframed_} reframed to wide so the face shrinks]'
                if pl_.get('pill'): il_['pill'] = True; why_pl += ' [ladder: compact icon+label pill]'
                else: why_pl += f" [icon ~{round(LGpx['size'] * pl_['scale'] * 0.7)}px, ladder rung {'1 beside-face' if not str(pl_['mode']).startswith('slot:') else '2/3 shoulder-edge slot' + (' + smaller size' if pl_['scale'] < min(PLI.get('scales', [0.9])) else '')}]"
            add(il_, f"illustration: \"{kw}\" -> {cpt['id']} icon {src_.get('icon')}" + why_pl)
            last_i = at; used[cpt['id']] = at; nil += 1; il_prev = beats[-1] if beats and beats[-1] is not None and beats[-1].get('type') == 'illustration' else None

    # ---- FACE-AWARE SHIFT (v4.1): titles / chip-stacks / prompt / comment never sit on the speaker's face or hair ----
    if faces_all and FP.get('enabled', True):
        ex = FP.get('expand', {'x': 0.06, 'up': 0.3, 'down': 0.05})
        sfr = LY['safe']; ymax = 1 - sfr['bottomR'] - FP.get('captionReserveR', 0.11)         # the caption moves below the element (assets/zones.ts), so keep room for it
        ymin = sfr['topR'] + 0.005
        for b in sorted(beats, key=lambda x: x['t0']):
            if b['type'] not in FP.get('types', ['title-burst', 'chip-stack', 'prompt-box', 'comment-box']): continue
            fr = logo_place.face_rect(faces_all, segs, CFG, ci, b['t0'], b['t1'])
            if not fr: continue
            fx = logo_place.expand(fr, ex, ci); fxf = [fx[0] / ci['W'], fx[1] / ci['H'], fx[2] / ci['W'], fx[3] / ci['H']]
            hit = lambda r, f=fxf: min(r[2], f[2]) - max(r[0], f[0]) > 0 and min(r[3], f[3]) - max(r[1], f[1]) > 0
            area = lambda r, f=fxf: max(0, min(r[2], f[2]) - max(r[0], f[0])) * max(0, min(r[3], f[3]) - max(r[1], f[1]))
            base = rects_of(dict(b, dy=0))
            tgt = [base[0]] if b['type'] == 'title-burst' else base
            if not any(hit(r) for r in tgt): continue
            own_tl = base[1:] if b['type'] == 'title-burst' else []
            oth = [r for o in beats if o is not b and o['type'] not in ('stars', 'brand-logo', 'info-scene', 'topic-card', 'broll', 'framed-focus', 'text-behind-speaker', 'sticker') and o['t0'] < b['t1'] and b['t0'] < o['t1'] for r in rects_of(o)]
            def search(obst):
                best = None
                for k in range(0, 91):
                    for sg in (1, -1):
                        dy = round(sg * k * 0.01, 2)
                        rr = [(r[0], r[1] + dy, r[2], r[3] + dy) for r in tgt]
                        if min(r[1] for r in rr) < ymin or max(r[3] for r in rr) > ymax: continue
                        if any(hit(r) for r in rr): continue
                        if any(min(r[2], o[2]) - max(r[0], o[0]) > 0.03 and min(r[3], o[3]) - max(r[1], o[1]) > 0.01 for r in rr for o in obst): continue
                        if best is None or abs(dy) < abs(best): best = dy
                    if best is not None: break
                return best
            dy = search(oth + own_tl)
            if dy is None and own_tl: dy = search(oth); b['timeline'] = False if dy is not None else b.get('timeline')
            if dy is None:
                # v4.2 GATE-CONSISTENT: no slot clear of the expanded face. The render gate (check_logo_faces.py) fails an element that covers > 10 % of the REAL (unexpanded) face box,
                # so accept a slot only when it stays under faceGateMaxR (default 5 %, half the gate limit) of the real face; otherwise DROP the beat - never keep a "least overlap" spot the gate rejects.
                def find_(fr, lim):
                    fr_f = [fr[0] / ci['W'], fr[1] / ci['H'], fr[2] / ci['W'], fr[3] / ci['H']]; fa = max(1e-9, (fr_f[2] - fr_f[0]) * (fr_f[3] - fr_f[1]))
                    ar_real = lambda r: max(0, min(r[2], fr_f[2]) - max(r[0], fr_f[0])) * max(0, min(r[3], fr_f[3]) - max(r[1], fr_f[1])) / fa
                    cs = []
                    for k in range(-60, 91):
                        dy_ = k * 0.01; rr = [(r[0], r[1] + dy_, r[2], r[3] + dy_) for r in tgt]
                        if min(r[1] for r in rr) < ymin or max(r[3] for r in rr) > ymax: continue
                        if any(min(r[2], o[2]) - max(r[0], o[0]) > 0.03 and min(r[3], o[3]) - max(r[1], o[1]) > 0.01 for r in rr for o in oth + own_tl): continue
                        w_ = max(ar_real(r) for r in rr)
                        if w_ <= lim: cs.append((abs(dy_), dy_, w_))
                    return cs
                lim = FP.get('faceGateMaxR', 0.05); cands = find_(fr, lim)
                if not cands and b['type'] == 'comment-box':
                    # v4.3.1: the CTA is NEVER dropped. 1) widen the framing of its segment (face shrinks) 2) else keep the least-overlap slot (autofix_overlaps then only MOVES it)
                    sg_ = max((g for g in (segs or []) if g['srcIn'] < b['t1'] and b['t0'] < g['srcOut']), key=lambda g: min(g['srcOut'], b['t1']) - max(g['srcIn'], b['t0']), default=None)     # the segment that carries most of the CTA window
                    c1 = sorted(find_(fr, 1.0), key=lambda c: (c[2], c[0]))[:1]; c2 = []
                    if sg_ and (sg_.get('framing') or 'wide') != 'wide' and not sg_.get('zoom'):
                        fr2 = logo_place.face_rect(faces_all, [dict(g, framing='wide', punch=False) if g is sg_ else g for g in segs], CFG, ci, b['t0'], b['t1'])
                        c2 = sorted(find_(fr2, 1.0), key=lambda c: (c[2], c[0]))[:1] if fr2 else []
                    if c2 and (not c1 or c2[0][2] < c1[0][2] - 0.005 or c2[0][2] <= lim):
                        cands = c2; REFRAMED.add(sg_['id']); sg_['framing'] = 'wide'; sg_['punch'] = False; b['_why'] = (b.get('_why', '') + f"; CTA kept: segment {sg_['id']} reframed to wide ({c2[0][2]:.0%} overlap)").lstrip('; ')
                    elif c1: cands = c1; b['_why'] = (b.get('_why', '') + '; CTA kept at the least-overlap slot (never dropped)').lstrip('; ')
                if cands:
                    dy = min(cands)[1] if b['type'] != 'comment-box' or min(cands)[2] <= lim else cands[0][1]; b['_why'] = (b.get('_why', '') + f'; face-aware: dy={dy:+.2f} (clear of the real face, {min(cands)[2]:.0%} overlap)').lstrip('; ')
                else:
                    b['_dropped'] = 'face-aware: no position keeps it off the speaker\'s face (render gate would fail) - dropped, not "least overlap"'
                    skip(b['type'], b['t0'], b['_dropped']); continue
                if own_tl and dy:        # the shifted title block may now sit on its own timeline (which does not move): drop the timeline rather than overlap
                    sh = [(r[0], r[1] + dy, r[2], r[3] + dy) for r in tgt]
                    if any(min(r[2], o[2]) - max(r[0], o[0]) > 0 and min(r[3], o[3]) - max(r[1], o[1]) > 0 for r in sh for o in own_tl):
                        b['timeline'] = False; b['_why'] += '; timeline dropped (title shifted onto it)'
            elif dy:
                b['_why'] = (b.get('_why', '') + f'; face-aware: shifted {dy:+.2f}H off the face').lstrip('; ')
            if dy: b['dy'] = dy

    # ---- spacing / sanity ----
    beats.sort(key=lambda b: (b['t0'], b['type']))
    for b in beats:
        b['t1'] = round(min(max(b['t1'], b['t0'] + A['spacing']['minBeatSec']), t_end + 0.3), 2)
    under = ('info-scene', 'topic-card', 'broll', 'framed-focus')
    kept = []
    for b in beats:
        # info/topic scenes are full-screen: never overlap each other
        clash = [k for k in kept if (k['type'] in under) and (b['type'] in under) and b['t0'] < k['t1'] and k['t0'] < b['t1']]
        if clash:
            b['_dropped'] = f"overlaps full-screen beat {clash[0]['type']}"; continue
        kept.append(b)

    # ---- COLLISION CHECK (v4.1 STRICT): interval check over time x exact screen rectangles, for EVERY beat type ----
    #  1. `exclusive` hero overlays (title-burst, avatar-chain, chip-stack, prompt-box, comment-box): never two at once, whatever their zones
    #  2. every other pair: no time overlap when their screen rectangles (x AND y) intersect; full-screen scenes cover the whole canvas
    #  The lower-priority beat is shifted (<= maxShiftSec after its trigger), trimmed, or dropped; a final pass re-verifies every pair.
    CZ = A.get('collision', {})
    collision_report = None
    if CZ.get('enabled', True):
        PRIO = CZ.get('priority', ['comment-box', 'info-scene', 'topic-card', 'framed-focus', 'title-burst', 'text-behind-speaker', 'prompt-box', 'chip-stack', 'big-word', 'selection-box', 'brand-logo', 'sticker', 'avatar-chain'])
        rank = {t: i for i, t in enumerate(PRIO)}; rank['stars'] = -1
        EXC = set(CZ.get('exclusive', []))
        OVER_SCENE = set(CZ.get('allowOverScene', ['stars']))
        SCENES = ('info-scene', 'topic-card', 'framed-focus')
        IGN = [set(x) for x in CZ.get('ignorePairs', [])]
        MINZ = CZ.get('minZoneOverlap', 0.02); MAXSHIFT = CZ.get('maxShiftSec', 1.2)
        MINB = A['spacing']['minBeatSec']
        def zov(a_, b_):
            for r1 in rects_of(a_):
                for r2 in rects_of(b_):
                    if min(r1[2], r2[2]) - max(r1[0], r2[0]) > 0.03 and min(r1[3], r2[3]) - max(r1[1], r2[1]) > MINZ: return True
            return False
        def conflict(x, y):
            if {x['type'], y['type']} in IGN: return None
            if not (x['t0'] < y['t1'] - 1e-6 and y['t0'] < x['t1'] - 1e-6): return None
            if x['type'] in SCENES and y['type'] in OVER_SCENE or y['type'] in SCENES and x['type'] in OVER_SCENE: return None
            if x['type'] in EXC and y['type'] in EXC: return 'exclusive hero overlays'
            if zov(x, y): return 'screen zones overlap'
            return None
        for b in kept: b['_t0o'] = b['t0']
        # a brand logo sits on the talking head: never over a full-screen scene (it would cover the scene's content)
        for bl_ in [b for b in kept if b['type'] == 'brand-logo' and '_dropped' not in b]:
            sc_ = next((b for b in kept if b['type'] in SCENES + ('broll',) and '_dropped' not in b and b['t0'] < bl_['t1'] and bl_['t0'] < b['t1']), None)
            if sc_: bl_['_dropped'] = f"full-screen {sc_['type']} at {sc_['t0']:.1f}-{sc_['t1']:.1f}s"
        changed = True; guard_n = 0
        while changed and guard_n < 80:
            changed = False; guard_n += 1
            ov = sorted([b for b in kept if b['type'] in rank and '_dropped' not in b], key=lambda b: (rank[b['type']], b['t0']))
            for i_, hi in enumerate(ov):
                for lo in ov[i_ + 1:]:
                    if '_dropped' in lo or '_dropped' in hi: continue
                    why_c = conflict(hi, lo)
                    if not why_c: continue
                    tag = f"{hi['type']} {hi['t0']:.1f}-{hi['t1']:.1f}s ({why_c})"
                    if lo['type'] in SCENES:                      # a scene is never shifted: trim its end before the other beat, else drop
                        if hi['t0'] - lo['t0'] >= 1.5: lo['t1'] = round(hi['t0'] - 0.05, 2); lo['_why'] = lo.get('_why', '') + f'; end trimmed before {tag}'
                        else: lo['_dropped'] = f'collision with {tag}'
                    elif lo['t1'] - hi['t1'] >= MINB and hi['t1'] + 0.08 - lo['_t0o'] <= MAXSHIFT:
                        lo['t0'] = round(hi['t1'] + 0.08, 2); lo['_why'] = lo.get('_why', '') + f'; start moved after {tag}'
                    elif hi['t0'] - lo['t0'] >= MINB:
                        lo['t1'] = round(hi['t0'] - 0.05, 2); lo['_why'] = lo.get('_why', '') + f'; end trimmed before {tag}'
                    else:
                        lo['_dropped'] = f'collision with {tag}'
                    changed = True
        # a selection box needs its big-word
        for sb in [b for b in kept if b['type'] == 'selection-box' and '_dropped' not in b]:
            bw = [b for b in kept if b['type'] == 'big-word' and '_dropped' not in b and b['t0'] <= sb['t0'] + 0.5 and b['t1'] >= sb['t0']]
            if not bw: sb['_dropped'] = 'its big-word was moved/dropped by the collision check'
        # at most maxConcurrentOverlays small overlays at once (checked AFTER the shifts/trims above, on the final times)
        done_ = []
        for b in sorted([b for b in kept if '_dropped' not in b], key=lambda b: (b['t0'], rank.get(b['type'], 99))):
            if b['type'] in under: done_.append(b); continue
            conc = [k for k in done_ if k['type'] not in under and b['t0'] < k['t1'] and k['t0'] < b['t1']]
            if len(conc) >= A['spacing']['maxConcurrentOverlays']: b['_dropped'] = 'more than maxConcurrentOverlays at once'; continue
            done_.append(b)
        # final validation: re-check every pair of surviving beats (never trust the loop above)
        alive = [b for b in kept if '_dropped' not in b and b['type'] in rank]
        viol = [(x, y, conflict(x, y)) for i_, x in enumerate(alive) for y in alive[i_ + 1:] if conflict(x, y)]
        for x, y, w_ in viol:
            lo = x if rank[x['type']] > rank[y['type']] else y
            lo['_dropped'] = f'final validation: {w_} with {(y if lo is x else x)["type"]}'
        alive = [b for b in kept if '_dropped' not in b and b['type'] in rank]
        left = sum(1 for i_, x in enumerate(alive) for y in alive[i_ + 1:] if conflict(x, y))
        collision_report = dict(pairsChecked=len(alive) * (len(alive) - 1) // 2, fixedInFinalPass=len(viol), remainingViolations=left)
        print(f"collision check: {left} violations ({len(alive)} beats, {collision_report['pairsChecked']} pairs; {len(viol)} fixed in the final pass)")
        for b in kept: b.pop('_t0o', None)
        kept = [b for b in kept if '_dropped' not in b] + [b for b in kept if '_dropped' in b]
    dropped = [b for b in beats if '_dropped' in b]
    beats = [b for b in kept if '_dropped' not in b]
    # info-scene header "thay vì prompt ..." when a prompt-box precedes it (reference header: "thay vì prompt từng lỗi")
    pb = next((b for b in beats if b['type'] == 'prompt-box'), None)
    for b in beats:
        if b['type'] == 'info-scene' and pb and 'cards' in b and b.get('headline') and pb['t0'] < b['t0'] < pb['t0'] + 6:
            b['header'] = 'thay vì prompt ' + ' '.join(pb['text'].rstrip('.').split()[-3:]).lower()
            b['_why'] += '; header from prompt-box'
    # REC counter: output-timeline second of title-burst
    if segs:
        def to_out(t):
            c = 0.0
            for s_ in segs:
                if s_['srcIn'] <= t <= s_['srcOut']: return c + (t - s_['srcIn']) / s_.get('speed', 1)
                c += (s_['srcOut'] - s_['srcIn']) / s_.get('speed', 1)
            return None
    else:
        to_out = lambda t: t
    for b in beats:
        if b['type'] == 'title-burst':
            o = to_out(b.pop('_recSrcT', b['t0'])) or b['t0']
            b['rec'] = f'{int(o // 60):02d}:{int(o % 60):02d}'
    CD = A.get('captionAnchorDefaults', {})
    anchors = [dict(t0=b['t0'], t1=b['t1'], anchor='top') for b in beats if b['type'] in CD.get('topDuring', A['captionAnchorTopDuring'])]
    anchors += [dict(t0=b['t0'], t1=b['t1'], anchor='top', variant='dark') for b in beats if b['type'] in CD.get('darkDuring', ['broll'])]
    for wv in screen_wins:      # detected screen b-roll in the footage (not our own full-screen scenes, which carry their own text)
        if any(b['type'] in ('info-scene', 'topic-card') and b['t0'] < wv['t1'] and wv['t0'] < b['t1'] for b in beats):
            continue
        if segs and not any(i0 < wv['t1'] and wv['t0'] < i1 for i0, i1 in kept_iv):
            continue
        anchors.append(dict(t0=wv['t0'], t1=wv['t1'], anchor='top', variant='dark', _why='detected screen-recording b-roll'))
    anchors.sort(key=lambda x: x['t0'])
    for b_ in dropped:
        if not any(k_['beat'] == b_['type'] and abs(k_['t'] - b_['t0']) < 0.01 for k_ in skips): skips.append(dict(beat=b_['type'], t=round(b_['t0'], 2), why=b_['_dropped']))
    out = dict(beats=beats, _skips=skips, captionAnchor=anchors, _generated=dict(by='scripts/make_beats.py', rules='style.config.json -> autoBeats', beatsPerMin=round(len(beats) / max(1, (t_end - ws[0]['s'])) * 60, 1), collision=collision_report, droppedByRule=[dict(type=b['type'], t0=b['t0'], why=b['_dropped']) for b in dropped]))
    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
    json.dump(out, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    need = {b['media']['src'] for b in beats if isinstance(b.get('media'), dict)}
    pdir = os.path.dirname(os.path.abspath(a.out))
    import subprocess
    # real stills (screen-b-roll window frame when one was detected, else a frame of the footage) for the generic topic-cards
    for k_, (src, t_) in enumerate(still_jobs):
        dst = os.path.join(os.path.dirname(pdir), src)
        if screen_wins and G.get('topicCardUseVideoStill', True):
            wv = screen_wins[k_ % len(screen_wins)]; t_ = round((wv['t0'] + wv['t1']) / 2, 2)
        if raw_path and os.path.exists(raw_path):
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(t_), '-i', raw_path, '-frames:v', '1', '-vf', "scale='min(1280,iw)':-2", '-q:v', '3', dst], check=False)
    missing = [n for n in need if not os.path.exists(os.path.join(os.path.dirname(pdir), n)) and os.path.basename(n) in ('editor.png', 'phone.png')]
    if missing:
        subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', 'make_placeholders.py'), '--dir', pdir], check=False)
    if REFRAMED and a.edl:     # ladder rung 5 widened some segments -> persist (the composition + masks read edl.json)
        _ed = json.load(open(a.edl))
        for g in _ed['segments']:
            if g['id'] in REFRAMED: g['framing'] = 'wide'; g['punch'] = False; g['_reframedBy'] = 'illustration ladder'
        json.dump(_ed, open(a.edl, 'w'), indent=1, ensure_ascii=False); print(f"edl: segments {sorted(REFRAMED)} reframed to wide by the illustration ladder (rung 5)")
    print(f"OK {a.out}: {len(beats)} beats ({out['_generated']['beatsPerMin']}/min; reference {20.0}/min), dropped {len(dropped)}")
    if a.report or True:
        for b in beats:
            print(f"  {b['t0']:6.2f}-{b['t1']:6.2f} {b['type']:14s} {b['_why']}")
        for b in dropped:
            print(f"  DROPPED {b['t0']:6.2f}-{b['t1']:6.2f} {b['type']:14s} {b['_dropped']}")


if __name__ == '__main__':
    main()
