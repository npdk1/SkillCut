import React, {useEffect, useLayoutEffect} from 'react';
import {AbsoluteFill, getRemotionEnvironment, useCurrentFrame} from 'remotion';
import {Layout} from '../../assets/layouts';

/**
 * LayoutCollisionGuard: samples every 5th frame and warns (console, prefix "[guard]") when
 *   - two [data-guard] boxes overlap by more than OVL_PX (6px) in both axes (e.g. a big-word on top of a title-burst),
 *   - a box leaves the canvas / the safe zone horizontally,
 *   - a text box is clipped (scrollWidth > clientWidth) instead of wrapping or shrinking.
 * Runs in Studio and in renders (browser log is shown with `--log=verbose`; scripts/verify-video.mjs greps it).
 * Each distinct warning is printed once. Mark anything important with data-guard="name". Pairs in PAIR_OK are by design.
 */
const PAIR_OK = new Set(['caption|caption', 'big-word|selection-box', 'selection-box|big-word']);
// scripts/check_overlaps.mjs renders with this guard at low scale and turns every "[ovl]" line into the overlap report (render gate)
const FACE_CHECKED = new Set(['title', 'rec', 'chips', 'prompt', 'comment', 'brand-logo', 'big-word', 'sticker', 'caption', 'illustration']);   // v4.2: captions are face-checked too
/** ONE overlap threshold for the whole pipeline (px, both axes): this guard, the warn level below, check_overlaps.mjs, check_logo_faces.py, make_beats.py and the docs all use 6 */
const OVL_PX = 6;
const effOpacity = (e: HTMLElement | null): number => { let o = 1; while (e) { o *= parseFloat(getComputedStyle(e).opacity || '1'); e = e.parentElement; } return o; };
const textRect = (e: HTMLElement, W: number): DOMRect => {
  const r = e.getBoundingClientRect();
  if (r.width === 0 || r.height === 0) {          // absolutely-positioned children only (chip-stack): measure the union of the children
    const kids = Array.from(e.children).map((k) => k.getBoundingClientRect()).filter((k) => k.width > 0);
    if (kids.length) return new DOMRect(Math.min(...kids.map((k) => k.left)), Math.min(...kids.map((k) => k.top)), Math.max(...kids.map((k) => k.right)) - Math.min(...kids.map((k) => k.left)), Math.max(...kids.map((k) => k.bottom)) - Math.min(...kids.map((k) => k.top)));
  }
  if (r.width > W * 0.8) {   // full-width wrappers (topic-line, info-header, ...): measure the real text/children, not the empty band
    const g = document.createRange(); g.selectNodeContents(e); const t = g.getBoundingClientRect(); if (t.width > 0) return t;
  }
  return r;
};
const seen = new Set<string>();

export const LayoutCollisionGuard: React.FC<{L: Layout; showSafe?: boolean}> = ({L, showSafe}) => {
  const frame = useCurrentFrame();
  const studio = getRemotionEnvironment().isStudio;
  // exhaustive per-frame check (every 2nd frame): logs EVERY visible intersection, no de-duplication
  useLayoutEffect(() => {
    // v4.4: captions are measured on EVERY frame (a caption can brush the forehead for a few frames only); everything else every 2nd frame
    const even = frame % 2 === 0;
    const els = (Array.from(document.querySelectorAll('[data-guard]')) as HTMLElement[]).filter((e) => (even || e.dataset.guard === 'caption') && effOpacity(e) > 0.15);
    const bx = els.map((e) => ({n: e.dataset.guard ?? '?', r: textRect(e, L.canvas.w)})).filter((x) => x.r.width > 0 && x.r.height > 0);
    for (const x of bx) if (FACE_CHECKED.has(x.n)) console.log('[box]' + JSON.stringify({f: frame, n: x.n, r: [x.r.left, x.r.top, x.r.right, x.r.bottom].map(Math.round)}));
    if (!even) return;
    for (let i = 0; i < bx.length; i++) for (let j = i + 1; j < bx.length; j++) {
      const a = bx[i], b = bx[j];
      if (PAIR_OK.has(`${a.n}|${b.n}`) || (a.n === b.n && a.n !== 'brand-logo')) continue;
      const ox = Math.min(a.r.right, b.r.right) - Math.max(a.r.left, b.r.left);
      const oy = Math.min(a.r.bottom, b.r.bottom) - Math.max(a.r.top, b.r.top);
      if (ox > OVL_PX && oy > OVL_PX) console.log('[ovl]' + JSON.stringify({f: frame, a: a.n, b: b.n, ox: Math.round(ox), oy: Math.round(oy), ra: [a.r.left, a.r.top, a.r.right, a.r.bottom].map(Math.round), rb: [b.r.left, b.r.top, b.r.right, b.r.bottom].map(Math.round)}));
    }
  });
  useEffect(() => {
    if (frame % 5 !== 0) return;
    const warn = (key: string, msg: string) => {
      if (seen.has(key)) return;
      seen.add(key);
      console.warn(`[guard] frame ${frame}: ${msg}`);
    };
    const els = Array.from(document.querySelectorAll('[data-guard]')) as HTMLElement[];
    const boxes = els.map((e) => ({n: e.dataset.guard ?? '?', r: e.getBoundingClientRect(), e}));
    for (let i = 0; i < boxes.length; i++) {
      const a = boxes[i];
      if (a.r.width === 0) continue;
      if (a.r.left < -4 || a.r.right > L.canvas.w + 4) warn(`out|${a.n}|${Math.floor(frame / 30)}`, `"${a.n}" leaves the canvas horizontally (${Math.round(a.r.left)}..${Math.round(a.r.right)} of ${L.canvas.w})`);
      if (a.e.scrollWidth > a.e.clientWidth + 2 && getComputedStyle(a.e).overflow !== 'visible') warn(`clip|${a.n}|${Math.floor(frame / 30)}`, `"${a.n}" text is clipped (${a.e.scrollWidth}>${a.e.clientWidth}px) - wrap or shrink it`);
      for (let j = i + 1; j < boxes.length; j++) {
        const b = boxes[j];
        if (PAIR_OK.has(`${a.n}|${b.n}`)) continue;
        const ox = Math.min(a.r.right, b.r.right) - Math.max(a.r.left, b.r.left);
        const oy = Math.min(a.r.bottom, b.r.bottom) - Math.max(a.r.top, b.r.top);
        if (ox > OVL_PX && oy > OVL_PX) warn(`ov|${a.n}|${b.n}|${Math.floor(frame / 30)}`, `"${a.n}" overlaps "${b.n}" (${Math.round(ox)}x${Math.round(oy)}px)`);
      }
    }
  }, [frame, L.canvas.w]);
  if (!studio || !showSafe) return null;
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <div style={{position: 'absolute', left: L.safe.left, right: L.safe.right, top: L.safe.top, bottom: L.safe.bottom, border: '2px dashed rgba(255,0,80,0.7)'}} />
    </AbsoluteFill>
  );
};
