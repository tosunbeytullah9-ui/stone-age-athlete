// The scene catalogue. A storyboard shot uses one with `visual: {comp: <id>, ...props}` (docs/REMOTION.md).
import React from 'react';
import {Bars} from './Bars';
import {CaseFile} from './CaseFile';
import {Counter} from './Counter';
import {Quote} from './Quote';
import {Timeline} from './Timeline';
import {Verdict} from './Verdict';

type Entry = {component: React.FC<any>; example: Record<string, unknown>};

export const COMPS: Record<string, Entry> = {
  'case-file': {
    component: CaseFile,
    example: {number: '001', org: 'BUREAU OF HUMAN ERROR', fields: [{label: 'SUBJECT', value: 'you'}], beats: [0, 45], frames: 120},
  },
  verdict: {
    component: Verdict,
    example: {word: 'WRONG', belief: 'Eight glasses of water a day', note: 'Your water comes from your food, your drinks and your thirst.', beats: [0, 60], frames: 150},
  },
  bars: {
    component: Bars,
    example: {
      title: 'Where adults get their water',
      of: 100,
      unit: '%',
      bars: [
        {label: 'Men: plain water', value: 30},
        {label: 'Women: plain water', value: 34},
      ],
      beats: [0, 40],
      frames: 150,
    },
  },
  counter: {
    component: Counter,
    example: {value: 5604, label: 'people in 26 countries', note: 'aged 8 days to 96 years', beats: [0, 60], frames: 120},
  },
  timeline: {
    component: Timeline,
    example: {
      events: [
        {when: '1945', text: 'About 2.5 litres a day, "most of it in food"'},
        {when: '1970s', text: 'At least six glasses'},
        {when: 'later', text: 'Eight glasses, for everybody', highlight: true},
      ],
      beats: [0, 45, 90],
      frames: 180,
    },
  },
  quote: {
    component: Quote,
    example: {text: 'Most of this quantity is contained in prepared foods.', source: 'Food and Nutrition Board, 1945', highlight: 'prepared foods', frames: 150},
  },
};
