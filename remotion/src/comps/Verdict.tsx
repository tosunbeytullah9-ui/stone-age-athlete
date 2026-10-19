// "Verdict: wrong." — the belief on the page is struck through in red pen, then the stamp comes down.
import React from 'react';
import {BaseProps, Page, shakeAt, usePageScene} from '../lib/scene';
import {Draw, fit, handLine, measure, Stamp, wrap, Write} from '../lib/ink';

export type VerdictProps = BaseProps & {
  word?: string; // stamp word, e.g. "WRONG"
  label?: string; // "VERDICT"
  belief?: string | null; // the sentence that gets struck through
  note?: string | null; // handwritten line under the stamp, appears at beat 1 (e.g. what is true instead)
  hit?: number | null; // seconds from the scene start when the stamp lands (default ~0.9 s, after the strike)
  hit_beat?: number | null; // or: the stamp lands when shot N of the scene starts (e.g. 1 = right after the first sentence)
};

export const Verdict: React.FC<VerdictProps> = (p) => {
  const sc = usePageScene(p);
  const {W, H, u, fps, theme, beat, ruleY, vertical, frame} = sc;
  const step = ruleY(1) - ruleY(0);
  const left = sc.marginX + (vertical ? 50 : 70) * u;
  const t0 = beat(0);
  const word = p.word ?? 'WRONG';
  const handF = theme.fonts.hand;
  const nodes: React.ReactNode[] = [];
  const labelK = Math.ceil((H * (vertical ? 0.16 : 0.14) - ruleY(0)) / step);
  nodes.push(<Write key="lab" text={`${p.label ?? 'VERDICT'}:`} x={left} y={ruleY(labelK)} size={54 * u} start={t0} font="type" cps={34} letterSpacing={6 * u} />);
  const midY = H * (vertical ? 0.42 : 0.5);
  const beliefY = midY - (vertical ? 330 : 200) * u;
  // the stamp lands on `hit` (the pipeline passes the moment "wrong" is said); belief and strike fit before it
  const sDur = 9;
  const hitDefault = t0 + Math.round(fps * 0.9);
  const hit =
    p.hit != null ? Math.max(t0 + 4, Math.round(p.hit * fps)) : p.hit_beat != null ? Math.max(t0 + 4, beat(p.hit_beat)) : hitDefault;
  if (p.belief) {
    const maxW = W * (vertical ? 0.8 : 0.7);
    const size = fit(p.belief, handF, (vertical ? 84 : 100) * u, maxW, vertical ? 4 : 2);
    const lines = wrap(p.belief, handF, size, maxW);
    const gap = Math.max(step, size * 1.15);
    const y0 = sc.nearestRule(beliefY - ((lines.length - 1) * gap) / 2);
    const room = hit - t0 - 2 - sDur - 4 - (lines.length - 1) * 5; // frames left for writing the belief
    const writeF = Math.max(3, Math.min(Math.ceil((p.belief.length / 70) * fps), room));
    const cps = (p.belief.length / writeF) * fps;
    nodes.push(<Write key="bel" text={p.belief} x={W / 2} y={y0} size={size} start={t0 + 2} cps={cps} maxW={maxW} lineGap={gap} anchor="middle" />);
    const strike0 = Math.max(t0 + 2 + writeF + 1, Math.min(hit - sDur - 4 - (lines.length - 1) * 5, t0 + Math.round(fps * 0.35)));
    lines.forEach((ln, i) => {
      const lw = measure(ln, handF, size);
      const y = y0 + i * gap - size * 0.3;
      const st = strike0 + i * 5;
      nodes.push(
        <Draw key={`s${i}`} d={handLine(W / 2 - lw / 2 - 18 * u, y + 6 * u, W / 2 + lw / 2 + 22 * u, y - 4 * u, `st${i}`, 3 * u)} start={st} dur={sDur} width={8} color={theme.accent} />,
      );
    });
  }
  const stampY = p.belief ? midY + (vertical ? 20 : 70) * u : midY;
  const stampSize = Math.min((vertical ? 140 : 156) * u, (W * 0.62) / Math.max(4, word.length * 1.1));
  nodes.push(<Stamp key="stamp" word={word} cx={W / 2} cy={stampY} size={stampSize} hit={hit} rotate={-7} />);
  if (p.note) {
    const nb = Math.max(beat(1), hit + Math.round(fps * 0.5));
    const ny = sc.nearestRule(stampY + (vertical ? 320 : 290) * u);
    nodes.push(<Write key="note" text={p.note} x={W / 2} y={ny} size={56 * u} start={nb} cps={24} maxW={W * 0.8} lineGap={step * (vertical ? 1 : 1.25)} anchor="middle" />);
  }
  return (
    <Page scene={sc} shake={shakeAt(frame, hit, u, sc.seed)}>
      {nodes}
    </Page>
  );
};
