import {Easing, interpolate} from 'remotion';
import {STYLE} from '../../assets/style';

export const clamp01 = (n: number) => Math.max(0, Math.min(1, n));
export const easeOutCubic = (t: number) => 1 - Math.pow(1 - clamp01(t), 3);
export const easeOutBack = (t: number) => Easing.out(Easing.back(1.6))(clamp01(t));
export const ease = (name: string, t: number) => (name === 'easeOutBack' ? easeOutBack(t) : easeOutCubic(t));

/** Standard beat in/out envelope. Returns opacity and scale. durationInFrames = Sequence length. */
export const envelope = (frame: number, duration: number, inF = STYLE.beats.common.inFrames, outF = STYLE.beats.common.outFrames) => {
  const a = clamp01(frame / Math.max(1, inF));
  const b = clamp01((duration - frame) / Math.max(1, outF));
  const pop = ease(STYLE.beats.common.ease, a);
  return {opacity: Math.min(a * 1.4, 1) * b, scale: STYLE.beats.common.popScaleFrom + (1 - STYLE.beats.common.popScaleFrom) * pop, in: a, out: b};
};

export const slideUp = (frame: number, startFrame: number, dur: number, px: number) =>
  interpolate(frame, [startFrame, startFrame + dur], [px, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
