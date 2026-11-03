import React from 'react';
import {STYLE} from '../../assets/style';
import {FONT_FAMILY} from '../../assets/font';

const K = STYLE.colors;

export const Star: React.FC<{size: number; rot?: number}> = ({size, rot = 0}) => (
  <svg width={size} height={size} viewBox="0 0 24 24" style={{transform: `rotate(${rot}deg)`, filter: 'drop-shadow(0 3px 6px rgba(0,0,0,.35))'}}>
    <path d="M12 1.8l3 6.6 7.2.8-5.4 4.8 1.6 7.1L12 17.4 5.6 21.1l1.6-7.1L1.8 9.2 9 8.4z" fill="#F7D64A" stroke="#FFF3B0" strokeWidth="1" strokeLinejoin="round" />
  </svg>
);

export const Sparkle: React.FC<{size: number; color?: string}> = ({size, color = '#fff'}) => (
  <svg width={size} height={size} viewBox="0 0 24 24"><path d="M12 0c1 7 5 11 12 12-7 1-11 5-12 12-1-7-5-11-12-12 7-1 11-5 12-12z" fill={color} /></svg>
);

/** brand tile (asterisk). Replace colours in style.config.json -> colors.claude* */
export const BrandTile: React.FC<{size: number}> = ({size}) => (
  <div style={{width: size, height: size, borderRadius: size * 0.24, background: K.claudeCream, boxShadow: '0 8px 22px rgba(0,0,0,.35)', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
    <svg width={size * 0.62} height={size * 0.62} viewBox="0 0 24 24">
      {Array.from({length: 8}).map((_, i) => (
        <rect key={i} x="11" y="1.5" width="2.2" height="8.5" rx="1.1" fill={K.claudeOrange} transform={`rotate(${i * 45} 12 12)`} />
      ))}
    </svg>
  </div>
);

export const Icon: React.FC<{name?: string; size: number}> = ({name, size}) => {
  const s = size;
  const text = (t: string, c = '#fff', fs = 0.55) => <span style={{fontFamily: FONT_FAMILY, fontWeight: 800, fontSize: s * fs, color: c}}>{t}</span>;
  const box = (child: React.ReactNode) => <div style={{width: s, height: s, borderRadius: s * 0.22, background: '#2B2C2D', display: 'flex', alignItems: 'center', justifyContent: 'center', flex: '0 0 auto'}}>{child}</div>;
  switch (name) {
    case 'aa': return box(text('Aa'));
    case 'shapes': return box(
      <svg width={s * 0.7} height={s * 0.7} viewBox="0 0 24 24"><circle cx="8" cy="8" r="6" fill={K.highlight} /><rect x="12" y="12" width="9" height="9" rx="2" fill="#fff" /><path d="M3 21l5-9 5 9z" fill="none" stroke="#fff" strokeWidth="1.6" /></svg>);
    case 'motion': return box(
      <svg width={s * 0.7} height={s * 0.7} viewBox="0 0 24 24"><path d="M3 18c4-12 8 6 12-6s4-4 6-6" fill="none" stroke="#fff" strokeWidth="1.8" /><circle cx="3" cy="18" r="2" fill={K.highlight} /><circle cx="21" cy="6" r="2" fill={K.highlight} /></svg>);
    case 'sound': return box(
      <svg width={s * 0.7} height={s * 0.7} viewBox="0 0 24 24">{[3, 8, 13, 18].map((x, i) => <rect key={i} x={x} y={12 - [3, 7, 5, 9][i] / 1} width="3" height={[6, 14, 10, 18][i]} rx="1.2" fill={K.highlight} />)}</svg>);
    case 'user': return box(
      <svg width={s * 0.6} height={s * 0.6} viewBox="0 0 24 24"><circle cx="12" cy="8" r="5" fill="#cfd0d1" /><path d="M3 22c1-6 6-8 9-8s8 2 9 8z" fill="#cfd0d1" /></svg>);
    case 'bolt': return box(
      <svg width={s * 0.6} height={s * 0.6} viewBox="0 0 24 24"><path d="M13 2L4 14h7l-1 8 9-12h-7z" fill="none" stroke="#fff" strokeWidth="1.8" strokeLinejoin="round" /></svg>);
    case 'check': return <span style={{color: K.highlight, fontFamily: FONT_FAMILY, fontWeight: 800, fontSize: s}}>✓</span>;
    case 'brand': return <BrandTile size={s} />;
    case 'chat': return (
      <div style={{width: s, height: s, borderRadius: s * 0.26, background: '#1F2021', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 8px 22px rgba(0,0,0,.35)'}}>
        <svg width={s * 0.6} height={s * 0.6} viewBox="0 0 24 24"><path d="M3 4h18v12H9l-5 4v-4H3z" fill={K.highlight} /><circle cx="8" cy="10" r="1.3" fill="#1F2021" /><circle cx="12" cy="10" r="1.3" fill="#1F2021" /><circle cx="16" cy="10" r="1.3" fill="#1F2021" /></svg>
      </div>);
    default: return box(text(name ? name.slice(0, 2) : '•'));
  }
};
