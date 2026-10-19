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

export const THEMES: Record<string, Theme> = {ledger: LEDGER, museum: MUSEUM};

export const resolveTheme = (t?: Partial<Theme> | null): Theme => {
  const base = THEMES[t?.name ?? 'ledger'] ?? LEDGER;
  return {
    ...base,
    ...(t ?? {}),
    fonts: {...base.fonts, ...(t?.fonts ?? {})},
    rules: t && 'rules' in t ? (t.rules ?? null) : base.rules,
  } as Theme;
};
