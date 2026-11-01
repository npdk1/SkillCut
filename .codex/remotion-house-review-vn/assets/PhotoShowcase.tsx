import React from 'react';
import {Img, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {sansFont, serifFont, scriptFont} from './font';

interface ShowcaseScene {
  startFrame: number;
  endFrame: number;
  cutFrame: number;
  shot1Img: string;
  shot2Img?: string;
  shot1Tag: string;
  shot1Title: string;
  shot1Subtitle: string;
  shot2Tag?: string;
  shot2Title?: string;
  shot2Subtitle?: string;
}

const SHOWCASE_SCENES: ShowcaseScene[] = [
  // 1. Hotel Vibe / La Carte (00:17 - 00:21.8)
  {
    startFrame: 510,
    endFrame: 654,
    cutFrame: 582,
    shot1Img: 'showcase/showcase_mirror.jpg',
    shot2Img: 'showcase/showcase_rooftop.jpg',
    shot1Tag: 'HOTEL LUXURY SUITE',
    shot1Title: 'Gương Sóng Nghệ Thuật',
    shot1Subtitle: 'Phong Cách La Carte',
    shot2Tag: 'KHÔNG GIAN NGHỈ DƯỠNG',
    shot2Title: 'Vườn Ban Công Chill',
    shot2Subtitle: 'Chuẩn Biệt Thự Mini',
  },
  // 2. Kitchen & Cocktail Bar (00:47 - 00:55)
  {
    startFrame: 1410,
    endFrame: 1650,
    cutFrame: 1530,
    shot1Img: 'showcase/showcase_kitchen.jpg',
    shot2Img: 'showcase/kitchen_bar.jpg',
    shot1Tag: 'KHÔNG GIAN BẾP ĂN',
    shot1Title: 'Kệ Bếp Chữ U',
    shot1Subtitle: 'Tủ Rượu & Quầy Bar Tiếp Khách',
    shot2Tag: 'TIỆN NGHI CAO CẤP',
    shot2Title: 'Góc Cocktail Sang Trọng',
    shot2Subtitle: 'Cuối Tuần Chill Cùng Bạn Bè',
  },
  // 3. Master Bedroom 5-Star (01:35 - 01:45)
  {
    startFrame: 2850,
    endFrame: 3150,
    cutFrame: 3000,
    shot1Img: 'showcase/showcase_bedroom_suite.jpg',
    shot2Img: 'showcase/showcase_mirror.jpg',
    shot1Tag: 'MASTER BEDROOM',
    shot1Title: 'Phòng Ngủ Master',
    shot1Subtitle: 'Tiêu Chuẩn Khách Sạn 5 Sao',
    shot2Tag: 'CHI TIẾT NGHỆ THUẬT',
    shot2Title: 'Gương Xoay Chiếu Sáng',
    shot2Subtitle: 'Vệ Sinh Khép Kín Riêng Biệt',
  },
  // 4. Rooftop Sky Garden Mini Villa (03:06 - 03:16.5)
  {
    startFrame: 5580,
    endFrame: 5895,
    cutFrame: 5735,
    shot1Img: 'showcase/showcase_rooftop.jpg',
    shot2Img: 'showcase/showcase_teatable.jpg',
    shot1Tag: 'SÂN THƯỢNG SKY GARDEN',
    shot1Title: 'Vườn Biệt Thự Mini',
    shot1Subtitle: 'Mái Kính Châu Âu Cực Chill',
    shot2Tag: 'GẮN KẾT GIA ĐÌNH',
    shot2Title: 'Bàn Trà Chiều Thư Giãn',
    shot2Subtitle: 'Nuôi Chim Cá Cảnh Ngắm Phố',
  },
  // 5. Altar Room (03:25 - 03:29.6)
  {
    startFrame: 6150,
    endFrame: 6290,
    cutFrame: 6290, // Single continuous shot with slow Ken Burns drift
    shot1Img: 'showcase/showcase_altar.jpg',
    shot1Tag: 'KHÔNG GIAN TÂM LINH',
    shot1Title: 'Phòng Thờ Trang Nghiêm',
    shot1Subtitle: 'Gạch Bông Đông Dương Hút Tài Lộc',
  },
];

export const PhotoShowcase: React.FC = () => {
  const frame = useCurrentFrame();

  // Find active showcase scene
  const activeScene = SHOWCASE_SCENES.find(
    (s) => frame >= s.startFrame && frame < s.endFrame
  );

  if (!activeScene) {
    return null;
  }

  const isShot1 = frame < activeScene.cutFrame;
  const shotProgress = isShot1
    ? (frame - activeScene.startFrame) /
      Math.max(activeScene.cutFrame - activeScene.startFrame, 1)
    : (frame - activeScene.cutFrame) /
      Math.max(activeScene.endFrame - activeScene.cutFrame, 1);

  // Ken Burns subtle scale / pan
  const scale = isShot1
    ? interpolate(shotProgress, [0, 1], [1.0, 1.06])
    : interpolate(shotProgress, [0, 1], [1.06, 1.01]);

  const imgSrc = isShot1
    ? staticFile(activeScene.shot1Img)
    : staticFile(activeScene.shot2Img || activeScene.shot1Img);

  const tag = isShot1 ? activeScene.shot1Tag : (activeScene.shot2Tag || activeScene.shot1Tag);
  const title = isShot1 ? activeScene.shot1Title : (activeScene.shot2Title || activeScene.shot1Title);
  const subtitle = isShot1 ? activeScene.shot1Subtitle : (activeScene.shot2Subtitle || activeScene.shot1Subtitle);

  // Flash transition at cut point
  const isTransitionCut =
    activeScene.shot2Img &&
    frame >= activeScene.cutFrame - 1 &&
    frame <= activeScene.cutFrame + 1;
  const flashOpacity = isTransitionCut ? 0.35 : 0;

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        zIndex: 25, // Sits above raw footage, below subtitles
        overflow: 'hidden',
      }}
    >
      {/* Photo with Ken Burns animation */}
      <div
        style={{
          width: '100%',
          height: '100%',
          transform: `scale(${scale})`,
          transformOrigin: isShot1 ? 'center 40%' : 'center 60%',
        }}
      >
        <Img
          src={imgSrc}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
          }}
        />
      </div>

      {/* Cinematic vignette & gradient overlays */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: 220,
          background:
            'linear-gradient(to bottom, rgba(0,0,0,0.7) 0%, rgba(0,0,0,0.3) 60%, transparent 100%)',
          pointerEvents: 'none',
        }}
      />
      <div
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          height: 200,
          background:
            'linear-gradient(to top, rgba(0,0,0,0.7) 0%, rgba(0,0,0,0.2) 60%, transparent 100%)',
          pointerEvents: 'none',
        }}
      />

      {/* Editorial Luxury Badge */}
      <div
        data-layout-role="overlay"
        data-layout-id={`showcase-badge-${activeScene.startFrame}`}
        style={{
          position: 'absolute',
          top: 70,
          left: 32,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'flex-start',
          pointerEvents: 'none',
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
          {tag}
        </div>

        <div
          style={{
            fontFamily: serifFont,
            fontSize: 30,
            fontWeight: 900,
            letterSpacing: '0.03em',
            color: '#FFFFFF',
            textShadow: '0 4px 16px rgba(0,0,0,0.95)',
            lineHeight: 1.1,
          }}
        >
          {title}
        </div>

        <div
          style={{
            fontFamily: scriptFont,
            fontSize: 34,
            fontWeight: 700,
            color: '#FFEA31',
            transform: 'rotate(-4deg)',
            textShadow: '0 2px 10px rgba(0,0,0,0.9)',
            marginTop: -4,
          }}
        >
          {subtitle}
        </div>
      </div>

      {/* White flash on cut transition */}
      {flashOpacity > 0 && (
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: '#FFFFFF',
            opacity: flashOpacity,
            pointerEvents: 'none',
          }}
        />
      )}
    </div>
  );
};
