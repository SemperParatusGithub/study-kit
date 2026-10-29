import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fnv1a, mulberry32, optionOrder, shuffled } from '../../src/lib/shuffle.ts';

// Printed by studykit.validate (site/tests/unit/fixtures/make_pdf_order.py).
const fixture = JSON.parse(
  readFileSync(new URL('./fixtures/pdf-order.json', import.meta.url), 'utf8'),
) as {
  fnv1a: Record<string, number>;
  mulberry32: { seed_id: string; values: number[] };
  n: number[];
  orders: Record<string, string[]>;
};

test('fnv1a matches studykit.validate._fnv1a, including non-ASCII input', () => {
  const ids = Object.keys(fixture.fnv1a);
  assert.ok(ids.length > 50);
  for (const id of ids) assert.equal(fnv1a(id), fixture.fnv1a[id], id);
});

test('mulberry32 matches studykit.validate._mulberry32 exactly', () => {
  const rand = mulberry32(fnv1a(fixture.mulberry32.seed_id));
  for (const expected of fixture.mulberry32.values) assert.equal(rand(), expected);
});

test('optionOrder reproduces pdf_order for every id, size and pin-last', () => {
  let checked = 0;
  for (const [id, orders] of Object.entries(fixture.orders)) {
    let k = 0;
    for (const n of fixture.n) {
      for (const pin of [false, true]) {
        const expected = [...(orders[k++] ?? '')].map(Number);
        assert.deepEqual(optionOrder(id, n, pin), expected, `${id} n=${n} pin=${pin}`);
        checked++;
      }
    }
  }
  assert.ok(checked > 1500, `only ${checked} cases`);
});

test('spot values printed by pdf_order', () => {
  // uv run --frozen python -c "from studykit.validate import pdf_order; print(pdf_order('mc-rc-tiefpass-001', 5, True))"
  assert.deepEqual(optionOrder('mc-rc-tiefpass-001', 5, true), [1, 0, 2, 3, 4]);
  assert.deepEqual(optionOrder('mc-rc-tiefpass-001', 4, false), [1, 0, 2, 3]);
});

test('pin-last keeps the last option last and the order is a permutation', () => {
  for (let i = 1; i <= 200; i++) {
    const id = `mc-topic-${String(i).padStart(3, '0')}`;
    for (const n of [3, 4, 5, 6]) {
      const order = optionOrder(id, n, true);
      assert.equal(order[n - 1], n - 1);
      assert.deepEqual([...order].sort(), Array.from({ length: n }, (_, k) => k));
    }
  }
});

test('the shuffle is deterministic and not the identity for most ids', () => {
  let moved = 0;
  for (let i = 1; i <= 100; i++) {
    const id = `mc-x-${String(i).padStart(3, '0')}`;
    assert.deepEqual(optionOrder(id, 5), optionOrder(id, 5));
    if (optionOrder(id, 5).some((v, k) => v !== k)) moved++;
  }
  assert.ok(moved > 90);
});

test('shuffled is a seeded permutation that leaves its input alone', () => {
  const items = Array.from({ length: 20 }, (_, i) => i);
  const a = shuffled(items, 'seed-1');
  assert.deepEqual(a, shuffled(items, 'seed-1'));
  assert.notDeepEqual(a, shuffled(items, 'seed-2'));
  assert.deepEqual([...a].sort((x, y) => x - y), items);
  assert.deepEqual(items, Array.from({ length: 20 }, (_, i) => i));
});
