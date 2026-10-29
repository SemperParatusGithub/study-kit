import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  addDays,
  clampDue,
  dayOf,
  daysBetween,
  effectiveDue,
  inRestDays,
  INTERVALS,
  isDay,
  isDue,
  nextBox,
  review,
  reviewDayOf,
  schedule,
} from '../../src/lib/leitner.ts';

const EXAM = '2027-02-15';
const LIMIT = '2027-02-13'; // exam − 2 days
const WINDOW = '2027-02-05'; // exam − 10 days

test('day arithmetic', () => {
  assert.equal(addDays('2026-12-31', 1), '2027-01-01');
  assert.equal(addDays('2027-03-01', -1), '2027-02-28');
  assert.equal(addDays('2028-03-01', -1), '2028-02-29');
  assert.equal(addDays('2026-03-29', 1), '2026-03-30'); // DST change in Europe
  assert.equal(daysBetween('2027-02-05', '2027-02-15'), 10);
  assert.equal(isDay('2027-02-15'), true);
  assert.equal(isDay('2027-02-30'), false);
  assert.equal(isDay('15.02.2027'), false);
  assert.equal(dayOf(new Date(2026, 10, 2, 23, 59)), '2026-11-02');
});

test('intervals are 0, 1, 3, 7, 14 and 30 days', () => {
  assert.deepEqual([...INTERVALS], [0, 1, 3, 7, 14, 30]);
  for (let box = 0; box <= 5; box++) {
    assert.equal(schedule(box, '2026-11-02'), addDays('2026-11-02', INTERVALS[box] as number));
  }
});

test('a correct answer moves up one box, at most box 5; new items start in box 1', () => {
  assert.equal(nextBox(null, 1, 'sure'), 2);
  assert.equal(nextBox(undefined, 1, 'unsure'), 2);
  assert.equal(nextBox(0, 1, 'sure'), 1);
  assert.equal(nextBox(3, 1, 'sure'), 4);
  assert.equal(nextBox(5, 1, 'sure'), 5);
});

test('a wrong answer goes to box 1, a sure wrong answer to box 0', () => {
  assert.equal(nextBox(4, 0, 'unsure'), 1);
  assert.equal(nextBox(4, 0.5, 'unsure'), 1); // a partial score is not a full answer
  assert.equal(nextBox(4, 0, 'sure'), 0);
  assert.equal(nextBox(null, 0.5, 'sure'), 0);
  const r = review(3, 0, 'sure', '2026-11-02');
  assert.deepEqual(r, { box: 0, due: '2026-11-02', misconception: true });
  const w = review(3, 0, 'unsure', '2026-11-02');
  assert.deepEqual(w, { box: 1, due: '2026-11-03', misconception: false });
  const c = review(3, 1, 'sure', '2026-11-02');
  assert.deepEqual(c, { box: 4, due: '2026-11-16', misconception: false });
});

test('exam clamp: nothing is due after exam − 2 days', () => {
  // Reviewed inside the window: a long interval ends at the limit.
  assert.equal(schedule(5, '2027-02-07', EXAM), LIMIT);
  assert.equal(schedule(4, '2027-02-10', EXAM), LIMIT);
  // A short interval that ends before the limit is kept.
  assert.equal(schedule(1, '2027-02-10', EXAM), '2027-02-11');
  assert.equal(schedule(2, '2027-02-10', EXAM), LIMIT); // 3 days → 02-13, exactly the limit
  // No schedule ever lands in (limit, exam].
  for (let d = -60; d <= 0; d++) {
    const today = addDays(EXAM, d);
    for (let box = 0; box <= 5; box++) {
      const due = schedule(box, today, EXAM);
      assert.ok(!(due > LIMIT && due <= EXAM), `${today} box ${box} → ${due}`);
    }
  }
});

test('exam clamp: every attempted item comes up again in the last 10 days', () => {
  // Reviewed before the window with an interval that would end after the limit:
  // due at the window start.
  assert.equal(schedule(5, '2027-01-20', EXAM), WINDOW);
  assert.equal(schedule(4, '2027-02-01', EXAM), WINDOW);
  // An interval ending before the window is kept; the item is rescheduled then.
  assert.equal(schedule(3, '2027-01-20', EXAM), '2027-01-27');
  // Simulate a student who always reviews on the due day: each item is due at least once
  // in [exam − 10, exam − 2], whatever its box.
  for (let start = -90; start <= -11; start += 7) {
    for (let box0 = 1; box0 <= 5; box0++) {
      let today = addDays(EXAM, start);
      let box = box0;
      let due = schedule(box, today, EXAM);
      let seenInWindow = false;
      for (let guard = 0; guard < 100 && due <= LIMIT; guard++) {
        if (due >= WINDOW) seenInWindow = true;
        today = due;
        box = nextBox(box, 1, 'sure');
        due = schedule(box, today, EXAM);
        if (today >= LIMIT) break;
      }
      assert.ok(seenInWindow, `start ${start} box ${box0}`);
    }
  }
});

test('exam clamp: reviews on or after the limit are next due after the exam', () => {
  assert.equal(schedule(0, LIMIT, EXAM), '2027-02-16');
  assert.equal(schedule(5, '2027-02-14', EXAM), '2027-03-16');
  assert.equal(schedule(1, EXAM, EXAM), '2027-02-16');
  // After the exam the clamp no longer applies.
  assert.equal(schedule(3, '2027-02-20', EXAM), '2027-02-27');
});

test('the last two days are rest days', () => {
  assert.equal(inRestDays('2027-02-13', EXAM), false);
  assert.equal(inRestDays('2027-02-14', EXAM), true);
  assert.equal(inRestDays(EXAM, EXAM), true);
  assert.equal(inRestDays('2027-02-16', EXAM), false);
  assert.equal(isDue('2027-02-01', '2027-01-31', '2027-02-14', EXAM), false);
  assert.equal(isDue('2027-02-01', '2027-01-31', '2027-02-13', EXAM), true);
});

test('isDue re-applies the clamp, so a moved exam date takes effect at once', () => {
  // Scheduled for 2027-03-10 before the exam date was known.
  assert.equal(isDue('2027-03-10', '2027-02-08', '2027-02-10', null), false);
  assert.equal(effectiveDue('2027-03-10', '2027-02-08', EXAM), LIMIT);
  assert.equal(isDue('2027-03-10', '2027-02-08', '2027-02-13', EXAM), true);
  // Reviewed before the window: due from the window start.
  assert.equal(isDue('2027-03-10', '2027-01-08', '2027-02-05', EXAM), true);
  assert.equal(isDue('2027-03-10', '2027-01-08', '2027-02-04', EXAM), false);
  // Unknown review day: treated as reviewed before the window.
  assert.equal(effectiveDue('2027-03-10', null, EXAM), WINDOW);
  assert.equal(isDue('2027-03-10', null, '2027-02-13', EXAM), true);
  assert.equal(isDue('2027-03-10', null, '2027-02-04', EXAM), false);
  // No due day: never due.
  assert.equal(isDue(null, null, '2027-02-13', EXAM), false);
  // Without an exam date the stored day decides.
  assert.equal(isDue('2026-11-02', null, '2026-11-02', null), true);
  assert.equal(isDue('2026-11-03', null, '2026-11-02', null), false);
  assert.equal(clampDue('2027-03-10', '2027-03-01', EXAM), '2027-03-10');
});

test('reviewDayOf: the review day of an entry that keeps none, on the right side of the clamp', () => {
  // unclamped: exact
  assert.equal(reviewDayOf('2026-11-13', 2), '2026-11-10');
  assert.equal(reviewDayOf('2027-03-10', 5), '2027-02-08');
  assert.equal(reviewDayOf(null, 2), null);
  assert.equal(reviewDayOf('2026-11-13', null), null);
  // every review day the clamp can have moved keeps its side of the limit
  for (let d = '2027-01-01'; d <= '2027-02-25'; d = addDays(d, 1)) {
    for (let box = 1; box <= 5; box++) {
      const due = schedule(box, d, EXAM);
      const est = reviewDayOf(due, box);
      assert.ok(est !== null && (est >= LIMIT) === (d >= LIMIT), `${d} box ${box}: ${est}`);
      assert.equal(effectiveDue(due, est, EXAM), effectiveDue(due, d, EXAM), `${d} box ${box}`);
    }
  }
});
