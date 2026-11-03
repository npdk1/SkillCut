#!/usr/bin/env python3
"""check_template_rules.py - template rules that the read-only render-env verify_rules.py (V01-V20) does not cover. v4.5

  V21 icon density   : <= floor(dur/secPerIcon + 0.2) icons (30 s -> 4, 60 s -> 8); density.gapMode 'start-to-start' (default): START of an icon >= minGapSec (5 s)
                       after the START of the previous one (OUTPUT time); 'end-to-start': minGapSec of clear air after the previous icon ends;
                       the same concept >= sameConceptGapSec (15 s) apart.
  V22 icon sides     : every icon records side + _freeLeftPx/_freeRightPx + _sideReason + _personMaskChecked (the per-frame person mask over the
                       icon's whole window was used); when 2+ icons are all on one side, EVERY icon after the first must state why the other side was not
                       free ("NOT free" + numbers). Clearance recorded >= 6 px.
  V23 no blur patch  : out/patch_manifest.json exists, status is 'reinpainted' or 'none-found' (not 'covered-only' unless a reason is written), and the
                       raw video has no leftover pill: detect (diff mode when the original exists) finds no patch in public/project/raw.mp4.
usage: python3 scripts/check_template_rules.py --project public/project --target-sec 30 [--manifest out/patch_manifest.json] [--out out/verify/template_rules.json]
Exit 1 on any FAIL. Never loosen thresholds: fix the beats / the raw."""
import argparse, json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tbs_manifest
ap = argparse.ArgumentParser(); ap.add_argument('--project', default='public/project'); ap.add_argument('--target-sec', type=float, default=30)
ap.add_argument('--source', default=None, help='raw video to blur-scan with render-env verify_rules.py --blur-scan (default <project>/raw.mp4)'); ap.add_argument('--render-env', default='/workspace/render-env'); ap.add_argument('--config', default='style.config.json'); ap.add_argument('--manifest', default='out/patch_manifest.json'); ap.add_argument('--out')
a = ap.parse_args()
J = lambda p, d=None: json.load(open(p, encoding='utf-8')) if os.path.exists(p) else d
CFG = J(a.config, {}); IL = CFG.get('autoBeats', {}).get('illustration', {}); DN = IL.get('density', {})
B = J(os.path.join(a.project, 'beats.json'), {}); edl = J(os.path.join(a.project, 'edl.json'), {}); mp = tbs_manifest.out_map(edl)
dur = sum(s['srcOut'] - s['srcIn'] for s in edl.get('segments', [])) or a.target_sec
ills = sorted([b for b in B.get('beats', []) if b.get('type') == 'illustration'], key=lambda b: b['t0'])
res = []
def add(i, ok, msg, ev=None): res.append(dict(rule_id=i, status='pass' if ok else 'fail', title=msg, evidence=ev or {}))
# V21
sec = DN.get('secPerIcon', 7.5); gap = DN.get('minGapSec', IL.get('minGapSec', 5.0)); same = DN.get('sameConceptGapSec', IL.get('sameConceptGapSec', 15.0))
cap = max(1, int(dur / sec + 0.2)); ot = [(mp(b['t0']), mp(b['t1']), b['concept']) for b in ills]; prob = []
if len(ills) > cap: prob.append(f'{len(ills)} icons > cap {cap} for {dur:.1f}s')
s2s = DN.get('gapMode', 'start-to-start') == 'start-to-start'
for (a0, a1, c0), (b0, b1, c1) in zip(ot, ot[1:]):
    if a0 is None or b0 is None: continue
    g_ = (b0 - a0) if s2s else (b0 - a1)
    if g_ < gap - 1e-6: prob.append(f"{c0}->{c1}: {'start-to-start' if s2s else 'end-to-start'} gap {g_:.2f}s < {gap}s")
for i in range(len(ot)):
    for j in range(i + 1, len(ot)):
        if ot[i][2] == ot[j][2] and ot[j][0] is not None and ot[i][0] is not None and ot[j][0] - ot[i][0] < same: prob.append(f"same concept '{ot[i][2]}' {ot[j][0] - ot[i][0]:.1f}s apart < {same}s")
add('V21', not prob, 'icon density', dict(icons=len(ills), cap=cap, gapMode=('start-to-start' if s2s else 'end-to-start'), duration=round(dur, 2), out_times=[[o[2], o[0], o[1]] for o in ot], problems=prob))
# V22
prob = []; sides = [b.get('side') for b in ills]
for k, b in enumerate(ills):
    for f in ('side', '_freeLeftPx', '_freeRightPx', '_sideReason'):
        if b.get(f) is None: prob.append(f"icon {k + 1} {b.get('concept')}: missing {f}")
    if b.get('_personMaskChecked') is not True: prob.append(f"icon {k + 1} {b.get('concept')}: person mask over the whole window not used (_personMaskChecked != true)")
if len(ills) >= 2 and len(set(sides)) == 1:
    for k, b in enumerate(ills[1:], 2):
        r = b.get('_sideReason') or ''
        if 'NOT free' not in r and 'no free' not in r.lower(): prob.append(f"icon {k}: all icons on '{sides[0]}' but _sideReason gives no reason for the other side")
for k in range(2, len(sides)):
    if sides[k] == sides[k - 1] == sides[k - 2] and sides[k] and 'NOT free' not in (ills[k].get('_sideReason') or ''): prob.append(f'3 icons in a row on {sides[k]}')
add('V22', not prob, 'icon side (person-mask slots, alternation, reason recorded)', dict(sides=sides, reasons=[b.get('_sideReason') for b in ills], clearancePx=CFG.get('autoBeats', {}).get('illustration', {}).get('placement', {}).get('maskClearPx'), problems=prob))
# V23
m = J(a.manifest); prob = []
if not m: prob.append(f'{a.manifest} missing - run scripts/reinpaint_patch.py detect/fill and write the manifest (references/quality-control.md "Subtitle-removal patch")')
else:
    st = m.get('status')
    if st not in ('reinpainted', 'none-found', 'covered-only'): prob.append(f'unknown status {st!r}')
    if st == 'covered-only' and not m.get('reason'): prob.append("status covered-only needs a 'reason' (why re-inpainting was impossible)")
    if st == 'reinpainted' and not (m.get('before_after') and m.get('method')): prob.append('reinpainted needs method + before_after crops')
    if m.get('detected_after_fix'): prob.append(f"patch still detected after the fix: {m['detected_after_fix']}")
src = os.path.abspath(a.source or os.path.join(a.project, 'raw.mp4')); scan = None
if os.path.exists(src) and os.path.exists(os.path.join(a.render_env, 'bin/verify_rules.py')):
    import subprocess, tempfile
    pr = subprocess.run([os.path.join(a.render_env, 'venv/bin/python'), os.path.join(a.render_env, 'bin/verify_rules.py'), '--blur-scan', src], capture_output=True, text=True, cwd=a.render_env); pr.stdout += pr.stderr
    scan = [l.strip() for l in pr.stdout.splitlines() if l.strip().startswith('#')]
    if pr.returncode != 0 or scan: prob.append(f'blur-scan of {src} found patch(es): {scan or pr.stdout[-200:]}')
add('V23', not prob, 'no visible subtitle-removal patch (blur box) in the raw', dict(blur_scan_source=src, blur_scan_patches=scan, manifest=a.manifest, status=(m or {}).get('status'), box=(m or {}).get('patch_box_xyxy'), problems=prob))
out = dict(summary=dict(passed=sum(r['status'] == 'pass' for r in res), fail=sum(r['status'] == 'fail' for r in res)), all_pass=all(r['status'] == 'pass' for r in res), results=res)
if a.out: os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True); json.dump(out, open(a.out, 'w'), indent=1, ensure_ascii=False)
for r in res: print(r['rule_id'], r['status'].upper(), r['title'], json.dumps(r['evidence'], ensure_ascii=False)[:400])
sys.exit(0 if out['all_pass'] else 1)
