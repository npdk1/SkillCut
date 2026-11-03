#!/usr/bin/env python3
"""v4.4  text-behind evidence manifest  (verified.md V06 / V07 / V10, D-rows 'person-only').

For every text-behind-speaker beat of public/project/beats.json it re-runs Render's text_occlusion.py on

  * the MERGED composition-space masks   out/tbs_canvas/<id>          (person + other elements: what the viewer really sees)   -> `command`
  * the PERSON-ONLY masks                out/tbs_canvas/<id>_person   (the speaker alone: this is what 'behind the crown' means) -> `command_person_only`

one command per LINE (a 2-line wrap has two track files: tbs_track_<id>_0.json = line 1 behind the crown, tbs_track_<id>_1.json = line 2).
Occlusion for the V06 / V07 numbers is ALWAYS taken from `command_person_only` - never from the merged mask (merged is kept as a cross-check only).

usage:  python3 scripts/tbs_manifest.py --project public/project --out-dir out --output-mp4 out/final.mp4 [--edl public/project/edl.json] [--write out/final_tbs.json]
        (library: build(...) -> dict)
exit 0 = written. The pass/fail judgement is in verify_all.py (V06/V07/V10)."""
import argparse, json, os, shutil, subprocess, sys

TOOL = os.environ.get('TEXT_OCCLUSION') or next((p for p in ('/workspace/render-env/bin/text_occlusion.py', os.path.join(os.path.dirname(__file__), 'text_occlusion.py')) if os.path.exists(p)), None)
MAX_GLYPH = 0.30

def load(p, default=None):
    try: return json.load(open(p, encoding='utf-8'))
    except Exception: return default

def out_map(edl):
    """source seconds -> output seconds from the EDL (cumulative kept length; speed 1)"""
    segs = (edl or {}).get('segments', []); acc = 0.0; table = []
    for s in segs:
        sp = float(s.get('speed', 1) or 1); d = (s['srcOut'] - s['srcIn']) / sp
        table.append((s['srcIn'], s['srcOut'], acc, sp)); acc += d
    def f(t):
        for a, b, o, sp in table:
            if a - 1e-6 <= t <= b + 1e-6: return round(o + (t - a) / sp, 3)
        return None
    return f

def run_tool(mask_dir, track, text, require_behind):
    cmd = [sys.executable, TOOL, mask_dir, '--track', track, '--text', text] + (['--require-behind'] if require_behind else []) + ['--max-glyph', str(MAX_GLYPH)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    try: j = json.loads(r.stdout)
    except Exception: j = {}
    return cmd, r.returncode, j

def sh(cmd): return ' '.join(f'"{c}"' if (' ' in c or '\n' in c) else c for c in cmd).replace('\n', '\\n')

def measured(j, rc):
    gl = j.get('glyph_occlusion') or []
    return dict(occlusion_mean=j.get('occlusion_mean'), occlusion_max=j.get('occlusion_max'), worst_frame=j.get('worst_frame'),
                readable_mean=None if j.get('occlusion_mean') is None else round(1 - j['occlusion_mean'], 4), readable_worst=None if j.get('occlusion_max') is None else round(1 - j['occlusion_max'], 4),
                behind_ratio=j.get('behind_ratio'), behind_effect=j.get('behind_effect'), pass_max=j.get('pass_max'), pass_min=j.get('pass_min'), pass_glyph=j.get('pass_glyph'), exit_code=rc,
                min_glyph_visibility=None if j.get('glyph_occlusion_max') is None else round(1 - j['glyph_occlusion_max'], 4), glyph_occlusion_max=j.get('glyph_occlusion_max'),
                worst_glyph=j.get('worst_glyph'), glyph_fail_count=sum(1 for g in gl if g.get('fail')), glyph_occlusion=gl)

def build(project='public/project', out_dir='out', output_mp4=None, edl=None, write=None):
    project = os.path.abspath(project); out_dir = os.path.abspath(out_dir)
    if not TOOL: raise SystemExit('text_occlusion.py not found (set TEXT_OCCLUSION=...)')
    B = load(os.path.join(project, 'beats.json'), {}).get('beats', []); E = load(edl or os.path.join(project, 'edl.json'), {}); mp = out_map(E)
    stem = os.path.splitext(output_mp4)[0] if output_mp4 else os.path.join(out_dir, 'tbs'); beats = []
    for b in B:
        if b.get('type') != 'text-behind-speaker' or not b.get('items'): continue
        bid = b['id']; n = len(b['items']); lines = []
        merged_dir = os.path.join(out_dir, 'tbs_canvas', bid); person_dir = os.path.join(out_dir, 'tbs_canvas', bid + '_person')
        for i, it in enumerate(b['items']):
            tk = os.path.join(project, f'tbs_track_{bid}.json' if n == 1 else f'tbs_track_{bid}_{i}.json')
            tj = load(tk, [])
            if not tj: lines.append(dict(index=i, text=it['text'], error=f'track file missing: {tk}')); continue
            txt = tj[0].get('text') or it['text']; first = (i == 0)
            keep = f'{stem}_tbs_track_{bid}' + ('' if n == 1 else f'_{i}') + '.json'
            if output_mp4: shutil.copyfile(tk, keep)
            c1, rc1, j1 = run_tool(merged_dir, tk, txt, first); c2, rc2, j2 = run_tool(person_dir, tk, txt, first)
            m_person = measured(j2, rc2); m_merged = measured(j1, rc1)
            lines.append(dict(index=i, text=txt, role='line1_behind_crown' if first else 'line2_wrap', require_behind=first, track_json=keep if output_mp4 else tk, project_track_json=tk,
                              command=sh(c1), command_person_only=sh(c2), measured_merged=m_merged, measured=m_person))
        l1 = next((l for l in lines if 'measured' in l), None)
        ok_lines = [l for l in lines if 'measured' in l]
        agg = {}
        if ok_lines:
            m1 = l1['measured']
            agg = dict(occlusion_mean=m1['occlusion_mean'], occlusion_max=max(l['measured']['occlusion_max'] or 0 for l in ok_lines), worst_frame=m1['worst_frame'],
                       readable_mean=min(l['measured']['readable_mean'] for l in ok_lines), readable_worst=min(l['measured']['readable_worst'] for l in ok_lines),
                       behind_ratio=m1['behind_ratio'], behind_effect=m1['behind_effect'], pass_min=m1['pass_min'], pass_max=all(l['measured']['pass_max'] for l in ok_lines),
                       min_glyph_visibility=min(l['measured']['min_glyph_visibility'] for l in ok_lines), glyph_occlusion_max=max(l['measured']['glyph_occlusion_max'] for l in ok_lines),
                       worst_glyph=max((l['measured'] for l in ok_lines), key=lambda m: m['glyph_occlusion_max'] or 0)['worst_glyph'],
                       glyph_fail_count=sum(l['measured']['glyph_fail_count'] for l in ok_lines), person_only_exit_codes=[l['measured']['exit_code'] for l in ok_lines],
                       merged_occlusion_mean_line1=l1['measured_merged']['occlusion_mean'], merged_occlusion_max=max(l['measured_merged']['occlusion_max'] or 0 for l in ok_lines))
        beats.append(dict(id=bid, text=' / '.join(i['text'] for i in b['items']).replace('\n', ' / '), phrase=b.get('phrase') or b.get('text'), layout=b.get('_layout') or ('line' if n == 1 else 'stack'), lines=lines, n_lines=sum(i['text'].count('\n') + 1 for i in b['items']),
                          wrap=b.get('_wrap'), source_window_s=[b['t0'], b['t1']], output_window_s=[mp(b['t0']), mp(b['t1'])], mask_dir=merged_dir, person_only_mask_dir=person_dir,
                          person_mask_source_dir=os.path.join(project, b.get('maskDir', 'masks/' + bid).replace('project/', '', 1)), size_W=min(i['size'] for i in b['items']), crown_tracked=bool(b.get('track')),
                          head_motion_px=b.get('_headMotionPx'), measured=agg, occlusion_source='command_person_only (person-only mask) - the merged mask is a cross-check, never the verdict'))
    man = dict(version='4.4', video=output_mp4, tool=TOOL, rule='occlusion is measured on the PERSON-ONLY mask (command_person_only); max glyph occlusion %.2f' % MAX_GLYPH,
               note='track frame = mask index (30 fps, linear interp); numbers measured on composition-space canvas masks (real, unshifted). Wrap: line 1 = tbs_track_<id>_0 (must be 3-10 %% behind the crown), line 2 = tbs_track_<id>_1 (readable only).', beats=beats)
    if write: json.dump(man, open(write, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return man

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--project', default='public/project'); ap.add_argument('--out-dir', default='out'); ap.add_argument('--output-mp4'); ap.add_argument('--edl'); ap.add_argument('--write')
    a = ap.parse_args(); w = a.write or ((os.path.splitext(a.output_mp4)[0] + '_tbs.json') if a.output_mp4 else os.path.join(a.out_dir, 'tbs_manifest.json'))
    m = build(a.project, a.out_dir, a.output_mp4, a.edl, w)
    for b in m['beats']: print(f'{b["id"]} [{b["layout"]}] "{b["text"]}" out {b["output_window_s"]} measured {({k: b["measured"].get(k) for k in ("occlusion_mean", "occlusion_max", "min_glyph_visibility", "behind_effect")})}')
    print('wrote', w)
