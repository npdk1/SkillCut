import {Edl, EdlSegment} from './types';

export interface MappedSegment extends EdlSegment {
  outStartFrame: number;
  durFrames: number;
  srcInFrame: number;
  speed: number;
}

/** Build the output timeline from the kept segments. Final duration is COMPUTED, never hard-coded. */
export const buildTimeline = (edl: Edl, fps: number): {segments: MappedSegment[]; totalFrames: number} => {
  let cursor = 0;
  const segments = edl.segments.map((s) => {
    const speed = s.speed ?? 1;
    const durFrames = Math.max(1, Math.round(((s.srcOut - s.srcIn) / speed) * fps));
    const m: MappedSegment = {...s, speed, outStartFrame: cursor, durFrames, srcInFrame: Math.round(s.srcIn * fps)};
    cursor += durFrames;
    return m;
  });
  return {segments, totalFrames: Math.max(1, cursor)};
};

/** source seconds -> output frame, or null if that instant was cut. */
export const srcToOutFrame = (segs: MappedSegment[], t: number, fps: number): number | null => {
  for (const s of segs) {
    if (t >= s.srcIn - 1e-6 && t <= s.srcOut + 1e-6) {
      return s.outStartFrame + Math.round(((t - s.srcIn) / s.speed) * fps);
    }
  }
  return null;
};

/** Map a source interval to output frames. Snaps to the nearest kept material; null if nothing survives. */
export const mapInterval = (segs: MappedSegment[], t0: number, t1: number, fps: number): [number, number] | null => {
  let a: number | null = null;
  let b: number | null = null;
  for (const s of segs) {
    const lo = Math.max(t0, s.srcIn);
    const hi = Math.min(t1, s.srcOut);
    if (hi <= lo) continue;
    const fa = s.outStartFrame + Math.round(((lo - s.srcIn) / s.speed) * fps);
    const fb = s.outStartFrame + Math.round(((hi - s.srcIn) / s.speed) * fps);
    if (a === null) a = fa;
    b = fb;
  }
  return a === null || b === null || b <= a ? null : [a, b];
};

/** Beat-internal source time (e.g. card.t) -> frames relative to the beat start, never negative. */
export const relFrame = (segs: MappedSegment[], tBeat: number, t0Beat: number, fps: number): number => {
  const a = srcToOutFrame(segs, Math.max(t0Beat, tBeat), fps);
  const o = srcToOutFrame(segs, t0Beat, fps);
  if (a === null || o === null) return 0;
  return Math.max(0, a - o);
};

/** the EDL segment playing at output frame `f`, and the matching SOURCE frame (for beats that carry their own copy of the footage). */
export const segAtOut = (segs: MappedSegment[], f: number): {seg: MappedSegment; srcFrame: number} => {
  const seg = segs.find((s) => f >= s.outStartFrame && f < s.outStartFrame + s.durFrames) ?? segs[segs.length - 1];
  return {seg, srcFrame: seg.srcInFrame + Math.round((f - seg.outStartFrame) * seg.speed)};
};
