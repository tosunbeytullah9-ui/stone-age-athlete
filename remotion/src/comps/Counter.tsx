// One big number that counts up, underlined in red pen, with a handwritten label.
import React from 'react';
import {BaseProps, Page, usePageScene} from '../lib/scene';
import {Draw, ease, fit, handLine, measure, Write} from '../lib/ink';

export type CounterProps = BaseProps & {
  value: number;
  from?: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  label?: string | null; // under the number
  note?: string | null; // smaller line, appears at beat 2 (label at beat 1) when the scene has those shots
  duration?: number; // seconds of counting (default 1.3)
  thousands?: boolean; // 5604 → 5,604 (default true)
};

const format = (v: number, d: number, sep: boolean) => {
  const s = v.toFixed(d);
  if (!sep) return s;
  const [a, b] = s.split('.');
  return a.replace(/\B(?=(\d{3})+(?!\d))/g, ',') + (b ? `.${b}` : '');
};

export const Counter: React.FC<CounterProps> = (p) => {
  const sc = usePageScene(p);
  const {W, H, u, fps, theme, beat, frame, vertical} = sc;
  const typeF = theme.fonts.type;
  const t0 = beat(0) + 3;
  const dur = Math.round((p.duration ?? 1.3) * fps);
  const g = ease(frame, t0, t0 + dur);
  const d = p.decimals ?? 0;
  const from = p.from ?? 0;
  const finalTxt = `${p.prefix ?? ''}${format(p.value, d, p.thousands !== false)}${p.suffix ?? ''}`;
  const txt = `${p.prefix ?? ''}${format(from + (p.value - from) * g, d, p.thousands !== false)}${p.suffix ?? ''}`;
  const size = fit(finalTxt, typeF, (vertical ? 230 : 280) * u, W * 0.84, 1, 60);
  const cy = H * (vertical ? 0.42 : 0.47);
  const fw = measure(finalTxt, typeF, size);
  const nodes: React.ReactNode[] = [];
  nodes.push(
    <text key="num" x={W / 2} y={cy} textAnchor="middle" fontFamily={`'${typeF}'`} fontSize={size} fill={theme.ink} filter={`url(#${sc.boilId})`} opacity={ease(frame, t0 - 3, t0 + 2)}>
      {txt}
    </text>,
  );
  const ulY = cy + size * 0.2;
  nodes.push(<Draw key="ul" d={handLine(W / 2 - fw / 2 - 10 * u, ulY + 8 * u, W / 2 + fw / 2 + 16 * u, ulY, 'ul', 4 * u)} start={t0 + dur - 4} dur={10} width={9} color={theme.accent} />);
  const nBeats = p.beats?.length ?? 1; // the label and the note come with their own shots when there are any
  const labelAt = nBeats > 1 ? Math.max(beat(1), t0 + 6) : t0 + 6;
  const noteAt = nBeats > 2 ? beat(2) : Math.max(nBeats > 1 ? beat(1) + Math.round(fps * 0.8) : 0, t0 + dur);
  if (p.label) {
    const ls = fit(p.label, theme.fonts.hand, 80 * u, W * 0.8, 2);
    nodes.push(<Write key="lab" text={p.label} x={W / 2} y={sc.nearestRule(ulY + 120 * u)} size={ls} start={labelAt} cps={26} anchor="middle" maxW={W * 0.8} lineGap={ls * 1.2} />);
  }
  if (p.note) {
    nodes.push(
      <Write key="note" text={p.note} x={W / 2} y={sc.nearestRule(ulY + (vertical ? 340 : 230) * u)} size={56 * u} start={noteAt} cps={28} anchor="middle" maxW={W * 0.8} color={theme.muted} />,
    );
  }
  return <Page scene={sc}>{nodes}</Page>;
};
