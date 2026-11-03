import {loadFont} from '@remotion/google-fonts/BeVietnamPro';
import {STYLE} from './style';

// Vietnamese subset is REQUIRED, otherwise diacritics fall back to a different font.
const f = loadFont('normal', {weights: ['500', '700', '800'], subsets: ['vietnamese', 'latin', 'latin-ext']});
export const FONT_FAMILY = `${f.fontFamily}, ${STYLE.fonts.family}, Inter, sans-serif`;
export const FONT_READY = f.waitUntilDone;
export const LETTER = `${STYLE.fonts.letterSpacingEm}em`;
