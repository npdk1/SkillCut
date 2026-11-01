import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {sansFont, serifFont, scriptFont} from './font';

export const Overlays: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // Helper animation
  const makeSpring = (start: number, end: number) => {
    if (frame < start || frame >= end) return null;
    const elapsed = frame - start;
    const remaining = end - frame;
    const enter = spring({
      frame: elapsed,
      fps,
      config: {damping: 16, mass: 0.5, stiffness: 140},
    });
    const opacity =
      interpolate(elapsed, [0, 8], [0, 1], {extrapolateRight: 'clamp'}) *
      interpolate(remaining, [0, 8], [0, 1], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      });
    return {enter, opacity};
  };

  // 1. Stat Feature: frame 272 to 340 (00:09 - 00:11.3)
  const anim1 = makeSpring(272, 340);
  if (anim1) {
    const translateY = interpolate(anim1.enter, [0, 1], [-12, 0]);
    return (
      <div
        data-layout-role="overlay"
        data-layout-id="overlay-stat-scene"
        style={{
          position: 'absolute',
          top: 75,
          left: 32,
          opacity: anim1.opacity,
          transform: `translateY(${translateY}px)`,
          zIndex: 40,
          pointerEvents: 'none',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'flex-start',
        }}
      >
        <div style={{display: 'flex', alignItems: 'baseline', gap: 6}}>
          <span
            style={{
              fontFamily: sansFont,
              fontSize: 26,
              fontWeight: 800,
              color: '#FFFFFF',
              textShadow: '0 3px 12px rgba(0,0,0,0.9)',
            }}
          >
            Nhà Phố
          </span>
          <span
            style={{
              fontFamily: scriptFont,
              fontSize: 34,
              fontWeight: 700,
              color: '#FFEA31',
              textShadow: '0 2px 10px rgba(0,0,0,0.9)',
            }}
          >
            4 Tầng
          </span>
        </div>
        <div
          style={{
            fontFamily: sansFont,
            fontSize: 16,
            fontWeight: 800,
            letterSpacing: '0.08em',
            color: 'rgba(255, 255, 255, 0.95)',
            textTransform: 'uppercase',
            textShadow: '0 2px 8px rgba(0,0,0,0.9)',
            marginTop: 2,
          }}
        >
          Diện Tích Đất: <span style={{color: '#FFD21C', fontSize: 20}}>51 m²</span>
        </div>
      </div>
    );
  }

  // 2. Hero Price: frame 354 to 425 (00:11.8 - 00:14.1)
  const anim2 = makeSpring(354, 425);
  if (anim2) {
    const scale = interpolate(anim2.enter, [0, 1], [0.92, 1.0]);
    return (
      <div
        data-layout-role="overlay"
        data-layout-id="overlay-hero-price"
        style={{
          position: 'absolute',
          top: 70,
          left: 32,
          opacity: anim2.opacity,
          transform: `scale(${scale})`,
          transformOrigin: 'top left',
          zIndex: 40,
          pointerEvents: 'none',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'flex-start',
        }}
      >
        <div style={{display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2}}>
          <span
            style={{
              fontFamily: sansFont,
              fontSize: 22,
              fontWeight: 800,
              color: '#FFFFFF',
              textShadow: '0 3px 10px rgba(0,0,0,0.9)',
            }}
          >
            Chào bán
          </span>
          <span
            style={{
              fontFamily: sansFont,
              fontSize: 12,
              fontWeight: 800,
              color: '#000000',
              backgroundColor: '#FFEA31',
              padding: '2px 8px',
              borderRadius: 999,
              letterSpacing: '0.04em',
            }}
          >
            chính chủ
          </span>
        </div>
        <div
          style={{
            fontFamily: sansFont,
            fontSize: 54,
            fontWeight: 900,
            lineHeight: 1.05,
            letterSpacing: '-0.03em',
            color: '#FFD21C',
            WebkitTextStroke: '2px #7A5B00',
            paintOrder: 'stroke fill',
            textShadow:
              '0 4px 20px rgba(0, 0, 0, 0.95), 0 0 25px rgba(255, 210, 28, 0.5)',
          }}
        >
          NHỈNH 12 TỶ
        </div>
        <div
          style={{
            fontFamily: sansFont,
            fontSize: 13,
            fontWeight: 700,
            color: 'rgba(255, 255, 255, 0.9)',
            textShadow: '0 2px 6px rgba(0,0,0,0.85)',
            marginTop: 4,
          }}
        >
          Xây mới 100% • Sổ đỏ trao tay
        </div>
      </div>
    );
  }

  // 3. Detail Feature: frame 710 to 820 (00:23.6 - 00:27.3)
  const anim3 = makeSpring(710, 820);
  if (anim3) {
    const translateY = interpolate(anim3.enter, [0, 1], [-10, 0]);
    return (
      <div
        data-layout-role="overlay"
        data-layout-id="overlay-design-detail"
        style={{
          position: 'absolute',
          top: 75,
          left: 32,
          opacity: anim3.opacity,
          transform: `translateY(${translateY}px)`,
          zIndex: 40,
          pointerEvents: 'none',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'flex-start',
        }}
      >
        <div style={{display: 'flex', alignItems: 'baseline', gap: 8}}>
          <span
            style={{
              fontFamily: sansFont,
              fontSize: 24,
              fontWeight: 800,
              color: '#FFFFFF',
              textShadow: '0 3px 10px rgba(0,0,0,0.9)',
            }}
          >
            Gia chủ
          </span>
          <span
            style={{
              fontFamily: scriptFont,
              fontSize: 34,
              fontWeight: 700,
              color: '#FFEA31',
              textShadow: '0 2px 10px rgba(0,0,0,0.9)',
            }}
          >
            tự thiết kế
          </span>
        </div>
        <div
          style={{
            fontFamily: sansFont,
            fontSize: 13,
            fontWeight: 700,
            color: 'rgba(255, 255, 255, 0.9)',
            textShadow: '0 2px 6px rgba(0,0,0,0.9)',
            marginTop: 2,
          }}
        >
          Full nội thất bàn ghế • Tỉ mỉ từng chi tiết
        </div>
      </div>
    );
  }

  // 4. Furniture Handover Tag: frame 1710 to 1830 (00:57.0 - 01:01.0)
  const anim4 = makeSpring(1710, 1830);
  if (anim4) {
    const translateY = interpolate(anim4.enter, [0, 1], [-10, 0]);
    return (
      <div
        data-layout-role="overlay"
        data-layout-id="overlay-furniture-chip"
        style={{
          position: 'absolute',
          top: 75,
          left: 32,
          opacity: anim4.opacity,
          transform: `translateY(${translateY}px)`,
          zIndex: 40,
          pointerEvents: 'none',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'flex-start',
        }}
      >
        <div style={{display: 'flex', alignItems: 'baseline', gap: 8}}>
          <span
            style={{
              fontFamily: sansFont,
              fontSize: 24,
              fontWeight: 800,
              color: '#FFFFFF',
              textShadow: '0 3px 10px rgba(0,0,0,0.9)',
            }}
          >
            Tặng lại
          </span>
          <span
            style={{
              fontFamily: scriptFont,
              fontSize: 34,
              fontWeight: 700,
              color: '#FFEA31',
              textShadow: '0 2px 10px rgba(0,0,0,0.9)',
            }}
          >
            full nội thất
          </span>
        </div>
        <div
          style={{
            fontFamily: sansFont,
            fontSize: 13,
            fontWeight: 700,
            color: 'rgba(255, 255, 255, 0.95)',
            textShadow: '0 2px 6px rgba(0,0,0,0.9)',
            marginTop: 2,
          }}
        >
          Xách vali về ở ngay • Gia chủ tâm huyết
        </div>
      </div>
    );
  }

  // 5. 4 Bedrooms Stat: frame 1980 to 2070 (01:06.0 - 01:09.0)
  const anim5 = makeSpring(1980, 2070);
  if (anim5) {
    const translateY = interpolate(anim5.enter, [0, 1], [-10, 0]);
    return (
      <div
        data-layout-role="overlay"
        data-layout-id="overlay-bedroom-stat"
        style={{
          position: 'absolute',
          top: 75,
          left: 32,
          opacity: anim5.opacity,
          transform: `translateY(${translateY}px)`,
          zIndex: 40,
          pointerEvents: 'none',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'flex-start',
        }}
      >
        <div style={{display: 'flex', alignItems: 'baseline', gap: 8}}>
          <span
            style={{
              fontFamily: sansFont,
              fontSize: 24,
              fontWeight: 800,
              color: '#FFFFFF',
              textShadow: '0 3px 10px rgba(0,0,0,0.9)',
            }}
          >
            Quy mô
          </span>
          <span
            style={{
              fontFamily: scriptFont,
              fontSize: 34,
              fontWeight: 700,
              color: '#FFEA31',
              textShadow: '0 2px 10px rgba(0,0,0,0.9)',
            }}
          >
            4 phòng ngủ
          </span>
        </div>
        <div
          style={{
            fontFamily: sansFont,
            fontSize: 13,
            fontWeight: 700,
            color: 'rgba(255, 255, 255, 0.95)',
            textShadow: '0 2px 6px rgba(0,0,0,0.9)',
            marginTop: 2,
          }}
        >
          Tất cả đều khép kín • Gia đình đa thế hệ
        </div>
      </div>
    );
  }

  // 6. Build Status (Xây mới 100%): frame 3720 to 3840 (02:04.0 - 02:08.0)
  const anim6 = makeSpring(3720, 3840);
  if (anim6) {
    const scale = interpolate(anim6.enter, [0, 1], [0.94, 1.0]);
    return (
      <div
        data-layout-role="overlay"
        data-layout-id="overlay-brand-new"
        style={{
          position: 'absolute',
          top: 72,
          left: 32,
          opacity: anim6.opacity,
          transform: `scale(${scale})`,
          transformOrigin: 'top left',
          zIndex: 40,
          pointerEvents: 'none',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'flex-start',
        }}
      >
        <div style={{display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2}}>
          <span
            style={{
              fontFamily: sansFont,
              fontSize: 12,
              fontWeight: 800,
              color: '#000000',
              backgroundColor: '#FFEA31',
              padding: '2px 8px',
              borderRadius: 999,
              letterSpacing: '0.04em',
            }}
          >
            CAM KẾT
          </span>
        </div>
        <div
          style={{
            fontFamily: serifFont,
            fontSize: 38,
            fontWeight: 900,
            letterSpacing: '0.02em',
            color: '#FFFFFF',
            textShadow: '0 4px 16px rgba(0, 0, 0, 0.95)',
            lineHeight: 1.1,
          }}
        >
          XÂY MỚI 100%
        </div>
        <div
          style={{
            fontFamily: sansFont,
            fontSize: 13,
            fontWeight: 700,
            color: 'rgba(255, 255, 255, 0.9)',
            textShadow: '0 2px 6px rgba(0,0,0,0.9)',
            marginTop: 2,
          }}
        >
          Không qua sửa chữa • Từng viên gạch mới tinh
        </div>
      </div>
    );
  }

  // 7. Proximity (50m ra ô tô): frame 4305 to 4425 (02:43.5 - 02:47.5)
  const anim7 = makeSpring(4305, 4425);
  if (anim7) {
    const translateY = interpolate(anim7.enter, [0, 1], [-10, 0]);
    return (
      <div
        data-layout-role="overlay"
        data-layout-id="overlay-proximity"
        style={{
          position: 'absolute',
          top: 75,
          left: 32,
          opacity: anim7.opacity,
          transform: `translateY(${translateY}px)`,
          zIndex: 40,
          pointerEvents: 'none',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'flex-start',
        }}
      >
        <div style={{display: 'flex', alignItems: 'baseline', gap: 8}}>
          <span
            style={{
              fontFamily: sansFont,
              fontSize: 24,
              fontWeight: 800,
              color: '#FFFFFF',
              textShadow: '0 3px 10px rgba(0,0,0,0.9)',
            }}
          >
            Chỉ đúng
          </span>
          <span
            style={{
              fontFamily: scriptFont,
              fontSize: 34,
              fontWeight: 700,
              color: '#FFEA31',
              textShadow: '0 2px 10px rgba(0,0,0,0.9)',
            }}
          >
            50 mét
          </span>
        </div>
        <div
          style={{
            fontFamily: sansFont,
            fontSize: 14,
            fontWeight: 800,
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
            color: 'rgba(255, 255, 255, 0.95)',
            textShadow: '0 2px 6px rgba(0,0,0,0.9)',
            marginTop: 2,
          }}
        >
          Ra Đường Ô Tô Tránh • Đi Lại Cực Thuận Tiện
        </div>
      </div>
    );
  }

  // 8. Grand Outro Hero Monogram: frame 6300 to 6500 (03:30.0 - 03:36.6)
  const anim8 = makeSpring(6300, 6500);
  if (anim8) {
    const scale = interpolate(anim8.enter, [0, 1], [0.92, 1.0]);
    return (
      <div
        data-layout-role="overlay"
        data-layout-id="overlay-grand-outro"
        style={{
          position: 'absolute',
          top: 65,
          left: 28,
          right: 28,
          opacity: anim8.opacity,
          transform: `scale(${scale})`,
          zIndex: 40,
          pointerEvents: 'none',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          textAlign: 'center',
        }}
      >
        <div
          style={{
            fontFamily: sansFont,
            fontSize: 11,
            fontWeight: 800,
            letterSpacing: '0.24em',
            textTransform: 'uppercase',
            color: '#FFEA31',
            textShadow: '0 2px 8px rgba(0,0,0,0.9)',
            marginBottom: 2,
          }}
        >
          HÀ NỘI • TỔNG KẾT BẤT ĐỘNG SẢN
        </div>

        <div
          style={{
            fontFamily: serifFont,
            fontSize: 32,
            fontWeight: 900,
            letterSpacing: '0.04em',
            color: '#FFFFFF',
            textShadow: '0 4px 20px rgba(0, 0, 0, 0.95)',
            lineHeight: 1.1,
          }}
        >
          NHÀ PHỐ CHÂU ÂU
        </div>

        <div
          style={{
            fontFamily: sansFont,
            fontSize: 40,
            fontWeight: 900,
            letterSpacing: '-0.02em',
            color: '#FFD21C',
            WebkitTextStroke: '2px #7A5B00',
            paintOrder: 'stroke fill',
            textShadow: '0 4px 16px rgba(0, 0, 0, 0.95), 0 0 20px rgba(255, 210, 28, 0.5)',
            marginTop: 4,
          }}
        >
          NHỈNH 12 TỶ
        </div>

        <div
          style={{
            fontFamily: sansFont,
            fontSize: 12,
            fontWeight: 800,
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
            color: '#FFFFFF',
            textShadow: '0 2px 8px rgba(0,0,0,0.9)',
            marginTop: 6,
          }}
        >
          51 m² × 4 Tầng • 4 Ngủ Khép Kín • Sân Thượng Chill
        </div>
      </div>
    );
  }

  return null;
};
