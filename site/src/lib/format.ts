// Formatting for UI chrome (English, docs/architecture.md §0). Dates are ISO YYYY-MM-DD
// strings throughout and are treated as calendar days, never shifted by time zones.

const DAY_MS = 86_400_000;

function utc(iso: string): Date {
  return new Date(`${iso.slice(0, 10)}T00:00:00Z`);
}

const LONG = new Intl.DateTimeFormat('en-GB', {
  weekday: 'short',
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  timeZone: 'UTC',
});
const SHORT = new Intl.DateTimeFormat('en-GB', {
  weekday: 'short',
  day: 'numeric',
  month: 'short',
  timeZone: 'UTC',
});
const DAY_MONTH = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' });

/** "Mon 15 Feb 2027" */
export function formatDate(iso: string): string {
  return LONG.format(utc(iso)).replace(',', '');
}

/** "Mon 2 Nov" */
export function formatDay(iso: string): string {
  return SHORT.format(utc(iso)).replace(',', '');
}

/** "2 Nov" */
export function formatDayMonth(iso: string): string {
  return DAY_MONTH.format(utc(iso));
}

/** Today in the build machine's local calendar, as YYYY-MM-DD. */
export function todayIso(now: Date = new Date()): string {
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 10);
}

/** Whole days from `a` to `b` (positive when b is later). */
export function daysBetween(a: string, b: string): number {
  return Math.round((utc(b).getTime() - utc(a).getTime()) / DAY_MS);
}

/** Monday of the ISO week that contains `iso`. */
export function weekStart(iso: string): string {
  const d = utc(iso);
  const back = (d.getUTCDay() + 6) % 7;
  return new Date(d.getTime() - back * DAY_MS).toISOString().slice(0, 10);
}

export function plural(n: number, one: string, many = `${one}s`): string {
  return `${n} ${n === 1 ? one : many}`;
}

/** 10 -> "10", 2.5 -> "2.5" */
export function formatNumber(n: number): string {
  return Number.isInteger(n) ? String(n) : String(Math.round(n * 100) / 100);
}

/** 90 -> "1 h 30 min" (with no-break spaces, so a value never wraps from its unit) */
export function formatMinutes(min: number): string {
  if (min < 60) return `${min} min`;
  const h = Math.floor(min / 60);
  const m = min % 60;
  return m ? `${h} h ${m} min` : `${h} h`;
}

export const DIFFICULTY: Record<number, string> = {
  1: 'Worked example',
  2: 'Standard',
  3: 'Advanced',
  4: 'Exam-hard',
};

export const MC_TYPE: Record<string, string> = {
  single: 'Single choice',
  multi: 'Multiple choice',
  kprim: 'Kprim',
};

export const SESSION_KIND: Record<string, string> = {
  learn: 'Learn',
  review: 'Review',
  mixed: 'Mixed',
  'mock-exam': 'Mock exam',
  cheatsheet: 'Cheat sheet',
  buffer: 'Buffer',
};

export const EXAM_FORMAT: Record<string, string> = {
  written: 'Written exam',
  mc: 'Multiple-choice exam',
  oral: 'Oral exam',
  mixed: 'Written exam with MC part',
};
