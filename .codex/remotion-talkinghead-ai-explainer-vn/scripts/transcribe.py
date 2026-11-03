#!/usr/bin/env python3
"""Vietnamese word-level transcript -> public/project/words.json  (list of {start,end,text,words:[{w,s,e,p}], lp,ns,cr,[recovered],[suspect]}).

  python3 scripts/transcribe.py public/project/raw.mp4 [--model medium] [--lang vi] [--no-vad] [--no-cleanup] [--glossary FILE]

PASSES (all knobs: style.config.json -> transcribe)
  1  faster-whisper with the VAD filter ON (tuned: threshold 0.35, min_silence 500 ms, speech_pad 300 ms).
  2  GAP RECOVERY: a more sensitive Silero-VAD (0.2) finds voiced regions; every region >= 0.6 s that pass 1 left (mostly) empty - dropped head,
     dropped tail, gap in the middle, a sentence cut short like 'Sài G' - is re-listened to WITHOUT VAD (padded clip) and its words are merged in.
  3  HALLUCINATION FILTER (gated on audio evidence): a segment is suspect when it is a known outro phrase ('đăng ký kênh', ...) or its
     no_speech_prob / avg_logprob / compression_ratio are bad. A suspect segment is re-transcribed once (other VAD mode, beam 8, previous text as
     prompt); the better candidate wins. It is only DROPPED when the region is not energetic (low rms AND low VAD coverage) - an audio-energetic
     region is never discarded, it stays with suspect:true so make_edl / a human can decide.
  4  scripts/text_cleanup.py (stray tokens, brand dictionary, glossary, proper nouns, sentence case). Untouched whisper output -> words.raw.json.
Runs on any python that can import faster_whisper + numpy; otherwise re-executes itself with /workspace/render-env/venv/bin/python (models in
/workspace/render-env/models; nothing is installed or written there).
"""
import argparse, json, os, re, subprocess, sys, tempfile, time, unicodedata, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RENV = '/workspace/render-env'
try:
    import numpy as np
    from faster_whisper import WhisperModel
except ImportError:
    py = RENV + '/venv/bin/python'
    if os.path.exists(py) and not os.environ.get('SKILLCUT_TR_REEXEC'):
        os.environ['SKILLCUT_TR_REEXEC'] = '1'
        os.execv(py, [py] + sys.argv)
    sys.exit('faster-whisper/numpy missing: pip install faster-whisper numpy (in a venv) or provide /workspace/render-env')
sys.path.insert(0, HERE)
from text_cleanup import clean_segments, fold
CFG = json.load(open(os.path.join(ROOT, 'style.config.json'), encoding='utf-8'))
TC = CFG['transcribe']; HC = TC['hallucination']

ap = argparse.ArgumentParser()
ap.add_argument('video'); ap.add_argument('--model', default=TC['model']); ap.add_argument('--lang', default='vi')
ap.add_argument('--out', default='public/project/words.json'); ap.add_argument('--no-cleanup', action='store_true')
ap.add_argument('--no-vad', action='store_true', help='pass 1 WITHOUT VAD (not recommended; pass 2 / hallucination filter then do the repair work)')
ap.add_argument('--no-recovery', action='store_true'); ap.add_argument('--glossary', default=None)
ap.add_argument('--threads', type=int, default=TC['maxThreads'], help='FIXED thread count (default config transcribe.maxThreads): int8 results depend on it, so it is not derived from the machine')
a = ap.parse_args()
if os.path.isdir(a.out) or a.out.endswith(('/', os.sep)):          # --out <dir> -> <dir>/words.json
    a.out = os.path.join(a.out, 'words.json')
os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
a.lang = 'vi' if a.lang in (None, '', 'auto') else a.lang           # language is always forced (never auto-detected)
T0 = time.time()
SR = 16000


def log(*x):
    print(*x, file=sys.stderr, flush=True)


# ---------- audio ----------
pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', a.video, '-vn', '-ac', '1', '-ar', str(SR), '-f', 's16le', '-'], capture_output=True, check=True).stdout
AUDIO = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768
DUR = len(AUDIO) / SR
HOP = SR // 20                                       # 50 ms frames
_n = len(AUDIO) // HOP
DB = 20 * np.log10(np.sqrt((AUDIO[:_n * HOP].reshape(_n, HOP) ** 2).mean(1)) + 1e-9) if _n else np.zeros(1)
FLOOR = float(np.percentile(DB, 10))

from faster_whisper.vad import get_speech_timestamps, VadOptions


def vad_regions(thr, min_sil=300, pad=100):
    ts = get_speech_timestamps(AUDIO, VadOptions(threshold=thr, min_silence_duration_ms=min_sil, speech_pad_ms=pad, min_speech_duration_ms=150))
    return [(t['start'] / SR, t['end'] / SR) for t in ts]


VAD_SENS = vad_regions(TC['recovery']['vadThreshold'])


def overlap(a0, a1, b0, b1):
    return max(0.0, min(a1, b1) - max(a0, b0))


def vad_cov(t0, t1):
    return sum(overlap(t0, t1, r0, r1) for r0, r1 in VAD_SENS) / max(1e-6, t1 - t0)


def energetic(t0, t1):
    i0, i1 = int(t0 / 0.05), max(int(t1 / 0.05), int(t0 / 0.05) + 1)
    seg = DB[i0:i1]
    rms_ok = len(seg) and float(seg.mean()) >= FLOOR + HC['energetic']['dbAboveFloor']
    return bool(rms_ok or vad_cov(t0, t1) >= HC['energetic']['vadCoverage'])


# ---------- whisper ----------
MODEL = WhisperModel(a.model, device='cpu', compute_type=TC.get('computeType', 'float32'), cpu_threads=a.threads, download_root=RENV + '/models' if os.path.isdir(RENV + '/models') else None)


def run(audio, vad, offset=0.0, beam=None, prompt=None):
    vp = TC['vad']
    # DETERMINISM: compute_type float32 (int8 CPU kernels race: different output per run), temperature is a single fixed 0.0 (no fallback ladder -> no random sampling), fixed beam, forced language, no conditioning on earlier text.
    ss, _ = MODEL.transcribe(audio, language=a.lang, task='transcribe', word_timestamps=True, beam_size=beam or TC['beam'], best_of=1, patience=1.0,
                             temperature=0.0, condition_on_previous_text=False, initial_prompt=prompt, compression_ratio_threshold=None, log_prob_threshold=None,
                             no_speech_threshold=None,   # [M] raw_clean.mp4: with log_prob_threshold=None faster-whisper SKIPS every 30 s window whose no_speech_prob > 0.6 even when avg_logprob is fine (-0.2) -> 30 s of normal speech vanished. The hallucination filter below judges ns post-hoc, with audio evidence.
                             without_timestamps=False, suppress_blank=True, multilingual=False,
                             vad_filter=vad, vad_parameters=dict(threshold=vp['threshold'], min_silence_duration_ms=vp['minSilenceMs'], speech_pad_ms=vp['speechPadMs']) if vad else None)
    out = []
    for s in ss:
        ws = [dict(w=w.word.strip(), s=round(w.start + offset, 3), e=round(w.end + offset, 3), p=round(w.probability, 3)) for w in (s.words or []) if w.word.strip()]
        ws = [w for w in ws if vi_token_ok(w)]
        if ws:
            out.append(dict(start=ws[0]['s'], end=ws[-1]['e'], text=' '.join(w['w'] for w in ws), words=ws, lp=round(s.avg_logprob, 3), ns=round(s.no_speech_prob, 3), cr=round(s.compression_ratio, 3)))
    return out


_VOW = set('aeiouyăâêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ')


def vi_token_ok(w):
    """Drop non-Vietnamese-script garbage (CJK/Kana/Hangul/Cyrillic/Arabic/Thai...) and implausible low-confidence fragments ('H', '-N', 'Liesh')."""
    t = w['w']
    for ch in t:
        if ch.isalpha() and not unicodedata.name(ch, '').startswith('LATIN'):
            return False
    letters = [c for c in t.lower() if c.isalpha()]
    if letters and w['p'] < 0.5:
        if not any(c in _VOW for c in letters):                  # every Vietnamese syllable has a vowel
            return False
        if len(letters) == 1 and w['p'] < 0.3 and letters[0] not in 'àáảãạôơêâ':
            return False
        if re.search(r'[bcdfghjklmnpqrstvxz]{3,}$|^[bcdfghjklmnpqrstvxz]{3,}', ''.join(letters)) and 'ngh' not in ''.join(letters) and 'ch' not in ''.join(letters) and 'ng' not in ''.join(letters) and 'nh' not in ''.join(letters):
            return False
    return True


def clip(t0, t1):
    return AUDIO[int(max(0, t0) * SR):int(min(DUR, t1) * SR)]


# ---------- pass 1 ----------
t = time.time()
segs = sorted(run(AUDIO, vad=not a.no_vad), key=lambda s: (s['start'], s['end']))
log(f'pass 1 (VAD {"off" if a.no_vad else "on"}): {len(segs)} segments, {sum(len(s["words"]) for s in segs)} words, {time.time()-t:.0f}s')
stats = dict(pass1_segments=len(segs), recovered_regions=[], hallucination=[])

# ---------- pass 2: gap recovery ----------
R = TC['recovery']
if not a.no_recovery:
    for rnd in range(2):
        words = sorted((w for s in segs for w in s['words']), key=lambda w: w['s'])
        added = 0
        # candidate regions = every VAD region + the long word-less stretches INSIDE a region (a sensitive VAD often merges 60 s of speech into one region,
        # so region-level coverage hides a 30 s hole: raw_clean.mp4 26-56 s)
        cands = []
        for r0, r1 in VAD_SENS:
            cands.append((r0, r1))
            if r1 - r0 >= R['innerGapSec']:
                prev = r0
                for w in words:
                    if w['e'] <= r0 or w['s'] >= r1: continue
                    if w['s'] - prev >= R['innerGapSec']: cands.append((prev, w['s']))
                    prev = max(prev, w['e'])
                if r1 - prev >= R['innerGapSec']: cands.append((prev, r1))
        for r0, r1 in sorted(set(cands)):
            if r1 - r0 < R['minRegionSec']:
                continue
            covered = sum(overlap(r0, r1, w['s'] - 0.05, w['e'] + 0.05) for w in words) / (r1 - r0)
            # a region touching the end/start of the file with a long silent-of-words stretch counts as a gap even when partially covered
            edge_gap = (r1 > DUR - 0.5 and r1 - max([w['e'] for w in words if w['e'] < r1] or [r0]) > R['edgeGapSec'] and r1 - r0 > R['minRegionSec']) or \
                       (r0 < 0.5 and min([w['s'] for w in words if w['s'] > r0] or [r1]) - r0 > R['edgeGapSec'])
            if covered > R['maxCoverage'] and not edge_gap:
                continue
            c0, c1 = max(0, r0 - R['padSec']), min(DUR, r1 + R['padSec'])
            got = run(clip(c0, c1), vad=False, offset=c0)
            new = []
            for sg in got:
                ws = [w for w in sg['words'] if r0 - 0.15 <= (w['s'] + w['e']) / 2 <= r1 + 0.15 and not any(overlap(w['s'], w['e'], x['s'], x['e']) > 0.5 * (w['e'] - w['s']) for x in words)]
                if ws:
                    mp = sum(w['p'] for w in ws) / len(ws)
                    if mp < R['minMeanWordProb'] or sg['ns'] > R['maxNoSpeech'] or sg['lp'] < R['minAvgLogprob']:
                        stats.setdefault('recovery_rejected', []).append(dict(t0=round(r0, 2), t1=round(r1, 2), text=' '.join(w['w'] for w in ws), meanP=round(mp, 2), ns=sg['ns'], lp=sg['lp']))
                        continue
                    new.append(dict(sg, start=ws[0]['s'], end=ws[-1]['e'], text=' '.join(w['w'] for w in ws), words=ws, recovered=True))
            if new:
                segs += new; added += 1
                stats['recovered_regions'].append(dict(t0=round(r0, 2), t1=round(r1, 2), covered=round(covered, 2), text=' '.join(s['text'] for s in new)))
                words = sorted((w for s in segs for w in s['words']), key=lambda w: w['s'])
        segs.sort(key=lambda s: (s['start'], s['end']))
        if not added:
            break
    log(f'pass 2: recovered {len(stats["recovered_regions"])} region(s)')

# ---------- pass 3: hallucination filter ----------
PHR = [fold(p) for p in HC['phrases']]


def suspicious(s):
    f = fold(s['text'])
    why = []
    if any(p and p in f for p in PHR): why.append('outro-phrase')
    if s.get('ns', 0) >= HC['maxNoSpeech'] and s.get('lp', 0) <= HC.get('nsMinLogprob', -0.6): why.append(f"no_speech {s['ns']}")   # like whisper's own rule: no_speech only counts together with a poor avg_logprob (raw_clean.mp4: ns 0.63 but lp -0.17 = clean speech)
    if s.get('lp', 0) <= HC['minAvgLogprob']: why.append(f"avg_logprob {s['lp']}")
    if s.get('cr', 0) >= HC['maxCompression']: why.append(f"compression {s['cr']}")
    return why


def badness(s):
    return len(suspicious(s)) * 1.0 - s.get('lp', -1.0) * -0.5 + (0.5 if s.get('ns', 0) >= HC['maxNoSpeech'] and s.get('lp', 0) <= HC.get('nsMinLogprob', -0.6) else 0)


final = []
for idx, s in enumerate(segs):
    why = suspicious(s)
    if not why:
        final.append(s); continue
    e = energetic(s['start'], s['end'])
    prev_txt = final[-1]['text'] if final else None
    c0, c1 = max(0, s['start'] - 0.3), min(DUR, s['end'] + 0.3)
    retry_vad = a.no_vad or s.get('recovered', False)       # try the opposite mode of the one that produced it
    cands = [s]
    for sg in run(clip(c0, c1), vad=retry_vad, offset=c0, beam=8, prompt=prev_txt):
        cands.append(sg)
    # merge the retry's segments into one candidate when it produced several
    if len(cands) > 2:
        ws = [w for sg in cands[1:] for w in sg['words']]
        cands = [s, dict(start=ws[0]['s'], end=ws[-1]['e'], text=' '.join(w['w'] for w in ws), words=ws, lp=min(sg['lp'] for sg in cands[1:]), ns=max(sg['ns'] for sg in cands[1:]), cr=max(sg['cr'] for sg in cands[1:]))]
    best = min(cands, key=lambda x: (len(suspicious(x)), badness(x)))
    still = suspicious(best)
    rec = dict(t0=round(s['start'], 2), t1=round(s['end'], 2), text=s['text'], why=why, energetic=e)
    if best is not s:
        rec['action'] = 'replaced by retry: ' + best['text']
        best = dict(best, retried=True)
    if still and not e:
        rec['action'] = 'dropped (not energetic)'
        stats['hallucination'].append(rec); continue
    if still:
        best = dict(best, suspect=True, why=still)
        rec.setdefault('action', 'kept (energetic region) suspect:true')
    else:
        rec.setdefault('action', 'kept')
    stats['hallucination'].append(rec)
    final.append(best)
segs = sorted(final, key=lambda s: (s['start'], s['end']))
for sg in segs:
    sg['words'].sort(key=lambda w: (w['s'], w['e']))
# overlapping segments (recovery/retry) -> trim so that the order is strictly increasing in time
for i in range(1, len(segs)):
    segs[i]['words'] = [w for w in segs[i]['words'] if w['s'] >= segs[i - 1]['end'] - 0.02] or segs[i]['words']
    segs[i]['start'] = segs[i]['words'][0]['s']; segs[i]['text'] = ' '.join(w['w'] for w in segs[i]['words'])
segs = sorted([sg for sg in segs if sg['words']], key=lambda s: (s['start'], s['end']))
if not segs:
    sys.exit('transcribe: 0 segments produced (silent file or decoding failure) - refusing to write an empty words.json')
for h in stats['hallucination']:
    log('hallucination check:', json.dumps(h, ensure_ascii=False))

raw_path = os.path.join(os.path.dirname(a.out) or '.', 'words.raw.json')
json.dump(segs, open(raw_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
if not a.no_cleanup:
    segs, cst = clean_segments(segs, glossary_path=a.glossary)
    print('cleanup:', json.dumps({k: v for k, v in cst.items() if not k.endswith('_log')}, ensure_ascii=False), *cst.get('brand_log', []), sep='\n  ')
if not segs:
    sys.exit('transcribe: 0 segments after cleanup - refusing to write an empty words.json')
segs.sort(key=lambda s: (s['start'], s['end']))
json.dump(segs, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
stats['sha256'] = dict(words=hashlib.sha256(open(a.out, 'rb').read()).hexdigest()[:16], raw=hashlib.sha256(open(raw_path, 'rb').read()).hexdigest()[:16], threads=a.threads, temperature=0.0, beam=TC['beam'], lang=a.lang)
json.dump(stats, open(os.path.join(os.path.dirname(a.out) or '.', 'transcribe_report.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'wrote {a.out} ({len(segs)} segments, model={a.model}, vad={"off" if a.no_vad else "on"}, recovered={len(stats["recovered_regions"])}, {time.time()-T0:.0f}s) raw: {raw_path}; report: transcribe_report.json')
