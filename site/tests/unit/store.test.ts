import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  emptyDoc,
  merge,
  migrate,
  ProgressStore,
  sanitizeEntry,
  SCHEMA,
  UNKNOWN_HASH,
  type Backend,
  type ExEntry,
  type McEntry,
  type ProgressDoc,
} from '../../src/lib/store.ts';

class FakeStorage implements Backend {
  data = new Map<string, string>();
  failWrites = false;
  getItem(k: string) {
    return this.data.get(k) ?? null;
  }
  setItem(k: string, v: string) {
    if (this.failWrites) throw new Error('QuotaExceededError');
    this.data.set(k, v);
  }
  removeItem(k: string) {
    this.data.delete(k);
  }
}

const SPEC_EXAMPLE = {
  schema: 'studykit-progress/1',
  course: 'get2',
  exported_at: '2026-11-20T18:03:00Z',
  items: {
    'mc:mc-rc-filter-003': {
      h: '9c01aa12',
      box: 3,
      due: '2026-11-24',
      attempts: [{ t: '2026-11-20T17:00:00Z', chosen: ['A'], score: 1, conf: 'sure', ms: 42000 }],
    },
    'ex:ex-rc-tp-grenzfrequenz': { h: '3f2a91c0', hints: 2, answer_ok: true, rating: 'partial', box: 2 },
    'exam:probeklausur-1': {
      attempts: [
        { started: '2026-11-19T09:00:00Z', duration_s: 6900, points: { 'pk1-t3': 12, mc: 14 }, total: 71 },
      ],
    },
    'plan:s-2026-11-02-a': { done: true },
  },
};

test('the §2.11 example survives migration unchanged (apart from defaults)', () => {
  const { doc, from, newer } = migrate(SPEC_EXAMPLE, 'get2');
  assert.equal(from, 1);
  assert.equal(newer, false);
  assert.equal(doc.schema, SCHEMA);
  assert.equal(doc.exported_at, '2026-11-20T18:03:00Z');
  assert.deepEqual(doc.items['mc:mc-rc-filter-003'], SPEC_EXAMPLE.items['mc:mc-rc-filter-003']);
  assert.deepEqual(doc.items['ex:ex-rc-tp-grenzfrequenz'], {
    h: '3f2a91c0', hints: 2, answer_ok: true, rating: 'partial', box: 2, due: null,
  });
  assert.deepEqual(doc.items['exam:probeklausur-1'], SPEC_EXAMPLE.items['exam:probeklausur-1']);
  assert.deepEqual(doc.items['plan:s-2026-11-02-a'], { done: true });
});

test('migration from version 0 (no schema, attempts with sure: boolean)', () => {
  const v0 = {
    course: 'get2',
    items: {
      'mc:mc-a-001': {
        h: 'abcdef12',
        box: 2,
        attempts: [
          { t: '2026-11-01T10:00:00Z', chosen: ['B'], score: 0, sure: true, ms: 1000 },
          { t: '2026-11-02T10:00:00Z', chosen: ['A'], score: 1, sure: false, ms: 2000 },
        ],
      },
    },
  };
  const { doc, from } = migrate(v0, 'get2');
  assert.equal(from, 0);
  const mc = doc.items['mc:mc-a-001'] as McEntry;
  assert.deepEqual(mc.attempts.map((a) => a.conf), ['sure', 'unsure']);
  assert.equal(mc.due, null);
});

test('migration drops what would not validate and never throws', () => {
  const { doc } = migrate(
    {
      schema: SCHEMA,
      items: {
        'mc:ok-001': { h: 'NOTAHASH', box: 9, due: '2026-02-30', attempts: [
          { t: 'yesterday', chosen: ['A'], score: 1, conf: 'sure', ms: 1 },
          { t: '2026-11-02T10:00:00Z', chosen: ['A', 'Z', 3], score: 0.5, conf: 'unsure', ms: 12.7 },
          { t: '2026-11-02T10:00:00Z', chosen: ['A'], score: 2, conf: 'sure', ms: 1 },
        ] },
        'Bad Key': { done: true },
        'plan:x': { done: 'yes' },
        'quiz:x': { done: true },
        'ex:e': { h: 'abcdef12', hints: -3, rating: 'great', extra: 1 },
      },
    },
    'c',
  );
  assert.deepEqual(Object.keys(doc.items).sort(), ['ex:e', 'mc:ok-001']);
  assert.deepEqual(doc.items['mc:ok-001'], {
    h: UNKNOWN_HASH, box: null, due: null,
    attempts: [{ t: '2026-11-02T10:00:00Z', chosen: ['A'], score: 0.5, conf: 'unsure', ms: 13 }],
  });
  assert.deepEqual(doc.items['ex:e'], {
    h: 'abcdef12', hints: 0, answer_ok: null, rating: null, box: null, due: null,
  });
  for (const junk of [null, 42, 'x', [], { schema: 'other/1' }]) {
    assert.deepEqual(migrate(junk, 'c').doc.items, {});
  }
  assert.equal(sanitizeEntry('plan:a', null), null);
});

test('a newer schema is read but never written', () => {
  const fake = new FakeStorage();
  fake.data.set('studykit:v1:c', JSON.stringify({ schema: 'studykit-progress/2', items: { 'plan:a': { done: true } } }));
  const s = new ProgressStore('c', fake);
  assert.equal(s.readOnly, true);
  assert.deepEqual(s.read().items, { 'plan:a': { done: true } });
  s.setPlanDone('b', true);
  assert.match(fake.data.get('studykit:v1:c') ?? '', /progress\/2/);
});

const doc = (items: ProgressDoc['items']): ProgressDoc => ({ ...emptyDoc('c'), items });

test('merge is a union: attempts combined without duplicates, newest schedule wins', () => {
  const a = doc({
    'mc:q-001': { h: 'aaaaaaaa', box: 2, due: '2026-11-05', attempts: [
      { t: '2026-11-01T10:00:00Z', chosen: ['A'], score: 1, conf: 'sure', ms: 1 },
      { t: '2026-11-02T10:00:00Z', chosen: ['A'], score: 1, conf: 'sure', ms: 1 },
    ] },
    'plan:s1': { done: false },
    'exam:e': { attempts: [{ started: '2026-11-01T09:00:00Z', duration_s: 10, points: {}, total: 5 }] },
    'ex:x': { h: 'aaaaaaaa', hints: 1, answer_ok: false, rating: null, box: 1, due: '2026-11-03' },
  });
  const b = doc({
    'mc:q-001': { h: 'bbbbbbbb', box: 0, due: '2026-11-03', attempts: [
      { t: '2026-11-02T10:00:00Z', chosen: ['A'], score: 1, conf: 'sure', ms: 1 },
      { t: '2026-11-03T10:00:00Z', chosen: ['B'], score: 0, conf: 'sure', ms: 1 },
    ] },
    'mc:q-002': { h: 'cccccccc', box: 1, due: null, attempts: [] },
    'plan:s1': { done: true },
    'exam:e': { attempts: [
      { started: '2026-11-01T09:00:00Z', duration_s: 10, points: {}, total: 5 },
      { started: '2026-11-08T09:00:00Z', duration_s: 20, points: {}, total: 7 },
    ] },
    'ex:x': { h: 'bbbbbbbb', hints: 3, answer_ok: true, rating: 'partial', box: 2, due: '2026-11-06' },
  });
  const { doc: m, added, merged } = merge(a, b);
  assert.equal(added, 1);
  assert.equal(merged, 4);
  const q = m.items['mc:q-001'] as McEntry;
  assert.deepEqual(q.attempts.map((x) => x.t), [
    '2026-11-01T10:00:00Z', '2026-11-02T10:00:00Z', '2026-11-03T10:00:00Z',
  ]);
  assert.deepEqual([q.h, q.box, q.due], ['bbbbbbbb', 0, '2026-11-03']);
  assert.deepEqual(m.items['plan:s1'], { done: true });
  assert.equal((m.items['exam:e'] as { attempts: unknown[] }).attempts.length, 2);
  assert.deepEqual(m.items['ex:x'], {
    h: 'aaaaaaaa', hints: 3, answer_ok: true, rating: 'partial', box: 2, due: '2026-11-06',
  });
  // merging is idempotent and does not touch its inputs
  assert.deepEqual(merge(m, b).doc, m);
  assert.equal((a.items['mc:q-001'] as McEntry).attempts.length, 2);
});

test('merge takes an exercise rating together with its own box and due day', () => {
  const local = doc({ 'ex:y': { h: 'aaaaaaaa', hints: 0, answer_ok: true, rating: 'solved', box: 3, due: '2026-11-05' } });
  const other = doc({ 'ex:y': { h: 'aaaaaaaa', hints: 0, answer_ok: false, rating: 'not-yet', box: 1, due: '2026-11-06' } });
  const pick = (d: ProgressDoc) => {
    const e = d.items['ex:y'] as ExEntry;
    return [e.rating, e.box, e.due];
  };
  assert.deepEqual(pick(merge(local, other).doc), ['not-yet', 1, '2026-11-06']);
  assert.deepEqual(pick(merge(other, local).doc), ['not-yet', 1, '2026-11-06']);
  const unrated = doc({ 'ex:y': { h: 'aaaaaaaa', hints: 1, answer_ok: null, rating: null, box: null, due: null } });
  assert.deepEqual(pick(merge(unrated, local).doc), ['solved', 3, '2026-11-05']);
  assert.deepEqual(pick(merge(local, unrated).doc), ['solved', 3, '2026-11-05']);
});

test('recordMc appends the attempt and applies Leitner', () => {
  const s = new ProgressStore('c', new FakeStorage());
  const r1 = s.recordMc('mc-a-001', { h: 'abcdef12', chosen: ['B', 'A'], score: 1, conf: 'sure', ms: 900 }, { today: '2026-11-02' });
  assert.deepEqual([r1.entry.box, r1.entry.due, r1.review.misconception], [2, '2026-11-05', false]);
  assert.deepEqual(r1.entry.attempts[0]?.chosen, ['A', 'B']);
  const r2 = s.recordMc('mc-a-001', { chosen: ['C'], score: 0, conf: 'sure', ms: 100 }, { today: '2026-11-05' });
  assert.deepEqual([r2.entry.box, r2.entry.due, r2.review.misconception], [0, '2026-11-05', true]);
  assert.equal(r2.entry.h, 'abcdef12');
  assert.equal(r2.entry.attempts.length, 2);
  const r3 = s.recordMc('mc-a-001', { chosen: ['A'], score: 1, conf: 'sure', ms: 1 }, { today: '2027-02-10', examDate: '2027-02-15' });
  assert.equal(r3.entry.due, '2027-02-11');
});

test('exercise helpers keep hints, answer check and rating', () => {
  const s = new ProgressStore('c', new FakeStorage());
  s.updateEx('ex-a', '12345678', { hints: 2 });
  s.updateEx('ex-a', undefined, { answer_ok: true });
  const e = s.rateEx('ex-a', undefined, 'partial', { today: '2026-11-02' });
  assert.deepEqual(e, { h: '12345678', hints: 2, answer_ok: true, rating: 'partial', box: 1, due: '2026-11-03' });
  s.rateEx('ex-b', '12345678', 'partial', { today: '2026-11-02' });
  const solved = s.rateEx('ex-b', undefined, 'solved', { today: '2026-11-03' });
  assert.deepEqual([solved.rating, solved.box, solved.due], ['solved', 2, '2026-11-06']);
});

test('rating an exercise again before its review replaces the rating, it moves no further', () => {
  const s = new ProgressStore('c', new FakeStorage());
  const d = { today: '2026-11-02' };
  const first = s.rateEx('ex-a', '12345678', 'solved', d);
  assert.deepEqual([first.box, first.due], [2, '2026-11-05']);
  // clicking "Solved" again, or a double click: the same rating of the same attempt
  for (let i = 0; i < 4; i++) assert.deepEqual(s.rateEx('ex-a', undefined, 'solved', d), first);
  // changed within the attempt: partly, then solved again
  assert.deepEqual(s.rateEx('ex-a', undefined, 'partial', d).box, 1);
  assert.deepEqual(s.rateEx('ex-a', undefined, 'solved', d), first);
  // from a higher box: the review moves it up once, re-rating keeps it there
  s.updateEx('ex-b', '12345678', { rating: 'solved', box: 3, due: '2026-11-02' });
  const reviewed = s.rateEx('ex-b', undefined, 'solved', d);
  assert.deepEqual([reviewed.box, reviewed.due], [4, '2026-11-16']);
  assert.deepEqual(s.rateEx('ex-b', undefined, 'solved', d), reviewed);
  assert.equal(s.rateEx('ex-b', undefined, 'solved', { today: '2026-11-05' }).box, 4);
  // the top box stays the top box
  s.updateEx('ex-c', '12345678', { rating: 'solved', box: 5, due: '2026-12-02' });
  assert.equal(s.rateEx('ex-c', undefined, 'solved', d).box, 5);
});

test('more than one hint caps "solved" at "partial", also a rating given before the hints', () => {
  const s = new ProgressStore('c', new FakeStorage());
  // rated with two hints open: stored as partial
  s.useHints('ex-a', '12345678', 2, { today: '2026-11-02' });
  const a = s.rateEx('ex-a', undefined, 'solved', { today: '2026-11-02' });
  assert.deepEqual([a.rating, a.box, a.due], ['partial', 1, '2026-11-03']);
  // rated "solved" first, then hints: one hint keeps it, the second caps it
  s.rateEx('ex-b', '12345678', 'solved', { today: '2026-11-02' });
  assert.deepEqual(s.get<ExEntry>('ex:ex-b')?.box, 2);
  const one = s.useHints('ex-b', undefined, 1, { today: '2026-11-02' });
  assert.deepEqual([one.hints, one.rating, one.box], [1, 'solved', 2]);
  const two = s.useHints('ex-b', undefined, 2, { today: '2026-11-02' });
  assert.deepEqual(two, { h: '12345678', hints: 2, answer_ok: null, rating: 'partial', box: 1, due: '2026-11-03' });
  // the count never goes down, and other ratings are left alone
  assert.equal(s.useHints('ex-b', undefined, 1, { today: '2026-11-02' }).hints, 2);
  s.rateEx('ex-c', undefined, 'not-yet', { today: '2026-11-02' });
  assert.equal(s.useHints('ex-c', undefined, 3).rating, 'not-yet');
});

test('a review is a new attempt: the hints of the rating before it no longer count', () => {
  const fake = new FakeStorage();
  const s = new ProgressStore('c', fake);
  const d1 = { today: '2026-11-23' };
  s.useHints('ex-a', '12345678', 2, d1);
  assert.deepEqual(s.rateEx('ex-a', undefined, 'solved', d1), {
    h: '12345678', hints: 2, answer_ok: null, rating: 'partial', box: 1, due: '2026-11-24',
  });
  // the same day the rating's hints still count
  assert.equal(s.exHints('ex-a', d1), 2);
  // due the next day: a new attempt without hints, rated "solved" without the cap
  const d2 = { today: '2026-11-24' };
  assert.equal(s.exHints('ex-a', d2), 0);
  assert.deepEqual(s.rateEx('ex-a', undefined, 'solved', d2), {
    h: '12345678', hints: 0, answer_ok: null, rating: 'solved', box: 2, due: '2026-11-27',
  });
  // a later review with one hint: kept in the session state until rated, then stored
  const d3 = { today: '2026-11-28' };
  assert.equal(s.useHints('ex-a', undefined, 1, d3).hints, 0);
  assert.equal(s.exHints('ex-a', d3), 1);
  assert.equal(s.get<ExEntry>('ex:ex-a')?.rating, 'solved');
  // a reload keeps the count; it never goes down within the attempt
  const again = new ProgressStore('c', fake);
  assert.equal(again.useHints('ex-a', undefined, 0, d3).hints, 0);
  assert.equal(again.exHints('ex-a', d3), 1);
  // two hints in the review cap it, and rating closes the review
  again.useHints('ex-a', undefined, 2, d3);
  assert.deepEqual(again.rateEx('ex-a', undefined, 'solved', d3), {
    h: '12345678', hints: 2, answer_ok: null, rating: 'partial', box: 1, due: '2026-11-29',
  });
  assert.equal(again.session('ex:ex-a'), undefined);
  assert.equal(again.exHints('ex-a', d3), 2);
  // a review left from an older due day does not count
  again.setSession('ex:ex-a', { due: '2026-11-24', hints: 3 });
  assert.equal(again.exHints('ex-a', { today: '2026-11-29' }), 0);
  // the rest days before the exam: nothing is due, but the due day has come
  assert.equal(again.exHints('ex-a', { today: '2026-11-29', examDate: '2026-11-30' }), 0);
});

test('merge caps a "solved" that meets the other side\'s hints', () => {
  const solvedHere = doc({ 'ex:z': { h: 'aaaaaaaa', hints: 0, answer_ok: true, rating: 'solved', box: 2, due: '2026-11-08' } });
  const hintsThere = doc({ 'ex:z': { h: 'aaaaaaaa', hints: 2, answer_ok: null, rating: 'partial', box: 1, due: '2026-11-03' } });
  for (const m of [merge(solvedHere, hintsThere).doc, merge(hintsThere, solvedHere).doc]) {
    assert.deepEqual(m.items['ex:z'], { h: 'aaaaaaaa', hints: 2, answer_ok: true, rating: 'partial', box: 1, due: '2026-11-03' });
  }
});

test('export has the file name and shape studykit.model.Progress validates', () => {
  const fake = new FakeStorage();
  const s = new ProgressStore('mini', fake);
  s.recordMc('mc-rc-tiefpass-001', { h: 'abcdef12', chosen: ['A'], score: 1, conf: 'sure', ms: 5 }, { today: '2026-11-02' });
  s.setPlanDone('s-2026-11-02-a', true);
  s.addExamAttempt('probeklausur-1', { started: '2026-11-02T09:00:00.000Z', duration_s: 60, points: { 'pk1-t1': 6, mc: 2 }, total: 8 });
  const { filename, text } = s.exportFile(new Date(2026, 10, 20, 12));
  assert.equal(filename, 'studykit-progress-mini-2026-11-20.json');
  const data = JSON.parse(text);
  assert.deepEqual(Object.keys(data), ['schema', 'course', 'exported_at', 'items']);
  assert.equal(data.schema, 'studykit-progress/1');
  assert.equal(data.course, 'mini');
  assert.ok(!Number.isNaN(Date.parse(data.exported_at)));
  assert.deepEqual(Object.keys(data.items).sort(), [
    'exam:probeklausur-1', 'mc:mc-rc-tiefpass-001', 'plan:s-2026-11-02-a',
  ]);
});

test('import merges a file of the same course and rejects others', () => {
  const s = new ProgressStore('get2', new FakeStorage());
  s.setPlanDone('s-2026-11-02-a', false);
  const r = s.importText(JSON.stringify(SPEC_EXAMPLE));
  assert.equal(r.ok, true);
  assert.deepEqual([r.added, r.merged], [3, 1]);
  assert.equal(r.message, 'Imported 4 items (3 new, 1 merged).');
  assert.deepEqual(s.get('plan:s-2026-11-02-a'), { done: true });
  const one = new ProgressStore('get2', new FakeStorage());
  const single = { ...SPEC_EXAMPLE, items: { 'plan:s-2026-11-02-a': { done: true } } };
  assert.equal(one.importText(JSON.stringify(single)).message, 'Imported 1 item (1 new, 0 merged).');
  assert.equal(s.importText('{nope').ok, false);
  const other = s.importText(JSON.stringify({ ...SPEC_EXAMPLE, course: 'other' }));
  assert.equal(other.ok, false);
  assert.match(other.message, /other/);
  for (const course of [undefined, 42, '']) {
    const none = s.importText(JSON.stringify({ ...SPEC_EXAMPLE, course }));
    assert.equal(none.ok, false);
    assert.equal(none.message, 'This progress file names no course, so it cannot be imported.');
  }
  // round trip: export → import into an empty store gives the same items
  const t = new ProgressStore('get2', new FakeStorage());
  t.importText(s.exportFile().text);
  assert.deepEqual(t.read().items, s.read().items);
});

test('import keeps only what studykit.model.Progress accepts: ISO timestamps, safe integers', () => {
  const s = new ProgressStore('get2', new FakeStorage());
  const attempt = { chosen: ['A'], score: 1, conf: 'sure', ms: 5 };
  const file = {
    schema: 'studykit-progress/1',
    course: 'get2',
    exported_at: 'Nov 20 2026',
    items: {
      'mc:mc-a-001': {
        h: 'abcdef12', box: 2, due: '2026-11-24',
        attempts: [
          { ...attempt, t: 'Oct 3 2026' },
          { ...attempt, t: '1' },
          { ...attempt, t: '2026-02-30T10:00:00Z' },
          { ...attempt, t: '2026-11-20T17:00:00Z', ms: 1e21 },
          { ...attempt, t: '2026-11-21 08:15:00+01:00' },
          { ...attempt, t: '2026-11-22' },
        ],
      },
      'ex:ex-a': { h: 'abcdef12', hints: 1e21, answer_ok: null, rating: null, box: null, due: null },
      'exam:pk-1': {
        attempts: [
          { started: '1', duration_s: 60, points: { mc: 1 }, total: 1 },
          { started: '2026-11-19T09:00:00Z', duration_s: 1e21, points: { mc: 2 }, total: 2 },
        ],
      },
    },
  };
  assert.equal(s.importText(JSON.stringify(file)).ok, true);
  const out = JSON.parse(s.exportFile().text);
  assert.deepEqual(
    out.items['mc:mc-a-001'].attempts.map((a: { t: string; ms: number }) => [a.t, a.ms]),
    [['2026-11-20T17:00:00Z', 0], ['2026-11-21 08:15:00+01:00', 5], ['2026-11-22', 5]],
  );
  assert.equal(out.items['ex:ex-a'].hints, 0);
  assert.deepEqual(out.items['exam:pk-1'].attempts, [
    { started: '2026-11-19T09:00:00Z', duration_s: 0, points: { mc: 2 }, total: 2 },
  ]);
  assert.ok(!/e\+/.test(s.exportFile().text), 'no number in exponent notation');
});

test('storage failures fall back to memory without throwing', () => {
  const fake = new FakeStorage();
  fake.failWrites = true;
  const s = new ProgressStore('q', fake);
  s.setPlanDone('a', true);
  assert.equal(s.persistent, false);
  const broken: Backend = {
    getItem() { throw new Error('SecurityError'); },
    setItem() { throw new Error('SecurityError'); },
    removeItem() { throw new Error('SecurityError'); },
  };
  const b = new ProgressStore('r', broken);
  b.setPlanDone('a', true);
  assert.deepEqual(b.get('plan:a'), { done: true });
  const none = new ProgressStore('n', null);
  assert.equal(none.persistent, false);
  assert.equal(none.readable, false);
  none.setPlanDone('a', true);
  assert.deepEqual(none.get('plan:a'), { done: true });
});

test('full storage: stored progress stays readable, failed writes stay visible, export has both', () => {
  const fake = new FakeStorage();
  const before = new ProgressStore('mini', fake);
  before.recordMc('mc-a-001', { h: 'abcdef12', chosen: ['A'], score: 1, conf: 'sure', ms: 5 }, { today: '2026-11-02' });
  fake.failWrites = true; // the origin's quota is used up (e.g. by another site on localhost)

  const s = new ProgressStore('mini', fake); // the next page load
  assert.equal(s.persistent, false);
  assert.equal(s.readable, true);
  assert.equal(s.get<McEntry>('mc:mc-a-001')?.box, 2);
  s.setPlanDone('s-1', true);
  s.recordMc('mc-a-001', { chosen: ['B'], score: 0, conf: 'sure', ms: 5 }, { today: '2026-11-05' });
  assert.deepEqual(s.get('plan:s-1'), { done: true });
  assert.equal(s.get<McEntry>('mc:mc-a-001')?.attempts.length, 2);
  assert.deepEqual(Object.keys(JSON.parse(s.exportFile().text).items).sort(), ['mc:mc-a-001', 'plan:s-1']);
  // the stored document is untouched; the session state works the same way
  assert.equal((JSON.parse(fake.data.get(s.key) ?? '{}').items['mc:mc-a-001'] as McEntry).attempts.length, 1);
  s.setSession('exam:e', { started: 'x' });
  assert.deepEqual(s.session('exam:e'), { started: 'x' });

  // once space is free again the next write stores everything
  fake.failWrites = false;
  s.setPlanDone('s-2', true);
  assert.equal(s.persistent, true);
  assert.deepEqual(Object.keys(JSON.parse(fake.data.get(s.key) ?? '{}').items).sort(), ['mc:mc-a-001', 'plan:s-1', 'plan:s-2']);
});

test('session state is separate from the exported document', () => {
  const fake = new FakeStorage();
  const s = new ProgressStore('c', fake);
  s.setSession('exam:e', { started: '2026-11-02T09:00:00Z' });
  assert.deepEqual(s.session('exam:e'), { started: '2026-11-02T09:00:00Z' });
  assert.equal(JSON.parse(s.exportFile().text).items['exam:e'], undefined);
  s.setSession('exam:e', null);
  assert.equal(s.session('exam:e'), undefined);
  assert.equal(fake.data.has('studykit:v1:c:session'), false);
});

test('saveExamAttempt replaces the attempt with the same start time', () => {
  const s = new ProgressStore('c', new FakeStorage());
  const a = { started: '2026-11-02T09:00:00.000Z', duration_s: 60, points: { t1: 0, mc: 4 }, total: 4 };
  s.saveExamAttempt('e', a);
  s.saveExamAttempt('e', { ...a, points: { t1: 6, mc: 4 }, total: 10 });
  s.saveExamAttempt('e', { ...a, started: '2026-11-01T09:00:00.000Z' });
  const e = s.get<{ attempts: Array<{ started: string; total: number }> }>('exam:e');
  assert.deepEqual(e?.attempts.map((x) => [x.started.slice(0, 10), x.total]), [['2026-11-01', 4], ['2026-11-02', 10]]);
});

test('update rejects keys outside the schema', () => {
  const s = new ProgressStore('c', new FakeStorage());
  assert.throws(() => s.update('quiz:x', () => ({ done: true })), /invalid progress key/);
  const ex = s.updateEx('ex-1', 'not-a-hash', {});
  assert.equal((ex as ExEntry).h, UNKNOWN_HASH);
});
