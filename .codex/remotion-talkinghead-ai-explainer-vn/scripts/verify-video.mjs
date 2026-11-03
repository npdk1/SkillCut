// QC of a rendered video against probe.json + edl.json.
// Usage: node scripts/verify-video.mjs <rendered.mp4> [public/project]
import {spawnSync} from 'node:child_process';
import {existsSync, readFileSync} from 'node:fs';

const [outputPath, dir = 'public/project'] = process.argv.slice(2);
if (!outputPath) { console.error('Usage: node scripts/verify-video.mjs <rendered.mp4> [public/project]'); process.exit(2); }
if (!existsSync(`${dir}/probe.json`)) { console.error(`FAIL: ${dir}/probe.json missing - probe gate was skipped (run scripts/probe_video.py first).`); process.exit(1); }
const probe = JSON.parse(readFileSync(`${dir}/probe.json`, 'utf8'));
const edl = JSON.parse(readFileSync(`${dir}/edl.json`, 'utf8'));
const errors = [];
const warns = [];

const ff = (path) => {
  const r = spawnSync('ffprobe', ['-v', 'error', '-show_entries', 'stream=codec_type,pix_fmt,r_frame_rate,duration,width,height', '-of', 'json', path], {encoding: 'utf8'});
  if (r.status !== 0) throw new Error(r.stderr || `ffprobe failed: ${path}`);
  return JSON.parse(r.stdout).streams;
};
const rate = (v) => { const [a, b] = v.split('/').map(Number); return b ? a / b : 0; };

// expected canvas - same rule as assets/layouts.ts buildLayout
const key = probe.layoutKey;
const vertical = key === 'vertical' || key.endsWith('-to-vertical');
const S = vertical || Math.min(probe.effective.width, probe.effective.height) >= 720 ? 1080 : 720;   // v4.3: vertical canvas always 1080x1920
const Lg = S === 1080 ? 1920 : 1280;
const [ew, eh] = vertical ? [S, Lg] : key === 'horizontal' ? [Lg, S] : [S, S];

const streams = ff(outputPath);
const v = streams.find((s) => s.codec_type === 'video');
const a = streams.find((s) => s.codec_type === 'audio');
if (!v) errors.push('no video stream');
if (probe.hasAudio && !a) errors.push('raw has audio but output has none');
if (v) {
  if (v.width !== ew || v.height !== eh) errors.push(`canvas ${v.width}x${v.height} != expected ${ew}x${eh} for layout "${key}"`);
  if (v.pix_fmt !== 'yuv420p') errors.push(`pix_fmt ${v.pix_fmt} != yuv420p (QuickTime/TikTok/phones need yuv420p; render with --pixel-format=yuv420p)`);
  const fps = rate(v.r_frame_rate);
  const wantFps = probe.fpsIsVariable || probe.fps < 20 ? 30 : Math.round(probe.fps);
  if (Math.abs(fps - wantFps) > 0.01) errors.push(`fps ${fps} != expected ${wantFps}`);
  const kept = edl.segments.reduce((t, s) => t + (s.srcOut - s.srcIn), 0);
  const speed = edl.speed ?? 1;
  const expected = kept / speed;
  if (Math.abs(Number(v.duration) - expected) > 0.25) errors.push(`duration ${Number(v.duration).toFixed(2)}s != EDL kept length ${expected.toFixed(2)}s`);
  if (a) {
    const drift = Math.abs(Number(v.duration) - Number(a.duration));
    if (!(drift <= 0.1)) errors.push(`A/V drift ${drift.toFixed(3)}s > 0.1s`);
  }
}
// pacing check (reference avg shot 3.7s, max static 4.0s) - warning only
const lens = edl.segments.map((s) => s.srcOut - s.srcIn);
const long = lens.filter((l) => l > 7.2).length;
if (long) warns.push(`${long} segment(s) longer than 7s (jump-cut rule)`);
const tiny = lens.filter((l) => l < 0.6).length;
if (tiny) warns.push(`${tiny} segment(s) shorter than 0.6s`);

console.log(JSON.stringify({layout: key, expectedCanvas: [ew, eh], output: v && {pix_fmt: v.pix_fmt, w: v.width, h: v.height, fps: rate(v.r_frame_rate), dur: Number(v.duration)}, segments: lens.length, errors, warns}, null, 2));
if (errors.length) process.exit(1);
