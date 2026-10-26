// The look of a channel, sent by the Python pipeline (studio/remotion.py → theme()).
// Every component draws only with these values, so one component serves every channel.

export type Rules = {first: number; step: number; margin: number | null}; // ruled ledger lines, in 1920×1080 paper px

export type Theme = {
  name: string;
  paper: string | null; // file inside public/ (copied there by Python), drawn edge to edge ("cover")
  bg: string; // page colour when there is no paper picture
  ink: string;
  accent: string; // red pen and stamp
  wash: string; // watercolour wash for bars and highlights
  wash2: string;
  muted: string; // secondary ink (labels, ticks)
  fonts: {type: string; hand: string; stamp: string};
  palette?: Record<string, string>; // named colours for code-drawn scenes (comp `mech`): fill: yellow, teal, ...
  boil: number; // hand-drawn line wobble in px at 1080 p (0 = off)
  rules: Rules | null; // put handwriting on the ruled lines of the paper
};

export const LEDGER: Theme = {
  name: 'ledger',
  paper: null,
  bg: '#f1e9d6',
  ink: '#181614',
  accent: '#b23026',
  wash: '#b8913f',
  wash2: '#8fb3c9',
  muted: '#5c534a',
  fonts: {type: 'Special Elite', hand: 'Patrick Hand', stamp: 'Alfa Slab One'},
  boil: 2.2,
  rules: {first: 58.5, step: 46, margin: 132.5},
};

export const MUSEUM: Theme = {
  ...LEDGER,
  name: 'museum',
  bg: '#efe2c4',
  ink: '#151311',
  accent: '#d8342c',
  wash: '#e3a447',
  wash2: '#6f9fc0',
  muted: '#5b4636',
  boil: 1.4,
  rules: null,
};

// Vivid explainer look (Drawer Physics): deep indigo stage, saturated flat colours, thick navy outlines,
// rounded display type. No paper, no line boil. `ink` is the text colour on the dark stage; outlines use palette.line.
export const POP: Theme = {
  name: 'pop',
  paper: null,
  bg: '#1b1f4b',
  ink: '#fff8e7',
  accent: '#ffcc33',
  wash: '#2ec4b6',
  wash2: '#ff6b5b',
  muted: '#aab0e0',
  fonts: {type: 'JetBrains Mono', hand: 'Fredoka', stamp: 'Fredoka'},
  boil: 0,
  rules: null,
  palette: {
    bg: '#1b1f4b', bg2: '#2a2f6e', grid: '#323882',
    line: '#0d1030', ink: '#0d1030', text: '#fff8e7', muted: '#aab0e0',
    yellow: '#ffcc33', gold: '#f5a623', orange: '#ff8a3d', coral: '#ff6b5b', red: '#ef3e4a', pink: '#ff7eb6',
    violet: '#9b6bff', blue: '#3d8bff', sky: '#5ad1ff', teal: '#2ec4b6', mint: '#7be3a6', lime: '#b8e04a',
    steel: '#c9d2e3', steel2: '#8d99b3', dark: '#3a3f6e', white: '#ffffff', cream: '#fff3d6',
    hot: '#ff4d2e', cold: '#3db8ff', steam: '#e8f1ff', food: '#e8763a',
  },
};

export const THEMES: Record<string, Theme> = {ledger: LEDGER, museum: MUSEUM, pop: POP};

export const resolveTheme = (t?: Partial<Theme> | null): Theme => {
  const base = THEMES[t?.name ?? 'ledger'] ?? LEDGER;
  return {
    ...base,
    ...(t ?? {}),
    fonts: {...base.fonts, ...(t?.fonts ?? {})},
    palette: {...(base.palette ?? {}), ...(t?.palette ?? {})},
    rules: t && 'rules' in t ? (t.rules ?? null) : base.rules,
  } as Theme;
};
