import {Layout} from './layouts';
import {Beat} from './types';
import {STYLE} from './style';

/**
 * SCREEN ZONES (v4.1). Every beat type declares the canvas rectangle(s) it occupies; the SAME numbers are used by
 *   - Captions.tsx      -> a caption page that would sit on an element is moved above/below it (captionTop)
 *   - make_beats.py     -> rects_of() is the Python mirror (collision pass: no two zone-sharing beats at the same time)
 *   - check_overlaps.mjs-> measures the REAL DOM boxes of every frame and fails the render on any intersection
 * Rect = [x0, y0, x1, y1] in canvas px.
 */
export type Rect = [number, number, number, number];

export const beatRects = (b: Beat, L: Layout): Rect[] => {
  const rs = beatRects0(b, L), d = ((b as {dy?: number}).dy ?? 0) * L.canvas.h;
  if (!d) return rs;
  return b.type === 'title-burst' ? rs.map((r, i) => (i === 0 ? [r[0], r[1] + d, r[2], r[3] + d] as Rect : r)) : rs.map((r) => [r[0], r[1] + d, r[2], r[3] + d] as Rect);
};

const beatRects0 = (b: Beat, L: Layout): Rect[] => {
  const W = L.canvas.w, H = L.canvas.h, u = L.u;
  switch (b.type) {
    case 'title-burst': {
      const t = L.title;
      const r: Rect[] = [[t.x, t.recY - 0.01 * H, W - L.safe.right, t.y + t.font * 1.15 + (b.sub ? t.subFont * 1.25 : 0)]];
      if (b.timeline) r.push([(W - t.timelineW) / 2, t.timelineY, (W + t.timelineW) / 2, t.timelineY + t.timelineH]);
      return r;
    }
    case 'prompt-box': return [[L.prompt.x, L.prompt.y, L.prompt.x + L.prompt.w, L.prompt.y + L.prompt.h]];
    case 'chip-stack': {
      const C = L.chips, n = b.items.length, rows = Math.ceil(n / C.cols), cols = Math.min(n, C.cols);
      return [[C.x, C.y, C.x + cols * C.w + (cols - 1) * C.gapX, C.y + rows * C.h + (rows - 1) * C.gapY]];
    }
    case 'comment-box': {
      const c = L.comment;
      return [[c.x, c.y + Math.min(0, c.bubbleDy), c.x + c.w, c.y + c.pillH + c.pillShift]];
    }
    case 'avatar-chain': return [[W * 0.05, H * 0.8, W * 0.95, H * 0.89]];
    case 'big-word': case 'selection-box': return [[W * 0.05, L.bigWord.y, W * 0.95, L.bigWord.y + L.bigWord.font * 1.2]];
    case 'brand-logo': case 'illustration': {
      const S = L.logo.size * (b.scale ?? 1), nf = L.logo.nameFont * (b.scale ?? 1), nm = b.type === 'illustration' ? b.label : b.name;
      const pill = b.type === 'illustration' && !!b.pill;
      const cw = pill ? L.logo.size * 0.45 + nm.length * L.logo.nameFont * 0.58 + 30 * u : Math.max(S, nm.length * nf * 0.58) + 16 * u, ch = pill ? L.logo.size * 0.5 : S + 1.7 * nf;
      if (b.x !== undefined && b.y !== undefined) return [[b.x * W - cw / 2, b.y * H, b.x * W + cw / 2, b.y * H + ch]];
      return [[(W - cw) / 2, L.logo.y, (W + cw) / 2, L.logo.y + ch]];
    }
    case 'text-behind-speaker': {
      if (b.items && b.items.length) return b.items.map((it) => { const lines = it.text.split('\n'), sz = it.size * W, w = Math.max(...lines.map((l) => l.length)) * sz * STYLE.beats.textBehind.glyphEm, x0 = it.align === 'l' ? it.x * W : it.align === 'r' ? it.x * W - w : it.x * W - w / 2; return [x0, it.y * H, x0 + w, it.y * H + lines.length * sz * STYLE.beats.textBehind.lineHeight] as [number, number, number, number]; });
      const n = b.text.split('\n').length; return [[0, (b.y ?? 0.3) * H, W, (b.y ?? 0.3) * H + n * textBehindFont(L, b.text) * STYLE.beats.textBehind.lineHeight]];
    }
    default: return [];   // stars / stickers sit in the top band; info-scene / topic-card are full-screen and replace the spoken caption
  }
};

const inter = (a: Rect, b: Rect, pad = 0) => Math.min(a[2], b[2]) - Math.max(a[0], b[0]) > pad && Math.min(a[3], b[3]) - Math.max(a[1], b[1]) > pad;

/** height of a caption block of n lines (pill/yellow lines carry padding) */
export const captionBlockH = (L: Layout, n: number, size: number) => n * (size * STYLE.caption.lineHeight + 2 * L.caption.padY) + (n - 1) * L.caption.lineGap;

/**
 * Where the caption block (default top `top`, height `h`) goes while `blockers` are on screen: the default position when free,
 * else directly above the blocking elements, else directly below them (inside the safe area), nearest to the default first.
 */
export const captionTop = (L: Layout, top: number, h: number, blockers: Rect[]): number => {
  const gap = 14 * L.u, W = L.canvas.w;
  const box = (t: number): Rect => [(W - L.caption.maxWidth) / 2, t, (W + L.caption.maxWidth) / 2, t + h];
  const hit = (t: number) => blockers.filter((r) => inter(box(t), r, 2));
  if (!hit(top).length) return top;
  const lo = L.safe.top, hi = L.canvas.h - L.safe.bottom - h;
  let best = top, bestD = Infinity;
  for (const dir of ['above', 'below'] as const) {
    let t = top;
    for (let k = 0; k < 4; k++) {
      const hs = hit(t);
      if (!hs.length) break;
      t = dir === 'above' ? Math.min(...hs.map((r) => r[1])) - gap - h : Math.max(...hs.map((r) => r[3])) + gap;
    }
    if (hit(t).length || t < lo || t > hi) continue;
    if (Math.abs(t - top) < bestD) { best = t; bestD = Math.abs(t - top); }
  }
  if (bestD === Infinity) best = Math.min(Math.max(top, lo), hi);   // nowhere clean: the make_beats collision pass / check_overlaps.mjs report it
  return best;
};

/** font size of a text-behind-speaker headline: big, one line per `\n`, capped to the width (shared by Scenes.tsx and make_beats.py) */
export const textBehindFont = (L: Layout, text: string): number => {
  const T = STYLE.beats.textBehind, lines = text.split('\n'), maxLen = Math.max(...lines.map((l) => l.length));
  return Math.min(T.fontPx * L.u, (L.canvas.w * T.maxWidthR) / (maxLen * T.glyphEm));
};
