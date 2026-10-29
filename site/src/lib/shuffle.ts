// Deterministic shuffles (docs/architecture.md §2.6, §3.2).
//
// MC options are shown in the same order as in mc.pdf: the FNV-1a 32-bit hash of the
// question id seeds mulberry32, then Fisher-Yates runs from the last option down, a
// pin-last option is left out, and the display letters (A)–(F) are assigned afterwards.
// This must stay identical to studykit.validate.pdf_order and M.order in mcq.lua;
// site/tests/unit/shuffle.test.ts checks it against values printed by Python.

/** Display letters, assigned after shuffling. */
export const LETTERS = 'ABCDEFGHIJ';

const encoder = new TextEncoder();

/** FNV-1a, 32 bit, over the UTF-8 bytes of `text`. */
export function fnv1a(text: string): number {
  let h = 0x811c9dc5;
  for (const byte of encoder.encode(text)) {
    h = Math.imul(h ^ byte, 0x01000193) >>> 0;
  }
  return h;
}

/** mulberry32: a 32-bit seeded generator returning floats in [0, 1). */
export function mulberry32(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = Math.imul(state ^ (state >>> 15), state | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function swap<T>(items: T[], a: number, b: number): void {
  const tmp = items[a] as T;
  items[a] = items[b] as T;
  items[b] = tmp;
}

/**
 * Source indices (0-based) in display order for a question with `n` options.
 * Mirrors studykit.validate.pdf_order(question_id, n, pin_last).
 */
export function optionOrder(questionId: string, n: number, pinLast = false): number[] {
  const order = Array.from({ length: n }, (_, i) => i);
  const rand = mulberry32(fnv1a(questionId));
  for (let i = pinLast ? n - 1 : n; i > 1; i--) {
    swap(order, i - 1, Math.floor(rand() * i));
  }
  return order;
}

/** A copy of `items` in a Fisher-Yates order seeded by `seed` (quiz question order). */
export function shuffled<T>(items: readonly T[], seed: string): T[] {
  const out = items.slice();
  const rand = mulberry32(fnv1a(seed));
  for (let i = out.length; i > 1; i--) {
    swap(out, i - 1, Math.floor(rand() * i));
  }
  return out;
}

/** A fresh random seed string for one quiz session. */
export function randomSeed(): string {
  const bytes = new Uint32Array(2);
  globalThis.crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(8, '0')).join('');
}
