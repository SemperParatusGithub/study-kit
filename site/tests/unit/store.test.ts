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
  const solved = s.rateEx('ex-a', undefined, 'solved', { today: '2026-11-03' });
  assert.deepEqual([solved.box, solved.due], [2, '2026-11-06']);
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
  assert.deepEqual(s.get('plan:s-2026-11-02-a'), { done: true });
  assert.equal(s.importText('{nope').ok, false);
  const other = s.importText(JSON.stringify({ ...SPEC_EXAMPLE, course: 'other' }));
  assert.equal(other.ok, false);
  assert.match(other.message, /other/);
  // round trip: export → import into an empty store gives the same items
  const t = new ProgressStore('get2', new FakeStorage());
  t.importText(s.exportFile().text);
  assert.deepEqual(t.read().items, s.read().items);
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
  none.setPlanDone('a', true);
  assert.deepEqual(none.get('plan:a'), { done: true });
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

test('update rejects keys outside the schema', () => {
  const s = new ProgressStore('c', new FakeStorage());
  assert.throws(() => s.update('quiz:x', () => ({ done: true })), /invalid progress key/);
  const ex = s.updateEx('ex-1', 'not-a-hash', {});
  assert.equal((ex as ExEntry).h, UNKNOWN_HASH);
});
