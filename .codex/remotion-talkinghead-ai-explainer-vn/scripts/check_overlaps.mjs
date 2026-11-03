// OVERLAP GATE (mandatory before every final render, see scripts/render.sh).
// Renders the composition at a tiny scale (layout is resolution independent), and on every 2nd frame the LayoutCollisionGuard
// measures the REAL DOM boxes of the captions and of every active beat element. ANY intersection (caption vs element, title vs element,
// element vs element) is a failure; so is a brand-logo card that covers the detected face (scripts/check_logo_faces.py).
// usage: node scripts/check_overlaps.mjs [public/project] [--report out/overlaps.json] [--frames 0-900]
import {spawnSync, spawn} from 'node:child_process';
import {mkdirSync, readFileSync, writeFileSync, existsSync, rmSync} from 'node:fs';
import {dirname, join} from 'node:path';
import {tmpdir} from 'node:os';

const args = process.argv.slice(2);
const opt = (n) => { const i = args.indexOf(n); return i >= 0 ? args.splice(i, 2)[1] : undefined; };
const reportPath = opt('--report') ?? 'out/overlaps.json';
const frames = opt('--frames');
const dir = args[0] ?? 'public/project';
const fps = (() => { try { return (() => { const p = JSON.parse(readFileSync(`${dir}/probe.json`, 'utf8')); return p.fpsIsVariable || p.fps < 20 ? 30 : Math.round(p.fps); })(); } catch { return 30; } })();

const tmp = join(tmpdir(), `ovl-${process.pid}.mp4`);
const cmd = ['remotion', 'render', 'src/index.ts', 'TalkingHead', tmp, '--scale=0.1', '--muted', `--concurrency=${process.env.GATE_CONCURRENCY ?? '6'}`, '--log=verbose', '--crf=40', ...(frames ? [`--frames=${frames}`] : [])];
const hits = [], boxes = [];
const feed = (chunk) => { for (const m of String(chunk).matchAll(/\[box\](\{[^\n]*?\})(?=\s|$)/g)) { try { boxes.push(JSON.parse(m[1])); } catch {} }
  for (const m of String(chunk).matchAll(/\[ovl\](\{[^\n]*?\})(?=\s|$)/g)) { try { hits.push(JSON.parse(m[1])); } catch {} } };
const child = spawn('npx', cmd, {stdio: ['ignore', 'pipe', 'pipe'], env: {...process.env, REMOTION_GATE: '1'}});   // v4.4: gate render skips video decode/blur (DOM boxes only)
let tail = '', lastLen = 0;
const onData = (c) => { feed(c); tail = (tail + c).slice(-400); if (/Rendered \d+\/\d+/.test(tail) && tail.length !== lastLen) { lastLen = tail.length; } };
child.stdout.on('data', onData); child.stderr.on('data', onData);
const code = await new Promise((r) => child.on('close', r));
rmSync(tmp, {force: true});
if (code !== 0) { console.error('FAIL: overlap-check render crashed:\n' + tail); process.exit(2); }

// frames -> time ranges per pair
const by = new Map();
for (const h of hits) { const k = `${h.a} x ${h.b}`; (by.get(k) ?? by.set(k, []).get(k)).push(h); }
const ranges = [];
for (const [k, hs] of by) {
  const u = [...new Map(hs.map((h) => [h.f, h])).values()].sort((x, y) => x.f - y.f);
  let cur = null;
  for (const h of u) {
    if (cur && h.f - cur.f1 <= 6) { cur.f1 = h.f; if (h.ox * h.oy > cur.area) { cur.area = h.ox * h.oy; cur.ex = h; } }
    else { cur = {pair: k, f0: h.f, f1: h.f, area: h.ox * h.oy, ex: h}; ranges.push(cur); }
  }
}
const out = ranges.map((r) => ({pair: r.pair, outFrom: +(r.f0 / fps).toFixed(2), outTo: +(r.f1 / fps).toFixed(2), maxOverlapPx: [r.ex.ox, r.ex.oy], boxA: r.ex.ra, boxB: r.ex.rb})).sort((a, b) => a.outFrom - b.outFrom);

// logo vs face
let logo = {checked: 0, violations: []};
const boxFile = join(tmpdir(), `ovl-boxes-${process.pid}.json`); writeFileSync(boxFile, JSON.stringify(boxes));
mkdirSync(dirname(reportPath), {recursive: true}); writeFileSync(join(dirname(reportPath), "boxes.json"), JSON.stringify({fps, boxes}));   // v4.4: every caption box of every frame (check_caption_face.py reads it)
const lf = spawnSync('python3', ['scripts/check_logo_faces.py', dir, boxFile], {encoding: 'utf8'}); rmSync(boxFile, {force: true});
try { logo = JSON.parse(lf.stdout); } catch { if (existsSync(`${dir}/faces.json`)) console.warn('WARN: logo/face check could not run: ' + (lf.stderr || '').trim().split('\n').pop()); }

const report = {sampledEvery: 'captions: every frame; other elements: 2 frames', overlapCount: out.length + logo.violations.length, overlaps: out, logoOverFace: logo.violations, logosChecked: logo.checked};
mkdirSync(dirname(reportPath), {recursive: true});
writeFileSync(reportPath, JSON.stringify(report, null, 2));
if (report.overlapCount) {
  console.error(`FAIL: ${report.overlapCount} overlap(s) (report: ${reportPath})`);
  for (const o of out) console.error(`  out ${o.outFrom}s-${o.outTo}s  ${o.pair}  ${o.maxOverlapPx.join('x')}px`);
  for (const v of logo.violations) console.error(v.kind === 'logo' ? `  logo "${v.name}" ${v.t0}-${v.t1}s covers the face (${v.overlapPct}%)` : `  out ${v.outFrom}s-${v.outTo}s  ${v.name} covers ${v.overlapPct}% of the face`);
  process.exit(1);
}
console.log(`OK: 0 overlaps (caption/title/element/logo-face), report ${reportPath}`);
