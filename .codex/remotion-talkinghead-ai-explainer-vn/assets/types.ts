// Shared types. ALL times in project JSON files are SOURCE (raw video) seconds.
// The EDL decides what survives; remap.ts converts source time -> output time.

export type Orientation = 'portrait' | 'landscape' | 'square';
export type Reframe = 'none' | 'blurfill' | 'crop';

/** Written by scripts/probe_video.py -> public/project/probe.json (MANDATORY first step). */
export interface Probe {
  version: 1;
  file: string; // path relative to public/ (e.g. "project/raw.mp4")
  codec: string;
  hasAudio: boolean;
  durationSec: number;
  fps: number; // measured average fps, rounded to 3 decimals
  fpsIsVariable: boolean;
  stored: {width: number; height: number};
  rotationDeg: 0 | 90 | 180 | 270; // from display matrix / rotate tag (normalised, clockwise)
  sar: number; // sample aspect ratio (1 = square pixels)
  effective: {width: number; height: number}; // AFTER rotation and SAR. Everything downstream uses this.
  aspect: number; // effective.width / effective.height
  orientation: Orientation;
  needsNormalize: boolean; // true when rotation!=0, SAR!=1 or VFR -> run probe_video.py --normalize
  layoutKey: LayoutKey; // chosen by the decision table in layouts.ts / references/orientation-layouts.md
  reframe: Reframe; // only meaningful for landscape/square -> vertical output
  cropFocusX?: number; // 0..1, used when reframe === 'crop'
}

export type LayoutKey = 'vertical' | 'horizontal' | 'square' | 'horizontal-to-vertical' | 'square-to-vertical';

export interface EdlSegment {
  id: string;
  srcIn: number; // seconds in raw
  srcOut: number;
  role: 'hook' | 'body' | 'payoff' | 'cta' | 'broll';
  reason: string; // WHY kept (rubric labels)
  score?: number; // 0..1 rubric score
  speed?: number; // default 1. Only 1.0-1.12 allowed for speech.
  zoom?: {from: number; to: number}; // requested punch-in, clamped by layout.maxZoom
  transitionIn?: 'cut' | 'flash';
  framing?: 'wide' | 'mid' | 'tight'; // from style.config.json framing.levels; assigned by make_edl.py
  grade?: boolean; // false = skip the colour grade + vignette for this segment (footage that already carries one, e.g. the reference-recreation plate)
  punch?: boolean; // run the punch-in-settle at segment start (default true when framing changed)
}

export interface EdlDropped {
  srcIn: number;
  srcOut: number;
  reason: 'silence' | 'filler' | 'repeat-take' | 'low-energy' | 'off-topic' | 'dead-air' | 'false-start' | 'over-window' | 'manual';
  note?: string;
}

/** Edit-decision list. Output length = sum of kept segments (never forced to raw/reference length). */
export interface Edl {
  version: 1;
  source: {file: string; fps: number; durationSec: number};
  target?: {minSec: number; maxSec: number; ratio: number};
  segments: EdlSegment[];
  dropped: EdlDropped[];
  stats?: Record<string, number | string>;
}

export type CaptionStyle = 'white' | 'pill' | 'yellow' | 'dark';
export interface CaptionWord {w: string; t0: number; t1: number; style?: CaptionStyle}
export interface CaptionLine {words: CaptionWord[]; style: CaptionStyle; t0?: number}
export interface CaptionPage {
  t0: number;
  t1: number;
  lines: CaptionLine[];
  anchor?: 'bottom' | 'top' | 'center'; // default bottom; switch to top when host/graphics occupy the lower third
  size?: 'hero' | 'normal';
  variant?: 'default' | 'dark'; // 'dark' = caption over bright screen b-roll (dark pill line 1 + yellow pill line 2). Auto when the page overlaps a broll beat or a captionAnchor entry has variant:'dark'
}

export interface BeatsFile {
  beats: Beat[];
  captionAnchor?: {t0: number; t1: number; anchor: 'top' | 'bottom' | 'center'; variant?: 'default' | 'dark'}[];
}

export type Beat =
  | {type: 'broll'; t0: number; t1: number; src: string; startFromSec?: number; fit?: 'cover' | 'contain'}
  | {type: 'stars'; t0: number; t1: number}
  | {type: 'sticker'; t0: number; t1: number; label?: string; sub?: string; side?: 'left' | 'right'; x?: number; y?: number; look?: 'tile' | 'label-above' | 'label-right'; hl?: string; anchor?: 'top-left' | 'top-right' | 'center-top'; icon?: string}
  | {type: 'chip-stack'; dy?: number; t0: number; t1: number; items: {t: number; title: string; sub: string; icon?: string}[]}
  | {type: 'avatar-chain'; t0: number; t1: number; left: string; chip: string; right: string; badge?: string}
  | {type: 'prompt-box'; dy?: number; t0: number; t1: number; text: string; strikeAt?: number}
  | {type: 'title-burst'; dy?: number; t0: number; t1: number; title: string; sub?: string; rec?: string; timeline?: boolean}
  | {type: 'big-word'; t0: number; t1: number; text: string; sparkles?: boolean; color?: 'yellow' | 'white'}
  | {type: 'selection-box'; t0: number; t1: number; label: string; size: string}
  | {type: 'brand-logo'; t0: number; t1: number; name: string; logo: string; color?: string; /** v4.1 face-aware placement (fractions of the canvas): card centre x, card top y, size multiplier */ x?: number; y?: number; scale?: number; /** v4.3 ladder last rung: compact icon+label pill */ pill?: boolean}
  | {type: 'illustration'; t0: number; t1: number; concept: string; label: string; icon: string; color?: string; source?: string; /** face-aware placement, same card model as brand-logo (card centre x, card top y, size multiplier) */ x?: number; y?: number; scale?: number; /** v4.3 ladder last rung: compact icon+label pill */ pill?: boolean}
  | {type: 'comment-box'; dy?: number; t0: number; t1: number; typed: string; bubble?: string}
  | {type: 'framed-focus'; t0: number; t1: number; header: string; lines: {t: number; text: string; pill?: boolean}[]; device?: 'phone' | 'window'; statusTime?: string; title?: string}
  | {type: 'text-behind-speaker'; t0: number; t1: number; text: string; id: string; y?: number; h?: number; color?: 'white' | 'yellow'; anim?: 'slide' | 'type' | 'marquee'; maskDir?: string; maskFirst?: number; maskStart?: number; items?: {text: string; align: 'l' | 'c' | 'r'; size: number; x: number; y: number}[]; track?: number[]; trackRef?: number; fallback?: 'headline'}
  | {type: 'info-scene'; t0: number; t1: number; header: string; headline?: {t: number; text: string}; cardsExitAt?: number; cards: {t: number; text: string; sub?: string; strike?: boolean; icon?: string; accent?: boolean}[]; pill?: {t: number; text: string}; media?: {src: string; kind: 'window' | 'phone'; t: number}}
  | {type: 'topic-card'; t0: number; t1: number; header: string; media: {src: string; kind: 'window' | 'phone'}; lines: {t: number; text: string; hl?: boolean; pill?: boolean; at?: 'top' | 'bottom'; slot?: number; until?: number}[]};
