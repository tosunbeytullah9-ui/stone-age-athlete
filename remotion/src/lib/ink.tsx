// Drawing primitives: text that is written or typed onto the page, strokes that draw themselves,
// watercolour washes and the rubber stamp. All deterministic (frame + seed), all in one SVG.
import React from 'react';
import {Easing, interpolate, random} from 'remotion';
import {useScene} from './scene';

// ------------------------------------------------------------------ text measuring and wrapping
let ctx: CanvasRenderingContext2D | null = null;
export const measure = (text: string, font: string, size: number): number => {
  if (typeof document === 'undefined') return text.length * size * 0.5;
  if (!ctx) ctx = document.createElement('canvas').getContext('2d');
  if (!ctx) return text.length * size * 0.5;
  ctx.font = `${size}px '${font}'`;
  return ctx.measureText(text).width;
};

export const wrap = (text: string, font: string, size: number, maxW: number): string[] => {
  const words = String(text).split(/\s+/).filter(Boolean);
  const lines: string[] = [];
  let cur = '';
  for (const w of words) {
    const next = cur ? `${cur} ${w}` : w;
    if (cur && measure(next, font, size) > maxW) {
      lines.push(cur);
      cur = w;
    } else cur = next;
  }
  if (cur) lines.push(cur);
  return lines.length ? lines : [''];
};

/** Largest size ≤ size at which text fits in maxW on at most maxLines lines. */
export const fit = (text: string, font: string, size: number, maxW: number, maxLines = 1, min = 18): number => {
  let s = size;
  while (s > min && wrap(text, font, s, maxW).length > maxLines) s -= 2;
  while (s > min && wrap(text, font, s, maxW).some((l) => measure(l, font, s) > maxW)) s -= 2;
  return s;
};

// ------------------------------------------------------------------ written / typed text
type TextProps = {
  text: string;
  x: number;
  y: number; // baseline of the first line
  size: number;
  start: number; // frame the pen starts
  cps?: number; // characters per second
  font?: 'hand' | 'type' | 'stamp';
  color?: string;
  maxW?: number; // wrap width (default: no wrap)
  lineGap?: number; // baseline to baseline
  anchor?: 'start' | 'middle' | 'end';
  typed?: boolean; // typewriter: whole characters, uneven ink
  letterSpacing?: number;
  opacity?: number;
  boil?: boolean;
};

/** Text that appears as it is written (smooth pen sweep) or typed (one key at a time). */
export const Write: React.FC<TextProps> = (p) => {
  const {frame, fps, theme, boilId, seed} = useScene();
  const fontName = theme.fonts[p.font ?? 'hand'];
  const typed = p.typed ?? p.font === 'type';
  const cps = p.cps ?? (typed ? 28 : 20);
  const lines = p.maxW ? wrap(p.text, fontName, p.size, p.maxW) : [p.text];
  const gap = p.lineGap ?? p.size * 1.25;
  const elapsed = Math.max(0, frame - p.start);
  let chars = (elapsed / fps) * cps;
  if (typed) chars = Math.floor(chars);
  const id = `${seed}-${Math.round(p.x)}-${Math.round(p.y)}-${p.start}`;
  const ls = p.letterSpacing ?? 0;
  const anchor = p.anchor ?? 'start';
  const out: React.ReactNode[] = [];
  let used = 0;
  lines.forEach((line, i) => {
    const n = line.length;
    const k = Math.max(0, Math.min(n, chars - used));
    used += n + 1;
    if (k <= 0) return;
    const full = measure(line, fontName, p.size) + ls * n;
    const shown = k >= n ? full + p.size : measure(line.slice(0, Math.floor(k)), fontName, p.size) + ls * Math.floor(k)
      + (k % 1) * (measure(line.charAt(Math.floor(k)) || ' ', fontName, p.size) + ls);
    const x0 = anchor === 'middle' ? p.x - full / 2 : anchor === 'end' ? p.x - full : p.x;
    const y = p.y + i * gap;
    out.push(
      <g key={i}>
        <clipPath id={`c${id}-${i}`}>
          <rect x={x0 - p.size * 0.2} y={y - p.size * 1.3} width={shown + p.size * 0.2} height={p.size * 1.8} />
        </clipPath>
        <text
          x={x0}
          y={y}
          fontFamily={`'${fontName}'`}
          fontSize={p.size}
          fill={p.color ?? theme.ink}
          letterSpacing={ls}
          clipPath={`url(#c${id}-${i})`}
        >
          {typed
            ? line.split('').map((ch, j) => (
                <tspan key={j} fillOpacity={0.78 + 0.22 * random(`${id}${i}${j}`)} dy={j === 0 ? 0 : 0}>
                  {ch}
                </tspan>
              ))
            : line}
        </text>
      </g>,
    );
  });
  return (
    <g filter={p.boil === false ? undefined : `url(#${boilId})`} opacity={p.opacity ?? 1}>
      {out}
    </g>
  );
};

/** Frames the Write above needs to finish. */
export const writeFrames = (text: string, fps: number, cps = 20) => Math.ceil((String(text).length / cps) * fps);

// ------------------------------------------------------------------ strokes
/** A slightly wobbly hand-drawn line from (x1,y1) to (x2,y2) as an SVG path. */
export const handLine = (x1: number, y1: number, x2: number, y2: number, seed: string, wobble = 4): string => {
  const n = 6;
  const pts: [number, number][] = [];
  const dx = x2 - x1;
  const dy = y2 - y1;
  const len = Math.hypot(dx, dy) || 1;
  const nx = -dy / len;
  const ny = dx / len;
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    const w = i === 0 || i === n ? 0 : (random(`${seed}${i}`) - 0.5) * 2 * wobble;
    pts.push([x1 + dx * t + nx * w, y1 + dy * t + ny * w]);
  }
  let d = `M ${pts[0][0].toFixed(1)} ${pts[0][1].toFixed(1)}`;
  for (let i = 1; i < pts.length; i++) {
    const [px, py] = pts[i - 1];
    const [cx, cy] = pts[i];
    d += ` Q ${px.toFixed(1)} ${py.toFixed(1)} ${((px + cx) / 2).toFixed(1)} ${((py + cy) / 2).toFixed(1)}`;
  }
  d += ` L ${pts[n][0].toFixed(1)} ${pts[n][1].toFixed(1)}`;
  return d;
};

/** A hand-drawn rectangle outline (four strokes that overshoot a little at the corners). */
export const handRect = (x: number, y: number, w: number, h: number, seed: string, wobble = 3): string => {
  const o = Math.min(10, Math.min(w, h) * 0.08);
  return [
    handLine(x - o, y, x + w + o * 0.6, y + 1, `${seed}t`, wobble),
    handLine(x + w, y - o * 0.5, x + w - 1, y + h + o, `${seed}r`, wobble),
    handLine(x + w + o * 0.4, y + h, x - o * 0.7, y + h - 1, `${seed}b`, wobble),
    handLine(x, y + h + o * 0.4, x + 1, y - o * 0.6, `${seed}l`, wobble),
  ].join(' ');
};

/** A path that draws itself between frames start and start+dur (pathLength trick). */
export const Draw: React.FC<{
  d: string;
  start: number;
  dur?: number;
  width?: number;
  color?: string;
  opacity?: number;
  boil?: boolean;
}> = ({d, start, dur = 12, width = 5, color, opacity = 1, boil = true}) => {
  const {frame, theme, boilId, u} = useScene();
  const p = interpolate(frame, [start, start + dur], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.inOut(Easing.quad),
  });
  if (p <= 0) return null;
  return (
    <path
      d={d}
      pathLength={1}
      strokeDasharray="1 1"
      strokeDashoffset={1 - p}
      fill="none"
      stroke={color ?? theme.ink}
      strokeWidth={width * u}
      strokeLinecap="round"
      strokeLinejoin="round"
      opacity={opacity}
      filter={boil ? `url(#${boilId})` : undefined}
    />
  );
};

// ------------------------------------------------------------------ colour
/** Watercolour wash rectangle that grows from the left (or bottom) with `p` 0..1. */
export const Wash: React.FC<{x: number; y: number; w: number; h: number; p: number; color?: string; vertical?: boolean; opacity?: number}> = ({
  x,
  y,
  w,
  h,
  p,
  color,
  vertical,
  opacity = 0.72,
}) => {
  const {theme, seed} = useScene();
  if (p <= 0) return null;
  const ww = vertical ? w : w * p;
  const hh = vertical ? h * p : h;
  const yy = vertical ? y + h - hh : y;
  return (
    <g filter={`url(#wash-${seed})`} opacity={opacity}>
      <rect x={x} y={yy} width={ww} height={hh} fill={color ?? theme.wash} rx={4} />
    </g>
  );
};

// ------------------------------------------------------------------ stamp
/** A rubber stamp that slams onto the page at frame `hit` (falls from above, lands with a squash). */
export const Stamp: React.FC<{
  word: string;
  cx: number;
  cy: number;
  size: number; // font size
  hit: number;
  rotate?: number;
  color?: string;
}> = ({word, cx, cy, size, hit, rotate = -8, color}) => {
  const {frame, theme, seed, u} = useScene();
  const t = frame - hit;
  if (t < -6) return null;
  const font = theme.fonts.stamp;
  const tw = measure(word, font, size) + size * 0.12 * word.length;
  const padX = size * 0.42;
  const padY = size * 0.3;
  const w = tw + padX * 2;
  const h = size * 1.05 + padY * 2;
  // -6..0: falling in big and blurred-light; 0..3: squash; then rest
  const scale = t < 0 ? interpolate(t, [-6, 0], [2.3, 1], {easing: Easing.in(Easing.quad)}) : t < 3 ? 1 - 0.035 * Math.sin((t / 3) * Math.PI) : 1;
  const opacity = t < 0 ? interpolate(t, [-6, 0], [0, 0.55]) : interpolate(t, [0, 2], [0.75, 0.92], {extrapolateRight: 'clamp'});
  const c = color ?? theme.accent;
  const sw = Math.max(4, size * 0.07);
  const splat = Array.from({length: 9}, (_, i) => {
    const a = random(`a${seed}${i}`) * Math.PI * 2;
    const r = (0.62 + random(`r${seed}${i}`) * 0.5) * (w / 2);
    return {x: Math.cos(a) * r, y: Math.sin(a) * r * (h / w) * 1.6, s: (2 + random(`s${seed}${i}`) * 6) * u};
  });
  return (
    <g transform={`translate(${cx} ${cy}) rotate(${rotate}) scale(${scale})`} opacity={opacity}>
      <g filter={`url(#grunge-${seed})`}>
        <rect x={-w / 2} y={-h / 2} width={w} height={h} rx={size * 0.12} fill="none" stroke={c} strokeWidth={sw} />
        <rect
          x={-w / 2 + sw * 1.8}
          y={-h / 2 + sw * 1.8}
          width={w - sw * 3.6}
          height={h - sw * 3.6}
          rx={size * 0.08}
          fill="none"
          stroke={c}
          strokeWidth={sw * 0.45}
        />
        <text
          x={0}
          y={size * 0.36}
          textAnchor="middle"
          fontFamily={`'${font}'`}
          fontSize={size}
          letterSpacing={size * 0.12}
          fill={c}
        >
          {word}
        </text>
      </g>
      {t >= 0 ? splat.map((s, i) => <circle key={i} cx={s.x} cy={s.y} r={s.s} fill={c} opacity={0.55} />) : null}
    </g>
  );
};

export const ease = (frame: number, a: number, b: number, from = 0, to = 1) =>
  interpolate(frame, [a, b], [from, to], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
