import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {sansFont, serifFont, scriptFont} from './font';

export const BehindHostText: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // Active during the outdoor walking intro: frame 15 to 80 (0.5s - 2.67s)
  if (frame < 15 || frame > 80) {
    return null;
  }

  const elapsed = frame - 15;
  const remaining = 80 - frame;

  const enter = spring({
    frame: elapsed,
    fps,
    config: {damping: 14, mass: 0.6, stiffness: 120},
  });

  const opacity =
    interpolate(elapsed, [0, 8], [0, 1], {extrapolateRight: 'clamp'}) *
    interpolate(remaining, [0, 8], [0, 1], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    });

  const scale = interpolate(enter, [0, 1], [0.9, 1.0]);
  const translateY = interpolate(enter, [0, 1], [-15, 0]);

  return (
    <div
      style={{
        position: 'absolute',
        top: 405, // Positioned right across the reviewer's head and shoulders
        left: 0,
        right: 0,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        opacity,
        transform: `translateY(${translateY}px) scale(${scale})`,
        zIndex: 15, // Anchored between background video (5) and foreground host cutout (20)
        pointerEvents: 'none',
      }}
    >
      {/* Category / Location Tag */}
      <div
        style={{
          fontFamily: sansFont,
          fontSize: 12,
          fontWeight: 800,
          letterSpacing: '0.24em',
          textTransform: 'uppercase',
          color: '#FFE27A',
          textShadow: '0 2px 10px rgba(0,0,0,0.95)',
          marginBottom: 4,
        }}
      >
        HÀ NỘI • NHÀ PHỐ TÂM ĐIỂM
      </div>

      {/* Hero 3D Serif Typography positioned behind reviewer */}
      <div
        style={{
          position: 'relative',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <div
          style={{
            fontFamily: serifFont,
            fontSize: 78,
            fontWeight: 900,
            letterSpacing: '0.04em',
            color: '#FFFFFF',
            WebkitTextStroke: '2px rgba(0,0,0,0.7)',
            textShadow:
              '0 8px 32px rgba(0, 0, 0, 0.95), 0 2px 8px rgba(0, 0, 0, 0.9)',
            lineHeight: 0.95,
          }}
        >
          CHÂU ÂU
        </div>

        {/* Script Accent overlapping */}
        <div
          style={{
            position: 'absolute',
            bottom: -24,
            right: 8,
            fontFamily: scriptFont,
            fontSize: 56,
            fontWeight: 700,
            color: '#FFEA31',
            transform: 'rotate(-7deg)',
            textShadow:
              '0 3px 12px rgba(0, 0, 0, 0.95), 0 0 16px rgba(255, 234, 49, 0.7)',
            pointerEvents: 'none',
          }}
        >
          thu nhỏ
        </div>
      </div>

      <div
        style={{
          fontFamily: sansFont,
          fontSize: 16,
          fontWeight: 800,
          letterSpacing: '0.2em',
          textTransform: 'uppercase',
          color: '#FFFFFF',
          marginTop: 26,
          textShadow: '0 2px 10px rgba(0,0,0,0.95)',
        }}
      >
        GIỮA LÒNG THỦ ĐÔ
      </div>
    </div>
  );
};
