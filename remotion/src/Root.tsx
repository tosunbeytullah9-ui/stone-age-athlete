import React from 'react';
import {CalculateMetadataFunction, Composition} from 'remotion';
import {COMPS} from './comps';
import {loadFonts} from './lib/fonts';

loadFonts();

type Meta = {frames?: number; fps?: number; width?: number; height?: number};

// Length, rate and size come from the pipeline with every job (the scene's narration decides the length).
const meta: CalculateMetadataFunction<Meta & Record<string, unknown>> = ({props}) => ({
  durationInFrames: Math.max(1, Math.round(Number(props.frames ?? 150))),
  fps: Number(props.fps ?? 30),
  width: Number(props.width ?? 1920),
  height: Number(props.height ?? 1080),
});

// `<id>` is what the pipeline renders: no default props, so nothing from the examples can leak into a video.
// `<id>-example` carries the example props for Remotion Studio (npm run studio).
export const Root: React.FC = () => (
  <>
    {Object.entries(COMPS).flatMap(([id, c]) =>
      [
        [id, {}],
        [`${id}-example`, c.example],
      ].map(([cid, props]) => (
        <Composition
          key={cid as string}
          id={cid as string}
          component={c.component}
          durationInFrames={150}
          fps={30}
          width={1920}
          height={1080}
          defaultProps={props as Record<string, unknown>}
          calculateMetadata={meta}
        />
      )),
    )}
  </>
);
