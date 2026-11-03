import React from 'react';
import {Audio, Sequence, staticFile} from 'remotion';
import {MappedSegment, mapInterval} from '../../assets/remap';
import {Beat, BeatsFile} from '../../assets/types';
import {STYLE} from '../../assets/style';

/**
 * SFX + music, entirely driven by style.config.json -> audio.*  (both OFF by default: the reference audio analysis
 * was inconclusive, see analysis.md). Drop files into public/sfx/ and set audio.sfx.enabled / audio.music.enabled.
 */
export const Sfx: React.FC<{segs: MappedSegment[]; beats: BeatsFile; fps: number; totalFrames: number; speechRanges?: [number, number][]}> = ({segs, beats, fps, totalFrames, speechRanges}) => {
  const A = STYLE.audio;
  const out: React.ReactNode[] = [];
  if (A.music.enabled) {
    const duck = (f: number) => {
      if (!speechRanges) return A.music.volume;
      const t = f / fps;
      return speechRanges.some(([a, b]) => t >= a && t <= b) ? A.music.duckTo : A.music.volume;
    };
    out.push(<Audio key="music" src={staticFile(A.music.file)} volume={duck} loop />);
  }
  if (A.sfx.enabled) {
    const vol = A.sfx.volume;
    const cues = A.sfx.cues;
    segs.forEach((s, i) => {
      if (i === 0 || s.framing === segs[i - 1].framing) return;
      const f = Math.max(0, s.outStartFrame + cues.whoosh.offsetFrames);
      out.push(<Sequence key={`w${i}`} from={f}><Audio src={staticFile(cues.whoosh.file)} volume={vol} /></Sequence>);
    });
    beats.beats.forEach((b: Beat, i: number) => {
      const r = mapInterval(segs, b.t0, b.t1, fps);
      if (!r) return;
      const file = (cues.ping.on as string[]).includes(b.type) ? cues.ping.file : (cues.type.on as string[]).includes(b.type) ? cues.type.file : cues.pop.file;
      out.push(<Sequence key={`b${i}`} from={Math.min(totalFrames - 1, r[0])}><Audio src={staticFile(file)} volume={vol} /></Sequence>);
    });
  }
  return <>{out}</>;
};
