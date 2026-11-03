import React from 'react';
import {AbsoluteFill, Img, OffthreadVideo, Sequence, staticFile, useCurrentFrame} from 'remotion';
import {Layout} from '../../assets/layouts';
import {MappedSegment, relFrame, segAtOut} from '../../assets/remap';
import {Beat, Probe} from '../../assets/types';
import {STYLE} from '../../assets/style';
import {FONT_FAMILY, LETTER} from '../../assets/font';
import {clamp01, easeOutCubic, envelope} from './anim';
import {zoomAt} from './VideoLayer';
import {textBehindFont} from '../../assets/zones';

const K = STYLE.colors;
const SC = STYLE.beats.framedFocus;
const TB = STYLE.beats.textBehind;
export type SceneCtx = {L: Layout; segs: MappedSegment[]; fps: number; dur: number; t0: number; probe: Probe | null; r0: number};

const txt = (size: number, extra: React.CSSProperties = {}): React.CSSProperties => ({fontFamily: FONT_FAMILY, fontWeight: 800, fontSize: size, letterSpacing: LETTER, lineHeight: 1.12, color: K.white, ...extra});
/** v4.4 (verified.md V05): the 'pill' line is yellow text with an 8-way black stroke + soft shadow, no filled box (beats.infoScene.pillFilled=false) */
const STROKE_SHADOW = (u: number) => [[-1, -1], [1, -1], [-1, 1], [1, 1], [0, -1.4], [0, 1.4], [-1.4, 0], [1.4, 0]].map(([dx, dy]) => `${dx * 4 * u}px ${dy * 4 * u}px 0 #000`).join(', ') + `, 0 ${4 * u}px ${12 * u}px rgba(0,0,0,.55)`;
const fit = (t: string, size: number, maxW: number, minScale = 0.6) => { const est = t.length * size * 0.56; return est <= maxW ? size : Math.max(size * minScale, size * (maxW / est)); };

/** the speaker footage inside a beat: same source frames / grade / focus as the main clip, muted (the main clip below keeps the audio).
 *  Split per EDL segment so a cut inside the beat stays in sync. `follow` = apply the main clip's framing zoom (text-behind-speaker must line up with its mask). */
const Footage: React.FC<{ctx: SceneCtx; style?: React.CSSProperties; zoom?: number; follow?: boolean; grade?: boolean}> = ({ctx, style, zoom = 1, follow, grade}) => {
  const {L, segs, probe, r0, dur} = ctx;
  if (!probe) return null;
  const parts = segs.filter((s) => s.outStartFrame < r0 + dur && s.outStartFrame + s.durFrames > r0);
  const gf = STYLE.grade.enabled ? `brightness(${STYLE.grade.brightness}) contrast(${STYLE.grade.contrast}) saturate(${STYLE.grade.saturate}) sepia(${STYLE.grade.sepia})` : 'none';
  return (
    <AbsoluteFill style={{filter: grade ? gf : undefined}}>
      {parts.map((s, i) => {
        const a = Math.max(r0, s.outStartFrame), z = Math.min(r0 + dur, s.outStartFrame + s.durFrames);
        return (
          <Sequence key={i} from={a - r0} durationInFrames={z - a}>
            <FootagePart seg={s} startFrame={s.srcInFrame + Math.round((a - s.outStartFrame) * s.speed)} outA={a} ctx={ctx} style={style} zoom={zoom} follow={follow} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
const FootagePart: React.FC<{seg: MappedSegment; startFrame: number; outA: number; ctx: SceneCtx; style?: React.CSSProperties; zoom: number; follow?: boolean}> = ({seg, startFrame, outA, ctx, style, zoom, follow}) => {
  const f = useCurrentFrame();
  const {L, probe} = ctx;
  const z = follow ? zoomAt(seg, outA + f - seg.outStartFrame, L) : zoom;
  return <OffthreadVideo src={staticFile(probe!.file)} startFrom={startFrame} playbackRate={seg.speed} muted style={{width: '100%', height: '100%', objectFit: 'cover', objectPosition: `${L.video.focusX * 100}% 50%`, transform: `scale(${z})`, transformOrigin: `${L.video.focusX * 100}% 40%`, ...style}} />;
};

/* ---------- 11. framed-focus: the speaker shrunk into a device frame over a blurred, darkened copy of himself + headline lines ---------- */
export const FramedFocus: React.FC<SceneCtx & {b: Extract<Beat, {type: 'framed-focus'}>}> = (ctx) => {
  const {L, segs, fps, dur, t0, b} = ctx;
  const f = useCurrentFrame();
  const W = L.canvas.w, H = L.canvas.h, u = L.u;
  const e = envelope(f, dur, SC.popFrames);
  const inP = easeOutCubic(f / SC.scaleInFrames);
  const out = clamp01((dur - f) / STYLE.beats.common.outFrames);
  const phone = (b.device ?? 'phone') === 'phone';
  // vertical budget (fractions of H): headline block, device, safe bottom
  const top = L.safe.top, headF = L.info.headerFont * SC.headScale;
  const headH = headF * 1.15, lineF = headF * SC.lineScale, lineH = lineF * 1.25;
  const nLines = Math.min(b.lines.length, 2);
  const blockH = headH + nLines * (lineH + 8 * u);
  const devTop = top + blockH + SC.gapPx * u;
  const devBottom = H - L.safe.bottom - SC.bottomPadPx * u;
  const avail = devBottom - devTop;
  const bez = (phone ? SC.phone.bezelPx : SC.window.bezelPx) * u, bar = phone ? 0 : SC.window.barPx * u;
  let devW: number, devH: number;
  if (phone) { devH = Math.min(avail, W * 1.45); devW = Math.min((devH - 2 * bez) * (9 / 19.5) + 2 * bez, W * SC.phone.maxWidthR); devH = Math.min(devH, (devW - 2 * bez) * (19.5 / 9) + 2 * bez); }
  else { devW = W * SC.window.widthR; devH = Math.min(avail, devW * SC.window.aspect); }
  const devX = (W - devW) / 2, devY = devTop + (avail - devH) / 2;
  const maxW = W - L.safe.left - L.safe.right;
  const lineAt = (i: number) => Math.min(relFrame(segs, b.lines[i].t, t0, fps), Math.round((SC.lineMaxDelaySec + 0.5 * i) * fps));
  const lineIn = (i: number) => easeOutCubic((f - lineAt(i)) / SC.lineInFrames);
  return (
    <AbsoluteFill style={{opacity: out}}>
      <AbsoluteFill style={{overflow: 'hidden', background: '#000'}}>
        <AbsoluteFill style={{filter: `blur(${SC.blurPx * u}px) brightness(${SC.dim})`, transform: 'scale(1.22)'}}><Footage ctx={ctx} grade /></AbsoluteFill>
      </AbsoluteFill>
      <div data-guard="ff-head" style={{position: 'absolute', left: 0, right: 0, top, textAlign: 'center', opacity: e.opacity, ...txt(fit(b.header, headF, maxW), {textShadow: `0 ${4 * u}px ${12 * u}px rgba(0,0,0,.55)`})}}>{b.header}</div>
      {b.lines.slice(0, 2).map((ln, i) => {
        const p = lineIn(i);
        if (f < lineAt(i)) return null;
        const sz = fit(ln.text, lineF, maxW - 80 * u);
        return (
          <div key={i} style={{position: 'absolute', left: 0, right: 0, top: top + headH + i * (lineH + 8 * u), display: 'flex', justifyContent: 'center', opacity: p, transform: `translateY(${(1 - p) * 18 * u}px)`}}>
            <div data-guard="ff-line" style={(ln.pill && STYLE.beats.infoScene.pillFilled !== false) ? txt(sz, {color: K.pillText, background: K.highlight, borderRadius: 999, padding: `${4 * u}px ${30 * u}px`} ) : txt(sz, {color: K.highlight, textShadow: ln.pill ? STROKE_SHADOW(u) : `0 ${4 * u}px ${12 * u}px rgba(0,0,0,.55)`})}>{ln.text}</div>
          </div>
        );
      })}
      <div data-guard="ff-device" style={{position: 'absolute', left: devX, top: devY, width: devW, height: devH, opacity: e.opacity, transform: `scale(${SC.scaleFrom + (1 - SC.scaleFrom) * inP})`, transformOrigin: '50% 50%', borderRadius: (phone ? SC.phone.radiusPx : SC.window.radiusPx) * u, background: phone ? '#0b0b0c' : '#1d1d1f', boxShadow: `0 ${30 * u}px ${80 * u}px rgba(0,0,0,.6), inset 0 0 0 ${2 * u}px rgba(255,255,255,.18)`, overflow: 'hidden'}}>
        {!phone && (
          <div style={{position: 'absolute', left: 0, right: 0, top: 0, height: bar, background: '#2b2b2e', display: 'flex', alignItems: 'center', gap: 12 * u, paddingLeft: 22 * u}}>
            {['#FF5F57', '#FEBC2E', '#28C840'].map((c) => <div key={c} style={{width: 20 * u, height: 20 * u, borderRadius: 99, background: c}} />)}
            {b.title && <div style={txt(24 * u, {fontWeight: 600, color: 'rgba(255,255,255,.55)', marginLeft: 'auto', marginRight: 26 * u})}>{b.title}</div>}
          </div>
        )}
        <div style={{position: 'absolute', left: bez, right: bez, top: bez + bar, bottom: bez, borderRadius: Math.max(0, (phone ? SC.phone.radiusPx : SC.window.radiusPx) - (phone ? bez : 4 * u)) * u / u, overflow: 'hidden', background: '#000'}}>
          <Footage ctx={ctx} zoom={SC.videoZoom} grade />
          {phone && (
            <>
              <div style={{position: 'absolute', left: 0, right: 0, top: 0, height: 74 * u, background: 'linear-gradient(rgba(0,0,0,.45), rgba(0,0,0,0))'}} />
              <div style={{position: 'absolute', left: '50%', top: 16 * u, width: 150 * u, height: 40 * u, marginLeft: -75 * u, borderRadius: 99, background: '#000'}} />
              <div style={txt(30 * u, {position: 'absolute', left: 40 * u, top: 20 * u, fontWeight: 700})}>{b.statusTime ?? '9:41'}</div>
              <div style={{position: 'absolute', right: 36 * u, top: 28 * u, display: 'flex', gap: 8 * u, alignItems: 'center'}}>
                {[10, 16, 22].map((h) => <div key={h} style={{width: 6 * u, height: h * u, background: '#fff', borderRadius: 2 * u}} />)}
                <div style={{width: 46 * u, height: 22 * u, border: `${2 * u}px solid #fff`, borderRadius: 7 * u, marginLeft: 8 * u, padding: 2 * u}}><div style={{width: '100%', height: '100%', background: '#fff', borderRadius: 3 * u}} /></div>
              </div>
            </>
          )}
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* ---------- 12. text behind the speaker: footage -> big text -> person cutout (mask frames from person_mask.py) ----------
 * v4.2: `b.items` = text placed ONLY in the empty background (make_masks.py tune + the shared text_occlusion.py gate); each item has its own
 * anchor x / align / size / y. The person mask is applied to the *zoomed video element itself*, so the cutout follows the framing zoom exactly.
 * Without `items` (legacy v4.1 beats) the old centred headline is drawn. A beat whose tune found no empty space carries `fallback` and is
 * turned into a normal headline beat by make_beats/make_masks, so this component never renders text that the speaker occludes. */
export const TextBehind: React.FC<SceneCtx & {b: Extract<Beat, {type: 'text-behind-speaker'}>}> = (ctx) => {
  const {L, segs, fps, dur, b, probe, r0} = ctx;
  const f = useCurrentFrame();
  const W = L.canvas.w, H = L.canvas.h, u = L.u;
  const {srcFrame} = segAtOut(segs, r0 + f);
  const e = envelope(f, dur, TB.fadeFrames);
  const dir = b.maskDir ?? `project/masks/${b.id}`;
  const srcFps = fps;
  const mi = Math.max(0, Math.round(srcFrame - Math.ceil((b.maskStart ?? b.t0) * srcFps))) + (b.maskFirst ?? 0);
  const maskUrl = staticFile(`${dir}/mask_${String(mi).padStart(5, '0')}.png`);
  const anim = b.anim ?? 'slide';
  const col = b.color === 'yellow' ? K.highlight : K.white;
  const items = b.items && b.items.length ? b.items : tbLegacyItems(L, b);
  // v4.3 crown tracking: b.track[maskIndex] = vertical offset (fraction of H) of the speaker's crown vs. its median in the window, already smoothed + velocity-capped by make_masks.py; the text rides with the head so it stays 3-10 % behind it
  const trk = b.track && b.track.length ? b.track[Math.min(b.track.length - 1, Math.max(0, mi))] * H : 0;
  const maskStyle = {WebkitMaskImage: `url(${maskUrl})`, maskImage: `url(${maskUrl})`, WebkitMaskSize: 'cover', maskSize: 'cover', WebkitMaskPosition: `${L.video.focusX * 100}% 50%`, maskPosition: `${L.video.focusX * 100}% 50%`, maskMode: 'luminance', maskRepeat: 'no-repeat'} as React.CSSProperties;
  const itemEl = (it: TbItem, i: number) => {
    const size = it.size * W, lines = it.text.split('\n');
    const lf = f - i * TB.lineStaggerFrames;
    const p = easeOutCubic(lf / TB.slideFrames);
    const dirX = it.align === 'r' ? 1 : it.align === 'l' ? -1 : (i % 2 ? 1 : -1);
    // slide: a short glide (never starts outside the frame) + fade; type: letters appear, the rest stays invisible so the layout never jumps
    const tx = anim === 'slide' ? (1 - p) * dirX * W * 0.07 : 0;
    const shown = anim === 'type' ? Math.floor((Math.max(0, lf) / fps) * TB.typeCharsPerSec) : Infinity;
    let seen = 0;
    const left = it.align === 'l' ? it.x * W : it.align === 'r' ? it.x * W : it.x * W;
    return (
      <div key={i} data-guard="tbs-text" style={{position: 'absolute', left, top: it.y * H + trk, transform: `translateX(${it.align === 'c' ? '-50%' : it.align === 'r' ? '-100%' : '0%'}) translateX(${tx}px)`, whiteSpace: 'nowrap', textAlign: it.align === 'c' ? 'center' : it.align === 'r' ? 'right' : 'left', opacity: anim === 'slide' ? p : 1,
        ...txt(size, {color: col, lineHeight: TB.lineHeight, textTransform: 'uppercase', fontWeight: 800, letterSpacing: LETTER, textShadow: `0 0 ${TB.shadowPx * u}px rgba(0,0,0,.4)`})}}>
        {lines.map((ln, k) => {
          const vis = Math.max(0, Math.min(ln.length, shown - seen)); seen += ln.length;
          return <div key={k} style={{height: size * TB.lineHeight}}>{anim === 'type' ? <><span>{ln.slice(0, vis)}</span><span style={{visibility: 'hidden'}}>{ln.slice(vis)}</span></> : ln}</div>;
        })}
      </div>
    );
  };
  if (!probe) return null;
  return (
    <AbsoluteFill style={{opacity: e.opacity}}>
      <AbsoluteFill style={{overflow: 'hidden'}}><Footage ctx={ctx} follow grade /></AbsoluteFill>
      <AbsoluteFill>{items.map(itemEl)}</AbsoluteFill>
      <Img src={maskUrl} style={{position: 'absolute', width: 1, height: 1, opacity: 0, left: 0, top: 0}} />
      <AbsoluteFill style={{overflow: 'hidden'}}><Footage ctx={ctx} follow grade style={maskStyle} /></AbsoluteFill>
    </AbsoluteFill>
  );
};
type TbItem = NonNullable<Extract<Beat, {type: 'text-behind-speaker'}>['items']>[number];
/** v4.1 beats (no `items`): one centred block, every `\n` a line */
const tbLegacyItems = (L: Layout, b: Extract<Beat, {type: 'text-behind-speaker'}>): TbItem[] => [{text: b.text, align: 'c', size: textBehindFont(L, b.text) / L.canvas.w, x: 0.5, y: b.y ?? 0.3}];
