// The flash cards of a topic (docs/architecture.md §5.6): what is due and in which order. The
// schedule itself is the Leitner one of lib/leitner.ts, without an exam to clamp to; the
// entries `card:<id>` live in the progress store.

import { isDue, reviewDayOf } from './leitner.ts';
import { shuffled } from './shuffle.ts';
import type { CardEntry, Entry } from './store.ts';

export type CardState = 'new' | 'due' | 'later';
export type CardMode = 'due' | 'all';

/** From this Leitner box on (a week or more until the next review) a card counts as known. */
export const KNOWN_BOX = 3;

export interface CardRef {
  id: string;
  topic: string | null;
}

export function cardEntry(items: Record<string, Entry>, id: string): CardEntry | undefined {
  return items[`card:${id}`] as CardEntry | undefined;
}

export function cardState(entry: CardEntry | undefined, today: string): CardState {
  if (!entry || entry.reviews === 0) return 'new';
  return isDue(entry.due, reviewDayOf(entry.due, entry.box), today) ? 'due' : 'later';
}

export interface CardCounts {
  total: number;
  /** never rated */
  fresh: number;
  due: number;
  known: number;
}

export function cardCounts(ids: readonly string[], items: Record<string, Entry>, today: string): CardCounts {
  const counts: CardCounts = { total: ids.length, fresh: 0, due: 0, known: 0 };
  for (const id of ids) {
    const entry = cardEntry(items, id);
    const state = cardState(entry, today);
    if (state === 'new') counts.fresh++;
    else if (state === 'due') counts.due++;
    if ((entry?.box ?? 0) >= KNOWN_BOX) counts.known++;
  }
  return counts;
}

/**
 * The cards of one round. `due`: the reviews due, shuffled, then the new cards in the order
 * they teach. `all`: every card in that order. `topic` narrows it to one chapter.
 */
export function cardQueue<T extends CardRef>(
  cards: readonly T[],
  items: Record<string, Entry>,
  mode: CardMode,
  topic: string | null,
  today: string,
  seed: string,
): T[] {
  const mine = topic ? cards.filter((c) => c.topic === topic) : [...cards];
  if (mode === 'all') return mine;
  const due = mine.filter((c) => cardState(cardEntry(items, c.id), today) === 'due');
  const fresh = mine.filter((c) => cardState(cardEntry(items, c.id), today) === 'new');
  return [...shuffled(due, seed), ...fresh];
}

/** The next day any of the cards comes up for review after `today`, or null. */
export function nextReview(ids: readonly string[], items: Record<string, Entry>, today: string): string | null {
  let next: string | null = null;
  for (const id of ids) {
    const due = cardEntry(items, id)?.due;
    if (due && due > today && (next === null || due < next)) next = due;
  }
  return next;
}
