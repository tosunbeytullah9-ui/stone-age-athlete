// A line drawn across the page; dates are typed on it and notes written under them, one per beat.
import React from 'react';
import {BaseProps, Page, usePageScene} from '../lib/scene';
import {Draw, ease, fit, handLine, wrap, Write} from '../lib/ink';

export type TimelineProps = BaseProps & {
  title?: string | null;
  events: {when: string; text: string; beat?: number; highlight?: boolean}[];
};

export const Timeline: React.FC<TimelineProps> = (p) => {
  const sc = usePageScene(p);
  const {W, H, u, fps, theme, beat, frame, vertical, ruleY} = sc;
  const handF = theme.fonts.hand;
  const typeF = theme.fonts.type;
  const ev = p.events ?? [];
  const n = Math.max(1, ev.length);
  const nodes: React.ReactNode[] = [];
  const t0 = beat(0);
  const step = ruleY(1) - ruleY(0);
  if (p.title) {
    nodes.push(
      <Write key="title" text={p.title} x={sc.marginX + 60 * u} y={sc.nearestRule(H * (vertical ? 0.1 : 0.15))} size={(vertical ? 64 : 70) * u} start={t0} cps={30} maxW={W * 0.8} />,
    );
  }
  const lineDur = Math.round(fps * 0.7);
  if (!vertical) {
    const y = sc.nearestRule(H * 0.47);
    const x0 = sc.marginX + 70 * u;
    const x1 = W - 90 * u;
    nodes.push(<Draw key="line" d={handLine(x0, y, x1, y + 2 * u, 'tl', 3 * u)} start={t0} dur={lineDur} width={6} />);
    nodes.push(<Draw key="arrow" d={`${handLine(x1 - 30 * u, y - 18 * u, x1 + 4 * u, y + 1 * u, 'a1', 1)} ${handLine(x1 + 4 * u, y + 1 * u, x1 - 30 * u, y + 20 * u, 'a2', 1)}`} start={t0 + lineDur - 4} dur={6} width={6} />);
    const span = (x1 - x0 - 80 * u) / n;
    ev.forEach((e, i) => {
      const cx = x0 + span * (i + 0.5) + 20 * u;
      const st = Math.max(beat(e.beat ?? i), i === 0 ? t0 + 6 : 0);
      const col = e.highlight ? theme.accent : theme.ink;
      nodes.push(<Draw key={`tk${i}`} d={handLine(cx, y - 22 * u, cx + 1, y + 22 * u, `tk${i}`, 1)} start={st} dur={6} width={6} color={col} />);
      const ws = fit(e.when, typeF, 66 * u, span * 0.95, 1, 30);
      nodes.push(<Write key={`w${i}`} text={e.when} x={cx} y={y - 52 * u} size={ws} start={st + 3} font="type" cps={24} anchor="middle" color={col} />);
      const ts = fit(e.text, handF, 56 * u, span * 0.92, 3, 26);
      const gap = Math.max(ts * 1.15, step);
      const lines = wrap(e.text, handF, ts, span * 0.92);
      nodes.push(<Write key={`t${i}`} text={e.text} x={cx} y={sc.nearestRule(y + 80 * u)} size={ts} start={st + 10} cps={26} anchor="middle" maxW={span * 0.92} lineGap={gap} color={col} />);
      if (e.highlight) {
        const r = Math.max(span * 0.46, 120 * u);
        const o = ease(frame, st + 16 + Math.round((e.text.length / 26) * fps), st + 30 + Math.round((e.text.length / 26) * fps));
        if (o > 0) {
          const topY = y - 52 * u - ws * 0.8;
          const botY = sc.nearestRule(y + 80 * u) + (lines.length - 1) * gap + ts * 0.35;
          nodes.push(
            <ellipse key={`hl${i}`} cx={cx} cy={(topY + botY) / 2} rx={r} ry={(botY - topY) / 2 + 40 * u} fill="none" stroke={theme.accent} strokeWidth={5 * u} pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - o} transform={`rotate(-4 ${cx} ${(topY + botY) / 2})`} filter={`url(#${sc.boilId})`} />,
          );
        }
      }
    });
  } else {
    const x = W * 0.2;
    const y0 = H * 0.2;
    const y1 = H * 0.9;
    nodes.push(<Draw key="line" d={handLine(x, y0, x + 2 * u, y1, 'tl', 3 * u)} start={t0} dur={lineDur} width={6} />);
    const span = (y1 - y0) / n;
    ev.forEach((e, i) => {
      const cy = y0 + span * (i + 0.35);
      const st = Math.max(beat(e.beat ?? i), i === 0 ? t0 + 6 : 0);
      const col = e.highlight ? theme.accent : theme.ink;
      nodes.push(<Draw key={`tk${i}`} d={handLine(x - 24 * u, cy, x + 24 * u, cy + 1, `tk${i}`, 1)} start={st} dur={6} width={6} color={col} />);
      nodes.push(<Write key={`w${i}`} text={e.when} x={x + 50 * u} y={cy + 18 * u} size={64 * u} start={st + 3} font="type" cps={24} color={col} />);
      const ts = fit(e.text, handF, 52 * u, W - x - 110 * u, 3, 26);
      nodes.push(<Write key={`t${i}`} text={e.text} x={x + 50 * u} y={cy + 100 * u} size={ts} start={st + 10} cps={26} maxW={W - x - 110 * u} lineGap={ts * 1.2} color={col} />);
    });
  }
  return <Page scene={sc}>{nodes}</Page>;
};
