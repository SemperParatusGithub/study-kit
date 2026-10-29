import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  decidedRight,
  examPartPoints,
  examPoints,
  examScore,
  gradeEstimate,
  isCorrect,
  isMisconception,
  multiRule,
  score,
} from '../../src/lib/scoring.ts';

const opts = (correct: string) =>
  [...correct].map((c, i) => ({ key: 'ABCDEF'[i] as string, correct: c === '1' }));

test('single: 1 for the correct option, 0 otherwise', () => {
  const o = opts('0100');
  assert.equal(score('single', o, ['B']), 1);
  assert.equal(score('single', o, ['A']), 0);
  assert.equal(score('single', o, []), 0);
  assert.equal(score('single', o, ['B', 'C']), 0);
  assert.equal(score('single', o, ['Z']), 0);
});

test('multi all-or-nothing: only the exact correct set scores', () => {
  const o = opts('1100');
  assert.equal(score('multi', o, ['A', 'B']), 1);
  assert.equal(score('multi', o, ['B', 'A']), 1);
  assert.equal(score('multi', o, ['A']), 0);
  assert.equal(score('multi', o, ['A', 'B', 'C']), 0);
  assert.equal(score('multi', o, []), 0);
  assert.equal(score('multi', o, ['A', 'B'], 'all-or-nothing'), 1);
});

test('multi partial: max(0, (right − wrong) / n)', () => {
  const o = opts('1100');
  assert.equal(score('multi', o, ['A', 'B'], 'partial'), 1);
  // A right, B missed, C, D right: 3 right, 1 wrong → 0.5
  assert.equal(score('multi', o, ['A'], 'partial'), 0.5);
  // nothing selected: C, D right, A, B wrong → 0
  assert.equal(score('multi', o, [], 'partial'), 0);
  // everything wrong → clamped at 0 (no negative marking)
  assert.equal(score('multi', o, ['C', 'D'], 'partial'), 0);
  // 5 options, 4 right, 1 wrong → 0.6
  assert.equal(score('multi', opts('10100'), ['A', 'C', 'D'], 'partial'), 0.6);
});

test('multi with the kprim rule: all right 1, one wrong 0.5, else 0', () => {
  const o = opts('1100');
  assert.equal(score('multi', o, ['A', 'B'], 'kprim'), 1);
  assert.equal(score('multi', o, ['A'], 'kprim'), 0.5);
  assert.equal(score('multi', o, ['A', 'C'], 'kprim'), 0);
});

test('kprim: 4/4 → 1, 3/4 → 0.5, otherwise 0', () => {
  const o = opts('1100'); // A, B true; C, D false
  assert.equal(score('kprim', o, ['A', 'B']), 1);
  assert.equal(score('kprim', o, ['A']), 0.5); // B judged false: 3/4
  assert.equal(score('kprim', o, ['A', 'B', 'C']), 0.5);
  assert.equal(score('kprim', o, ['C']), 0); // A, B, C wrong
  assert.equal(score('kprim', o, ['A', 'C']), 0); // B, C wrong: 2/4
  assert.equal(score('kprim', o, []), 0); // 2/4
  // The multi rule never changes Kprim scoring.
  assert.equal(score('kprim', o, ['A'], 'partial'), 0.5);
  assert.equal(score('kprim', o, ['A'], 'all-or-nothing'), 0.5);
});

test('kprim: a statement left open counts as wrong', () => {
  const o = opts('1100');
  // A, B judged true, C judged false, D open: 3/4
  assert.equal(score('kprim', o, ['A', 'B'], 'all-or-nothing', ['A', 'B', 'C']), 0.5);
  assert.equal(score('kprim', o, ['A', 'B'], 'all-or-nothing', ['A', 'B']), 0);
  assert.equal(decidedRight(o, ['A', 'B'], ['A', 'B', 'C', 'D']), 4);
});

test('scores never go below 0 or above 1', () => {
  const o = opts('101100');
  const subsets = Array.from({ length: 64 }, (_, m) =>
    ['A', 'B', 'C', 'D', 'E', 'F'].filter((_, i) => m & (1 << i)),
  );
  for (const chosen of subsets) {
    for (const rule of ['all-or-nothing', 'partial', 'kprim'] as const) {
      const s = score('multi', o, chosen, rule);
      assert.ok(s >= 0 && s <= 1, `${chosen} ${rule} ${s}`);
    }
  }
});

test('correctness, misconceptions and rule parsing', () => {
  assert.equal(isCorrect(1), true);
  assert.equal(isCorrect(0.5), false);
  assert.equal(isMisconception(0, 'sure'), true);
  assert.equal(isMisconception(0.5, 'sure'), true);
  assert.equal(isMisconception(0, 'unsure'), false);
  assert.equal(isMisconception(1, 'sure'), false);
  assert.equal(multiRule('partial'), 'partial');
  assert.equal(multiRule('kprim'), 'kprim');
  assert.equal(multiRule('bogus'), 'all-or-nothing');
  assert.equal(multiRule(undefined), 'all-or-nothing');
});

test('exam points and grade estimate', () => {
  assert.equal(examPoints(0.5, 2), 1);
  assert.equal(examPoints(1, 2.5), 2.5);
  assert.equal(gradeEstimate(100, 100, 50), 1.0);
  assert.equal(gradeEstimate(50, 100, 50), 4.0);
  assert.equal(gradeEstimate(49.5, 100, 50), 5.0);
  assert.equal(gradeEstimate(55, 100, 50), 3.7);
  assert.equal(gradeEstimate(75, 100, 50), 2.3);
  assert.equal(gradeEstimate(95, 100, 50), 1.0);
  assert.equal(gradeEstimate(94.9, 100, 50), 1.3);
  assert.equal(gradeEstimate(10, 20, null), null);
});

test('exam score without negative marking is the normal score', () => {
  const o = opts('0100');
  assert.equal(examScore('single', o, ['A']), 0);
  assert.equal(examScore('single', o, ['B'], 'all-or-nothing', undefined, false), 1);
  assert.equal(examScore('multi', opts('1100'), ['C', 'D'], 'partial'), 0);
});

test('exam score with negative marking: a wrong answer costs a right one', () => {
  const single = opts('0100');
  assert.equal(examScore('single', single, ['B'], 'all-or-nothing', undefined, true), 1);
  assert.equal(examScore('single', single, ['A'], 'all-or-nothing', undefined, true), -1);
  assert.equal(examScore('single', single, [], 'all-or-nothing', undefined, true), 0); // blank
  const multi = opts('1100');
  assert.equal(examScore('multi', multi, ['A'], 'all-or-nothing', undefined, true), -1);
  assert.equal(examScore('multi', multi, [], 'all-or-nothing', undefined, true), 0);
  // partial rule without the floor: (right − wrong) / n
  assert.equal(examScore('multi', multi, ['A'], 'partial', undefined, true), 0.5);
  assert.equal(examScore('multi', multi, ['C', 'D'], 'partial', undefined, true), -1);
  assert.equal(examScore('multi', multi, ['A', 'C'], 'partial', undefined, true), 0);
  // kprim: 3/4 keeps its half point, worse costs the question's points, nothing judged is 0
  assert.equal(examScore('kprim', multi, ['A'], 'all-or-nothing', ['A', 'B', 'C', 'D'], true), 0.5);
  assert.equal(examScore('kprim', multi, ['C'], 'all-or-nothing', ['A', 'B', 'C', 'D'], true), -1);
  assert.equal(examScore('kprim', multi, [], 'all-or-nothing', [], true), 0);
});

test('the MC part never goes below 0', () => {
  assert.equal(examPartPoints([2, -2, -2]), 0);
  assert.equal(examPartPoints([2, 2, -2, 1]), 3);
  assert.equal(examPartPoints([]), 0);
});
