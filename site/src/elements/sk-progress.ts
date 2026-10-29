// <sk-progress data-course data-topics='[{id, title}]' [data-exams='{"id":{"title","points"}}']>
// (docs/architecture.md §2.11, §3.2).
//
// Reads the progress document and shows: an overall ring, per-topic bars (accuracy over the
// last 10 attempts of the topic, as progress.py computes it), due reviews, misconceptions
// (last answer sure but not fully right), sure/unsure calibration and the mock exam history.
// The MC topic comes from the question id (mc-<topic>-NNN); exam-only questions are left out.
// Updates live when progress changes on this page or in another tab.

import { dayOf, isDue } from '../lib/leitner.ts';
import { isCorrect } from '../lib/scoring.ts';
import type { ExamEntry, ExEntry, McEntry } from '../lib/store.ts';
import { courseOf, duration, examDate, h, parseJson, percent, pts, storeFor, today } from './util.ts';

interface TopicInfo {
  id: string;
  title: string;
}

interface Scored {
  t: string;
  score: number;
  conf: string;
}

interface TopicStat extends TopicInfo {
  questions: number;
  recent: Scored[];
  due: number;
  misconceptions: number;
}

export const RECENT = 10;

/** The topic of a practice question id mc-<topic>-NNN, if it is one of `topics`. */
export function mcTopic(id: string, topics: readonly string[]): string | null {
  const m = /^mc-(.+)-\d{3}$/.exec(id);
  return m && topics.includes(m[1] ?? '') ? (m[1] ?? null) : null;
}

const mean = (xs: readonly number[]): number | null =>
  xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null;

export class SkProgress extends HTMLElement {
  private ready = false;
  private unsubscribe: (() => void) | null = null;

  private get course(): string {
    return this.dataset.course || courseOf(this);
  }

  connectedCallback(): void {
    if (!this.ready) {
      this.ready = true;
      this.classList.add('sk-progress-ready');
    }
    this.unsubscribe ??= storeFor(this.course).subscribe(() => this.render());
    this.render();
  }

  disconnectedCallback(): void {
    this.unsubscribe?.();
    this.unsubscribe = null;
  }

  private render(): void {
    const topics = parseJson<unknown[]>(this.dataset.topics, [])
      .filter((t): t is TopicInfo => typeof (t as TopicInfo)?.id === 'string')
      .map((t) => ({ id: t.id, title: t.title || t.id }));
    const exams = parseJson<Record<string, { title?: string; points?: number }>>(this.dataset.exams, {});
    const ids = topics.map((t) => t.id);
    const items = storeFor(this.course).read().items;
    const day = today();
    const exam = examDate();
    const stats = new Map<string, TopicStat>(
      topics.map((t) => [t.id, { ...t, questions: 0, recent: [], due: 0, misconceptions: 0 }]),
    );
    const all: Scored[] = [];
    let dueTotal = 0;
    let misTotal = 0;
    const ratings = { solved: 0, partial: 0, 'not-yet': 0 };
    const examRows: Array<{ id: string; started: string; total: number; duration_s: number }> = [];

    for (const [key, entry] of Object.entries(items)) {
      const [kind, id = ''] = key.split(/:(.*)/s);
      if (kind === 'mc') {
        const e = entry as McEntry;
        const last = e.attempts.at(-1);
        const lastDay = last ? dayOf(new Date(last.t)) : null;
        const due = isDue(e.due, lastDay, day, exam);
        const mis = last !== undefined && last.conf === 'sure' && !isCorrect(last.score);
        all.push(...e.attempts);
        const topic = mcTopic(id, ids);
        const st = topic ? stats.get(topic) : undefined;
        if (due) dueTotal++;
        if (mis) misTotal++;
        if (!st) continue;
        if (e.attempts.length) st.questions++;
        st.recent.push(...e.attempts);
        if (due) st.due++;
        if (mis) st.misconceptions++;
      } else if (kind === 'ex') {
        const r = (entry as ExEntry).rating;
        if (r) ratings[r]++;
        const e = entry as ExEntry;
        if (isDue(e.due, null, day, exam)) dueTotal++;
      } else if (kind === 'exam') {
        for (const a of (entry as ExamEntry).attempts) examRows.push({ id, ...a });
      }
    }
    for (const st of stats.values()) {
      st.recent = st.recent.sort((a, b) => (a.t < b.t ? -1 : 1)).slice(-RECENT);
    }
    const recentAll = [...stats.values()].flatMap((s) => s.recent.map((r) => r.score));
    const overall = mean(recentAll);
    const sure = all.filter((a) => a.conf === 'sure').map((a) => a.score);
    const unsure = all.filter((a) => a.conf === 'unsure').map((a) => a.score);

    this.replaceChildren(
      h('div', { class: 'sk-progress-overview' },
        ring(overall),
        h('ul', { class: 'sk-stats' },
          stat(all.length, all.length === 1 ? 'answer' : 'answers'),
          stat(dueTotal, 'due today'),
          stat(misTotal, misTotal === 1 ? 'misconception' : 'misconceptions'),
          stat(ratings.solved, 'exercises solved'))),
      h('h3', {}, 'Topics'),
      topics.length
        ? h('ul', { class: 'sk-topic-list' }, ...[...stats.values()].map((s) => topicRow(s)))
        : h('p', { class: 'sk-muted' }, 'No topics.'),
      h('h3', {}, 'Sure or unsure?'),
      calibration(sure, unsure),
      h('h3', {}, 'Mock exams'),
      examTable(examRows, exams),
    );
  }
}

function stat(value: number, label: string): HTMLElement {
  return h('li', {}, h('strong', {}, String(value)), ` ${label}`);
}

function ring(value: number | null): HTMLElement {
  const r = 36;
  const c = 2 * Math.PI * r;
  const frac = value ?? 0;
  const label = value === null ? 'No answers yet' : `${percent(value)} right in the last ${RECENT} answers per topic`;
  const wrap = h('div', { class: 'sk-ring', role: 'img', 'aria-label': label });
  wrap.innerHTML =
    `<svg viewBox="0 0 88 88" width="88" height="88" aria-hidden="true">` +
    `<circle class="sk-ring-track" cx="44" cy="44" r="${r}"/>` +
    `<circle class="sk-ring-fill" cx="44" cy="44" r="${r}" stroke-dasharray="${(frac * c).toFixed(2)} ${c.toFixed(2)}" transform="rotate(-90 44 44)"/>` +
    `</svg>`;
  wrap.append(
    h('span', { class: 'sk-ring-value', 'aria-hidden': 'true' }, value === null ? '–' : percent(value)),
    h('span', { class: 'sk-ring-label', 'aria-hidden': 'true' }, 'right'),
  );
  return wrap;
}

function meter(value: number | null, label: string): HTMLElement {
  return h('span', { class: 'sk-meter', role: 'img', 'aria-label': label },
    h('span', { class: 'sk-meter-fill', style: `width:${((value ?? 0) * 100).toFixed(1)}%` }));
}

function topicRow(s: TopicStat): HTMLElement {
  const acc = mean(s.recent.map((r) => r.score));
  const meta = s.questions
    ? [
        `${s.questions} ${s.questions === 1 ? 'question' : 'questions'} answered`,
        s.due ? `${s.due} due` : '',
        s.misconceptions ? `${s.misconceptions} ${s.misconceptions === 1 ? 'misconception' : 'misconceptions'}` : '',
      ].filter(Boolean).join(' · ')
    : 'not started';
  return h('li', { class: `sk-topic${acc === null ? ' is-empty' : ''}` },
    h('span', { class: 'sk-topic-name' }, s.title),
    meter(acc, acc === null ? `${s.title}: not started` : `${s.title}: ${percent(acc)} right`),
    h('span', { class: 'sk-topic-value' }, acc === null ? '–' : percent(acc)),
    h('span', { class: 'sk-topic-meta' }, meta));
}

function calibration(sure: number[], unsure: number[]): HTMLElement {
  const s = mean(sure);
  const u = mean(unsure);
  const row = (name: string, v: number | null, n: number) =>
    h('li', { class: 'sk-calib-row' },
      h('span', { class: 'sk-topic-name' }, name),
      meter(v, v === null ? `${name}: no answers` : `${name}: ${percent(v)} right`),
      h('span', { class: 'sk-topic-value' }, v === null ? '–' : percent(v)),
      h('span', { class: 'sk-topic-meta' }, `${n} ${n === 1 ? 'answer' : 'answers'}`));
  let text = 'Answer questions with Sure or Unsure to see how well your confidence matches.';
  if (sure.length + unsure.length >= 5) {
    if (s !== null && sure.length >= 3 && s < 0.8) {
      text = 'You are often wrong when you are sure. Review your misconceptions first.';
    } else if (u !== null && unsure.length >= 3 && u >= 0.8) {
      text = 'Your unsure answers are mostly right: you know more than you think.';
    } else {
      text = 'Your confidence matches your results well.';
    }
  }
  return h('div', { class: 'sk-calib' },
    h('ul', { class: 'sk-topic-list' }, row('When sure', s, sure.length), row('When unsure', u, unsure.length)),
    h('p', { class: 'sk-calib-text' }, text));
}

function examTable(
  rows: Array<{ id: string; started: string; total: number; duration_s: number }>,
  exams: Record<string, { title?: string; points?: number }>,
): HTMLElement {
  if (rows.length === 0) return h('p', { class: 'sk-muted' }, 'No mock exam taken yet.');
  rows.sort((a, b) => (a.started < b.started ? 1 : -1));
  return h('table', { class: 'sk-exam-history' },
    h('thead', {}, h('tr', {},
      h('th', { scope: 'col' }, 'Exam'), h('th', { scope: 'col' }, 'Date'),
      h('th', { scope: 'col' }, 'Points'), h('th', { scope: 'col' }, 'Time'))),
    h('tbody', {}, ...rows.map((r) => {
      const max = exams[r.id]?.points;
      return h('tr', {},
        h('th', { scope: 'row' }, exams[r.id]?.title ?? r.id),
        h('td', {}, new Date(r.started).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })),
        h('td', { class: 'sk-num' }, max ? `${pts(r.total)} / ${pts(max)}` : pts(r.total)),
        h('td', { class: 'sk-num' }, duration(r.duration_s * 1000)));
    })));
}
