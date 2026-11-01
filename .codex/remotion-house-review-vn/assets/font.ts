import {loadFont as loadBeVietnamPro} from '@remotion/google-fonts/BeVietnamPro';
import {loadFont as loadPlayfair} from '@remotion/google-fonts/PlayfairDisplay';
import {loadFont as loadDancing} from '@remotion/google-fonts/DancingScript';

export const {fontFamily: sansFont} = loadBeVietnamPro('normal', {
  weights: ['600', '700', '800', '900'],
  subsets: ['latin', 'vietnamese'],
});

export const {fontFamily: serifFont} = loadPlayfair('normal', {
  weights: ['700', '900'],
  subsets: ['latin', 'vietnamese'],
});

export const {fontFamily: scriptFont} = loadDancing('normal', {
  weights: ['700'],
  subsets: ['latin', 'vietnamese'],
});

export const fontFamily = sansFont;
