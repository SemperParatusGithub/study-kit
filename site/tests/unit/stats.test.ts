import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  behindCount,
  dueCount,
  examSummary,
  exerciseStatus,
  exercisesDue,
  mastery,
  nextSession,
  RECENT,
  topicResolver,
  topicStats,
  weakestTopics,
  type Items,
  type TopicInfo,
} from '../../src/lib/stats.ts';

const TODAY = '2026-11-10';
const EXAM = '2027-02-15';

const at = (day: string, score: number, conf: 'sure' | 'unsure' = 'unsure') => ({
  t: `${day}T12:00:00`,
  chosen: ['A'],
  score,
  conf,
  ms: 1000,
});

const TOPICS: TopicInfo[] = [
  { id: 'spannungsteiler', title: 'Spannungsteiler', weight: 0.25, href: '/s/', mc: ['mc-spannungsteiler-001', 'mc-spannungsteiler-002'] },
  { id: 'wechselstrom', title: 'Wechselstrom', weight: 0.35, href: '/w/', mc: ['mc-wechselstrom-001'] },
  { id: 'rc-filter', title: 'RC-Filter', weight: 0.4, href: null, mc: ['mc-rc-filter-001', 'mc-rc-filter-002'] },
];

const ITEMS: Items = {
  // due yesterday, right last time
  'mc:mc-spannungsteiler-001': { h: 'aaaaaaaa', box: 2, due: '2026-11-09', attempts: [at('2026-11-06', 1)] },
  // due in the future, wrong (unsure)
  'mc:mc-spannungsteiler-002': { h: 'aaaaaaaa', box: 1, due: '2026-11-11', attempts: [at('2026-11-10', 0)] },
  // sure but wrong: box 0, due today, a misconception
  'mc:mc-rc-filter-001': { h: 'aaaaaaaa', box: 0, due: '2026-11-10', attempts: [at('2026-11-10', 0, 'sure')] },
  // a retired question (no longer in any bank): never counted
  'mc:mc-rc-filter-099': { h: 'aaaaaaaa', box: 0, due: '2026-11-01', attempts: [at('2026-11-01', 0)] },
  // exam-only question
  'mc:pk1-mc-01': { h: 'aaaaaaaa', box: null, due: null, attempts: [at('2026-11-05', 1)] },
  'ex:ex-a': { h: 'aaaaaaaa', hints: 0, answer_ok: true, rating: 'solved', box: 2, due: '2026-11-10' },
  'ex:ex-b': { h: 'aaaaaaaa', hints: 2, answer_ok: null, rating: 'partial', box: 1, due: '2026-11-12' },
  'exam:probeklausur-1': {
    attempts: [
      { started: '2026-11-04T09:00:00Z', duration_s: 3000, points: { mc: 10 }, total: 62 },
      { started: '2026-11-08T09:00:00Z', duration_s: 3300, points: { mc: 12 }, total: 55 },
    ],
  },
  'plan:s-1': { done: true },
};

test('questions map to topics by the bank lists, else by id', () => {
  const byList = topicResolver(TOPICS);
  assert.equal(byList('mc-rc-filter-001'), 'rc-filter');
  assert.equal(byList('mc-rc-filter-099'), null); // retired
  assert.equal(byList('pk1-mc-01'), null);
  const byId = topicResolver([{ id: 'rc-filter', title: '' }, { id: 'rc', title: '' }]);
  assert.equal(byId('mc-rc-filter-007'), 'rc-filter');
  assert.equal(byId('mc-rc-007'), 'rc');
  assert.equal(byId('mc-other-001'), null);
});

test('topic accuracy over the last 10 attempts, due and misconceptions', () => {
  const stats = topicStats(ITEMS, TOPICS, TODAY, EXAM);
  assert.deepEqual(stats.map((s) => s.id), ['spannungsteiler', 'wechselstrom', 'rc-filter']);
  const [sp, ws, rc] = stats;
  assert.equal(sp?.accuracy, 0.5);
  assert.equal(sp?.answered, 2);
  assert.equal(sp?.due, 1);
  assert.equal(ws?.accuracy, null);
  assert.equal(rc?.accuracy, 0);
  assert.equal(rc?.misconceptions, 1);
  assert.equal(rc?.due, 1);

  // only the last RECENT attempts count, across the questions of the topic
  const many = Array.from({ length: 12 }, (_, i) => at(`2026-10-${String(10 + i).padStart(2, '0')}`, i < 2 ? 0 : 1));
  const recent = topicStats({ 'mc:mc-wechselstrom-001': { h: 'aaaaaaaa', box: 3, due: null, attempts: many } }, TOPICS, TODAY, EXAM);
  assert.equal(recent[1]?.recent.length, RECENT);
  assert.equal(recent[1]?.accuracy, 1);
});

test('due count: all topics or one, retired and exam questions left out', () => {
  assert.equal(dueCount(ITEMS, TOPICS, TODAY, EXAM), 2);
  assert.equal(dueCount(ITEMS, TOPICS, TODAY, EXAM, 'rc-filter'), 1);
  assert.equal(dueCount(ITEMS, TOPICS, TODAY, EXAM, 'wechselstrom'), 0);
  // nothing is due in the two rest days before the exam
  assert.equal(dueCount(ITEMS, TOPICS, '2027-02-14', EXAM), 0);
  assert.equal(exercisesDue(ITEMS, TODAY, EXAM), 1);
});

test('weakest topics and mastery', () => {
  const stats = topicStats(ITEMS, TOPICS, TODAY, EXAM);
  assert.deepEqual(weakestTopics(stats, TOPICS, 3).map((s) => s.id), ['rc-filter', 'spannungsteiler']);
  assert.deepEqual(weakestTopics(stats, TOPICS, 1).map((s) => s.id), ['rc-filter']);
  const skipped = TOPICS.map((t) => (t.id === 'rc-filter' ? { ...t, skip: true } : t));
  assert.deepEqual(weakestTopics(stats, skipped).map((s) => s.id), ['spannungsteiler']);
  // 0.25 · 0.5 + 0.35 · 0 + 0.4 · 0, over weights that add up to 1
  assert.ok(Math.abs((mastery(stats, TOPICS) ?? -1) - 0.125) < 1e-12);
  assert.equal(mastery(topicStats({}, TOPICS, TODAY, EXAM), TOPICS), null);
  // skipped topics leave the weighting: 0.25 · 0.5 / 0.6
  assert.ok(Math.abs((mastery(stats, skipped) ?? -1) - 0.125 / 0.6) < 1e-12);
});

test('exercise status, exam summary and plan sessions', () => {
  assert.equal(exerciseStatus(ITEMS['ex:ex-a']), 'solved');
  assert.equal(exerciseStatus(ITEMS['ex:ex-b']), 'partial');
  assert.equal(exerciseStatus(undefined), 'new');
  assert.equal(exerciseStatus({ h: 'aaaaaaaa', hints: 1, answer_ok: null, rating: null, box: null, due: null }), 'new');

  const exam = examSummary(ITEMS['exam:probeklausur-1']);
  assert.equal(exam.count, 2);
  assert.equal(exam.best?.total, 62);
  assert.equal(exam.last?.total, 55);
  assert.deepEqual(examSummary(undefined), { count: 0, best: null, last: null });

  const sessions = [
    { id: 's-0', date: '2026-11-08' },
    { id: 's-1', date: '2026-11-10' },
    { id: 's-2', date: '2026-11-12' },
  ];
  assert.equal(nextSession(sessions, ITEMS, TODAY)?.id, 's-2'); // s-1 is done
  assert.equal(nextSession(sessions, {}, TODAY)?.id, 's-1');
  assert.equal(nextSession(sessions, ITEMS, '2026-11-13'), null);
  assert.equal(behindCount(sessions, ITEMS, TODAY), 1);
  assert.equal(behindCount(sessions, ITEMS, '2026-11-13'), 2);
});
