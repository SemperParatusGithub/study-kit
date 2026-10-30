import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  advance,
  configure,
  DEFAULT_SETTINGS,
  fresh,
  isActive,
  isRunning,
  MINUTE,
  parse,
  pause,
  remaining,
  reset,
  serialize,
  skip,
  start,
} from '../../src/lib/pomodoro.ts';

const T0 = Date.UTC(2026, 9, 30, 9, 0, 0);

test('a fresh timer waits at a full focus phase', () => {
  const p = fresh();
  assert.equal(p.timer.phase, 'focus');
  assert.equal(remaining(p, T0), 25 * MINUTE);
  assert.equal(isRunning(p), false);
  assert.equal(isActive(p), false);
});

test('start, pause and resume keep the time left', () => {
  let p = start(fresh(), T0);
  assert.equal(p.timer.endsAt, T0 + 25 * MINUTE);
  assert.equal(remaining(p, T0 + 10 * MINUTE), 15 * MINUTE);
  p = pause(p, T0 + 10 * MINUTE);
  assert.equal(isRunning(p), false);
  assert.equal(isActive(p), true);
  assert.equal(remaining(p, T0 + 99 * MINUTE), 15 * MINUTE);
  p = start(p, T0 + 20 * MINUTE);
  assert.equal(p.timer.endsAt, T0 + 35 * MINUTE);
  assert.equal(start(p, T0 + 21 * MINUTE), p, 'starting a running timer changes nothing');
});

test('a finished focus phase counts and stops at its break without auto-start', () => {
  const p = start(fresh(), T0);
  const { state, finished } = advance(p, T0 + 25 * MINUTE + 500);
  assert.deepEqual(finished, ['focus']);
  assert.equal(state.timer.phase, 'short');
  assert.equal(state.timer.done, 1);
  assert.equal(isRunning(state), false);
  assert.equal(remaining(state, T0 + 30 * MINUTE), 5 * MINUTE);
});

test('every longEvery-th focus phase is followed by the long break', () => {
  let p = fresh({ ...DEFAULT_SETTINGS, longEvery: 2 });
  let now = T0;
  const phases: string[] = [];
  for (let i = 0; i < 4; i++) {
    p = start(p, now);
    now += remaining(p, now);
    p = advance(p, now).state;
    phases.push(p.timer.phase);
  }
  assert.deepEqual(phases, ['short', 'focus', 'long', 'focus']);
  assert.equal(p.timer.done, 2);
});

test('auto-start catches up with phases that ended while the tab slept', () => {
  let p = start(fresh({ ...DEFAULT_SETTINGS, autoStart: true }), T0);
  // focus 25 + short 5 + focus 25 = 55 min, then 2 minutes into the second short break
  const { state, finished } = advance(p, T0 + 57 * MINUTE);
  assert.deepEqual(finished, ['focus', 'short', 'focus']);
  assert.equal(state.timer.phase, 'short');
  assert.equal(state.timer.done, 2);
  assert.equal(remaining(state, T0 + 57 * MINUTE), 3 * MINUTE);
  p = state;
  assert.equal(isRunning(p), true);
});

test('a timer left running for days stops instead of looping', () => {
  const p = start(fresh({ ...DEFAULT_SETTINGS, autoStart: true }), T0);
  const { state, finished } = advance(p, T0 + 3 * 24 * 60 * MINUTE);
  assert.ok(finished.length <= 2 * DEFAULT_SETTINGS.longEvery + 2);
  assert.equal(isRunning(state), false);
});

test('skip moves on without counting, and keeps running when it ran', () => {
  const running = skip(start(fresh(), T0), T0 + MINUTE);
  assert.equal(running.timer.phase, 'short');
  assert.equal(running.timer.done, 0);
  assert.equal(running.timer.endsAt, T0 + 6 * MINUTE);
  const stopped = skip(fresh(), T0);
  assert.equal(stopped.timer.phase, 'short');
  assert.equal(isRunning(stopped), false);
  assert.equal(skip(stopped, T0).timer.phase, 'focus');
});

test('reset goes back to the first focus phase and keeps the settings', () => {
  const settings = { ...DEFAULT_SETTINGS, focus: 50 };
  const p = reset(skip(start(fresh(settings), T0), T0));
  assert.deepEqual(p, fresh(settings));
});

test('new settings change a waiting phase, a started one keeps its time left', () => {
  const longer = { ...DEFAULT_SETTINGS, focus: 45 };
  assert.equal(remaining(configure(fresh(), longer), T0), 45 * MINUTE);
  const paused = pause(start(fresh(), T0), T0 + 5 * MINUTE);
  assert.equal(remaining(configure(paused, longer), T0), 20 * MINUTE);
  const shorter = configure(paused, { ...DEFAULT_SETTINGS, focus: 10 });
  assert.equal(remaining(shorter, T0), 10 * MINUTE);
});

test('parse round-trips and repairs what does not validate', () => {
  const p = pause(start(fresh({ ...DEFAULT_SETTINGS, sound: false }), T0), T0 + MINUTE);
  assert.deepEqual(parse(serialize(p)), p);
  assert.deepEqual(parse(null), fresh());
  assert.deepEqual(parse('{not json'), fresh());
  const bad = parse(
    JSON.stringify({
      settings: { focus: 0, short: 7, long: 'x', longEvery: 99, autoStart: 'yes', sound: false },
      timer: { phase: 'nap', done: -1, endsAt: 'soon', left: 10 ** 12 },
    }),
  );
  assert.deepEqual(bad.settings, { ...DEFAULT_SETTINGS, short: 7, sound: false });
  assert.deepEqual(bad.timer, { phase: 'focus', done: 0, endsAt: null, left: 25 * MINUTE });
});
