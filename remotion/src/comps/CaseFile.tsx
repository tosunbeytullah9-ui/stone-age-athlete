// "Case file zero zero one. Subject: …" — a ledger entry that is typed and written as it is read.
import React from 'react';
import {BaseProps, Page, usePageScene} from '../lib/scene';
import {Draw, fit, handLine, measure, Stamp, wrap, Write} from '../lib/ink';

export type CaseFileProps = BaseProps & {
  number: string; // "001"
  label?: string; // "CASE FILE"
  org?: string; // small header, e.g. "BUREAU OF HUMAN ERROR"
  fields?: {label: string; value: string; beat?: number}[];
  stamp?: string | null; // small stamp at the end, e.g. "OPEN"
};

export const CaseFile: React.FC<CaseFileProps> = (p) => {
  const sc = usePageScene(p);
  const {W, H, u, fps, theme, beat, ruleY, vertical} = sc;
  const step = ruleY(1) - ruleY(0);
  const left = sc.marginX + (vertical ? 50 : 80) * u;
  const right = W - (vertical ? 60 : 150) * u;
  const t0 = beat(0);
  const org = p.org ?? '';
  const label = p.label ?? 'CASE FILE';
  const typeF = theme.fonts.type;
  const handF = theme.fonts.hand;
  const title = `${label}  No. ${p.number}`;
  const titleSize = fit(title, typeF, (vertical ? 96 : 132) * u, right - left);
  const fields = p.fields ?? [];
  const labSize = (vertical ? 44 : 46) * u;
  const labelW = vertical ? 0 : Math.max(0, ...fields.map((f) => measure(`${f.label}:`, typeF, labSize))) + 36 * u;
  const valueSize = Math.min(step * 2.1, 96 * u);
  const valueW = right - left - labelW;
  const valueLines = fields.map((f) => wrap(f.value, handF, valueSize, valueW).length);
  // block height in rules: org (3) + title (3) + per field (value lines × 2 + 1, plus 1 more when stacked)
  const per = vertical ? 1 : 2; // rules per handwritten line (vertical pages have wider rules)
  const span = (org ? 3 : 0) + 3 + valueLines.reduce((a, n) => a + n * per + 1 + (vertical ? 1 : 0), 0);
  let k = Math.round((H * (vertical ? 0.45 : 0.5) - ruleY(0)) / step - span / 2) + 2;
  const nodes: React.ReactNode[] = [];
  if (org) {
    nodes.push(<Write key="org" text={org} x={left} y={ruleY(k)} size={32 * u} start={t0} font="type" cps={60} color={theme.muted} letterSpacing={8 * u} />);
    nodes.push(<Draw key="orgline" d={handLine(left - 10 * u, ruleY(k) + 16 * u, right, ruleY(k) + 14 * u, 'ol', 2 * u)} start={t0 + 6} dur={14} width={3} />);
    k += 3;
  }
  const titleY = ruleY(k);
  nodes.push(<Write key="title" text={title} x={left} y={titleY} size={titleSize} start={t0 + 4} font="type" cps={30} />);
  k += 3;
  let lastEnd = t0 + 4 + Math.ceil((title.length / 30) * fps);
  fields.forEach((f, i) => {
    const b = beat(f.beat ?? i + 1);
    const lab = `${f.label}:`;
    const vStart = b + Math.ceil((lab.length / 40) * fps) + 4;
    nodes.push(<Write key={`l${i}`} text={lab} x={left} y={ruleY(k)} size={labSize} start={b} font="type" cps={40} color={theme.muted} letterSpacing={3 * u} />);
    if (vertical) k += 1;
    nodes.push(<Write key={`v${i}`} text={f.value} x={left + labelW} y={ruleY(k)} size={valueSize} start={vStart} cps={22} maxW={valueW} lineGap={step * per} />);
    lastEnd = vStart + Math.ceil((f.value.length / 22) * fps);
    k += valueLines[i] * per + 1;
  });
  if (p.stamp) {
    const hit = Math.min(sc.total - 6, lastEnd + 8);
    nodes.push(<Stamp key="stamp" word={p.stamp} cx={right - 150 * u} cy={vertical ? ruleY(k + 1) : titleY - 30 * u} size={60 * u} hit={hit} rotate={-9} />);
  }
  return <Page scene={sc}>{nodes}</Page>;
};
