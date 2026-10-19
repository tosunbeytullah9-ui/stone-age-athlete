// Inked bar chart: each bar's outline is drawn, a watercolour wash grows inside it and its number counts up.
// `of` turns a bar into "part of a whole" (the whole is a dashed outline, e.g. 30 % of all water).
import React from 'react';
import {BaseProps, Page, usePageScene} from '../lib/scene';
import {Draw, ease, fit, handLine, handRect, measure, Wash, Write} from '../lib/ink';

export type Bar = {label: string; value: number; display?: string; color?: string; beat?: number};

export type BarsProps = BaseProps & {
  title?: string | null;
  bars: Bar[];
  of?: number | null; // the whole (e.g. 100): draws the full length as a dashed outline
  max?: number | null; // scale (default: largest value, or `of`)
  unit?: string; // appended to counted numbers, e.g. "%", " L"
  decimals?: number;
  note?: string | null; // small handwritten line at the bottom (appears after the last bar)
};

const fmt = (v: number, d: number) => v.toFixed(d);

export const Bars: React.FC<BarsProps> = (p) => {
  const sc = usePageScene(p);
  const {W, H, u, fps, theme, beat, frame, vertical} = sc;
  const handF = theme.fonts.hand;
  const typeF = theme.fonts.type;
  const bars = p.bars ?? [];
  const n = Math.max(1, bars.length);
  const decimals = p.decimals ?? 0;
  const unit = p.unit ?? '';
  const scaleMax = p.max ?? p.of ?? Math.max(1e-9, ...bars.map((b) => b.value));
  const nodes: React.ReactNode[] = [];
  const left = sc.marginX + 60 * u;
  const right = W - (vertical ? 60 : 110) * u;
  const rowH = Math.min((H * (vertical ? 0.62 : 0.6)) / n, (vertical ? 340 : 230) * u);
  const titleH = p.title ? (vertical ? 200 : 150) * u : 0;
  let top = (H - n * rowH - titleH) / 2 + titleH + (vertical ? 0 : 20 * u);
  if (p.title) {
    const ts = fit(p.title, handF, (vertical ? 72 : 80) * u, right - left, 2);
    const ty = sc.nearestRule(top - titleH + ts);
    nodes.push(<Write key="title" text={p.title} x={left} y={ty} size={ts} start={beat(0)} cps={30} maxW={right - left} lineGap={ts * 1.2} />);
    top = Math.max(top, ty + 50 * u);
  }
  const labelSize = (vertical ? 62 : 60) * u;
  const labelW = vertical ? 0 : Math.min(W * 0.3, Math.max(...bars.map((b) => measure(b.label, handF, labelSize))) + 40 * u);
  const valueSpace = (vertical ? 0 : 260) * u;
  const trackX = left + labelW;
  const trackW = right - trackX - valueSpace;
  const barH = Math.min(rowH * (vertical ? 0.36 : 0.55), 128 * u);
  let lastEnd = 0;
  const seen: Record<number, number> = {};
  bars.forEach((b, i) => {
    const bi = b.beat ?? i;
    const start = beat(bi) + 4 + (seen[bi] ?? 0) * 14; // bars on the same shot follow each other
    seen[bi] = (seen[bi] ?? 0) + 1;
    const grow = Math.round(fps * 0.9);
    const rowTop = top + i * rowH + (vertical ? rowH * 0.12 : 0);
    const by = vertical ? rowTop + labelSize * 1.5 : rowTop + (rowH - barH) / 2;
    const frac = Math.max(0, Math.min(1, b.value / scaleMax));
    const bw = Math.max(6 * u, trackW * frac);
    const g = ease(frame, start + 6, start + 6 + grow);
    const col = b.color ?? (i % 2 ? theme.wash2 : theme.wash);
    // label
    nodes.push(
      vertical ? (
        <Write key={`lab${i}`} text={b.label} x={trackX} y={rowTop + labelSize} size={labelSize} start={start} cps={34} />
      ) : (
        <Write key={`lab${i}`} text={b.label} x={trackX - 30 * u} y={by + barH / 2 + labelSize * 0.32} size={labelSize} start={start} cps={34} anchor="end" />
      ),
    );
    // the whole (dashed) when the bar is a part of something
    if (p.of) {
      nodes.push(
        <g key={`of${i}`} opacity={ease(frame, start, start + 8) * 0.55}>
          <rect x={trackX} y={by} width={trackW} height={barH} fill="none" stroke={theme.muted} strokeWidth={3 * u} strokeDasharray={`${14 * u} ${10 * u}`} rx={4} />
        </g>,
      );
    }
    nodes.push(<Wash key={`w${i}`} x={trackX} y={by} w={bw} h={barH} p={g} color={col} />);
    nodes.push(<Draw key={`o${i}`} d={handRect(trackX, by, bw, barH, `b${i}`, 2.5 * u)} start={start + 4} dur={grow + 4} width={4.5} />);
    // value: counts while the bar grows, then the display text (if any) is written
    const vx = vertical ? trackX + bw + 26 * u : trackX + bw + 28 * u;
    const vSize = (vertical ? 72 : 84) * u;
    const vy = by + barH / 2 + vSize * 0.34;
    const done = start + 6 + grow;
    if (frame >= start + 6) {
      const txt = b.display && frame >= done ? b.display : `${fmt(b.value * g, decimals)}${unit}`;
      const inside = vertical && vx + measure(txt, typeF, vSize) > W - 30 * u;
      nodes.push(
        <text
          key={`v${i}`}
          x={inside ? trackX + bw - 24 * u : vx}
          y={vertical ? by + barH + vSize * 1.05 : vy}
          textAnchor={inside ? 'end' : 'start'}
          fontFamily={`'${typeF}'`}
          fontSize={vSize}
          fill={theme.ink}
          filter={`url(#${sc.boilId})`}
        >
          {txt}
        </text>,
      );
    }
    lastEnd = Math.max(lastEnd, done);
  });
  // baseline axis
  if (!vertical) {
    nodes.push(<Draw key="axis" d={handLine(trackX - 6 * u, top - 10 * u, trackX - 2 * u, top + n * rowH, 'ax', 2 * u)} start={beat(0)} dur={14} width={4} />);
  }
  if (p.note) {
    nodes.push(
      <Write key="note" text={p.note} x={left} y={sc.nearestRule(H * (vertical ? 0.88 : 0.93))} size={48 * u} start={lastEnd + 6} cps={30} color={theme.muted} maxW={right - left} />,
    );
  }
  return <Page scene={sc}>{nodes}</Page>;
};
