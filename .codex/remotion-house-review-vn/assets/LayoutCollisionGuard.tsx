import {useLayoutEffect} from 'react';
import {getRemotionEnvironment, useCurrentFrame} from 'remotion';

export const LayoutCollisionGuard = () => {
  const frame = useCurrentFrame();

  useLayoutEffect(() => {
    const elements = [...document.querySelectorAll<HTMLElement>('[data-layout-role]')]
      .filter((element) => {
        const style = window.getComputedStyle(element);
        return style.display !== 'none' && style.visibility !== 'hidden' && Number(style.opacity) > 0.05;
      });
    const collisions: string[] = [];

    for (let firstIndex = 0; firstIndex < elements.length; firstIndex++) {
      for (let secondIndex = firstIndex + 1; secondIndex < elements.length; secondIndex++) {
        const first = elements[firstIndex];
        const second = elements[secondIndex];
        const roles = [first.dataset.layoutRole, second.dataset.layoutRole];
        const blockedPair =
          (roles.includes('caption') && roles.includes('overlay')) ||
          (roles[0] === 'overlay' && roles[1] === 'overlay') ||
          (roles.includes('overlay') && roles.includes('protected'));
        if (!blockedPair) continue;
        const a = first.getBoundingClientRect();
        const b = second.getBoundingClientRect();
        const width = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left));
        const height = Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
        if (width * height > 36) collisions.push(`${first.dataset.layoutId ?? 'text'} ↔ ${second.dataset.layoutId ?? 'element'}`);
      }
    }

    if (collisions.length > 0) {
      const message = `Layout collision at frame ${frame}: ${collisions.join(', ')}`;
      if (getRemotionEnvironment().isRendering) throw new Error(message);
      console.warn(message);
    }
  }, [frame]);

  return null;
};
