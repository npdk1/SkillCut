import {BeatsFile, Beat} from './types';

type StickerBeat = Extract<Beat, {type: 'sticker'}>;

const overlaps = (a0: number, a1: number, b0: number, b1: number) => a0 < b1 && b0 < a1;

/** is a top-anchored caption (or a b-roll cutaway, which forces one) on screen during [t0,t1]? */
export const topCaptionDuring = (beats: BeatsFile, t0: number, t1: number): boolean =>
  !!beats.captionAnchor?.some((a) => a.anchor === 'top' && overlaps(a.t0, a.t1, t0, t1)) ||
  beats.beats.some((b) => b.type === 'broll' && overlaps(b.t0, b.t1, t0, t1));

/** Sticker look: explicit `look`, else sub -> label-right card, label -> label above tile, nothing -> bare tile. */
export const stickerLook = (b: StickerBeat): 'tile' | 'label-above' | 'label-right' => b.look ?? (b.sub ? 'label-right' : b.label ? 'label-above' : 'tile');

/** Sticker anchor: explicit, else top-left when a top caption/b-roll is active (the caption then shifts right), else centre-top for label-above, else top-left. */
export const stickerAnchor = (b: StickerBeat, beats: BeatsFile): 'top-left' | 'top-right' | 'center-top' => {
  if (b.anchor) return b.anchor;
  if (b.side === 'right') return 'top-right';
  if (topCaptionDuring(beats, b.t0, b.t1)) return 'top-left';
  return stickerLook(b) === 'label-above' ? 'center-top' : 'top-left';
};

/** Does a top-left tile sticker occupy the area beside a top caption at time t? (used to shift the dark caption block right) */
export const stickerBesideCaption = (beats: BeatsFile, t0: number, t1: number): boolean =>
  beats.beats.some((b) => b.type === 'sticker' && overlaps(b.t0, b.t1, t0, t1) && stickerLook(b) === 'tile' && stickerAnchor(b, beats) === 'top-left');
