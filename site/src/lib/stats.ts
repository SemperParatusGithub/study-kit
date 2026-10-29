// Progress figures in the browser (docs/architecture.md §2.11): what the shell's
// placeholders (elements/dashboard.ts) and <sk-progress> show. Pure functions over the
// stored progress items and the course info the shell writes into the page
// (components/CourseData.astro), so they run in Node unit tests as well.
//
// - Accuracy of a topic: mean score of its last RECENT MC attempts (as progress.py).
// - Due: MC questions the Leitner schedule has due today (exam clamp included); only the
//   questions the course still has count, so a retired question never stays due.
// - Mastery: topic accuracies weighted by topic weight over the topics not skipped; a topic
//   without attempts counts 0. Null while nothing has been answered.
// - Weakest topics: answered topics with the lowest accuracy.
// - Exercise status: new, not-yet, partial or solved (the self-assessment).
// - Next session: the first plan session today or later that is not done; behind: past
//   sessions that are not done.

import { dayOf, isDue, reviewDayOf } from './leitner.ts';
import { isCorrect } from './scoring.ts';
import type { Entry, ExamAttempt, ExamEntry, ExEntry, McAttempt, McEntry, PlanEntry } from './store.ts';

export const RECENT = 10;

export interface TopicInfo {
  id: string;
  title: string;
  /** Share of the exam, 0–1. */
  weight?: number;
  skip?: boolean;
  /** Where the topic is read (summary chapter, else its MC bank), or null. */
  href?: string | null;
  /** Practice MC question ids of the topic's bank. */
  mc?: string[];
  /** Exercise ids of the topic. */
  ex?: string[];
}

export interface ExamInfo {
  id: string;
  title: string;
  points: number;
}

export interface SessionInfo {
  id: string;
  date: string;
}

/** What the shell tells the client about a course (CourseData.astro). */
export interface CourseInfo {
  id: string;
  examDate: string | null;
  topics: TopicInfo[];
  exams: ExamInfo[];
  sessions: SessionInfo[];
}

export type Items = Record<string, Entry>;
/** new: nothing done; started: hints opened or an answer checked, not rated yet. */
export type ExerciseStatus = 'new' | 'started' | 'not-yet' | 'partial' | 'solved';

const MC_ID_RE = /^mc-(.+)-\d{3}$/;

/**
 * Which topic an MC question belongs to: the topic whose question list has it, or (when no
 * topic lists its questions) the topic named in the id mc-<topic>-NNN. Null for exam-only
 * and retired questions.
 */
export function topicResolver(topics: readonly TopicInfo[]): (id: string) => string | null {
  const lists = topics.some((t) => (t.mc?.length ?? 0) > 0);
  if (lists) {
    const byId = new Map<string, string>();
    for (const t of topics) for (const q of t.mc ?? []) byId.set(q, t.id);
    return (id) => byId.get(id) ?? null;
  }
  const ids = new Set(topics.map((t) => t.id));
  return (id) => {
    const m = MC_ID_RE.exec(id);
    return m && ids.has(m[1] ?? '') ? (m[1] ?? null) : null;
  };
}

/** The day of the last attempt (local calendar day), or null. */
export function lastAttemptDay(e: McEntry): string | null {
  const t = e.attempts.at(-1)?.t;
  return t ? dayOf(new Date(t)) : null;
}

export function mcIsDue(e: McEntry, today: string, examDate: string | null): boolean {
  return isDue(e.due, lastAttemptDay(e), today, examDate);
}

/** Sure, but not fully right the last time: a misconception (§2.11). */
export function isMisconceived(e: McEntry): boolean {
  const last = e.attempts.at(-1);
  return last !== undefined && last.conf === 'sure' && !isCorrect(last.score);
}

export interface TopicStat {
  id: string;
  title: string;
  /** Questions answered at least once. */
  answered: number;
  /** The last RECENT attempts, oldest first. */
  recent: McAttempt[];
  /** Mean score of `recent`, or null without attempts. */
  accuracy: number | null;
  due: number;
  misconceptions: number;
}

export const mean = (xs: readonly number[]): number | null =>
  xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null;

function mcEntries(items: Items): Array<[string, McEntry]> {
  return Object.entries(items)
    .filter(([key]) => key.startsWith('mc:'))
    .map(([key, e]) => [key.slice(3), e as McEntry]);
}

/** Per-topic MC figures, in the order of `topics`. */
export function topicStats(
  items: Items,
  topics: readonly TopicInfo[],
  today: string,
  examDate: string | null,
): TopicStat[] {
  const topicOf = topicResolver(topics);
  const stats = new Map<string, TopicStat & { all: McAttempt[] }>(
    topics.map((t) => [
      t.id,
      { id: t.id, title: t.title || t.id, answered: 0, recent: [], accuracy: null, due: 0, misconceptions: 0, all: [] },
    ]),
  );
  for (const [id, e] of mcEntries(items)) {
    const topic = topicOf(id);
    const st = topic ? stats.get(topic) : undefined;
    if (!st) continue;
    if (e.attempts.length) st.answered++;
    st.all.push(...e.attempts);
    if (mcIsDue(e, today, examDate)) st.due++;
    if (isMisconceived(e)) st.misconceptions++;
  }
  return [...stats.values()].map(({ all, ...st }) => {
    const recent = [...all].sort((a, b) => (a.t < b.t ? -1 : a.t > b.t ? 1 : 0)).slice(-RECENT);
    return { ...st, recent, accuracy: mean(recent.map((a) => a.score)) };
  });
}

/** MC questions due today, of one topic or of all topics. */
export function dueCount(
  items: Items,
  topics: readonly TopicInfo[],
  today: string,
  examDate: string | null,
  topic?: string,
): number {
  const topicOf = topicResolver(topics);
  let n = 0;
  for (const [id, e] of mcEntries(items)) {
    const t = topicOf(id);
    if (t === null || (topic && t !== topic)) continue;
    if (mcIsDue(e, today, examDate)) n++;
  }
  return n;
}

/** An exercise whose self-assessment is due for review today (exam clamp included). */
export function exIsDue(e: ExEntry, today: string, examDate: string | null): boolean {
  return isDue(e.due, reviewDayOf(e.due, e.box), today, examDate);
}

/** Exercises whose self-assessment is due for review today. */
export function exercisesDue(items: Items, today: string, examDate: string | null): number {
  let n = 0;
  for (const [key, e] of Object.entries(items)) {
    if (key.startsWith('ex:') && exIsDue(e as ExEntry, today, examDate)) n++;
  }
  return n;
}

/** The `n` answered topics with the lowest accuracy (skipped topics left out). */
export function weakestTopics(stats: readonly TopicStat[], topics: readonly TopicInfo[], n = 3): TopicStat[] {
  const skipped = new Set(topics.filter((t) => t.skip).map((t) => t.id));
  const order = new Map(topics.map((t, i) => [t.id, i]));
  return stats
    .filter((s) => s.accuracy !== null && !skipped.has(s.id))
    .sort((a, b) => (a.accuracy ?? 0) - (b.accuracy ?? 0) || (order.get(a.id) ?? 0) - (order.get(b.id) ?? 0))
    .slice(0, n);
}

/**
 * Mastery 0–1: topic accuracies weighted by topic weight, over the topics not skipped; a
 * topic without attempts counts 0. Equal weights when none are given. Null while no
 * question has been answered.
 */
export function mastery(stats: readonly TopicStat[], topics: readonly TopicInfo[]): number | null {
  if (!stats.some((s) => s.accuracy !== null)) return null;
  const byId = new Map(stats.map((s) => [s.id, s]));
  const counted = topics.filter((t) => !t.skip);
  const weights = counted.map((t) => (typeof t.weight === 'number' && t.weight > 0 ? t.weight : 0));
  const total = weights.reduce((a, b) => a + b, 0);
  let sum = 0;
  counted.forEach((t, i) => {
    const w = total > 0 ? (weights[i] ?? 0) / total : 1 / counted.length;
    sum += w * (byId.get(t.id)?.accuracy ?? 0);
  });
  return Math.min(1, Math.max(0, sum));
}

export function exerciseStatus(entry: Entry | undefined): ExerciseStatus {
  const ex = entry as ExEntry | undefined;
  const rating = ex?.rating;
  if (rating === 'solved' || rating === 'partial' || rating === 'not-yet') return rating;
  return ex && ((ex.hints ?? 0) > 0 || typeof ex.answer_ok === 'boolean') ? 'started' : 'new';
}

export interface ExamSummary {
  count: number;
  best: ExamAttempt | null;
  last: ExamAttempt | null;
}

export function examSummary(entry: Entry | undefined): ExamSummary {
  const attempts = [...((entry as ExamEntry | undefined)?.attempts ?? [])].sort((a, b) =>
    a.started < b.started ? -1 : a.started > b.started ? 1 : 0,
  );
  const best = attempts.reduce<ExamAttempt | null>((b, a) => (b === null || a.total > b.total ? a : b), null);
  return { count: attempts.length, best, last: attempts.at(-1) ?? null };
}

export function sessionDone(items: Items, id: string): boolean {
  return (items[`plan:${id}`] as PlanEntry | undefined)?.done === true;
}

/** The first session dated today or later that is not done, or null. */
export function nextSession<S extends SessionInfo>(sessions: readonly S[], items: Items, today: string): S | null {
  return [...sessions]
    .sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0))
    .find((s) => s.date >= today && !sessionDone(items, s.id)) ?? null;
}

/** Past sessions (before today) that are not done. */
export function behindCount(sessions: readonly SessionInfo[], items: Items, today: string): number {
  return sessions.filter((s) => s.date < today && !sessionDone(items, s.id)).length;
}
