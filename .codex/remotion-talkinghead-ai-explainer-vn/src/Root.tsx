import React from 'react';
import {CalculateMetadataFunction, Composition, staticFile} from 'remotion';
import {TalkingHead, TalkingHeadProps} from './Composition';
import {buildLayout} from '../assets/layouts';
import {buildTimeline} from '../assets/remap';
import {BeatsFile, CaptionPage, Edl, Probe} from '../assets/types';

const getJson = async <T,>(name: string, required: boolean, fallback: T): Promise<T> => {
  const res = await fetch(staticFile(`project/${name}`));
  if (!res.ok) {
    if (required) throw new Error(`public/project/${name} not found. ORDER: 1) scripts/probe_video.py  2) scripts/transcribe.py  3) scripts/make_edl.py  4) write beats.json.`);
    return fallback;
  }
  return (await res.json()) as T;
};

/** The composition size, fps and length are COMPUTED from probe.json + edl.json. Never hard-code them. */
const calculateMetadata: CalculateMetadataFunction<TalkingHeadProps> = async ({props}) => {
  const probe = await getJson<Probe>('probe.json', true, null as unknown as Probe); // mandatory gate
  const edl = await getJson<Edl>('edl.json', true, null as unknown as Edl);
  const captions = await getJson<CaptionPage[]>('captions.json', false, []);
  const beats = await getJson<BeatsFile>('beats.json', false, {beats: []});
  const L = buildLayout(probe);
  const {totalFrames} = buildTimeline(edl, L.fps);
  return {width: L.canvas.w, height: L.canvas.h, fps: L.fps, durationInFrames: totalFrames, props: {...props, probe, edl, captions, beats}};
};

export const RemotionRoot: React.FC = () => (
  <Composition
    id="TalkingHead"
    component={TalkingHead}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={30}
    defaultProps={{probe: null, edl: null, captions: [], beats: {beats: []}, showSafe: false} as TalkingHeadProps}
    calculateMetadata={calculateMetadata}
  />
);
