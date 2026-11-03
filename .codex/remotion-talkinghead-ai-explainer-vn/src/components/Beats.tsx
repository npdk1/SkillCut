import React from 'react';
import {AbsoluteFill, Img, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {Layout} from '../../assets/layouts';
import {MappedSegment, mapInterval, relFrame} from '../../assets/remap';
import {Beat, BeatsFile, Probe} from '../../assets/types';
import {STYLE} from '../../assets/style';
import {FONT_FAMILY, LETTER} from '../../assets/font';
import {clamp01, easeOutBack, easeOutCubic, envelope} from './anim';
import {FramedFocus, TextBehind} from './Scenes';
import {BrandTile, Icon, Sparkle, Star} from './Icons';
import {stickerAnchor, stickerLook} from '../../assets/placement';

const K = STYLE.colors;
const B = STYLE.beats;
type Ctx = {L: Layout; segs: MappedSegment[]; fps: number; dur: number; t0: number; beats?: BeatsFile};
const text = (L: Layout, size: number, extra: React.CSSProperties = {}): React.CSSProperties => ({fontFamily: FONT_FAMILY, fontWeight: 800, fontSize: size, letterSpacing: LETTER, lineHeight: 1.12, color: K.white, ...extra});
/** v4.4: 8-way black stroke + soft shadow (readability without any box behind text; verified.md V05) */
const strokeShadow = (L: Layout) => [[-1, -1], [1, -1], [-1, 1], [1, 1], [0, -1.4], [0, 1.4], [-1.4, 0], [1.4, 0]].map(([dx, dy]) => `${dx * 4 * L.u}px ${dy * 4 * L.u}px 0 #000`).join(', ') + `, 0 ${4 * L.u}px ${10 * L.u}px rgba(0,0,0,.5)`;
const shadow = (L: Layout) => `0 ${4 * L.u}px ${10 * L.u}px rgba(0,0,0,.5)`;
/** Fit a text into a box: shrink the font (down to minScale) so it stays on ONE line when possible; below that it WRAPS at word boundaries. Never cuts a word. */
const fitSize = (txt: string, size: number, maxW: number, minScale = 0.62): number => {
  const est = txt.length * size * 0.56;              // ~0.56 em per glyph for the template font (uppercase-heavy Vietnamese, [E])
  return est <= maxW ? size : Math.max(size * minScale, size * (maxW / est));
};
const isVideo = (s: string) => /\.(mp4|mov|webm|m4v)$/i.test(s);

const Media: React.FC<{src: string; style?: React.CSSProperties}> = ({src, style}) =>
  isVideo(src) ? <OffthreadVideo src={staticFile(src)} muted style={{width: '100%', height: '100%', objectFit: 'cover', ...style}} /> : <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover', ...style}} />;

/* ---------- 1. stars (hook, 0-1.5s of reference) ---------- */
const Stars: React.FC<Ctx> = ({L, dur}) => {
  const f = useCurrentFrame();
  const S = B.stars;
  return (
    <AbsoluteFill style={{opacity: clamp01((dur - f) / 5)}}>
      {S.xs.slice(0, S.count).map((x, i) => {
        const p = easeOutBack((f - i * S.startStaggerFrames) / S.perStarFrames);
        const sz = S.size * L.u * (i === 2 ? 1.25 : 1);
        return (
          <div key={i} data-guard="star" style={{position: 'absolute', left: L.canvas.w * x - sz / 2, top: L.canvas.h * S.yRatio + Math.abs(i - 2) * 14 * L.u, transform: `scale(${p})`}}>
            <Star size={sz} rot={S.spin ? (1 - p) * -90 : 0} />
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

/* ---------- 2. sticker (brand tile + optional dark label pill) ---------- */
/** text with an optional yellow-highlighted substring */
const Hl: React.FC<{t: string; hl?: string}> = ({t, hl}) => {
  const i = hl ? t.toLowerCase().indexOf(hl.toLowerCase()) : -1;
  if (!hl || i < 0) return <>{t}</>;
  return <>{t.slice(0, i)}<span style={{color: K.highlight}}>{t.slice(i, i + hl.length)}</span>{t.slice(i + hl.length)}</>;
};

const Sticker: React.FC<Ctx & {b: Extract<Beat, {type: 'sticker'}>}> = ({L, dur, b, beats}) => {
  const f = useCurrentFrame();
  const e = envelope(f, dur, STYLE.beats.sticker.popFrames);
  const V = STYLE.beats.sticker.variants;
  const look = stickerLook(b);
  const anchor = beats ? stickerAnchor(b, beats) : 'top-left';
  const S = L.sticker, W = L.canvas.w, H = L.canvas.h;
  // data-driven placement (see assets/placement.ts + style.config.json beats.sticker.autoPlacement); b.x / b.y (fractions) override
  const yR = look === 'label-above' ? S.centerTopYr : look === 'label-right' ? S.cardYr : S.topYr;
  const y = b.y !== undefined ? b.y * H : Math.round(H * yR);
  const left = b.x !== undefined ? b.x * W : anchor === 'top-right' ? W - Math.round(W * S.topXr) - S.size : Math.round(W * (look === 'label-right' ? V.labelRight.cardXr : S.topXr));
  const centred = anchor === 'center-top' && b.x === undefined;
  const sparkle = [0, 1, 2].slice(0, STYLE.beats.sticker.sparkles).map((i) => (
    <div key={i} style={{position: 'absolute', left: [-14, S.size - 6, S.size * 0.5][i] * L.u, top: [-14, 6, -24][i] * L.u, opacity: 0.6 + 0.4 * Math.sin((f + i * 5) / 4)}}><Sparkle size={(16 + i * 4) * L.u} color={K.highlight} /></div>
  ));
  const pill = (children: React.ReactNode, extra: React.CSSProperties = {}) => (
    <div style={{background: K.chipBg, border: `${2 * L.u}px solid ${K.chipStroke}`, borderRadius: 18 * L.u, padding: `${12 * L.u}px ${22 * L.u}px`, ...extra}}>{children}</div>
  );
  const tileSize = look === 'label-above' ? Math.round(S.size * V.labelAbove.tileScale) : look === 'label-right' ? Math.round(S.size * V.labelRight.tileScale) : S.size;
  const tile = <div style={{position: 'relative'}}><BrandTile size={tileSize} />{sparkle}</div>;
  const wrapStyle: React.CSSProperties = centred
    ? {position: 'absolute', left: 0, right: 0, top: y, display: 'flex', justifyContent: 'center'}
    : {position: 'absolute', left, top: y};
  const inner = look === 'label-above' ? (
    <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: V.labelAbove.gapPx * L.u}}>
      {b.label && pill(<div style={text(L, V.labelAbove.labelFont * L.u)}><Hl t={b.label} hl={b.hl} /></div>, {background: V.labelAbove.bg, border: V.labelAbove.strokePx ? `${V.labelAbove.strokePx * L.u}px solid ${K.chipStroke}` : 'none'})}
      {tile}
    </div>
  ) : look === 'label-right' ? (
    <div style={{display: 'flex', alignItems: 'center'}}>
      {tile}
      <div style={{width: V.labelRight.connectorPx * L.u, height: V.labelRight.connectorWidthPx * L.u, background: K.chipStroke, opacity: 0.8}} />
      {pill(
        <div style={{display: 'flex', alignItems: 'center', gap: 14 * L.u}}>
          {b.icon && <Icon name={b.icon} size={S.size * 0.55} />}
          <div>
            {b.sub && <div style={text(L, S.labelFont * V.labelRight.subFontScale, {fontWeight: 500, opacity: 0.75})}>{b.sub}</div>}
            {b.label && <div style={text(L, S.labelFont * V.labelRight.mainFontScale)}><Hl t={b.label} hl={b.hl} /></div>}
          </div>
        </div>, {padding: `${V.labelRight.cardPadYPx * L.u}px ${V.labelRight.cardPadXPx * L.u}px`, minWidth: Math.round(W * V.labelRight.cardMinWr), boxSizing: 'border-box'})}
    </div>
  ) : tile;
  return (
    <div data-guard="sticker" style={{...wrapStyle, opacity: e.opacity}}>
      <div style={{transform: `scale(${e.scale})`}}>{inner}</div>
    </div>
  );
};

/* ---------- 3. chip stack (Typography / Graphic / Motion / Sound) ---------- */
const ChipStack: React.FC<Ctx & {b: Extract<Beat, {type: 'chip-stack'}>}> = ({L, segs, fps, dur, b, t0}) => {
  const f = useCurrentFrame();
  const C = L.chips;
  const lastIdx = b.items.reduce((acc, it, i) => (f >= relFrame(segs, it.t, t0, fps) ? i : acc), -1);
  const out = clamp01((dur - f) / B.common.outFrames);
  return (
    <div data-guard="chips" style={{position: 'absolute', left: C.x, top: C.y + (b.dy ?? 0) * L.canvas.h, opacity: out}}>
      {b.items.map((it, i) => {
        const at = relFrame(segs, it.t, t0, fps);
        if (f < at) return null;
        const p = easeOutBack((f - at) / B.chipStack.enterFrames);
        const col = i % C.cols, row = Math.floor(i / C.cols);
        const latest = B.chipStack.highlightLatest && i === lastIdx;
        return (
          <div key={i} style={{position: 'absolute', left: col * (C.w + C.gapX), top: row * (C.h + C.gapY), width: C.w, height: C.h, borderRadius: 26 * L.u, background: K.chipBg, border: `${2.5 * L.u}px solid ${latest ? K.chipStroke : 'rgba(255,255,255,.08)'}`, display: 'flex', alignItems: 'center', gap: 18 * L.u, padding: `0 ${22 * L.u}px`, transform: `scale(${0.8 + 0.2 * p})`, opacity: clamp01((f - at) / 4), boxShadow: '0 10px 24px rgba(0,0,0,.35)'}}>
            <Icon name={it.icon} size={C.h * 0.46} />
            <div>
              <div style={text(L, C.titleFont)}>{it.title}</div>
              <div style={text(L, C.subFont, {color: K.highlight, fontWeight: 700})}>{it.sub}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

/* ---------- 4. avatar chain: [Mike] --(edit video)--> [AI] + badge ---------- */
const AvatarChain: React.FC<Ctx & {b: Extract<Beat, {type: 'avatar-chain'}>}> = ({L, dur, b}) => {
  const f = useCurrentFrame();
  const e = envelope(f, dur);
  const d = L.canvas.w * 0.9, av = 70 * L.u, y = L.canvas.h * 0.842;
  const draw = clamp01(f / B.avatarChain.drawFrames);
  const circle = (label: string, right?: boolean) => (
    <div style={{width: av, height: av, borderRadius: av, background: '#F4EFE6', border: `${4 * L.u}px solid ${K.highlight}`, display: 'flex', alignItems: 'center', justifyContent: 'center', ...text(L, av * 0.32, {color: '#222'}), [right ? 'right' : 'left']: 0, position: 'absolute', top: -av / 2}}>{label}</div>
  );
  return (
    <div data-guard="avatar-chain" style={{position: 'absolute', left: (L.canvas.w - d) / 2, top: y, width: d, height: 0, opacity: e.opacity}}>
      <div style={{position: 'absolute', left: av, right: av, top: 0, height: 3 * L.u, background: `rgba(255,255,255,${B.avatarChain.lineAlpha})`, transformOrigin: 'left', transform: `scaleX(${easeOutCubic(draw)})`}} />
      {circle(b.left)}
      {b.right && circle(b.right, true)}
      <div style={{position: 'absolute', left: '50%', top: -34 * L.u, transform: `translateX(-50%) scale(${e.scale})`, background: K.chipBg, border: `${2 * L.u}px solid rgba(255,255,255,.2)`, borderRadius: 14 * L.u, padding: `${10 * L.u}px ${20 * L.u}px`, ...text(L, 30 * L.u)}}>{b.chip}</div>
      {b.badge && <div style={{position: 'absolute', left: '50%', top: 30 * L.u, transform: 'translateX(-50%)', background: K.highlight, color: K.pillText, borderRadius: 999, padding: `${6 * L.u}px ${18 * L.u}px`, ...text(L, 26 * L.u, {color: K.pillText})}}>✓ {b.badge}</div>}
    </div>
  );
};

/* ---------- 5. prompt box (typing + red strike) ---------- */
const PromptBox: React.FC<Ctx & {b: Extract<Beat, {type: 'prompt-box'}>}> = ({L, segs, fps, dur, b, t0}) => {
  const f = useCurrentFrame();
  const e = envelope(f, dur);
  const P = B.promptBox;
  const chars = Math.min(b.text.length, Math.floor((f / fps) * P.typeCharsPerSec));
  const strikeAt = b.strikeAt !== undefined ? relFrame(segs, b.strikeAt, t0, fps) : Infinity;
  const strike = clamp01((f - strikeAt) / P.strikeFrames);
  return (
    <div data-guard="prompt" style={{position: 'absolute', left: L.prompt.x, top: L.prompt.y + (b.dy ?? 0) * L.canvas.h, width: L.prompt.w, height: L.prompt.h, borderRadius: P.radius * L.u, background: P.bg, boxShadow: '0 12px 30px rgba(0,0,0,.35)', display: 'flex', alignItems: 'center', padding: `0 ${30 * L.u}px`, opacity: e.opacity, transform: `scale(${e.scale})`}}>
      <span style={text(L, L.prompt.font, {color: P.text, fontWeight: 600, position: 'relative'})}>
        {b.text.slice(0, chars)}
        {chars < b.text.length || Math.floor(f / 8) % 2 === 0 ? '|' : ''}
        <span style={{position: 'absolute', left: 0, top: '52%', height: 4 * L.u, width: `${strike * 100}%`, background: P.strikeColor}} />
      </span>
      <div style={{marginLeft: 'auto', width: L.prompt.h * 0.62, height: L.prompt.h * 0.62, borderRadius: 999, background: '#0F0F10', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: FONT_FAMILY, fontWeight: 800, fontSize: L.prompt.h * 0.36}}>↑</div>
    </div>
  );
};

/* ---------- 6. title burst (big yellow title + REC + timeline widget) ---------- */
const TitleBurst: React.FC<Ctx & {b: Extract<Beat, {type: 'title-burst'}>}> = ({L, dur, b}) => {
  const f = useCurrentFrame();
  const T = B.titleBurst;
  const e = envelope(f, dur, T.inFrames);
  const grow = clamp01(f / T.timeline.growFrames);
  const titleMaxW = L.canvas.w - L.title.x - L.safe.right;
  const rows = [[0.0, 0.34], [0.38, 0.22], [0.64, 0.34], [0.05, 0.22], [0.3, 0.12], [0.46, 0.28], [0.0, 0.5], [0.55, 0.4]];
  return (
    <AbsoluteFill>
      {b.rec && (
        <div data-guard="rec" style={{position: 'absolute', left: L.title.x + 6 * L.u, top: L.title.recY + (b.dy ?? 0) * L.canvas.h, display: 'flex', alignItems: 'center', gap: 10 * L.u, opacity: e.opacity, ...text(L, T.rec.font * L.u, {fontWeight: 600, opacity: 0.85})}}>
          <span style={{width: 12 * L.u, height: 12 * L.u, borderRadius: 99, background: T.rec.dot, opacity: Math.floor(f / T.rec.blinkFrames) % 2 ? 0.3 : 1}} />REC {b.rec.replace(/^\s*REC\s*/i, '')}
        </div>
      )}
      <div data-guard="title" style={{position: 'absolute', left: L.title.x, top: L.title.y + (b.dy ?? 0) * L.canvas.h, opacity: e.opacity, transform: `translateY(${(1 - e.in) * 24 * L.u}px) scale(${0.96 + 0.04 * e.in})`, transformOrigin: 'left center'}}>
        <div style={text(L, fitSize(b.title, L.title.font, titleMaxW), {color: K.highlight, textShadow: shadow(L), maxWidth: titleMaxW, overflowWrap: 'break-word', whiteSpace: 'normal'})}>{b.title}</div>
        {b.sub && <div style={text(L, fitSize(b.sub, L.title.subFont, titleMaxW, 0.75), {fontWeight: 600, textShadow: shadow(L), maxWidth: titleMaxW, overflowWrap: 'break-word', whiteSpace: 'normal'})}>{b.sub}</div>}
      </div>
      {b.timeline && (
        <div data-guard="timeline" style={{position: 'absolute', left: (L.canvas.w - L.title.timelineW) / 2, top: L.title.timelineY, width: L.title.timelineW, height: L.title.timelineH, borderRadius: 22 * L.u, background: 'rgba(14,14,14,.82)', border: `${1.5 * L.u}px solid rgba(255,255,255,.12)`, padding: `${34 * L.u}px ${18 * L.u}px ${14 * L.u}px`, opacity: e.opacity, overflow: 'hidden'}}>
          {rows.slice(0, T.timeline.rows * 2).filter((_, i) => i < T.timeline.rows * 2).map((r, i) => {
            const row = Math.floor(i / 2);
            const w = Math.max(0, Math.min(r[1], grow * 1.2 - r[0]));
            return <div key={i} style={{position: 'absolute', left: `${3 + r[0] * 92}%`, top: (34 + row * 36) * L.u, width: `${w * 92}%`, height: 24 * L.u, borderRadius: T.timeline.barRadius * L.u, background: T.timeline.fill, opacity: i % 3 === 2 ? 0.45 : 1}} />;
          })}
          <div style={{position: 'absolute', left: `${6 + grow * 56}%`, top: 6 * L.u, bottom: 6 * L.u, width: 3 * L.u, background: `rgba(255,255,255,${T.timeline.playheadAlpha})`}} />
        </div>
      )}
    </AbsoluteFill>
  );
};

/* ---------- 7. big word + sparkles ("token", "tiện!") ---------- */
const BigWord: React.FC<Ctx & {b: Extract<Beat, {type: 'big-word'}>}> = ({L, dur, b}) => {
  const f = useCurrentFrame();
  const e = envelope(f, dur, B.bigWord.inFrames);
  return (
    <AbsoluteFill>
      <div data-guard="big-word" style={{position: 'absolute', left: 0, right: 0, top: L.bigWord.y, textAlign: 'center', opacity: e.opacity, transform: `scale(${e.scale})`, padding: `0 ${L.safe.left}px`, ...text(L, fitSize(b.text, L.bigWord.font, L.canvas.w - L.safe.left - L.safe.right, 0.5), {color: b.color === 'white' ? K.white : K.highlight, textShadow: shadow(L)})}}>{b.text}</div>
      {b.sparkles && Array.from({length: B.bigWord.sparkles}).map((_, i) => {
        const a = (i / B.bigWord.sparkles) * Math.PI * 2 + 0.5;
        const r = L.canvas.w * (0.34 + (i % 2) * 0.08);
        return <div key={i} style={{position: 'absolute', left: L.canvas.w / 2 + Math.cos(a) * r - 14 * L.u, top: L.bigWord.y + L.bigWord.font * 0.5 + Math.sin(a) * r * 0.45, opacity: e.opacity * (0.55 + 0.45 * Math.sin((f + i * 4) / 3))}}><Sparkle size={B.bigWord.sparkleSize * L.u * (0.6 + (i % 3) * 0.3)} color={i % 2 ? '#fff' : K.highlight} /></div>;
      })}
    </AbsoluteFill>
  );
};


/* ---------- 7b. brand logo (real logo file from public/project/logos/, pops in with its name + brand-colour glow) ---------- */
const BrandLogo: React.FC<Ctx & {b: Extract<Beat, {type: 'brand-logo'}>}> = ({L, dur, b}) => {
  const f = useCurrentFrame();
  const e = envelope(f, dur, 7);
  // v4.1: make_beats puts the card where the speaker's face is NOT (x = card centre / canvas w, y = card top / canvas h, scale = card shrink). No x/y -> centred at L.logo.y (old behaviour).
  const k = b.scale ?? 1;
  const S = L.logo.size * k;
  const nf = L.logo.nameFont * k;
  const hex = /^#[0-9a-f]{6}$/i.test(b.color || '') ? (b.color as string) : '#ffffff';
  const lum = (parseInt(hex.slice(1, 3), 16) * 0.299 + parseInt(hex.slice(3, 5), 16) * 0.587 + parseInt(hex.slice(5, 7), 16) * 0.114);
  const glow = lum < 70 ? '#9aa0a6' : hex;   // black/very dark brand colours (GitHub, TikTok, Notion) would give an invisible glow
  const cardW = Math.max(S, b.name.length * nf * 0.58) + 16 * L.u;   // same formula as scripts/logo_place.py card_size()
  const placed = b.x !== undefined && b.y !== undefined;
  const pos: React.CSSProperties = placed ? {left: b.x! * L.canvas.w - cardW / 2, width: cardW, top: b.y! * L.canvas.h} : {left: 0, right: 0, top: L.logo.y};
  return (
    <AbsoluteFill>
      <div data-guard="brand-logo" style={{position: 'absolute', ...pos, display: 'flex', flexDirection: 'column', alignItems: 'center', opacity: e.opacity, transform: `scale(${e.scale})`, transformOrigin: placed ? '50% 0%' : '50% 50%'}}>
        <div style={{width: S, height: S, borderRadius: S * 0.24, background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: `0 0 ${S * 0.35}px ${glow}cc, 0 ${8 * L.u}px ${24 * L.u}px rgba(0,0,0,.45)`}}>
          <Img src={staticFile(b.logo)} style={{width: S * 0.62, height: S * 0.62, objectFit: 'contain'}} />
        </div>
        <div style={{marginTop: nf * 0.35, whiteSpace: 'nowrap', ...text(L, nf, {textShadow: `0 0 ${nf * 0.5}px ${glow}, ${shadow(L)}`})}}>{b.name}</div>
      </div>
    </AbsoluteFill>
  );
};

/* ---------- 7c. illustration / concept icon (v4.2): the spoken concept is DRAWN - a real open-license icon (Lucide / Tabler / Phosphor / Iconify, fetched by scripts/fetch_icon.sh) or a hand-drawn SVG composition, never a blank box ---------- */
const Illustration: React.FC<Ctx & {b: Extract<Beat, {type: 'illustration'}>}> = ({L, dur, b}) => {
  const f = useCurrentFrame();
  const e = envelope(f, dur, 7);
  const k = b.scale ?? 1, S = L.logo.size * k, nf = L.logo.nameFont * k;   // v4.3: icon = 0.70 of the card (was 0.64) and scales 1.12/1.03/0.95 -> 196/180/167px icons on the 1080 canvas
  const hex = /^#[0-9a-f]{6}$/i.test(b.color || '') ? (b.color as string) : '#ffd400';
  if (b.pill) {   // v4.3 ladder last rung: compact icon + label pill (same size model as scripts/logo_place.py card_size(pill=True) / assets/zones.ts)
    const ph = L.logo.size * 0.5, pw = L.logo.size * 0.45 + b.label.length * L.logo.nameFont * 0.58 + 30 * L.u, ic = ph * 0.74;
    const placedP = b.x !== undefined && b.y !== undefined;
    const wobP = Math.sin(f * 0.7) * 5 * Math.exp(-f / 5);
    return (
      <AbsoluteFill>
        <div data-guard="illustration" style={{position: 'absolute', ...(placedP ? {left: b.x! * L.canvas.w - pw / 2, top: b.y! * L.canvas.h} : {left: (L.canvas.w - pw) / 2, top: L.logo.y}), width: pw, height: ph, boxSizing: 'border-box', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10 * L.u, borderRadius: ph / 2, background: 'linear-gradient(145deg, rgba(20,22,30,.92), rgba(45,48,62,.88))', border: `${3 * L.u}px solid ${hex}`, boxShadow: `0 0 ${ph * 0.4}px ${hex}aa, 0 ${6 * L.u}px ${18 * L.u}px rgba(0,0,0,.5)`, opacity: e.opacity, transform: `scale(${e.scale}) rotate(${wobP}deg)`}}>
          <Img src={staticFile(b.icon)} style={{width: ic, height: ic, objectFit: 'contain'}} />
          <div style={{whiteSpace: 'nowrap', ...text(L, L.logo.nameFont, {textShadow: `0 0 ${L.logo.nameFont * 0.5}px ${hex}, ${shadow(L)}`})}}>{b.label}</div>
        </div>
      </AbsoluteFill>
    );
  }
  const cardW = Math.max(S, b.label.length * nf * 0.58) + 16 * L.u;   // same formula as scripts/logo_place.py card_size() / assets/zones.ts
  const placed = b.x !== undefined && b.y !== undefined;
  const pos: React.CSSProperties = placed ? {left: b.x! * L.canvas.w - cardW / 2, width: cardW, top: b.y! * L.canvas.h} : {left: 0, right: 0, top: L.logo.y};
  const wob = Math.sin(f * 0.7) * 7 * Math.exp(-f / 5);   // pop-in: overshoot (envelope) + damped wobble
  return (
    <AbsoluteFill>
      <div data-guard="illustration" style={{position: 'absolute', ...pos, display: 'flex', flexDirection: 'column', alignItems: 'center', opacity: e.opacity, transform: `scale(${e.scale}) rotate(${wob}deg)`, transformOrigin: placed ? '50% 0%' : '50% 50%'}}>
        <div style={{width: S, height: S, borderRadius: S * 0.26, background: 'linear-gradient(145deg, rgba(20,22,30,.92), rgba(45,48,62,.88))', border: `${3 * L.u}px solid ${hex}`, display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: `0 0 ${S * 0.4}px ${hex}aa, 0 ${8 * L.u}px ${24 * L.u}px rgba(0,0,0,.5)`}}>
          <Img src={staticFile(b.icon)} style={{width: S * 0.7, height: S * 0.7, objectFit: 'contain'}} />
        </div>
        <div style={{marginTop: nf * 0.35, whiteSpace: 'nowrap', ...text(L, nf, {textShadow: `0 0 ${nf * 0.5}px ${hex}, ${shadow(L)}`})}}>{b.label}</div>
      </div>
    </AbsoluteFill>
  );
};

/* ---------- 8. selection box (draws around the word, handles + size label) ---------- */
const SelectionBox: React.FC<Ctx & {b: Extract<Beat, {type: 'selection-box'}>}> = ({L, dur, b}) => {
  const f = useCurrentFrame();
  const S = B.selectionBox;
  const p = easeOutCubic(f / S.drawFrames);
  const w = L.canvas.w * 0.42, h = L.bigWord.font * 1.1, x = (L.canvas.w - w) / 2, y = L.bigWord.y - L.bigWord.font * 0.06;
  const hd = S.handle * L.u;
  return (
    <AbsoluteFill style={{opacity: clamp01((dur - f) / 4)}}>
      <div style={{position: 'absolute', left: x, top: y, width: w * p, height: h * p, border: `${2.5 * L.u}px solid ${S.stroke}`}}>
        {[[0, 0], [1, 0], [0, 1], [1, 1]].map(([cx, cy], i) => <div key={i} style={{position: 'absolute', left: cx ? '100%' : 0, top: cy ? '100%' : 0, width: hd, height: hd, marginLeft: -hd / 2, marginTop: -hd / 2, background: '#fff', border: `${2.5 * L.u}px solid ${S.stroke}`}} />)}
      </div>
      <div style={{position: 'absolute', left: x + w / 2 - 70 * L.u, top: y + h + 18 * L.u, background: S.labelBg, color: K.pillText, borderRadius: 8 * L.u, padding: `${4 * L.u}px ${14 * L.u}px`, opacity: p, ...text(L, 24 * L.u, {color: K.pillText})}}>{b.size}</div>
    </AbsoluteFill>
  );
};

/* ---------- 9. comment box (CTA) ---------- */
const CommentBox: React.FC<Ctx & {b: Extract<Beat, {type: 'comment-box'}>}> = ({L, fps, dur, b}) => {
  const f = useCurrentFrame();
  const e = envelope(f, dur);
  const chars = Math.min(b.typed.length, Math.floor((f / fps) * STYLE.beats.commentBox.typeCharsPerSec));
  const done = chars >= b.typed.length;
  return (
    <AbsoluteFill>
      {b.bubble && done && (
        <div style={{position: 'absolute', left: L.comment.x, top: L.comment.y + (b.dy ?? 0) * L.canvas.h + L.comment.bubbleDy, width: L.comment.w, height: L.comment.bubbleH, borderRadius: 26 * L.u, background: STYLE.beats.commentBox.bubbleBg, display: 'flex', alignItems: 'center', padding: `0 ${24 * L.u}px`, gap: 18 * L.u, opacity: clamp01((f - b.typed.length * 2) / 6)}}>
          <div style={{width: 52 * L.u, height: 52 * L.u, borderRadius: 99, background: K.highlight, color: K.pillText, display: 'flex', alignItems: 'center', justifyContent: 'center', ...text(L, 28 * L.u, {color: K.pillText})}}>B</div>
          <div><div style={text(L, L.comment.font * 0.55, {fontWeight: 500, opacity: 0.6})}>bạn</div><div style={text(L, L.comment.font)}>{b.bubble}</div></div>
          <div style={{marginLeft: 'auto', color: K.heart, fontSize: 44 * L.u}}>♥</div>
        </div>
      )}
      <div data-guard="comment" style={{position: 'absolute', left: L.comment.x, top: L.comment.y + (b.dy ?? 0) * L.canvas.h + (b.bubble && done ? L.comment.pillShift : 0), width: L.comment.w, height: L.comment.pillH, borderRadius: 999, background: '#fff', display: 'flex', alignItems: 'center', padding: `0 ${34 * L.u}px`, opacity: e.opacity, transform: `scale(${e.scale})`, boxShadow: '0 10px 28px rgba(0,0,0,.3)'}}>
        <span style={text(L, L.comment.font, {color: '#222', fontWeight: 600})}>{b.bubble && done ? '' : b.typed.slice(0, chars)}{Math.floor(f / 8) % 2 === 0 ? '|' : ''}</span>
        <span style={{marginLeft: 'auto', ...text(L, L.comment.font * 0.8, {color: K.link})}}>Đăng</span>
      </div>
      {done && <div style={{position: 'absolute', left: Math.round(L.canvas.w * L.sticker.chatXr), top: Math.round(L.canvas.h * L.sticker.chatYr), opacity: e.opacity, transform: `scale(${e.scale})`}}><Icon name="chat" size={L.sticker.size * 0.95} /></div>}
    </AbsoluteFill>
  );
};

/* ---------- 10. info scene (dark/blur backdrop + header + cards + headline + pill + media) ---------- */
const WindowCard: React.FC<{src: string; kind: 'window' | 'phone'; L: Layout; scale: number}> = ({src, kind, L, scale}) => {
  const w = kind === 'phone' ? L.info.mediaW * 0.42 : L.info.mediaW, h = kind === 'phone' ? w * 2.28 : w * 0.62;
  return (
    <div style={{width: w, height: h, borderRadius: (kind === 'phone' ? 46 : 18) * L.u, overflow: 'hidden', background: K.windowBg, border: kind === 'phone' ? `${8 * L.u}px solid #101112` : 'none', boxShadow: '0 24px 60px rgba(0,0,0,.5)', transform: `scale(${scale})`, position: 'relative'}}>
      {kind === 'window' && <div style={{position: 'absolute', left: 0, right: 0, top: 0, height: 22 * L.u, background: '#F2F2F2', zIndex: 2, display: 'flex', gap: 6 * L.u, alignItems: 'center', paddingLeft: 12 * L.u}}>{['#FF5F57', '#FEBC2E', '#28C840'].map((c) => <div key={c} style={{width: 9 * L.u, height: 9 * L.u, borderRadius: 9, background: c}} />)}</div>}
      <div style={{position: 'absolute', inset: 0, paddingTop: kind === 'window' ? 22 * L.u : 0}}><Media src={src} /></div>
    </div>
  );
};

const InfoScene: React.FC<Ctx & {b: Extract<Beat, {type: 'info-scene'}>}> = ({L, segs, fps, dur, b, t0}) => {
  const f = useCurrentFrame();
  const I = B.infoScene;
  const fade = clamp01(f / STYLE.cuts.darkSceneFadeFrames);
  const out = clamp01((dur - f) / B.common.outFrames);
  const at = (t: number) => relFrame(segs, t, t0, fps);
  return (
    <AbsoluteFill style={{opacity: out}}>
      <AbsoluteFill style={{backdropFilter: `blur(${I.blurBgPx * L.u}px)`, background: `radial-gradient(ellipse at 50% 38%, ${K.darkGlow} 0%, ${K.darkScene} 62%)`, opacity: 0.35 + 0.62 * fade}} />
      <AbsoluteFill style={{backgroundImage: `radial-gradient(${K.dotGrid} 1px, transparent 1px)`, backgroundSize: `${34 * L.u}px ${34 * L.u}px`, opacity: K.dotGridAlpha * fade}} />
      <div data-guard="info-header" style={{position: 'absolute', left: 0, right: 0, top: L.info.headerY, textAlign: 'center', ...text(L, L.info.headerFont, {textShadow: shadow(L)})}}>{b.header}</div>
      {b.headline && f >= at(b.headline.t) && (() => {
        const p = clamp01((f - at(b.headline.t)) / I.headlineInFrames);
        return (
          <div style={{position: 'absolute', left: 0, right: 0, top: L.info.headlineY, textAlign: 'center', ...text(L, L.info.headerFont * I.headlineScale, {color: K.highlight, textShadow: shadow(L), letterSpacing: `${I.headlineTrackingEm}em`, lineHeight: 1.05}), opacity: p, filter: `blur(${(1 - easeOutCubic(p)) * I.headlineBlurPx * L.u}px)`}}>{b.headline.text}</div>
        );
      })()}
      {b.cards.map((c, i) => {
        const a = at(c.t);
        if (f < a) return null;
        const p = easeOutCubic((f - a) / I.cardEnterFrames);
        const sk = c.strike ? clamp01((f - a - 12) / I.strikeFrames) : 0;
        const x0 = (L.canvas.w - L.info.cardW) / 2;
        // cards leave (blur + squash + fade) when the headline takes over their slot
        const exitAtT = b.cardsExitAt ?? b.headline?.t;
        const ex = exitAtT !== undefined ? clamp01((f - at(exitAtT) - i * I.cardExitStaggerFrames) / I.cardExitFrames) : 0;
        if (ex >= 1) return null;
        return (
          <div key={i} data-guard="info-card" style={{position: 'absolute', left: x0, top: L.info.listY + i * (L.info.cardH + L.info.cardGap) + (1 - p) * 24 * L.u, width: L.info.cardW, height: L.info.cardH, transformOrigin: 'center', transform: ex > 0 ? `scaleY(${1 - ex * (1 - I.cardExitScaleY)})` : undefined, filter: ex > 0 ? `blur(${ex * I.cardExitBlurPx * L.u}px)` : undefined, borderRadius: 24 * L.u, background: K.infoCard, border: `${1.5 * L.u}px solid rgba(255,255,255,.1)`, boxShadow: '0 14px 30px rgba(0,0,0,.4)', display: 'flex', alignItems: 'center', padding: `0 ${28 * L.u}px`, opacity: p * (1 - ex), gap: 18 * L.u, ...(c.accent ? {borderColor: K.chipStroke} : {})}}>
            {c.icon && <Icon name={c.icon} size={L.info.cardH * 0.5} />}
            <div style={{position: 'relative'}}>
              <span style={text(L, L.info.cardFont, {opacity: c.strike && sk > 0.5 ? I.struckTextOpacity : 1, textShadow: c.strike ? shadow(L) : undefined})}>{c.text}</span>
              {c.sub && <div style={text(L, L.info.cardFont * 0.5, {color: K.highlight, fontWeight: 600})}>{c.sub}</div>}
            </div>
            {c.strike && <div style={{position: 'absolute', left: 20 * L.u, top: '50%', height: I.strikeThickness * L.u, borderRadius: 3 * L.u, boxShadow: `0 0 ${6 * L.u}px rgba(0,0,0,.55)`, width: (L.info.cardW - 40 * L.u) * sk, background: K.strike}} />}
            {c.strike && <div style={{marginLeft: 'auto', width: 38 * L.u, height: 38 * L.u, borderRadius: 99, background: 'rgba(255,255,255,.34)', display: 'flex', alignItems: 'center', justifyContent: 'center', ...text(L, 22 * L.u), opacity: sk}}>✕</div>}
          </div>
        );
      })}
      {b.pill && f >= at(b.pill.t) && (
        <div style={{position: 'absolute', left: 0, right: 0, top: L.info.mediaY - 110 * L.u, display: 'flex', justifyContent: 'center', opacity: clamp01((f - at(b.pill.t)) / 5), transform: `scale(${0.85 + 0.15 * easeOutBack((f - at(b.pill.t)) / 8)})`}}>
          {I.pillFilled === false
            ? <div style={{background: 'transparent', color: K.highlight, padding: `${12 * L.u}px ${34 * L.u}px`, ...text(L, I.pillFont * L.u, {color: K.highlight, textShadow: strokeShadow(L)})}}>{b.pill.text}</div>
            : <div style={{background: K.highlight, color: K.pillText, borderRadius: 999, padding: `${12 * L.u}px ${34 * L.u}px`, ...text(L, I.pillFont * L.u, {color: K.pillText})}}>{b.pill.text}</div>}
        </div>
      )}
      {b.media && f >= at(b.media.t) && (
        <div style={{position: 'absolute', left: 0, right: 0, top: L.info.mediaY, display: 'flex', justifyContent: 'center'}}>
          <WindowCard src={b.media.src} kind={b.media.kind} L={L} scale={0.9 + 0.1 * easeOutCubic((f - at(b.media.t)) / I.mediaEnterFrames)} />
        </div>
      )}
    </AbsoluteFill>
  );
};

/* ---------- 11. broll (cutaway video; raw audio keeps playing underneath) ---------- */
const Broll: React.FC<Ctx & {b: Extract<Beat, {type: 'broll'}>}> = ({b, dur}) => {
  const f = useCurrentFrame();
  return <AbsoluteFill style={{opacity: clamp01((dur - f) / 2)}}><OffthreadVideo src={staticFile(b.src)} muted startFrom={Math.round((b.startFromSec ?? 0) * 30)} style={{width: '100%', height: '100%', objectFit: b.fit ?? 'cover'}} /></AbsoluteFill>;
};

/* ---------- 12. topic card (header + window/phone + lines) = info-scene variant ---------- */
const TopicCard: React.FC<Ctx & {b: Extract<Beat, {type: 'topic-card'}>}> = ({L, segs, fps, dur, b, t0}) => {
  const f = useCurrentFrame();
  const I = B.infoScene;
  const fade = clamp01(f / STYLE.cuts.darkSceneFadeFrames);
  const out = clamp01((dur - f) / B.common.outFrames);
  const at = (t: number) => relFrame(segs, t, t0, fps);
  const phone = b.media.kind === 'phone';
  const mediaY = phone ? L.info.topicPhoneY : L.info.topicWinY;
  // lines: the first one defaults to the top group (under the header), the others to the bottom group (under the media). `at` overrides.
  const where = (i: number, l: {at?: 'top' | 'bottom'}) => l.at ?? (i === 0 ? 'top' : 'bottom');
  const render1 = (l: Extract<Beat, {type: 'topic-card'}>['lines'][number], k: number, topIdx: number, y: number) => {
    const a = at(l.t);
    if (f < a || (l.until !== undefined && f >= at(l.until))) return null;
    const p = clamp01((f - a) / 6);
    const sz = L.info.topicLineFont;
    return (
      <div key={k} data-guard="topic-line" style={{position: 'absolute', left: 0, right: 0, top: y, display: 'flex', justifyContent: 'center', opacity: p, transform: `translateY(${(1 - easeOutCubic(p)) * 0.4 * sz}px)`}}>
        {(() => {
          const filled = !!l.pill && I.pillFilled !== false;   // v4.4: pillFilled=false -> the 'pill' line is yellow text with a stroke, no box (V05)
          return <div style={{...text(L, sz, {color: filled ? K.pillText : (l.pill || l.hl) ? K.highlight : K.white, textShadow: filled ? 'none' : (l.pill && I.pillFilled === false) ? strokeShadow(L) : shadow(L)}), background: filled ? K.highlight : 'transparent', borderRadius: 14 * L.u, padding: filled ? `${6 * L.u}px ${22 * L.u}px` : 0}}>{l.text}</div>;
        })()}
      </div>
    );
  };
  const top = b.lines.map((l, i) => ({l, i})).filter(({l, i}) => where(i, l) === 'top');
  const bottom = b.lines.map((l, i) => ({l, i})).filter(({l, i}) => where(i, l) === 'bottom');
  const gap = L.info.topicLineFont * 1.35;
  return (
    <AbsoluteFill style={{opacity: out}}>
      <AbsoluteFill style={{backdropFilter: `blur(${I.blurBgPx * L.u}px)`, background: `rgba(10,10,10,${I.blurBgDim + 0.25 * fade})`}} />
      <div data-guard="topic-header" style={{position: 'absolute', left: 0, right: 0, top: L.info.headerY, textAlign: 'center', ...text(L, L.info.headerFont, {textShadow: shadow(L)})}}>{b.header}</div>
      {top.map(({l, i}, k) => render1(l, i, k, L.info.headerY + L.info.headerFont * 1.5 + (l.slot ?? k) * gap))}
      <div style={{position: 'absolute', left: 0, right: 0, top: mediaY, display: 'flex', justifyContent: 'center'}}>
        <WindowCard src={b.media.src} kind={b.media.kind} L={L} scale={0.9 + 0.1 * easeOutCubic((f - 0) / I.mediaEnterFrames)} />
      </div>
      {bottom.map(({l, i}, k) => render1(l, i, k, L.info.topicBottomY + (l.slot ?? k) * gap))}
    </AbsoluteFill>
  );
};

const render = (b: Beat, c: Ctx): React.ReactNode => {
  switch (b.type) {
    case 'stars': return <Stars {...c} />;
    case 'sticker': return <Sticker {...c} b={b} />;
    case 'chip-stack': return <ChipStack {...c} b={b} />;
    case 'avatar-chain': return <AvatarChain {...c} b={b} />;
    case 'prompt-box': return <PromptBox {...c} b={b} />;
    case 'title-burst': return <TitleBurst {...c} b={b} />;
    case 'big-word': return <BigWord {...c} b={b} />;
    case 'brand-logo': return <BrandLogo {...c} b={b} />;
    case 'illustration': return <Illustration {...c} b={b} />;
    case 'selection-box': return <SelectionBox {...c} b={b} />;
    case 'comment-box': return <CommentBox {...c} b={b} />;
    case 'info-scene': return <InfoScene {...c} b={b} />;
    case 'topic-card': return <TopicCard {...c} b={b} />;
    case 'broll': return <Broll {...c} b={b} />;
  }
};

/** BROLL/INFO beats below the captions, small overlays above. Order by array position. */
export const Beats: React.FC<{beats: BeatsFile; L: Layout; segs: MappedSegment[]; fps: number; only?: 'under' | 'over'; probe?: Probe | null}> = ({beats, L, segs, fps, only, probe}) => (
  <AbsoluteFill>
    {beats.beats.map((b, i) => {
      const under = b.type === 'broll' || b.type === 'info-scene' || b.type === 'topic-card' || b.type === 'framed-focus' || b.type === 'text-behind-speaker';
      if (only === 'under' && !under) return null;
      if (only === 'over' && under) return null;
      const r = mapInterval(segs, b.t0, b.t1, fps);
      if (!r) return null; // the beat's moment was cut out
      const dur = r[1] - r[0];
      return (
        <Sequence key={i} from={r[0]} durationInFrames={dur}>
          {b.type === 'framed-focus' ? <FramedFocus L={L} segs={segs} fps={fps} dur={dur} t0={b.t0} probe={probe ?? null} r0={r[0]} b={b} /> : b.type === 'text-behind-speaker' ? <TextBehind L={L} segs={segs} fps={fps} dur={dur} t0={b.t0} probe={probe ?? null} r0={r[0]} b={b} /> : render(b, {L, segs, fps, dur, t0: b.t0, beats})}
        </Sequence>
      );
    })}
  </AbsoluteFill>
);
