import {LayoutKey, Probe} from './types';
import {STYLE} from './style';

/**
 * ORIENTATION-AWARE LAYOUTS (decision table: references/orientation-layouts.md).
 * Nothing in the composition hard-codes 1080x1920: width / height / fps / positions / font sizes
 * come from buildLayout(probe) + style.config.json -> layout.{vertical|horizontal|square}.
 */
export interface Layout {
  key: LayoutKey;
  canvas: {w: number; h: number};
  fps: number;
  u: number; // px scale vs. 1080-short-side design tokens
  tier: '1080' | '720';
  vertical: boolean;
  video: {
    fit: 'cover' | 'blurfill' | 'crop';
    fgBox: {x: number; y: number; w: number; h: number};
    blurPx: number;
    dim: number;
    focusX: number;
    maxZoom: number;
    defaultPunch: number;
    srcScale: number; // canvas px per source px at zoom 1
  };
  safe: {top: number; bottom: number; left: number; right: number};
  caption: {bottomY: number; topY: number; centerY: number; normal: number; hero: number; lineGap: number; maxWidth: number; padX: number; padY: number; radius: number};
  title: {x: number; y: number; font: number; subFont: number; recY: number; timelineY: number; timelineW: number; timelineH: number};
  chips: {x: number; y: number; w: number; h: number; gapX: number; gapY: number; cols: number; titleFont: number; subFont: number};
  info: {headerY: number; headerFont: number; listY: number; cardW: number; cardH: number; cardGap: number; cardFont: number; mediaY: number; mediaW: number; titleY: number; headlineY: number; topicWinY: number; topicPhoneY: number; topicBottomY: number; topicLineFont: number};
  prompt: {x: number; y: number; w: number; h: number; font: number};
  bigWord: {y: number; font: number};
  logo: {y: number; size: number; nameFont: number};
  sticker: {x: number; y: number; size: number; labelFont: number; topYr: number; centerTopYr: number; cardYr: number; centerXr: number; topXr: number; chatXr: number; chatYr: number};
  comment: {x: number; y: number; w: number; h: number; font: number; bubbleDy: number; bubbleH: number; pillShift: number; pillH: number};
}

export const nearestFps = (fps: number, variable: boolean): number => {
  if (variable || !isFinite(fps) || fps < 20) return 30;
  if (fps > 60) return 60;
  return Math.round(fps); // 29.97 -> 30, 23.976 -> 24
};

/** The decision table in code. probe_video.py writes the SAME rule into probe.layoutKey. */
export const chooseLayoutKey = (p: Pick<Probe, 'orientation' | 'reframe'>): LayoutKey => {
  if (p.orientation === 'portrait') return 'vertical';
  if (p.orientation === 'landscape') return p.reframe === 'none' ? 'horizontal' : 'horizontal-to-vertical';
  return p.reframe === 'none' ? 'square' : 'square-to-vertical';
};

export const buildLayout = (p: Probe): Layout => {
  const key = chooseLayoutKey(p);
  const vertical = key === 'vertical' || key.endsWith('-to-vertical');
  const profile = key === 'horizontal' ? STYLE.layout.horizontal : key === 'square' ? STYLE.layout.square : STYLE.layout.vertical;
  const RF = STYLE.layout.reframe;

  const shortSrc = Math.min(p.effective.width, p.effective.height);
  // v4.3: a vertical canvas (reframe of a 16:9 / square clip, or a portrait clip) is ALWAYS 1080x1920 - the short side of a 16:9 source (1080x608 -> 608) used to pick the 720 tier
  const tier: '1080' | '720' = vertical || shortSrc >= 720 ? '1080' : '720';
  const S = tier === '1080' ? 1080 : 720;
  const L = tier === '1080' ? 1920 : 1280;
  let w: number, h: number;
  if (vertical) { w = S; h = L; } else if (key === 'horizontal') { w = L; h = S; } else { w = S; h = S; }
  const u = S / 1080;
  const V = (n: number) => Math.round(n * u);

  let fgBox = {x: 0, y: 0, w, h};
  let fit: 'cover' | 'blurfill' | 'crop' = 'cover';
  if (key === 'horizontal-to-vertical' || key === 'square-to-vertical') {
    if (p.reframe === 'crop') fit = 'crop';
    else {
      fit = 'blurfill';
      const fh = Math.round(w / p.aspect);
      fgBox = {x: 0, y: Math.round((h - fh) / 2 + h * RF.fgYShiftR), w, h: fh};
    }
  }
  const fgScale = fit === 'blurfill' ? fgBox.w / p.effective.width : Math.max(w / p.effective.width, h / p.effective.height);
  const maxZoom = Math.max(1, Math.min(profile.maxZoom, RF.qualityCap / fgScale));
  const r2 = (n: number) => Math.round(n * 100) / 100;
  const H = h, W = w;

  const c = profile.caption;
  const caption = {
    bottomY: Math.round(H * c.bottomYr), topY: Math.round(H * c.topYr), centerY: Math.round(H * c.centerYr),
    normal: V(c.normal), hero: V(c.hero), lineGap: V(c.lineGap), maxWidth: Math.round(W * c.maxWidthR), padX: V(c.padX), padY: V(c.padY), radius: V(c.radius),
  };
  const sf = profile.safe;
  const safe = {top: Math.round(H * sf.topR), bottom: Math.round(H * sf.bottomR), left: Math.round(W * sf.leftR), right: Math.round(W * sf.rightR)};
  if (fit === 'blurfill') {
    caption.bottomY = Math.min(Math.round(fgBox.y + fgBox.h + (H - fgBox.y - fgBox.h) * 0.42), Math.round(H * 0.7));
    caption.topY = Math.round(fgBox.y * 0.5);
  }
  const t = profile.title, ch = profile.chips as {xR: number; yR: number; w?: number; wR?: number; h: number; gapX: number; gapY: number; cols: number; titleFont: number; subFont: number};
  const i = profile.info, pr = profile.prompt, bw = profile.bigWord, lg = (profile as any).logo as {yR: number; size: number; nameFont: number}, st = profile.sticker, cm = profile.comment;

  return {
    key, canvas: {w, h}, fps: nearestFps(p.fps, p.fpsIsVariable), u, tier, vertical,
    video: {fit, fgBox, blurPx: V(RF.blurPx), dim: RF.dim, focusX: p.cropFocusX ?? 0.5, maxZoom: r2(maxZoom), defaultPunch: r2(Math.min(maxZoom, profile.defaultPunch)), srcScale: fgScale},
    safe, caption,
    title: {x: Math.round(W * t.xR), y: Math.round(H * t.yR), font: V(t.font), subFont: V(t.subFont), recY: Math.round(H * t.recYR), timelineY: Math.round(H * t.timelineYR), timelineW: Math.round(W * t.timelineWR), timelineH: V(t.timelineH)},
    chips: {x: Math.round(W * ch.xR), y: Math.round(H * ch.yR), w: ch.w !== undefined ? V(ch.w) : Math.round(W * (ch.wR ?? 0.4)), h: V(ch.h), gapX: V(ch.gapX), gapY: V(ch.gapY), cols: ch.cols, titleFont: V(ch.titleFont), subFont: V(ch.subFont)},
    info: {headerY: Math.round(H * i.headerYR), headerFont: V(i.headerFont), listY: Math.round(H * i.listYR), cardW: Math.round(W * i.cardWR), cardH: V(i.cardH), cardGap: V(i.cardGap), cardFont: V(i.cardFont), mediaY: Math.round(H * i.mediaYR), mediaW: Math.round(W * i.mediaWR), titleY: Math.round(H * i.titleYR), headlineY: Math.round(H * (i.headlineYR ?? i.titleYR)), topicWinY: Math.round(H * i.topicWinYR), topicPhoneY: Math.round(H * i.topicPhoneYR), topicBottomY: Math.round(H * i.topicBottomYR), topicLineFont: V(i.topicLineFont)},
    prompt: {x: Math.round(W * pr.xR), y: Math.round(H * pr.yR), w: Math.round(W * pr.wR), h: V(pr.h), font: V(pr.font)},
    bigWord: {y: Math.round(H * bw.yR), font: V(bw.font)},
    logo: {y: Math.round(H * lg.yR), size: V(lg.size), nameFont: V(lg.nameFont)},
    sticker: {x: Math.round(W * st.xR), y: Math.round(H * st.yR), size: V(st.size), labelFont: V(st.labelFont), topYr: st.topYr, centerTopYr: st.centerTopYr, cardYr: st.cardYr, centerXr: st.centerXr, topXr: st.topXr, chatXr: st.chatXr, chatYr: st.chatYr},
    comment: {x: Math.round(W * cm.xR), y: Math.round(H * cm.yR), w: Math.round(W * cm.wR), h: V(cm.h), font: V(cm.font), bubbleDy: Math.round(H * cm.bubbleDyR), bubbleH: Math.round(H * cm.bubbleHR), pillShift: Math.round(H * cm.pillShiftYr), pillH: Math.round(H * cm.pillHR)},
  };
};
