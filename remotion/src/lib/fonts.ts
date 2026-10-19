// Local, licence-checked fonts (public/fonts, licences next to the files). Nothing is downloaded at render time.
import {continueRender, delayRender, staticFile} from 'remotion';

const LATIN =
  'U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD';
const LATIN_EXT =
  'U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF';

const FACES: {family: string; file: string; range?: string}[] = [
  {family: 'Special Elite', file: 'fonts/special-elite-latin-400-normal.woff2', range: LATIN}, // Apache-2.0
  {family: 'Special Elite', file: 'fonts/special-elite-latin-ext-400-normal.woff2', range: LATIN_EXT},
  {family: 'Patrick Hand', file: 'fonts/patrick-hand-latin-400-normal.woff2', range: LATIN}, // OFL-1.1
  {family: 'Patrick Hand', file: 'fonts/patrick-hand-latin-ext-400-normal.woff2', range: LATIN_EXT},
  {family: 'Alfa Slab One', file: 'fonts/AlfaSlabOne-Regular.ttf'}, // OFL-1.1
];

let started = false;

export const loadFonts = () => {
  if (started || typeof document === 'undefined') return;
  started = true;
  const handle = delayRender('Loading fonts');
  Promise.all(
    FACES.map((f) => {
      const face = new FontFace(f.family, `url(${staticFile(f.file)})`, f.range ? {unicodeRange: f.range} : {});
      (document.fonts as unknown as {add: (f: FontFace) => void}).add(face);
      return face.load();
    }),
  )
    .then(() => continueRender(handle))
    .catch((err) => {
      console.error('font load failed', err);
      continueRender(handle);
    });
};
