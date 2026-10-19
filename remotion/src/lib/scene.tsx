// Shared scene plumbing: size, theme, beats (when each narration shot starts), the paper page,
// the hand-drawn "boil" filter and the impact shake.
import React, {createContext, useContext, useMemo} from 'react';
import {AbsoluteFill, Img, random, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {resolveTheme, Theme} from './theme';

export type BaseProps = {
  frames?: number;
  fps?: number;
  width?: number;
  height?: number;
  beats?: number[]; // frame (from the scene start) at which each shot of the scene starts; beats[0] = 0
  theme?: Partial<Theme> | null;
  seed?: number;
  hold?: number; // frames at the end that only hold the final state (cross-fade tail)
};

export type Scene = {
  frame: number;
  fps: number;
  W: number;
  H: number;
  u: number; // 1 unit = 1 px at 1080 p
  vertical: boolean;
  theme: Theme;
  seed: number;
  total: number; // frames that carry narration (without the tail)
  beat: (i: number, fallbackGap?: number) => number;
  ruleY: (k: number) => number; // y of ruled line k (paper px → screen px), or an even grid without rules
  nearestRule: (y: number) => number;
  marginX: number;
  boilId: string;
};

const Ctx = createContext<Scene | null>(null);
export const useScene = () => {
  const s = useContext(Ctx);
  if (!s) throw new Error('useScene outside <Page>');
  return s;
};

export const usePageScene = (p: BaseProps): Scene => {
  const frame = useCurrentFrame();
  const {fps, width: W, height: H, durationInFrames} = useVideoConfig();
  const theme = useMemo(() => resolveTheme(p.theme), [p.theme]);
  const seed = p.seed ?? 1;
  const total = Math.max(1, durationInFrames - (p.hold ?? 0));
  const beats = p.beats && p.beats.length ? p.beats : [0];
  const beat = (i: number, gap = Math.round(fps * 0.6)) =>
    i < beats.length ? beats[i] : beats[beats.length - 1] + (i - beats.length + 1) * gap;
  // the paper picture is 1920×1080, drawn "cover"
  const s = Math.max(W / 1920, H / 1080);
  const ox = (W - 1920 * s) / 2;
  const oy = (H - 1080 * s) / 2;
  const r = theme.rules;
  const step = r ? r.step * s : 46 * Math.min(W, H) / 1080;
  const first = r ? oy + r.first * s : step;
  const ruleY = (k: number) => first + k * step;
  const nearestRule = (y: number) => ruleY(Math.round((y - first) / step));
  return {
    frame,
    fps,
    W,
    H,
    u: Math.min(W, H) / 1080,
    vertical: H > W,
    theme,
    seed,
    total,
    beat,
    ruleY,
    nearestRule,
    marginX: r && r.margin != null && ox + r.margin * s > 0.03 * W && ox + r.margin * s < 0.25 * W ? ox + r.margin * s : 0.06 * W,
    boilId: `boil-${seed}`,
  };
};

/** Turbulence-displacement that changes every 3 frames: the line "boil" of hand-drawn animation. */
export const BoilFilter: React.FC<{id: string; amount: number; frame: number; seed: number}> = ({id, amount, frame, seed}) => {
  const step = Math.floor(frame / 3);
  return (
    <filter id={id} x="-5%" y="-5%" width="110%" height="110%">
      <feTurbulence type="fractalNoise" baseFrequency="0.022" numOctaves={2} seed={(seed * 31 + step * 7) % 997} result="n" />
      <feDisplacementMap in="SourceGraphic" in2="n" scale={amount} xChannelSelector="R" yChannelSelector="G" />
    </filter>
  );
};

/** Ink speckle for rubber stamps: the impression is never perfectly solid. */
export const GrungeFilter: React.FC<{id: string; seed: number}> = ({id, seed}) => (
  <filter id={id} x="-10%" y="-10%" width="120%" height="120%">
    <feTurbulence type="fractalNoise" baseFrequency="0.75" numOctaves={2} seed={seed} result="n" />
    <feColorMatrix in="n" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  -2.6 0 0 0 2.15" result="m" />
    <feComposite in="SourceGraphic" in2="m" operator="in" result="g" />
    <feTurbulence type="fractalNoise" baseFrequency="0.018" numOctaves={1} seed={seed + 5} result="n2" />
    <feDisplacementMap in="g" in2="n2" scale={6} xChannelSelector="R" yChannelSelector="G" />
  </filter>
);

/** Watercolour wash: soft, uneven pigment with a darker rim. */
export const WashFilter: React.FC<{id: string; seed: number}> = ({id, seed}) => (
  <filter id={id} x="-8%" y="-8%" width="116%" height="116%">
    <feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves={3} seed={seed} result="n" />
    <feDisplacementMap in="SourceGraphic" in2="n" scale={9} xChannelSelector="R" yChannelSelector="G" result="d" />
    <feTurbulence type="fractalNoise" baseFrequency="0.12" numOctaves={2} seed={seed + 9} result="g" />
    <feColorMatrix in="g" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0.9 0 0 0 0.35" result="ga" />
    <feComposite in="d" in2="ga" operator="in" />
  </filter>
);

/** Page shake after a stamp hits: decaying, deterministic. */
export const shakeAt = (frame: number, hit: number, u: number, seed = 1) => {
  const t = frame - hit;
  if (t < 0 || t > 14) return {x: 0, y: 0};
  const k = Math.exp(-t / 4) * 9 * u;
  return {x: (random(`sx${seed}${t}`) - 0.5) * 2 * k, y: (random(`sy${seed}${t}`) - 0.5) * 2 * k};
};

export const Page: React.FC<{scene: Scene; shake?: {x: number; y: number}; children: React.ReactNode}> = ({scene, shake, children}) => {
  const {theme, W, H, frame, seed, boilId, u} = scene;
  const sx = shake?.x ?? 0;
  const sy = shake?.y ?? 0;
  return (
    <Ctx.Provider value={scene}>
      <AbsoluteFill style={{backgroundColor: theme.bg, overflow: 'hidden'}}>
        <AbsoluteFill style={{transform: `translate(${sx}px, ${sy}px) scale(${shake && (sx || sy) ? 1.012 : 1})`}}>
          {theme.paper ? (
            <Img src={staticFile(theme.paper)} style={{width: W, height: H, objectFit: 'cover'}} />
          ) : null}
          <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{position: 'absolute', inset: 0}}>
            <defs>
              <BoilFilter id={boilId} amount={theme.boil * u} frame={frame} seed={seed} />
              <GrungeFilter id={`grunge-${seed}`} seed={seed + 3} />
              <WashFilter id={`wash-${seed}`} seed={seed + 11} />
            </defs>
            {children}
          </svg>
        </AbsoluteFill>
      </AbsoluteFill>
    </Ctx.Provider>
  );
};
