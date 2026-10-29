// Leitner review schedule (docs/architecture.md §3.2), mirrored in progress.py.
//
// - Boxes 0–5 with intervals of 0, 1, 3, 7, 14 and 30 days. A new item starts in box 1.
// - A fully correct answer moves the item up one box (at most box 5).
// - A wrong answer (any score below 1) sends it to box 1.
// - A "sure" answer that is wrong sends it to box 0 (again today): a misconception.
// - Exam clamp, with limit = exam_date − 2 days and window = the last 10 days
//   [exam_date − 10, exam_date − 2]:
//   - no item is due after the limit, so the last two days stay free;
//   - every attempted item comes up again within the window: an interval that would end
//     after the limit ends at the window start (reviewed before the window) or at the
//     limit (reviewed inside it);
//   - an item reviewed on or after the limit is next due the day after the exam.
//   The clamp is applied when scheduling and again when asking "is it due?", so a
//   changed exam date takes effect at once. After the exam date it no longer applies.
//
// Dates are local calendar days written YYYY-MM-DD.

export type Conf = 'sure' | 'unsure';

export const INTERVALS = [0, 1, 3, 7, 14, 30] as const;
export const MAX_BOX = 5;
export const ENTRY_BOX = 1;
export const CLAMP_LIMIT_DAYS = 2;
export const CLAMP_WINDOW_DAYS = 10;

const DAY_RE = /^(\d{4})-(\d{2})-(\d{2})$/;

export function isDay(value: unknown): value is string {
  if (typeof value !== 'string') return false;
  const m = DAY_RE.exec(value);
  if (!m) return false;
  const d = new Date(Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3])));
  return d.toISOString().slice(0, 10) === value;
}

/** The local calendar day of `date` as YYYY-MM-DD. */
export function dayOf(date: Date = new Date()): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

export function addDays(day: string, days: number): string {
  const m = DAY_RE.exec(day);
  if (!m) throw new RangeError(`not a YYYY-MM-DD day: ${day}`);
  const t = Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3])) + days * 86_400_000;
  return new Date(t).toISOString().slice(0, 10);
}

/** Whole days from `a` to `b` (positive when b is later). */
export function daysBetween(a: string, b: string): number {
  const ta = Date.parse(`${a}T00:00:00Z`);
  const tb = Date.parse(`${b}T00:00:00Z`);
  return Math.round((tb - ta) / 86_400_000);
}

function clampBox(box: number | null | undefined): number | null {
  if (typeof box !== 'number' || !Number.isFinite(box)) return null;
  return Math.min(MAX_BOX, Math.max(0, Math.trunc(box)));
}

/** The box after an answer with `score` (1 = fully right) and confidence `conf`. */
export function nextBox(box: number | null | undefined, score: number, conf: Conf): number {
  if (score >= 1 - 1e-9) return Math.min(MAX_BOX, (clampBox(box) ?? ENTRY_BOX) + 1);
  return conf === 'sure' ? 0 : ENTRY_BOX;
}

/** Apply the exam clamp to a due day for an item reviewed on `reviewedOn`. */
export function clampDue(due: string, reviewedOn: string, examDate?: string | null): string {
  if (!examDate || !isDay(examDate) || reviewedOn > examDate) return due;
  const limit = addDays(examDate, -CLAMP_LIMIT_DAYS);
  const windowStart = addDays(examDate, -CLAMP_WINDOW_DAYS);
  if (reviewedOn >= limit) return due > examDate ? due : addDays(examDate, 1);
  if (due <= limit) return due;
  return reviewedOn < windowStart ? windowStart : limit;
}

/** The due day for an item that is now in `box`, reviewed on `today`. */
export function schedule(box: number, today: string, examDate?: string | null): string {
  const interval = INTERVALS[clampBox(box) ?? ENTRY_BOX] ?? 0;
  return clampDue(addDays(today, interval), today, examDate);
}

export interface Review {
  box: number;
  due: string;
  misconception: boolean;
}

/** Box, due day and misconception flag after one answer. */
export function review(
  box: number | null | undefined,
  score: number,
  conf: Conf,
  today: string,
  examDate?: string | null,
): Review {
  const next = nextBox(box, score, conf);
  return {
    box: next,
    due: schedule(next, today, examDate),
    misconception: next === 0,
  };
}

/** True during the two rest days before the exam (nothing is due then). */
export function inRestDays(today: string, examDate?: string | null): boolean {
  if (!examDate || !isDay(examDate)) return false;
  return today > addDays(examDate, -CLAMP_LIMIT_DAYS) && today <= examDate;
}

/**
 * The day an entry was reviewed, worked out from its due day and box, for entries that keep
 * no review day (exercises): the due day less the box's interval. It is exact unless the
 * exam clamp moved the due day, and then it still lies on the same side of the clamp limit
 * as the real review day (a review on or after the limit gives a due day after the exam; one
 * before it, a due day no later than the limit), which is all clampDue looks at. Null
 * without a valid due day and box.
 */
export function reviewDayOf(due: string | null | undefined, box: number | null | undefined): string | null {
  const b = clampBox(box);
  if (!isDay(due) || b === null) return null;
  return addDays(due, -(INTERVALS[b] ?? 0));
}

/** Stands in for an unknown review day: long ago. */
const LONG_AGO = '0001-01-01';

/**
 * The effective due day of an entry: its stored due day, clamped again for the current
 * exam date. `reviewedOn` is the day of the last attempt when known.
 */
export function effectiveDue(
  due: string | null | undefined,
  reviewedOn: string | null | undefined,
  examDate?: string | null,
): string | null {
  if (!isDay(due)) return null;
  return clampDue(due, isDay(reviewedOn) ? reviewedOn : LONG_AGO, examDate);
}

export function isDue(
  due: string | null | undefined,
  reviewedOn: string | null | undefined,
  today: string,
  examDate?: string | null,
): boolean {
  if (inRestDays(today, examDate)) return false;
  const eff = effectiveDue(due, reviewedOn, examDate);
  return eff !== null && eff <= today;
}
