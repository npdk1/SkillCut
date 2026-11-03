import React from 'react';
import {AbsoluteFill, OffthreadVideo, Sequence, staticFile, useCurrentFrame} from 'remotion';
import {Layout} from '../../assets/layouts';
import {MappedSegment} from '../../assets/remap';
import {Probe} from '../../assets/types';
import {STYLE} from '../../assets/style';
import {easeOutCubic} from './anim';

const g = STYLE.grade;
/** v4.4 PROFILE FIX: the overlap gate (scripts/check_overlaps.mjs) only measures DOM boxes, never pixels -> REMOTION_GATE=1 skips video decode + blur + grade entirely
 *  (the gate used to decode and blur the full footage up to 4x per render.sh run). Never set for a real render. */
const GATE = process.env.REMOTION_GATE === '1';
/** blurred backdrop is rendered at 1/BLUR_DIV size and scaled up: the blur radius shrinks by the same factor, so the look is identical but the per-frame cost is ~1/16 */
const BLUR_DIV = 4;
const gradeFilter = g.enabled ? `brightness(${g.brightness}) contrast(${g.contrast}) saturate(${g.saturate}) sepia(${g.sepia})` : 'none';

/** zoom for a segment: framing level clamped by layout.maxZoom, with the measured punch-in-settle at the start. */
export const zoomAt = (seg: MappedSegment, frame: number, layout: Layout): number => {
  const level = STYLE.framing.levels[seg.framing ?? 'wide'];
  const requested = seg.zoom ? seg.zoom.from + (seg.zoom.to - seg.zoom.from) * (frame / Math.max(1, seg.durFrames)) : level;
  const base = Math.min(requested, layout.video.maxZoom);
  if (seg.punch === false || (seg.framing ?? 'wide') === 'wide' && !seg.punch) return base;
  const p = STYLE.framing.punch;
  const k = 1 + (p.overshoot - 1) * (1 - easeOutCubic(frame / p.settleFrames));
  return Math.min(base * k, layout.video.maxZoom * p.overshoot);
};

const Clip: React.FC<{seg: MappedSegment; probe: Probe; layout: Layout}> = ({seg, probe, layout}) => {
  const frame = useCurrentFrame();
  const z = zoomAt(seg, frame, layout);
  const v = layout.video;
  const src = staticFile(probe.file);
  const gf = seg.grade === false ? 'none' : gradeFilter;
  const common = {src, startFrom: seg.srcInFrame, playbackRate: seg.speed} as const;
  if (GATE) return <AbsoluteFill style={{backgroundColor: '#222'}} />;

  if (v.fit === 'blurfill') {
    return (
      <AbsoluteFill style={{overflow: 'hidden'}}>
        <div style={{position: 'absolute', left: 0, top: 0, width: layout.canvas.w / BLUR_DIV, height: layout.canvas.h / BLUR_DIV, transformOrigin: '0 0', transform: `scale(${BLUR_DIV * 1.25}) translate(${-layout.canvas.w / BLUR_DIV * 0.1}px, ${-layout.canvas.h / BLUR_DIV * 0.1}px)`, filter: `blur(${v.blurPx / BLUR_DIV}px) brightness(${v.dim})`}}>
          <OffthreadVideo {...common} muted style={{width: '100%', height: '100%', objectFit: 'cover'}} />
        </div>
        <div style={{position: 'absolute', left: v.fgBox.x, top: v.fgBox.y, width: v.fgBox.w, height: v.fgBox.h, overflow: 'hidden', filter: gf}}>
          <OffthreadVideo {...common} style={{width: '100%', height: '100%', objectFit: 'fill', transform: `scale(${z})`}} />
        </div>
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={{overflow: 'hidden', filter: gf}}>
      <OffthreadVideo {...common} style={{width: '100%', height: '100%', objectFit: 'cover', objectPosition: `${v.focusX * 100}% 50%`, transform: `scale(${z})`, transformOrigin: `${v.focusX * 100}% 40%`}} />
    </AbsoluteFill>
  );
};

export const VideoLayer: React.FC<{segs: MappedSegment[]; probe: Probe; layout: Layout}> = ({segs, probe, layout}) => (
  <AbsoluteFill style={{backgroundColor: '#000'}}>
    {segs.map((s) => (
      <Sequence key={s.id} from={s.outStartFrame} durationInFrames={s.durFrames}>
        <Clip seg={s} probe={probe} layout={layout} />
      </Sequence>
    ))}
    {/* weak vignette, measured corner/centre luma 0.85-1.0 */}
    {segs.some((s) => s.grade !== false) && <AbsoluteFill style={{pointerEvents: 'none', background: `radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 55%, rgba(0,0,0,${g.vignette}) 100%)`}} />}
  </AbsoluteFill>
);
