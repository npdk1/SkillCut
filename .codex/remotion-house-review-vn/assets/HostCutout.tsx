import React from 'react';
import {Img, staticFile, useCurrentFrame} from 'remotion';

export const HostCutout: React.FC = () => {
  const frame = useCurrentFrame();

  // Active during the outdoor walking intro: frame 15 to 80
  if (frame < 15 || frame > 80) {
    return null;
  }

  const paddedFrame = String(frame).padStart(3, '0');
  const cutoutSrc = staticFile(`cutouts/f_${paddedFrame}.png`);

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        zIndex: 20, // Rendered ABOVE behind text (15), so host occludes the letters!
        pointerEvents: 'none',
      }}
    >
      <Img
        src={cutoutSrc}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
        }}
      />
    </div>
  );
};
