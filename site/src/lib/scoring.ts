// MC scoring (docs/architecture.md §2.6), mirrored in progress.py. No negative marking:
// every score lies in [0, 1].
//
// | type   | score                                                              |
// |--------|--------------------------------------------------------------------|
// | single | 1 or 0                                                             |
// | multi  | all-or-nothing: 1 only if the selected set equals the correct set  |
// |        | partial: max(0, (options decided right − options decided wrong)/n) |
// |        | kprim: the Kprim rule applied to the n options (see below)          |
// | kprim  | 4/4 decided right → 1, 3/4 → 0.5, otherwise 0                       |
//
// For multi an option is "decided right" when it is selected and correct or unselected
// and wrong. For Kprim every statement is judged true or false; `chosen` lists the keys
// judged true and `answered` the keys judged at all (a statement left open is wrong).
// course.exam.mc.scoring (all-or-nothing | partial | kprim) picks the multi rule.

export type McType = 'single' | 'multi' | 'kprim';
export type MultiRule = 'all-or-nothing' | 'partial' | 'kprim';

export const MULTI_RULES: readonly MultiRule[] = ['all-or-nothing', 'partial', 'kprim'];

export interface ScoredOption {
  key: string;
  correct: boolean;
}

export function isMcType(value: unknown): value is McType {
  return value === 'single' || value === 'multi' || value === 'kprim';
}

export function multiRule(value: unknown): MultiRule {
  return MULTI_RULES.includes(value as MultiRule) ? (value as MultiRule) : 'all-or-nothing';
}

/** Number of options decided right: selected-and-correct or unselected-and-wrong. */
export function decidedRight(
  options: readonly ScoredOption[],
  chosen: readonly string[],
  answered?: readonly string[],
): number {
  const picked = new Set(chosen);
  const judged = answered ? new Set(answered) : null;
  let right = 0;
  for (const opt of options) {
    if (judged && !judged.has(opt.key)) continue;
    if (picked.has(opt.key) === opt.correct) right++;
  }
  return right;
}

/** Kprim rule for n statements: all right → 1, one wrong → 0.5, otherwise 0. */
function kprimRule(right: number, n: number): number {
  if (n > 0 && right === n) return 1;
  if (n > 1 && right === n - 1) return 0.5;
  return 0;
}

export function score(
  type: McType,
  options: readonly ScoredOption[],
  chosen: readonly string[],
  rule: MultiRule = 'all-or-nothing',
  answered?: readonly string[],
): number {
  const n = options.length;
  if (n === 0) return 0;
  switch (type) {
    case 'single': {
      if (chosen.length !== 1) return 0;
      return options.some((o) => o.key === chosen[0] && o.correct) ? 1 : 0;
    }
    case 'multi': {
      const right = decidedRight(options, chosen);
      if (rule === 'partial') return Math.max(0, (right - (n - right)) / n);
      if (rule === 'kprim') return kprimRule(right, n);
      return right === n ? 1 : 0;
    }
    case 'kprim':
      return kprimRule(decidedRight(options, chosen, answered), n);
  }
}

/** A score counts as correct (for Leitner and "mistakes") only when it is full marks. */
export function isCorrect(value: number): boolean {
  return value >= 1 - 1e-9;
}

/** Sure but not fully right: a misconception (§2.11). */
export function isMisconception(value: number, conf: 'sure' | 'unsure'): boolean {
  return conf === 'sure' && !isCorrect(value);
}

/** Points for one exam question: its share of the MC part times the score. */
export function examPoints(value: number, pointsEach: number): number {
  return Math.round(value * pointsEach * 100) / 100;
}

/**
 * Grade estimate on the German 1.0–5.0 scale: the pass mark is 4.0, full points 1.0, and
 * the range between them is split into ten equal steps (1.0, 1.3, 1.7 … 3.7, 4.0).
 * Returns null when the exam defines no pass mark.
 */
export function gradeEstimate(total: number, points: number, pass: number | null): number | null {
  if (pass === null || !(points > pass)) return null;
  if (total < pass) return 5.0;
  const steps = [4.0, 3.7, 3.3, 3.0, 2.7, 2.3, 2.0, 1.7, 1.3, 1.0];
  const k = Math.min(9, Math.floor(((total - pass) / (points - pass)) * 10 + 1e-9));
  return steps[Math.max(0, k)] ?? 1.0;
}
