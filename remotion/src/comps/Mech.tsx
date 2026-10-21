// `mech`: a code-drawn, animated vector scene. Every part is declared in the storyboard (shapes, gears, springs,
// arrows, waves, gauges, particles, labels, formulas) and every movement is tied to the narration: a key starts on
// a beat (a shot of the scene), on a spoken word ("@valve", resolved by the pipeline from the word timing) or at a
// time. Drawn on a 1920×1080 design canvas; the pipeline fits it to the output size. Docs: docs/REMOTION.md → mech.
import React from 'react';
import {Easing, interpolate, interpolateColors, random} from 'remotion';
import {BaseProps, Page, Scene, usePageScene} from '../lib/scene';
import {measure, wrap} from '../lib/ink';

// ------------------------------------------------------------------ types
export type Cue = number | string | {f?: number; beat?: number; t?: number} | null | undefined;

type Key = {at: Cue; dur?: number; ease?: string} & Record<string, unknown>;

type In = Cue | {at: Cue; fx?: 'pop' | 'fade' | 'draw' | 'grow' | 'slide' | 'type' | 'none'; dur?: number; from?: [number, number]};

export type Item = {
  id?: string;
  kind: string;
  x?: number;
  y?: number;
  rotate?: number;
  scale?: number;
  sx?: number;
  sy?: number;
  opacity?: number;
  pivot?: [number, number];
  fill?: string;
  stroke?: string;
  sw?: number;
  dash?: number[];
  glow?: string;
  in?: In;
  out?: Cue;
  keys?: Key[];
  spin?: {speed: number; from?: Cue; to?: Cue};
  bob?: {amp: number; period?: number};
  pulse?: {amount: number; period?: number; from?: Cue; to?: Cue};
  shake?: {at: Cue; amount?: number};
  items?: Item[];
  clip?: [number, number, number, number]; // x, y, w, h in local coords (groups)
  def?: string;
  [k: string]: unknown;
};

export type MechProps = BaseProps & {
  items?: Item[];
  defs?: Record<string, Item>;
  cues?: Record<string, number>; // "@word" / "@word#2" → frame from the scene start (filled by the pipeline)
  bg?: string | {color?: string; color2?: string; grid?: boolean} | null;
  camera?: {at: Cue; x?: number; y?: number; zoom?: number; dur?: number; ease?: string}[];
  drift?: number; // slow push-in over the scene (default 0.025; 0 = off)
};

// ------------------------------------------------------------------ helpers
const DW = 1920;
const DH = 1080;

const EASE: Record<string, (t: number) => number> = {
  inOut: Easing.inOut(Easing.cubic),
  out: Easing.out(Easing.cubic),
  in: Easing.in(Easing.cubic),
  linear: (t) => t,
  back: Easing.out(Easing.back(1.7)),
  bounce: Easing.bounce,
  elastic: (t) => (t <= 0 ? 0 : t >= 1 ? 1 : 1 - Math.exp(-6 * t) * Math.cos(11 * t)),
};

const CUE_RE = /^\s*(@[^+\-]+?|b\d+|t\d+(?:\.\d+)?)\s*([+-]\s*\d+(?:\.\d+)?)?\s*$/;

/** Frame (from the scene start) of a cue. */
export const cueFrame = (c: Cue, sc: Scene, cues?: Record<string, number>): number => {
  if (c === null || c === undefined) return 0;
  if (typeof c === 'number') return sc.beat(c);
  if (typeof c === 'object') {
    if (typeof c.f === 'number') return c.f;
    if (typeof c.t === 'number') return Math.round(c.t * sc.fps);
    if (typeof c.beat === 'number') return sc.beat(c.beat);
    return 0;
  }
  const m = CUE_RE.exec(String(c));
  if (!m) return 0;
  const head = m[1].trim();
  const off = m[2] ? Math.round(parseFloat(m[2].replace(/\s/g, '')) * sc.fps) : 0;
  let base = 0;
  if (head.startsWith('@')) base = cues?.[head] ?? cues?.[head.toLowerCase()] ?? 0;
  else if (head.startsWith('b')) base = sc.beat(parseInt(head.slice(1), 10));
  else base = Math.round(parseFloat(head.slice(1)) * sc.fps);
  return Math.max(0, base + off);
};

const isNum = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);
const isColorKey = (k: string) => k === 'fill' || k === 'stroke' || k === 'color' || k === 'bgc';

type Ctx = {sc: Scene; cues?: Record<string, number>; pal: Record<string, string>; defs: Record<string, Item>};

const col = (c: unknown, pal: Record<string, string>, fallback: string): string => {
  if (typeof c !== 'string' || !c) return fallback;
  if (c === 'none') return 'none';
  return pal[c] ?? c;
};

/** Value of a property at this frame: the base value, then every key in time order eases it to its target. */
const prop = (it: Item, name: string, base: unknown, cx: Ctx): unknown => {
  const keys = (it.keys ?? []).filter((k) => name in k);
  if (!keys.length) return base;
  const sorted = keys
    .map((k) => ({k, s: cueFrame(k.at, cx.sc, cx.cues)}))
    .sort((a, b) => a.s - b.s);
  let v = base;
  for (const {k, s} of sorted) {
    if (cx.sc.frame <= s) break;
    const d = Math.max(1, Math.round((isNum(k.dur) ? k.dur : 0.6) * cx.sc.fps));
    const e = EASE[String(k.ease ?? 'inOut')] ?? EASE.inOut;
    const p = e(Math.min(1, (cx.sc.frame - s) / d));
    const target = k[name];
    if (isColorKey(name)) {
      const a = col(v, cx.pal, '#000000');
      const b = col(target, cx.pal, a);
      v = a === 'none' || b === 'none' ? (p < 0.5 ? a : b) : interpolateColors(p, [0, 1], [a, b]);
    } else if (isNum(v) && isNum(target)) {
      v = v + (target - v) * p;
    } else if (Array.isArray(v) && Array.isArray(target)) {
      v = (v as number[]).map((x, i) => (isNum(x) && isNum(target[i]) ? x + ((target[i] as number) - x) * p : x));
    } else if (p >= 0.5) {
      v = target;
    }
  }
  return v;
};

const num = (it: Item, name: string, dflt: number, cx: Ctx): number => {
  const v = prop(it, name, isNum(it[name]) ? it[name] : dflt, cx);
  return isNum(v) ? v : dflt;
};

const inSpec = (it: Item) => {
  const v = it.in;
  if (v === undefined) return null;
  if (v !== null && typeof v === 'object' && 'at' in (v as object)) return v as {at: Cue; fx?: string; dur?: number; from?: [number, number]};
  return {at: v as Cue, fx: undefined as string | undefined, dur: undefined as number | undefined, from: undefined};
};

const defaultFx = (kind: string) =>
  kind === 'arrow' || kind === 'line' || kind === 'path' || kind === 'curve' ? 'draw' : kind === 'text' || kind === 'formula' ? 'type' : 'pop';

// ------------------------------------------------------------------ shapes
const gearPath = (r: number, teeth: number, depth: number, hole: number) => {
  const n = Math.max(6, Math.round(teeth));
  const ro = r;
  const ri = r - depth;
  let d = '';
  for (let i = 0; i < n; i++) {
    const a0 = (i / n) * Math.PI * 2;
    const a = (k: number) => a0 + (k / n) * Math.PI * 2;
    const pts: [number, number][] = [
      [Math.cos(a(0)) * ri, Math.sin(a(0)) * ri],
      [Math.cos(a(0.12)) * ro, Math.sin(a(0.12)) * ro],
      [Math.cos(a(0.42)) * ro, Math.sin(a(0.42)) * ro],
      [Math.cos(a(0.54)) * ri, Math.sin(a(0.54)) * ri],
    ];
    pts.forEach(([x, y], j) => (d += `${i === 0 && j === 0 ? 'M' : 'L'}${x.toFixed(1)} ${y.toFixed(1)} `));
    d += `A ${ri} ${ri} 0 0 1 ${(Math.cos(a(1)) * ri).toFixed(1)} ${(Math.sin(a(1)) * ri).toFixed(1)} `;
  }
  d += 'Z';
  if (hole > 0) d += ` M ${hole} 0 A ${hole} ${hole} 0 1 0 ${-hole} 0 A ${hole} ${hole} 0 1 0 ${hole} 0 Z`;
  return d;
};

const springPath = (dx: number, dy: number, coils: number, width: number) => {
  const len = Math.hypot(dx, dy) || 1;
  const ux = dx / len;
  const uy = dy / len;
  const nx = -uy;
  const ny = ux;
  const n = Math.max(2, Math.round(coils)) * 2;
  const lead = Math.min(18, len * 0.08);
  let d = `M0 0 L${(ux * lead).toFixed(1)} ${(uy * lead).toFixed(1)} `;
  for (let i = 1; i < n; i++) {
    const t = lead + ((len - 2 * lead) * i) / n;
    const s = i % 2 ? 1 : -1;
    d += `L${(ux * t + nx * s * width / 2).toFixed(1)} ${(uy * t + ny * s * width / 2).toFixed(1)} `;
  }
  d += `L${(ux * (len - lead)).toFixed(1)} ${(uy * (len - lead)).toFixed(1)} L${dx.toFixed(1)} ${dy.toFixed(1)}`;
  return d;
};

const arrowPath = (dx: number, dy: number, bend: number) => {
  if (!bend) return `M0 0 L${dx} ${dy}`;
  const mx = dx / 2;
  const my = dy / 2;
  const len = Math.hypot(dx, dy) || 1;
  const cx = mx - (dy / len) * bend;
  const cy = my + (dx / len) * bend;
  return `M0 0 Q${cx.toFixed(1)} ${cy.toFixed(1)} ${dx} ${dy}`;
};

const ShapeDrawn: React.FC<{d: string; p: number; stroke: string; sw: number; fill?: string; dash?: number[]; cap?: 'round' | 'butt'}> = ({
  d,
  p,
  stroke,
  sw,
  fill,
  dash,
  cap = 'round',
}) =>
  p >= 1 || dash ? (
    <path d={d} fill={fill ?? 'none'} stroke={stroke} strokeWidth={sw} strokeLinecap={cap} strokeLinejoin="round" strokeDasharray={dash?.join(' ')} />
  ) : (
    <path d={d} fill="none" stroke={stroke} strokeWidth={sw} strokeLinecap={cap} strokeLinejoin="round" pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - p} />
  );

// ------------------------------------------------------------------ one item
const Node: React.FC<{it: Item; cx: Ctx; depth?: number}> = ({it: raw, cx, depth = 0}) => {
  const it: Item = raw.kind === 'use' && raw.def && cx.defs[raw.def] ? {...cx.defs[raw.def], ...raw, kind: cx.defs[raw.def].kind} : raw;
  const {sc, pal} = cx;
  const {frame, fps} = sc;
  // appearance
  const spec = inSpec(it);
  const start = spec ? cueFrame(spec.at, sc, cx.cues) : 0;
  const fx = spec ? spec.fx ?? defaultFx(it.kind) : 'none';
  const inDur = Math.max(1, Math.round((spec?.dur ?? (fx === 'draw' ? 0.7 : fx === 'type' ? 0.9 : 0.4)) * fps));
  if (spec && frame < start) return null;
  const pIn = spec ? Math.min(1, (frame - start) / inDur) : 1;
  const outAt = it.out !== undefined ? cueFrame(it.out, sc, cx.cues) : Infinity;
  if (frame >= outAt + Math.round(0.3 * fps)) return null;
  const pOut = frame >= outAt ? 1 - (frame - outAt) / Math.round(0.3 * fps) : 1;

  // transform
  let x = num(it, 'x', 0, cx);
  let y = num(it, 'y', 0, cx);
  let rot = num(it, 'rotate', 0, cx);
  let s = num(it, 'scale', 1, cx);
  const sx0 = num(it, 'sx', 1, cx);
  const sy0 = num(it, 'sy', 1, cx);
  let op = num(it, 'opacity', 1, cx) * pOut;
  if (it.spin) {
    const a = cueFrame(it.spin.from ?? 0, sc, cx.cues);
    const b = it.spin.to !== undefined ? cueFrame(it.spin.to, sc, cx.cues) : Infinity;
    rot += (it.spin.speed * (Math.min(frame, b) - a)) / fps * (frame > a ? 1 : 0);
  }
  if (it.bob) y += Math.sin((frame / fps / (it.bob.period ?? 2)) * Math.PI * 2) * it.bob.amp;
  if (it.pulse) {
    const a = cueFrame(it.pulse.from ?? 0, sc, cx.cues);
    const b = it.pulse.to !== undefined ? cueFrame(it.pulse.to, sc, cx.cues) : Infinity;
    if (frame >= a && frame < b) s *= 1 + it.pulse.amount * (0.5 - 0.5 * Math.cos(((frame - a) / fps / (it.pulse.period ?? 1)) * Math.PI * 2));
  }
  if (it.shake) {
    const t = frame - cueFrame(it.shake.at, sc, cx.cues);
    if (t >= 0 && t < 14) {
      const k = Math.exp(-t / 4) * (it.shake.amount ?? 8);
      x += (random(`shx${it.id}${t}`) - 0.5) * 2 * k;
      y += (random(`shy${it.id}${t}`) - 0.5) * 2 * k;
    }
  }
  let sx = sx0;
  let sy = sy0;
  if (fx === 'pop' && pIn < 1) s *= EASE.back(pIn);
  if (fx === 'grow' && pIn < 1) sy *= EASE.out(pIn);
  if (fx === 'fade' || fx === 'pop' || fx === 'grow' || fx === 'slide') op *= Math.min(1, pIn * 2.5);
  if (fx === 'slide' && pIn < 1) {
    const from = spec?.from ?? [0, 40];
    x += from[0] * (1 - EASE.out(pIn));
    y += from[1] * (1 - EASE.out(pIn));
  }
  if (op <= 0.001) return null;
  const [px, py] = it.pivot ?? [0, 0];

  const fill = col(prop(it, 'fill', it.fill ?? (it.kind === 'text' || it.kind === 'formula' || it.kind === 'counter' ? 'text' : 'none'), cx), pal, 'none');
  const stroke = col(prop(it, 'stroke', it.stroke ?? 'line', cx), pal, pal.line ?? '#0d1030');
  const sw = num(it, 'sw', it.kind === 'arrow' ? 10 : 6, cx);
  const draw = fx === 'draw' ? EASE.inOut(pIn) : 1;
  const body = renderBody(it, cx, {fill, stroke, sw, draw, pIn, fx, start, depth});
  const tr = `translate(${x.toFixed(2)} ${y.toFixed(2)}) rotate(${rot.toFixed(3)} ${px} ${py}) scale(${(s * sx).toFixed(4)} ${(s * sy).toFixed(4)})`;
  const glow = it.glow ? col(it.glow, pal, '#ffcc33') : null;
  return (
    <g transform={tr} opacity={op} style={glow ? {filter: `drop-shadow(0 0 14px ${glow}) drop-shadow(0 0 4px ${glow})`} : undefined}>
      {body}
    </g>
  );
};

type Look = {fill: string; stroke: string; sw: number; draw: number; pIn: number; fx: string; start: number; depth: number};

const renderBody = (it: Item, cx: Ctx, L: Look): React.ReactNode => {
  const {sc, pal} = cx;
  const {frame, fps} = sc;
  const {fill, stroke, sw} = L;
  const dash = Array.isArray(it.dash) ? (it.dash as number[]) : undefined;
  const text = pal.text ?? '#fff8e7';
  switch (it.kind) {
    case 'group':
    case 'use': {
      const kids = (it.items ?? []).map((c, i) => <Node key={c.id ?? i} it={c} cx={cx} depth={L.depth + 1} />);
      if (it.clip) {
        const [cxx, cy, cw, ch] = it.clip;
        const id = `clip-${it.id ?? 'g'}-${L.depth}-${cxx}-${cy}`;
        return (
          <>
            <clipPath id={id}>
              <rect x={cxx} y={cy} width={cw} height={ch} />
            </clipPath>
            <g clipPath={`url(#${id})`}>{kids}</g>
          </>
        );
      }
      return <>{kids}</>;
    }
    case 'rect': {
      const w = num(it, 'w', 100, cx);
      const h = num(it, 'h', 100, cx);
      const ax = isNum(it.ax) ? it.ax : 0.5;
      const ay = isNum(it.ay) ? it.ay : 0.5;
      return <rect x={-w * ax} y={-h * ay} width={w} height={h} rx={num(it, 'r', 0, cx)} fill={fill} stroke={stroke} strokeWidth={sw} strokeDasharray={dash?.join(' ')} />;
    }
    case 'circle':
      return <circle r={num(it, 'r', 50, cx)} fill={fill} stroke={stroke} strokeWidth={sw} strokeDasharray={dash?.join(' ')} />;
    case 'ellipse':
      return <ellipse rx={num(it, 'rx', 80, cx)} ry={num(it, 'ry', 40, cx)} fill={fill} stroke={stroke} strokeWidth={sw} strokeDasharray={dash?.join(' ')} />;
    case 'path':
    case 'poly': {
      let d = String(it.d ?? '');
      if (it.kind === 'poly' && Array.isArray(it.points)) {
        const pts = it.points as [number, number][];
        d = pts.map(([a, b], i) => `${i ? 'L' : 'M'}${a} ${b}`).join(' ') + (it.closed === false ? '' : ' Z');
      }
      if (L.draw < 1 && fill === 'none') return <ShapeDrawn d={d} p={L.draw} stroke={stroke} sw={sw} dash={dash} />;
      return <path d={d} fill={fill} stroke={stroke} strokeWidth={sw} strokeLinejoin="round" strokeLinecap="round" fillRule="evenodd" strokeDasharray={dash?.join(' ')} opacity={L.draw < 1 ? L.draw : 1} />;
    }
    case 'line': {
      const to = (prop(it, 'to', it.to ?? [100, 0], cx) as [number, number]) ?? [100, 0];
      return <ShapeDrawn d={`M0 0 L${to[0]} ${to[1]}`} p={L.draw} stroke={stroke} sw={sw} dash={dash} />;
    }
    case 'arrow': {
      const to = (prop(it, 'to', it.to ?? [200, 0], cx) as [number, number]) ?? [200, 0];
      const c = col(prop(it, 'color', it.color ?? 'yellow', cx), pal, '#ffcc33');
      const bend = num(it, 'bend', 0, cx);
      const len = Math.hypot(to[0], to[1]) || 1;
      const head = num(it, 'head', Math.max(26, sw * 2.6), cx);
      // direction of the tip
      const mid = bend ? [to[0] / 2 - (to[1] / len) * bend, to[1] / 2 + (to[0] / len) * bend] : [0, 0];
      const tdx = to[0] - mid[0];
      const tdy = to[1] - mid[1];
      const tl = Math.hypot(tdx, tdy) || 1;
      const ux = tdx / tl;
      const uy = tdy / tl;
      const bx = to[0] - ux * head * 0.9;
      const by = to[1] - uy * head * 0.9;
      const shaft = bend ? arrowPath(bx, by, bend * (Math.hypot(bx, by) / len)) : `M0 0 L${bx.toFixed(1)} ${by.toFixed(1)}`;
      const tip = `M${to[0]} ${to[1]} L${(bx - uy * head * 0.62).toFixed(1)} ${(by + ux * head * 0.62).toFixed(1)} L${(bx + uy * head * 0.62).toFixed(1)} ${(by - ux * head * 0.62).toFixed(1)} Z`;
      const outline = pal.line ?? '#0d1030';
      return (
        <>
          <ShapeDrawn d={shaft} p={L.draw} stroke={outline} sw={sw + 8} cap="round" />
          <ShapeDrawn d={shaft} p={L.draw} stroke={c} sw={sw} cap="round" />
          {L.draw >= 0.92 ? <path d={tip} fill={c} stroke={outline} strokeWidth={4} strokeLinejoin="round" /> : null}
        </>
      );
    }
    case 'spring': {
      const to = (prop(it, 'to', it.to ?? [0, 160], cx) as [number, number]) ?? [0, 160];
      const k = num(it, 'value', 1, cx); // length factor: 1 = rest, 0.5 = squeezed to half
      return <path d={springPath(to[0] * k, to[1] * k, num(it, 'coils', 7, cx), num(it, 'width', 46, cx))} fill="none" stroke={col(it.color ?? 'steel', pal, '#c9d2e3')} strokeWidth={sw} strokeLinejoin="round" strokeLinecap="round" />;
    }
    case 'gear':
      return <path d={gearPath(num(it, 'r', 80, cx), num(it, 'teeth', 14, cx), num(it, 'depth', 16, cx), num(it, 'hole', 14, cx))} fill={fill === 'none' ? col('steel', pal, '#c9d2e3') : fill} stroke={stroke} strokeWidth={sw} fillRule="evenodd" strokeLinejoin="round" />;
    case 'wave': {
      const w = num(it, 'w', 800, cx);
      const amp = num(it, 'amp', 60, cx) * num(it, 'value', 1, cx);
      const lam = num(it, 'length', 240, cx);
      const f = num(it, 'speed', 0.8, cx);
      const t = (frame - L.start) / fps;
      const standing = Boolean(it.standing);
      const pts: string[] = [];
      const n = Math.max(24, Math.round(w / 6));
      const reach = L.draw * w;
      for (let i = 0; i <= n; i++) {
        const xx = (i / n) * w;
        if (xx > reach) break;
        const k = (2 * Math.PI * xx) / lam;
        const yy = standing ? amp * Math.sin(k) * Math.cos(2 * Math.PI * f * t) : amp * Math.sin(k - 2 * Math.PI * f * t);
        pts.push(`${i ? 'L' : 'M'}${xx.toFixed(1)} ${yy.toFixed(1)}`);
      }
      const c = col(prop(it, 'color', it.color ?? 'sky', cx), pal, '#5ad1ff');
      return (
        <>
          <path d={pts.join(' ')} fill="none" stroke={pal.line ?? '#0d1030'} strokeWidth={sw + 8} strokeLinecap="round" strokeLinejoin="round" />
          <path d={pts.join(' ')} fill="none" stroke={c} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round" />
        </>
      );
    }
    case 'gauge': {
      const r = num(it, 'r', 120, cx);
      const v = Math.max(0, Math.min(1, num(it, 'value', 0, cx)));
      const a0 = -210;
      const a1 = 30;
      const ang = (deg: number) => (deg * Math.PI) / 180;
      const arc = (from: number, to: number, rr: number) =>
        `M${(Math.cos(ang(from)) * rr).toFixed(1)} ${(Math.sin(ang(from)) * rr).toFixed(1)} A ${rr} ${rr} 0 ${to - from > 180 ? 1 : 0} 1 ${(Math.cos(ang(to)) * rr).toFixed(1)} ${(Math.sin(ang(to)) * rr).toFixed(1)}`;
      const na = a0 + (a1 - a0) * v;
      const ticks = Array.from({length: 9}, (_, i) => a0 + ((a1 - a0) * i) / 8);
      return (
        <>
          <circle r={r} fill={fill === 'none' ? col('cream', pal, '#fff3d6') : fill} stroke={stroke} strokeWidth={sw} />
          <path d={arc(a0, a0 + (a1 - a0) * 0.62, r * 0.8)} fill="none" stroke={col('teal', pal, '#2ec4b6')} strokeWidth={r * 0.12} />
          <path d={arc(a0 + (a1 - a0) * 0.62, a1, r * 0.8)} fill="none" stroke={col('coral', pal, '#ff6b5b')} strokeWidth={r * 0.12} />
          {ticks.map((t, i) => (
            <line key={i} x1={Math.cos(ang(t)) * r * 0.62} y1={Math.sin(ang(t)) * r * 0.62} x2={Math.cos(ang(t)) * r * 0.7} y2={Math.sin(ang(t)) * r * 0.7} stroke={stroke} strokeWidth={4} />
          ))}
          <line x1={0} y1={0} x2={Math.cos(ang(na)) * r * 0.74} y2={Math.sin(ang(na)) * r * 0.74} stroke={col('red', pal, '#ef3e4a')} strokeWidth={9} strokeLinecap="round" />
          <circle r={r * 0.1} fill={stroke} />
        </>
      );
    }
    case 'particles': {
      const w = num(it, 'w', 400, cx);
      const h = num(it, 'h', 300, cx);
      const n = Math.max(1, Math.round(num(it, 'count', 30, cx)));
      const size = num(it, 'size', 12, cx);
      const energy = num(it, 'value', 1, cx);
      const speed = num(it, 'speed', 120, cx);
      const mode = String(it.mode ?? 'gas');
      const c = col(prop(it, 'color', it.color ?? 'sky', cx), pal, '#5ad1ff');
      // energy is integrated over time so that a key on `value` speeds the particles up smoothly
      const tsec = (frame - L.start) / fps;
      const travel = speed * tsec * (0.5 + energy) ;
      const dots: React.ReactNode[] = [];
      for (let i = 0; i < n; i++) {
        const seed = `${it.id ?? 'p'}${i}`;
        const r0 = random(seed + 'a');
        const r1 = random(seed + 'b');
        const r2 = random(seed + 'c');
        const r3 = random(seed + 'd');
        let px = 0;
        let py = 0;
        let o = 1;
        let rr = size * (0.75 + 0.5 * r2);
        if (mode === 'gas') {
          // straight-line flight with bounces off the walls (triangle wave)
          const tri = (v: number, L2: number) => {
            const m = ((v % (2 * L2)) + 2 * L2) % (2 * L2);
            return m < L2 ? m : 2 * L2 - m;
          };
          const dirA = r3 * Math.PI * 2;
          px = tri(r0 * w + Math.cos(dirA) * travel, w);
          py = tri(r1 * h + Math.sin(dirA) * travel, h);
          px -= w / 2;
          py -= h / 2;
        } else {
          // rising: steam fades and spreads, bubbles wobble
          const life = 1.6 + r2 * 1.4;
          const phase = (tsec * (0.5 + energy * 0.5) / life + r0) % 1;
          px = (r1 - 0.5) * w + Math.sin((tsec + r3 * 7) * 2.4) * (mode === 'steam' ? 24 * phase : 10);
          py = h / 2 - phase * h;
          o = mode === 'steam' ? Math.sin(phase * Math.PI) * 0.75 : Math.min(1, (1 - phase) * 3);
          rr = mode === 'steam' ? size * (1 + phase * 2.2) : rr;
        }
        dots.push(<circle key={i} cx={px} cy={py} r={rr} fill={c} opacity={o} stroke={mode === 'gas' ? pal.line : 'none'} strokeWidth={mode === 'gas' ? 3 : 0} />);
      }
      return <>{dots}</>;
    }
    case 'text':
    case 'formula':
    case 'counter': {
      const font = it.kind === 'formula' || it.font === 'mono' ? cx.sc.theme.fonts.type : cx.sc.theme.fonts.hand;
      const size = num(it, 'size', it.kind === 'formula' ? 64 : 56, cx);
      const weight = isNum(it.weight) ? it.weight : 700;
      let str = String(it.text ?? '');
      if (it.kind === 'counter') {
        const v = num(it, 'value', 0, cx);
        const d = isNum(it.decimals) ? it.decimals : 0;
        let s = v.toFixed(d);
        if (it.thousands !== false) {
          const [a, b] = s.split('.');
          s = a.replace(/\B(?=(\d{3})+(?!\d))/g, ',') + (b ? `.${b}` : '');
        }
        str = `${it.prefix ?? ''}${s}${it.suffix ?? ''}`;
      }
      const maxW = isNum(it.maxW) ? it.maxW : 0;
      const lines = maxW ? wrap(str, font, size, maxW) : str.split('\n');
      const align = (it.align as string) ?? 'middle';
      const lh = size * 1.18;
      const total = lines.join(' ').length;
      const shown = L.fx === 'type' ? Math.floor(total * L.pIn) : total;
      const bg = it.bg ? col(it.bg, pal, '#0d1030') : null;
      const pad = isNum(it.pad) ? it.pad : size * 0.32;
      const widths = lines.map((l) => measure(l, font, size));
      const wMax = Math.max(...widths, 1);
      let x0 = align === 'middle' ? -wMax / 2 : align === 'end' ? -wMax : 0;
      let shift = 0; // keep top-level text on the canvas
      if (L.depth === 0 && isNum(it.x)) {
        const left = it.x + x0 - pad;
        const right = it.x + x0 + wMax + pad;
        if (left < 24) shift = 24 - left;
        else if (right > DW - 24) shift = DW - 24 - right;
      }
      x0 += shift;
      let used = 0;
      return (
        <>
          {bg ? (
            <rect x={x0 - pad} y={-size * 0.86 - pad * 0.7} width={wMax + pad * 2} height={lh * (lines.length - 1) + size * 1.12 + pad * 1.4} rx={(size + pad) * 0.35} fill={bg} stroke={pal.line} strokeWidth={5} />
          ) : null}
          {lines.map((l, i) => {
            const k = Math.max(0, Math.min(l.length, shown - used));
            used += l.length + 1;
            return (
              <text
                key={i}
                x={shift}
                y={i * lh}
                textAnchor={align as 'start' | 'middle' | 'end'}
                fontFamily={`'${font}'`}
                fontWeight={weight}
                fontSize={size}
                fill={fill === 'none' ? text : fill}
                stroke={it.outline === false ? undefined : pal.line}
                strokeWidth={it.outline === false ? 0 : size * 0.12}
                paintOrder="stroke"
                strokeLinejoin="round"
              >
                {L.fx === 'type' && k < l.length ? (
                  <>
                    {l.slice(0, k)}
                    <tspan fillOpacity={0}>{l.slice(k)}</tspan>
                  </>
                ) : (
                  l
                )}
              </text>
            );
          })}
        </>
      );
    }
    case 'label': {
      // a callout: dot at the origin (the thing), a leader line, a pill with the words at `to`
      const to = (prop(it, 'to', it.to ?? [160, -120], cx) as [number, number]) ?? [160, -120];
      const size = num(it, 'size', 46, cx);
      const font = cx.sc.theme.fonts.hand;
      const str = String(it.text ?? '');
      const tw = measure(str, font, size);
      const bg = col(it.bg ?? 'cream', pal, '#fff3d6');
      const fg = col(it.color ?? 'line', pal, '#0d1030');
      const pad = size * 0.38;
      const right = to[0] >= 0;
      let bx = right ? to[0] : to[0] - tw - pad * 2;
      const ax = isNum(it.x) ? it.x : 0; // keep the pill on the canvas (top-level labels)
      if (L.depth === 0) bx = Math.max(24 - ax, Math.min(DW - 24 - ax - (tw + pad * 2), bx));
      const lineP = Math.min(1, L.pIn * 1.6);
      const pillP = Math.max(0, (L.pIn - 0.45) / 0.55);
      return (
        <>
          <circle r={11} fill={bg} stroke={pal.line} strokeWidth={5} />
          <ShapeDrawn d={`M0 0 L${to[0]} ${to[1]}`} p={L.fx === 'none' ? 1 : lineP} stroke={bg} sw={6} />
          {pillP > 0 ? (
            <g opacity={Math.min(1, pillP * 2)} transform={`translate(${bx + (tw + pad * 2) / 2} ${to[1]}) scale(${EASE.back(Math.min(1, pillP))}) translate(${-(bx + (tw + pad * 2) / 2)} ${-to[1]})`}>
              <rect x={bx} y={to[1] - size * 0.72} width={tw + pad * 2} height={size * 1.44} rx={size * 0.5} fill={bg} stroke={pal.line} strokeWidth={5} />
              <text x={bx + pad} y={to[1] + size * 0.34} fontFamily={`'${font}'`} fontWeight={700} fontSize={size} fill={fg}>
                {str}
              </text>
            </g>
          ) : null}
        </>
      );
    }
    default:
      return null;
  }
};

// ------------------------------------------------------------------ the scene
export const Mech: React.FC<MechProps> = (p) => {
  const sc = usePageScene(p);
  const {frame, fps, W, H, theme} = sc;
  const pal: Record<string, string> = {...(theme.palette ?? {}), text: theme.palette?.text ?? theme.ink};
  const cx: Ctx = {sc, cues: p.cues, pal, defs: p.defs ?? {}};
  // camera: keys move the view centre and zoom; a slow push-in keeps a still scene alive
  let camX = DW / 2;
  let camY = DH / 2;
  let zoom = 1;
  for (const k of [...(p.camera ?? [])].map((c) => ({c, s: cueFrame(c.at, sc, p.cues)})).sort((a, b) => a.s - b.s)) {
    if (frame <= k.s) break;
    const d = Math.max(1, Math.round((k.c.dur ?? 1.2) * fps));
    const e = (EASE[k.c.ease ?? 'inOut'] ?? EASE.inOut)(Math.min(1, (frame - k.s) / d));
    if (isNum(k.c.x)) camX += (k.c.x - camX) * e;
    if (isNum(k.c.y)) camY += (k.c.y - camY) * e;
    if (isNum(k.c.zoom)) zoom += (k.c.zoom - zoom) * e;
  }
  const drift = p.drift ?? 0.025;
  zoom *= 1 + drift * interpolate(frame, [0, Math.max(1, sc.total)], [0, 1], {extrapolateRight: 'clamp'});
  const bgo = typeof p.bg === 'object' && p.bg ? p.bg : {};
  const bg = col(typeof p.bg === 'string' ? p.bg : bgo.color ?? 'bg', pal, theme.bg);
  const bg2 = col(bgo.color2 ?? 'bg2', pal, bg);
  const grid = bgo.grid !== false && p.bg !== 'plain';
  const gridC = pal.grid ?? '#323882';
  const lines: React.ReactNode[] = [];
  if (grid) {
    for (let gx = 0; gx <= DW; gx += 80) lines.push(<line key={`gx${gx}`} x1={gx} y1={0} x2={gx} y2={DH} stroke={gridC} strokeWidth={gx % 400 === 0 ? 2.5 : 1.2} />);
    for (let gy = 0; gy <= DH; gy += 80) lines.push(<line key={`gy${gy}`} x1={0} y1={gy} x2={DW} y2={gy} stroke={gridC} strokeWidth={gy % 400 === 0 ? 2.5 : 1.2} />);
  }
  const gid = `mechbg-${sc.seed}`;
  return (
    <Page scene={sc}>
      <rect x={0} y={0} width={W} height={H} fill={bg} />
      <svg x={0} y={0} width={W} height={H} viewBox={`0 0 ${DW} ${DH}`} preserveAspectRatio="xMidYMid meet" overflow="visible">
        <defs>
          <radialGradient id={gid} cx="50%" cy="45%" r="75%">
            <stop offset="0%" stopColor={bg2} />
            <stop offset="100%" stopColor={bg} />
          </radialGradient>
        </defs>
        <rect x={-DW} y={-DH} width={DW * 3} height={DH * 3} fill={`url(#${gid})`} />
        <g transform={`translate(${DW / 2} ${DH / 2}) scale(${zoom.toFixed(4)}) translate(${(-camX).toFixed(2)} ${(-camY).toFixed(2)})`}>
          <g opacity={0.55}>{lines}</g>
          {(p.items ?? []).map((it, i) => (
            <Node key={it.id ?? i} it={it} cx={cx} />
          ))}
        </g>
      </svg>
    </Page>
  );
};
