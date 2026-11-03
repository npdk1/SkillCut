import React from 'react';
import {AbsoluteFill, Audio, staticFile} from 'remotion';
import {buildLayout} from '../assets/layouts';
import {buildTimeline} from '../assets/remap';
import {BeatsFile, CaptionPage, Edl, Probe} from '../assets/types';
import {STYLE} from '../assets/style';
import {Beats} from './components/Beats';
import {Captions} from './components/Captions';
import {LayoutCollisionGuard} from './components/LayoutCollisionGuard';
import {Sfx} from './components/Sfx';
import {VideoLayer} from './components/VideoLayer';

export type TalkingHeadProps = {
  probe: Probe | null;
  edl: Edl | null;
  captions: CaptionPage[];
  beats: BeatsFile;
  showSafe?: boolean;
};

/**
 * 7-layer stack (same as remotion-house-review-vn):
 * 1 footage (EDL segments, punch-in framing, grade)  2 under-beats (b-roll, info scenes)  3 over-beats (chips, stickers, prompts ...)
 * 4 captions  5 sfx/music  6 collision guard (studio only)
 * Everything geometric comes from buildLayout(probe); everything stylistic from style.config.json.
 */
export const TalkingHead: React.FC<TalkingHeadProps> = ({probe, edl, captions, beats, showSafe}) => {
  if (!probe || !edl) throw new Error('probe.json / edl.json missing. Run scripts/probe_video.py FIRST, then scripts/make_edl.py.');
  const L = buildLayout(probe);
  const {segments, totalFrames} = buildTimeline(edl, L.fps);
  return (
    <AbsoluteFill style={{backgroundColor: '#000'}}>
      <VideoLayer segs={segments} probe={probe} layout={L} />
      <Beats beats={beats} L={L} segs={segments} fps={L.fps} only="under" probe={probe} />
      <Beats beats={beats} L={L} segs={segments} fps={L.fps} only="over" probe={probe} />
      <Captions pages={captions} beats={beats} L={L} segs={segments} fps={L.fps} />
      <Sfx segs={segments} beats={beats} fps={L.fps} totalFrames={totalFrames} />
      <LayoutCollisionGuard L={L} showSafe={showSafe} />
    </AbsoluteFill>
  );
};

export const _styleVersion = STYLE.reference.file; // keeps the config import in the bundle graph
export const _audio = Audio; // (Audio is used by Sfx; re-exported only to keep tree-shaking predictable)
export const _staticFile = staticFile;
