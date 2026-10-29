// <sk-progress data-course data-topics='[{id, title, mc?, ex?}]'
//   [data-exams='[{id, title, points}]' (or {"id": {title, points}})] [data-exam-date]>
// (docs/architecture.md §2.11, §3.2).
//
// Reads the progress document and shows: a mastery ring (the same figure as the course
// cards, lib/stats.ts mastery()), per-topic bars (accuracy over the
// last 10 attempts of the topic, as progress.py computes it), MC reviews due, exercises to
// review, misconceptions (last answer sure but not fully right), sure/unsure calibration and
// the mock exam history. A question belongs to the topic whose `mc` list has it (else the
// topic in its id mc-<topic>-NNN); exam-only questions count for calibration only. The
// figures come from lib/stats.ts, like the shell's placeholders (dashboard.ts). Updates live
// when progress changes on this page or in another tab.

import { isDay } from '../lib/leitner.ts';
import {
  dueCount,
  exercisesDue,
  isMisconceived,
  mastery,
  mean,
  RECENT,
  topicStats,
  type TopicInfo,
  type TopicStat,
} from '../lib/stats.ts';
import type { ExamEntry, ExEntry, McEntry } from '../lib/store.ts';
import { courseOf, duration, examDate, h, langs, parseJson, percent, pts, storeFor, today } from './util.ts';

export { RECENT };

interface Scored {
  t: string;
  score: number;
  conf: string;
}

interface ExamMeta {
  title?: string;
  points?: number;
}

/** data-exams as an array [{id, title, points}] or a map {id: {title, points}}. */
function examMeta(raw: unknown): Record<string, ExamMeta> {
  if (Array.isArray(raw)) {
    return Object.fromEntries(
      raw.filter((e): e is ExamMeta & { id: string } => typeof e?.id === 'string').map((e) => [e.id, e]),
    );
  }
  return raw && typeof raw === 'object' ? (raw as Record<string, ExamMeta>) : {};
}

export class SkProgress extends HTMLElement {
  private ready = false;
  private unsubscribe: (() => void) | null = null;
  /** lang for topic and exam titles (the element's own text is English). */
  private content: string | undefined;

  private get course(): string {
    return this.dataset.course || courseOf(this);
  }

  private get examDate(): string | null {
    const own = this.dataset.examDate;
    return isDay(own) ? own : examDate();
  }

  connectedCallback(): void {
    if (!this.ready) {
      this.ready = true;
      const lang = langs(this);
      this.content = lang.content;
      if (lang.ui) this.lang = lang.ui;
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
      .map((t) => ({ ...t, title: t.title || t.id }));
    const exams = examMeta(parseJson<unknown>(this.dataset.exams, {}));
    const items = storeFor(this.course).read().items;
    const day = today();
    const exam = this.examDate;
    const stats = topicStats(items, topics, day, exam);
    const all: Scored[] = [];
    let misTotal = 0;
    let solved = 0;
    const examRows: Array<{ id: string; started: string; total: number; duration_s: number }> = [];

    for (const [key, entry] of Object.entries(items)) {
      const sep = key.indexOf(':');
      const kind = key.slice(0, sep);
      const id = key.slice(sep + 1);
      if (kind === 'mc') {
        const e = entry as McEntry;
        all.push(...e.attempts);
        if (isMisconceived(e)) misTotal++;
      } else if (kind === 'ex') {
        if ((entry as ExEntry).rating === 'solved') solved++;
      } else if (kind === 'exam') {
        for (const a of (entry as ExamEntry).attempts) examRows.push({ id, ...a });
      }
    }
    const due = dueCount(items, topics, day, exam);
    const exDue = exercisesDue(items, day, exam);
    // one overall figure across the site: mastery, as on the course cards and the course page
    const overall = mastery(stats, topics);
    const sure = all.filter((a) => a.conf === 'sure').map((a) => a.score);
    const unsure = all.filter((a) => a.conf === 'unsure').map((a) => a.score);

    this.replaceChildren(
      h('div', { class: 'sk-progress-overview' },
        ring(overall),
        h('ul', { class: 'sk-stats' },
          stat(all.length, all.length === 1 ? 'answer' : 'answers'),
          stat(due, due === 1 ? 'review due' : 'reviews due'),
          stat(misTotal, misTotal === 1 ? 'misconception' : 'misconceptions'),
          stat(solved, solved === 1 ? 'exercise solved' : 'exercises solved'),
          exDue ? stat(exDue, exDue === 1 ? 'exercise to review' : 'exercises to review') : null)),
      h('p', { class: 'sk-progress-note' },
        `Mastery averages how many of each topic's last ${RECENT} answers were right, weighted by the topic's share of the exam; topics not started count as 0.`),
      h('h3', {}, 'Topics'),
      topics.length
        ? h('ul', { class: 'sk-topic-list' }, ...stats.map((s) => topicRow(s, this.content)))
        : h('p', { class: 'sk-muted' }, 'No topics.'),
      h('h3', {}, 'Sure or unsure?'),
      calibration(sure, unsure),
      h('h3', {}, 'Mock exams'),
      examTable(examRows, exams, this.content),
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
  const label = value === null ? 'Mastery: no answers yet' : `Mastery ${percent(value)}`;
  const wrap = h('div', { class: 'sk-ring', role: 'img', 'aria-label': label });
  wrap.innerHTML =
    `<svg viewBox="0 0 88 88" width="88" height="88" aria-hidden="true">` +
    `<circle class="sk-ring-track" cx="44" cy="44" r="${r}"/>` +
    // no fill at 0: a round line cap would still draw a dot
    (frac > 0
      ? `<circle class="sk-ring-fill" cx="44" cy="44" r="${r}" stroke-dasharray="${(frac * c).toFixed(2)} ${c.toFixed(2)}" transform="rotate(-90 44 44)"/>`
      : '') +
    `</svg>`;
  wrap.append(
    h('span', { class: 'sk-ring-value', 'aria-hidden': 'true' }, value === null ? '–' : percent(value)),
    h('span', { class: 'sk-ring-label', 'aria-hidden': 'true' }, 'mastery'),
  );
  return wrap;
}

function meter(value: number | null, label: string): HTMLElement {
  return h('span', { class: 'sk-meter', role: 'img', 'aria-label': label },
    h('span', { class: 'sk-meter-fill', style: `width:${((value ?? 0) * 100).toFixed(1)}%` }));
}

function topicRow(s: TopicStat, lang: string | undefined): HTMLElement {
  const acc = s.accuracy;
  const meta = s.answered
    ? [
        `${s.answered} ${s.answered === 1 ? 'question' : 'questions'} answered`,
        s.due ? `${s.due} due` : '',
        s.misconceptions ? `${s.misconceptions} ${s.misconceptions === 1 ? 'misconception' : 'misconceptions'}` : '',
      ].filter(Boolean).join(' · ')
    : 'not started';
  return h('li', { class: `sk-topic${acc === null ? ' is-empty' : ''}` },
    h('span', { class: 'sk-topic-name', lang }, s.title),
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
  exams: Record<string, ExamMeta>,
  lang: string | undefined,
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
        h('th', { scope: 'row', lang }, exams[r.id]?.title ?? r.id),
        h('td', {}, new Date(r.started).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })),
        h('td', { class: 'sk-num' }, max ? `${pts(r.total)} / ${pts(max)}` : pts(r.total)),
        h('td', { class: 'sk-num' }, duration(r.duration_s * 1000)));
    })));
}
