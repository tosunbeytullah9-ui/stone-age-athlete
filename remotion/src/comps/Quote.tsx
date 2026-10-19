// A typed paper slip with a quote; the words that matter are underlined in red pen afterwards.
import React from 'react';
import {BaseProps, Page, usePageScene} from '../lib/scene';
import {Draw, ease, fit, handLine, measure, wrap, Write} from '../lib/ink';

export type QuoteProps = BaseProps & {
  text: string;
  source?: string | null; // handwritten under the slip, e.g. "Food and Nutrition Board, 1945"
  highlight?: string | null; // a part of `text` to underline after typing
};

export const Quote: React.FC<QuoteProps> = (p) => {
  const sc = usePageScene(p);
  const {W, H, u, fps, theme, beat, frame, vertical, total} = sc;
  const typeF = theme.fonts.type;
  const text = `“${p.text.replace(/^["“]|["”]$/g, '')}”`;
  const slipW = W * (vertical ? 0.88 : 0.76);
  const pad = 56 * u;
  const size = fit(text, typeF, (vertical ? 72 : 88) * u, slipW - pad * 2, vertical ? 7 : 4, 28);
  const lines = wrap(text, typeF, size, slipW - pad * 2);
  const gap = size * 1.42;
  const slipH = pad * 2 + lines.length * gap;
  const cx = W / 2;
  const cy = H * (vertical ? 0.42 : 0.45);
  const x0 = cx - slipW / 2;
  const y0 = cy - slipH / 2;
  const t0 = beat(0);
  const appear = ease(frame, t0, t0 + 8);
  // finish typing by ~55 % of the scene (but never faster than a brisk typist)
  const cps = Math.max(26, text.length / Math.max(0.6, ((total - t0) * 0.55) / fps));
  const typedEnd = t0 + 8 + Math.ceil((text.length / cps) * fps);
  const nodes: React.ReactNode[] = [];
  nodes.push(
    <g key="slip" opacity={appear} transform={`rotate(${vertical ? -1 : -1.4} ${cx} ${cy}) translate(0 ${(1 - appear) * 30 * u})`}>
      <rect x={x0 + 10 * u} y={y0 + 14 * u} width={slipW} height={slipH} fill="#000" opacity={0.12} rx={3} />
      <rect x={x0} y={y0} width={slipW} height={slipH} fill="#fbf6ea" stroke={theme.muted} strokeOpacity={0.35} strokeWidth={2 * u} rx={3} />
      <Write text={text} x={x0 + pad} y={y0 + pad + size * 0.95} size={size} start={t0 + 8} font="type" cps={cps} maxW={slipW - pad * 2} lineGap={gap} boil={false} />
      {p.highlight
        ? (() => {
            // underline the highlighted words, line by line
            const out: React.ReactNode[] = [];
            const hl = p.highlight.toLowerCase();
            const flat = lines.join(' ').toLowerCase(); // same length as the text, so indexes line up
            const at = flat.indexOf(hl);
            if (at < 0) return null;
            let pos = 0;
            lines.forEach((ln, i) => {
              const a = Math.max(at, pos);
              const b = Math.min(at + hl.length, pos + ln.length);
              if (b > a) {
                const xa = x0 + pad + measure(ln.slice(0, a - pos), typeF, size);
                const xb = x0 + pad + measure(ln.slice(0, b - pos), typeF, size);
                const y = y0 + pad + size * 0.95 + i * gap + size * 0.22;
                out.push(<Draw key={`u${i}`} d={handLine(xa - 4 * u, y + 3 * u, xb + 6 * u, y, `u${i}`, 2 * u)} start={typedEnd + 6 + out.length * 6} dur={9} width={6} color={theme.accent} />);
              }
              pos += ln.length + 1;
            });
            return out;
          })()
        : null}
    </g>,
  );
  if (p.source) {
    nodes.push(
      <Write key="src" text={`— ${p.source}`} x={x0 + slipW - 10 * u} y={sc.nearestRule(y0 + slipH + 90 * u)} size={56 * u} start={Math.max(typedEnd + 2, beat(1))} cps={30} anchor="end" color={theme.muted} />,
    );
  }
  return <Page scene={sc}>{nodes}</Page>;
};
