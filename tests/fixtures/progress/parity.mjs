// Runs the site's own progress code (site/src/lib/store.ts and stats.ts, through Node's
// type stripping) on the shared fixture cases and prints the results as JSON, so
// tests/py/test_progress.py can compare studykit.progress with them value for value.
//
//   node tests/fixtures/progress/parity.mjs < cases.json
//
// Input: {merge: [{local, incoming}], stats: [{items, topics, today, examDate}]}
// The time zone is the process's (the Python test sets TZ and passes the same zone).

import { readFileSync } from 'node:fs';
import { merge, migrate } from '../../../site/src/lib/store.ts';
import {
  behindCount,
  dueCount,
  examSummary,
  exerciseStatus,
  exercisesDue,
  mastery,
  nextSession,
  topicStats,
  weakestTopics,
} from '../../../site/src/lib/stats.ts';

const input = JSON.parse(readFileSync(0, 'utf8'));

const merges = (input.merge ?? []).map(({ local, incoming }) => {
  const a = migrate(local, local.course).doc;
  const b = migrate(incoming, incoming.course).doc;
  const { doc, added, merged } = merge(a, b);
  return { items: doc.items, added, merged };
});

const stats = (input.stats ?? []).map(({ items, topics, today, examDate, sessions }) => {
  const st = topicStats(items, topics, today, examDate);
  const exercises = {};
  for (const [key, entry] of Object.entries(items)) {
    if (key.startsWith('ex:')) exercises[key.slice(3)] = exerciseStatus(entry);
  }
  const exams = {};
  for (const [key, entry] of Object.entries(items)) {
    if (key.startsWith('exam:')) exams[key.slice(5)] = examSummary(entry);
  }
  return {
    topics: st.map((s) => ({
      id: s.id,
      answered: s.answered,
      accuracy: s.accuracy,
      due: s.due,
      misconceptions: s.misconceptions,
      recent: s.recent.length,
    })),
    mastery: mastery(st, topics),
    due: dueCount(items, topics, today, examDate),
    exercisesDue: exercisesDue(items, today, examDate),
    weakest: weakestTopics(st, topics).map((s) => s.id),
    exercises,
    exams,
    next: nextSession(sessions ?? [], items, today)?.id ?? null,
    behind: behindCount(sessions ?? [], items, today),
  };
});

process.stdout.write(JSON.stringify({ merge: merges, stats }));
