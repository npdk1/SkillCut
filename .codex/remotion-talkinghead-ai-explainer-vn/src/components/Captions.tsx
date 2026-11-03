import React from 'react';
import {AbsoluteFill, Sequence, useCurrentFrame} from 'remotion';
import {Layout} from '../../assets/layouts';
import {MappedSegment, mapInterval, srcToOutFrame} from '../../assets/remap';
import {BeatsFile, CaptionLine, CaptionPage} from '../../assets/types';
import {STYLE} from '../../assets/style';
import {FONT_FAMILY, LETTER} from '../../assets/font';
import {clamp01, easeOutCubic} from './anim';
import {stickerBesideCaption} from '../../assets/placement';
import {beatRects, captionBlockH, captionTop} from '../../assets/zones';

const C = STYLE.caption;
const colorFor = (style: string) => (style === 'yellow' ? STYLE.colors.highlight : STYLE.colors.white);

const Word: React.FC<{text: string; i: number; frame: number; size: number; color: string}> = ({text, i, frame, size, color}) => {
  const a = C.anim;
  const start = i * a.staggerFrames;
  const p = easeOutCubic((frame - start) / a.durFrames);
  const o = clamp01((frame - start) / a.fadeFrames);
  return (
    <span style={{display: 'inline-block', clipPath: a.clipBottom ? 'inset(-60% -30% -4% -30%)' : undefined, marginRight: size * 0.26}}>
      <span style={{display: 'inline-block', transform: `translateY(${(1 - p) * a.risePxEm * size}px)`, opacity: o, color}}>{text}</span>
    </span>
  );
};

/** v4.4: NO caption background at all (no pill, no dark box, no frosted/blurred/white panel). The caption is readable by an outline
 *  (ring of text-shadows = stroke, works in every Chromium) + a soft drop shadow only. `caption.background.enabled` must stay false (verified.md V05). */
const outline = (px: number, color: string) => {
  const n = 12; const r = Math.max(1, px);
  return Array.from({length: n}, (_, i) => { const a = (i / n) * Math.PI * 2; return `${(Math.cos(a) * r).toFixed(2)}px ${(Math.sin(a) * r).toFixed(2)}px 0 ${color}`; }).join(', ');
};

const Line: React.FC<{line: CaptionLine; startIdx: number; localFrame: number; size: number; L: Layout; style: string}> = ({line, startIdx, localFrame, size, L, style}) => {
  // 'dark' / 'pill' styles keep their TEXT colours but lose the box: dark -> white text, pill (yellow keyword) -> yellow text
  const color = style === 'dark' ? C.dark.text : style === 'pill' ? STYLE.colors.highlight : colorFor(style);
  const strokePx = Math.max(C.stroke.widthPx, 4) * L.u * 0.5;
  const shadow = `0 ${C.shadow.offsetY * L.u}px ${C.shadow.blur * L.u}px rgba(0,0,0,${C.shadow.alpha})`;
  return (
    <div
      data-guard="caption"
      style={{
        display: 'inline-block', whiteSpace: 'nowrap', fontFamily: FONT_FAMILY, fontWeight: C.weight, fontSize: size, lineHeight: C.lineHeight, letterSpacing: LETTER, color,
        background: 'transparent', border: 'none', borderRadius: 0, padding: 0, boxShadow: 'none',
        textShadow: `${outline(strokePx, C.stroke.color)}, ${shadow}`,
      }}
    >
      {line.words.map((w, i) => (
        <Word key={i} text={w.w} i={Math.max(0, startIdx + i)} frame={localFrame} size={size} color={color} />
      ))}
    </div>
  );
};

const Page: React.FC<{page: CaptionPage; L: Layout; segs: MappedSegment[]; fps: number; anchor: 'top' | 'bottom' | 'center'; durFrames: number; variant: 'default' | 'dark'; shifted: boolean; beats: BeatsFile}> = ({page, L, segs, fps, anchor, durFrames, variant, shifted, beats}) => {
  const frame = useCurrentFrame();
  const D = C.dark;
  const dk = variant === 'dark';
  const size = page.size === 'hero' ? L.caption.hero : L.caption.normal;
  // dark variant: line 1 small on a dark pill, line 2 normal size on a yellow pill; block top-anchored
  let y = dk ? Math.round(L.canvas.h * D.line1CentreYr) : anchor === 'top' ? L.caption.topY : anchor === 'center' ? L.caption.centerY : L.caption.bottomY;
  if (!dk) {
    // v4.1 zone rule: while a beat element occupies the caption band, the caption moves above/below it (assets/zones.ts) - never drawn on top of an element
    const blockers = beats.beats.filter((b) => b.t0 < page.t1 && page.t0 < b.t1).flatMap((b) => beatRects(b, L));
    const h = captionBlockH(L, page.lines.length, size);
    y = captionTop(L, y - size * 0.6, h, blockers) + size * 0.6;
  }
  const pageOut = clamp01((durFrames - frame) / Math.max(1, dk ? D.pageOutFadeFrames : C.anim.pageOutFadeFrames));
  const line1Out = dk ? clamp01((durFrames - 2 - frame) / Math.max(1, D.pageOutFadeFrames)) : 1; // dark variant: line 1 drops first
  const pageStart = srcToOutFrame(segs, page.t0, fps) ?? 0;
  const cx = L.canvas.w * (dk && shifted ? D.shiftedCentreXr : D.unshiftedCentreXr);
  const boxH = (D.fontPx * C.lineHeight + 2 * D.padYPx) * L.u;
  let idx = 0;
  return (
    <AbsoluteFill style={{opacity: dk ? 1 : pageOut}}>
      <div style={{position: 'absolute', left: dk ? cx - L.canvas.w / 2 : 0, width: dk ? L.canvas.w : undefined, right: dk ? undefined : 0, top: dk ? y - boxH / 2 : y - size * 0.6, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: dk ? D.overlapPx * L.u : L.caption.lineGap}}>
        {page.lines.map((line, li) => {
          const lineStart = line.t0 !== undefined ? Math.max(0, (srcToOutFrame(segs, line.t0, fps) ?? pageStart) - pageStart) : 0;
          const start = idx;
          idx += line.words.length;
          if (frame < lineStart) return null;
          const st = dk ? (line.style === 'yellow' || line.style === 'pill' ? 'pill' : 'dark') : line.style;
          const sz = dk && st === 'dark' ? Math.round(D.fontPx * L.u) : size;
          const o = dk ? (li === 0 && page.lines.length > 1 ? line1Out : pageOut) : 1;
          return (
            <div key={li} style={{opacity: o, position: 'relative', zIndex: li}}>
              <Line line={line} startIdx={start - 0} localFrame={frame - lineStart + start * C.anim.staggerFrames} size={sz} L={L} style={st} />
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

export const Captions: React.FC<{pages: CaptionPage[]; beats: BeatsFile; L: Layout; segs: MappedSegment[]; fps: number}> = ({pages, beats, L, segs, fps}) => (
  <AbsoluteFill>
    {pages.map((p, i) => {
      const r = mapInterval(segs, p.t0, p.t1, fps);
      if (!r) return null; // whole page was cut
      const mid = (p.t0 + p.t1) / 2;
      // info-scene / topic-card beats carry their own text (header + lines): the spoken caption is suppressed underneath (reference behaviour)
      if (beats.beats.some((b) => (b.type === 'info-scene' || b.type === 'topic-card' || b.type === 'framed-focus') && p.t0 >= b.t0 - 0.05 && p.t0 < b.t1)) return null;
      const ov = beats.captionAnchor?.find((a) => mid >= a.t0 && mid <= a.t1);
      const brollOver = beats.beats.some((bb) => bb.type === 'broll' && mid >= bb.t0 && mid <= bb.t1);
      const variant = p.variant ?? ov?.variant ?? (brollOver ? 'dark' : 'default');
      const anchor = variant === 'dark' ? 'top' : p.anchor ?? ov?.anchor ?? 'bottom';
      const shifted = variant === 'dark' && stickerBesideCaption(beats, p.t0, p.t1);
      return (
        <Sequence key={i} from={r[0]} durationInFrames={r[1] - r[0]}>
          <Page page={p} L={L} segs={segs} fps={fps} anchor={anchor} durFrames={r[1] - r[0]} variant={variant} shifted={shifted} beats={beats} />
        </Sequence>
      );
    })}
  </AbsoluteFill>
);
