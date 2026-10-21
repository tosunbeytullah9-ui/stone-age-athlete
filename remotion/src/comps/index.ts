// The scene catalogue. A storyboard shot uses one with `visual: {comp: <id>, ...props}` (docs/REMOTION.md).
import React from 'react';
import {Bars} from './Bars';
import {CaseFile} from './CaseFile';
import {Counter} from './Counter';
import {Quote} from './Quote';
import {Timeline} from './Timeline';
import {Verdict} from './Verdict';
import {Mech} from './Mech';

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
  mech: {
    component: Mech,
    example: {
      theme: {name: 'pop'},
      frames: 180,
      beats: [0, 60, 120],
      cues: {'@crank': 70},
      items: [
        {id: 'g1', kind: 'gear', x: 760, y: 560, r: 150, teeth: 16, depth: 26, fill: 'yellow', in: 0, spin: {speed: 90, from: '@crank'}},
        {id: 'g2', kind: 'gear', x: 1035, y: 560, r: 112, teeth: 12, depth: 26, fill: 'teal', rotate: 15, in: 0, spin: {speed: -120, from: '@crank'}},
        {id: 'a1', kind: 'arrow', x: 560, y: 300, to: [160, 120], bend: -40, in: '@crank', color: 'coral'},
        {id: 'l1', kind: 'label', x: 1035, y: 560, to: [180, -200], text: 'feed wheel', in: 1},
        {id: 't1', kind: 'formula', x: 960, y: 930, text: 'pressure = force ÷ area', in: 2},
        {id: 'w1', kind: 'wave', x: 1300, y: 300, w: 480, amp: 40, length: 160, standing: true, in: 0},
        {id: 'gg', kind: 'gauge', x: 300, y: 820, r: 120, value: 0.1, in: 0, keys: [{at: 1, value: 0.85, dur: 1.5}]},
        {id: 'pp', kind: 'particles', x: 300, y: 330, w: 360, h: 260, count: 22, size: 13, value: 0.2, in: 0, keys: [{at: 1, value: 2.5, dur: 1}]},
      ],
    },
  },
  quote: {
    component: Quote,
    example: {text: 'Most of this quantity is contained in prepared foods.', source: 'Food and Nutrition Board, 1945', highlight: 'prepared foods', frames: 150},
  },
};
