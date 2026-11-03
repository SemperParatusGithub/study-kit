import { test } from 'node:test';
import assert from 'node:assert/strict';
import { cardCounts, cardQueue, cardState, nextReview, type CardRef } from '../../src/lib/cards.ts';
import { ProgressStore, merge, sanitizeEntry, type Backend, type CardEntry, type Entry } from '../../src/lib/store.ts';

const TODAY = '2026-11-03';
const entry = (box: number, due: string, reviews = 1): CardEntry => ({ h: 'aaaaaaaa', box, due, reviews });

class FakeStorage implements Backend {
  data = new Map<string, string>();
  getItem(k: string) {
    return this.data.get(k) ?? null;
  }
  setItem(k: string, v: string) {
    this.data.set(k, v);
  }
  removeItem(k: string) {
    this.data.delete(k);
  }
}

test('a card is new until it is rated, then due or later by its schedule', () => {
  assert.equal(cardState(undefined, TODAY), 'new');
  assert.equal(cardState(entry(1, '2026-11-03'), TODAY), 'due');
  assert.equal(cardState(entry(1, '2026-10-30'), TODAY), 'due');
  assert.equal(cardState(entry(2, '2026-11-04'), TODAY), 'later');
});

test('counts add up over the given cards', () => {
  const items: Record<string, Entry> = {
    'card:a': entry(1, '2026-11-01'),
    'card:b': entry(4, '2026-11-20'),
    'card:gone': entry(1, '2026-11-01'),
  };
  assert.deepEqual(cardCounts(['a', 'b', 'c'], items, TODAY), { total: 3, fresh: 1, due: 1, known: 1 });
});

test('a round brings due reviews first, new cards in their order, nothing that can wait', () => {
  const cards: CardRef[] = [
    { id: 'a', topic: 'one' },
    { id: 'b', topic: 'one' },
    { id: 'c', topic: 'two' },
    { id: 'd', topic: 'two' },
    { id: 'e', topic: 'two' },
  ];
  const items: Record<string, Entry> = {
    'card:b': entry(1, '2026-11-01'),
    'card:d': entry(1, '2026-11-03'),
    'card:e': entry(3, '2026-11-09'),
  };
  const round = cardQueue(cards, items, 'due', null, TODAY, 'seed').map((c) => c.id);
  assert.deepEqual([...round.slice(0, 2)].sort(), ['b', 'd']);
  assert.deepEqual(round.slice(2), ['a', 'c']);
  assert.deepEqual(cardQueue(cards, items, 'all', null, TODAY, 'seed').map((c) => c.id), ['a', 'b', 'c', 'd', 'e']);
  assert.deepEqual(cardQueue(cards, items, 'all', 'one', TODAY, 'seed').map((c) => c.id), ['a', 'b']);
  assert.deepEqual(cardQueue(cards, items, 'due', 'two', TODAY, 'seed').map((c) => c.id), ['d', 'c']);
});

test('the next review is the earliest due day after today', () => {
  const items: Record<string, Entry> = {
    'card:a': entry(2, '2026-11-06'),
    'card:b': entry(1, '2026-11-04'),
    'card:c': entry(1, '2026-11-01'),
  };
  assert.equal(nextReview(['a', 'b', 'c'], items, TODAY), '2026-11-04');
  assert.equal(nextReview(['c'], items, TODAY), null);
});

test('rating a card moves it through the Leitner boxes without an exam clamp', () => {
  const store = new ProgressStore('topic', new FakeStorage());
  let e = store.recordCard('card-a-001', 'abcdef12', true, { today: TODAY });
  assert.deepEqual(e, { h: 'abcdef12', box: 2, due: '2026-11-06', reviews: 1 });
  e = store.recordCard('card-a-001', 'abcdef12', true, { today: '2026-11-06' });
  assert.deepEqual([e.box, e.due, e.reviews], [3, '2026-11-13', 2]);
  e = store.recordCard('card-a-001', 'abcdef12', false, { today: '2026-11-13' });
  assert.deepEqual([e.box, e.due, e.reviews], [1, '2026-11-14', 3]);
  assert.deepEqual(store.read().items['card:card-a-001'], e);
});

test('card entries are checked, and the merge keeps the one with more reviews', () => {
  assert.deepEqual(sanitizeEntry('card:x', { h: 'zz', box: 9, due: 'soon', reviews: -1 }), {
    h: '00000000',
    box: null,
    due: null,
    reviews: 0,
  });
  const doc = (e: CardEntry) => ({
    schema: 'studykit-progress/1' as const,
    course: 'topic',
    exported_at: '2026-11-03T10:00:00Z',
    items: { 'card:x': e },
  });
  const few = entry(2, '2026-11-06', 1);
  const many = entry(1, '2026-11-04', 4);
  assert.deepEqual(merge(doc(few), doc(many)).doc.items['card:x'], many);
  assert.deepEqual(merge(doc(many), doc(few)).doc.items['card:x'], many);
  const later = entry(3, '2026-11-20', 1);
  assert.deepEqual(merge(doc(few), doc(later)).doc.items['card:x'], later);
});
