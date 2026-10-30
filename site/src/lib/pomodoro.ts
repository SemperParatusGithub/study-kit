// Pomodoro timer state (docs/architecture.md §3.2, <sk-pomodoro>). Pure functions over one
// JSON document that store.ts keeps under studykit:pomodoro, so the timer runs on across
// page loads and tabs: a running phase stores the time it ends, not a countdown.
//
//   {"v":1,
//    "settings":{"focus":25,"short":5,"long":15,"longEvery":4,"autoStart":false,"sound":true,"notify":false},
//    "timer":{"phase":"focus","done":0,"endsAt":null,"left":1500000}}
//
// settings are minutes (focus, short, long) and a count (longEvery: a long break after that
// many focus phases); timer.done counts the focus phases finished since the last reset;
// endsAt (epoch ms) is set while the phase runs, left (ms) while it is paused or not started.
// A stored document that does not validate falls back field by field to DEFAULTS.

export type Phase = 'focus' | 'short' | 'long';

export interface Settings {
  focus: number;
  short: number;
  long: number;
  longEvery: number;
  autoStart: boolean;
  sound: boolean;
  notify: boolean;
}

export interface Timer {
  phase: Phase;
  done: number;
  endsAt: number | null;
  left: number;
}

export interface Pomodoro {
  v: 1;
  settings: Settings;
  timer: Timer;
}

export const MINUTE = 60_000;
export const LIMITS = {
  focus: [1, 180],
  short: [1, 60],
  long: [1, 120],
  longEvery: [1, 12],
} as const satisfies Record<string, readonly [number, number]>;

export const DEFAULT_SETTINGS: Settings = {
  focus: 25,
  short: 5,
  long: 15,
  longEvery: 4,
  autoStart: false,
  sound: true,
  notify: false,
};

export const PHASE_LABELS: Record<Phase, string> = { focus: 'Focus', short: 'Short break', long: 'Long break' };

/** The length of a phase in ms. */
export function length(settings: Settings, phase: Phase): number {
  return settings[phase] * MINUTE;
}

export function fresh(settings: Settings = DEFAULT_SETTINGS): Pomodoro {
  return { v: 1, settings: { ...settings }, timer: { phase: 'focus', done: 0, endsAt: null, left: length(settings, 'focus') } };
}

function whole(v: unknown, [lo, hi]: readonly [number, number], fallback: number): number {
  return typeof v === 'number' && Number.isInteger(v) && v >= lo && v <= hi ? v : fallback;
}

function flag(v: unknown, fallback: boolean): boolean {
  return typeof v === 'boolean' ? v : fallback;
}

/** Settings from any value: valid fields are kept, the rest come from DEFAULT_SETTINGS. */
export function sanitizeSettings(v: unknown): Settings {
  const s = (v && typeof v === 'object' ? v : {}) as Record<string, unknown>;
  const d = DEFAULT_SETTINGS;
  return {
    focus: whole(s.focus, LIMITS.focus, d.focus),
    short: whole(s.short, LIMITS.short, d.short),
    long: whole(s.long, LIMITS.long, d.long),
    longEvery: whole(s.longEvery, LIMITS.longEvery, d.longEvery),
    autoStart: flag(s.autoStart, d.autoStart),
    sound: flag(s.sound, d.sound),
    notify: flag(s.notify, d.notify),
  };
}

/** The stored document, or a fresh timer when there is none or it does not validate. */
export function parse(text: string | null): Pomodoro {
  let raw: unknown = null;
  try {
    raw = text ? JSON.parse(text) : null;
  } catch {
    raw = null;
  }
  const doc = (raw && typeof raw === 'object' ? raw : {}) as Record<string, unknown>;
  const settings = sanitizeSettings(doc.settings);
  const t = (doc.timer && typeof doc.timer === 'object' ? doc.timer : {}) as Record<string, unknown>;
  const phase: Phase = t.phase === 'short' || t.phase === 'long' ? t.phase : 'focus';
  const full = length(settings, phase);
  const endsAt = typeof t.endsAt === 'number' && Number.isFinite(t.endsAt) ? t.endsAt : null;
  const left = typeof t.left === 'number' && t.left > 0 && t.left <= full ? t.left : full;
  const done = typeof t.done === 'number' && Number.isSafeInteger(t.done) && t.done >= 0 ? t.done : 0;
  return { v: 1, settings, timer: { phase, done, endsAt, left } };
}

export function serialize(p: Pomodoro): string {
  return JSON.stringify(p);
}

export function isRunning(p: Pomodoro): boolean {
  return p.timer.endsAt !== null;
}

/** Started and not reset: running, or paused part way through a phase. */
export function isActive(p: Pomodoro): boolean {
  return isRunning(p) || p.timer.left < length(p.settings, p.timer.phase) || p.timer.phase !== 'focus' || p.timer.done > 0;
}

/** Time left in the current phase at `now`, in ms. */
export function remaining(p: Pomodoro, now: number): number {
  return p.timer.endsAt === null ? p.timer.left : Math.max(0, p.timer.endsAt - now);
}

/** The phase after `phase` when `done` focus phases are finished (counting this one). */
export function following(phase: Phase, done: number, settings: Settings): Phase {
  if (phase !== 'focus') return 'focus';
  return done % settings.longEvery === 0 ? 'long' : 'short';
}

export function start(p: Pomodoro, now: number): Pomodoro {
  if (isRunning(p)) return p;
  return { ...p, timer: { ...p.timer, endsAt: now + p.timer.left } };
}

export function pause(p: Pomodoro, now: number): Pomodoro {
  if (!isRunning(p)) return p;
  return { ...p, timer: { ...p.timer, endsAt: null, left: Math.max(1000, remaining(p, now)) } };
}

/** Back to the first focus phase, stopped. */
export function reset(p: Pomodoro): Pomodoro {
  return fresh(p.settings);
}

/**
 * Go to the next phase. A finished focus phase counts (`finished`); a skipped one does not.
 * The next phase starts at `startAt` when the timer auto-starts (or `run` is true), else it
 * waits with its full length.
 */
function next(p: Pomodoro, finished: boolean, startAt: number, run: boolean): Pomodoro {
  const done = p.timer.done + (finished && p.timer.phase === 'focus' ? 1 : 0);
  const phase = following(p.timer.phase, finished ? done : p.timer.done + 1, p.settings);
  const full = length(p.settings, phase);
  return { ...p, timer: { phase, done, endsAt: run ? startAt + full : null, left: full } };
}

/** Skip to the next phase; it runs on when the skipped one was running. */
export function skip(p: Pomodoro, now: number): Pomodoro {
  return next(p, false, now, isRunning(p));
}

/**
 * Finish every phase that has ended by `now`. With autoStart the next phase starts when the
 * last one ended (so a tab that slept catches up), else the timer stops at the next phase.
 * Returns the new state and the phases that finished, oldest first.
 */
export function advance(p: Pomodoro, now: number): { state: Pomodoro; finished: Phase[] } {
  const finished: Phase[] = [];
  let state = p;
  // at most one cycle's worth of catch-up, so a timer left for days stops instead of looping
  const limit = 2 * state.settings.longEvery + 2;
  while (state.timer.endsAt !== null && state.timer.endsAt <= now && finished.length < limit) {
    finished.push(state.timer.phase);
    state = next(state, true, state.timer.endsAt, state.settings.autoStart);
  }
  if (state.timer.endsAt !== null && state.timer.endsAt <= now) state = pause(state, now);
  return { state, finished };
}

/**
 * New settings. A phase that has not started yet takes its new length; a running or paused
 * one keeps its time left (capped at the new length).
 */
export function configure(p: Pomodoro, settings: Settings): Pomodoro {
  const s = sanitizeSettings(settings);
  const full = length(s, p.timer.phase);
  const untouched = !isRunning(p) && p.timer.left === length(p.settings, p.timer.phase);
  const left = untouched ? full : Math.min(p.timer.left, full);
  return { ...p, settings: s, timer: { ...p.timer, left } };
}
