// <sk-quiz data-course data-mode="practice|test|mistakes|due|mixed" data-pools='["…json"]'
//          data-topic-titles='{"id":"Title"}' data-summary-base="/c/<c>/summary/"
//          [data-n="3"] [data-intro="false"] [data-frame="none"]>
// (docs/architecture.md §3.2). data-n is the default number of questions; data-intro="false"
// leaves out the mode title and description (the page already shows them); data-frame="none"
// drops the start and result screens' own frame inside a box that is framed already.
//
// Each pool URL returns {topic, questions:[{id, type, difficulty, topic, h, html}]}, html
// being an <sk-mc> outerHTML. Modes:
//   practice  instant feedback after every question
//   test      N questions, feedback at the end, optional time limit
//   mistakes  questions whose last answer was not fully right (misconceptions first)
//   due       questions the Leitner schedule says are due (exam clamp included)
//   mixed     every pool together, instant feedback
// URL parameters: ?n=10&minutes=15&topics=a,b&difficulty=1,2 (or 1-3)&mode=… pre-fill the
// start form. With several quizzes on a page (the MC hub has one per mode) each keeps its
// data-mode and the parameters go to the quiz of ?mode= (or to all without it); a quiz
// alone on its page takes ?mode= as its mode. The result screen shows the score per topic, the time, the misconceptions
// (sure but wrong) and links to the topic summaries. Every answer is recorded by <sk-mc>,
// once: a question has no "Try again" inside a quiz, the first answer is the quiz result,
// and "Retry mistakes" (after the solutions were shown) is a practice round that records
// nothing.

import { dayOf, effectiveDue, isDue } from '../lib/leitner.ts';
import { randomSeed, shuffled } from '../lib/shuffle.ts';
import { isCorrect, isMcType } from '../lib/scoring.ts';
import { storeFor, type McEntry } from '../lib/store.ts';
import type { McAnswerDetail, SkMc } from './sk-mc.ts';
import {
  announce,
  clock,
  courseOf,
  duration,
  emit,
  examDate,
  excerpt,
  h,
  parseJson,
  percent,
  pts,
  relativeDay,
  today,
} from './util.ts';

export type QuizMode = 'practice' | 'test' | 'mistakes' | 'due' | 'mixed';
const MODES: readonly QuizMode[] = ['practice', 'test', 'mistakes', 'due', 'mixed'];

export interface PoolQuestion {
  id: string;
  type: string;
  difficulty: number;
  topic: string;
  h: string;
  html: string;
}

const INFO: Record<QuizMode, { title: string; text: string; n: number | null }> = {
  practice: { title: 'Practice', text: 'Feedback after every question.', n: 10 },
  test: { title: 'Test', text: 'Feedback at the end, with an optional time limit.', n: 10 },
  mistakes: { title: 'Mistakes', text: 'Questions you did not get fully right last time.', n: null },
  due: { title: 'Due for review', text: 'Questions the review schedule has due today.', n: null },
  mixed: { title: 'Mixed', text: 'Questions from every topic, with feedback after each.', n: 20 },
};

interface Settings {
  n: number | null;
  minutes: number | null;
  topics: string[] | null;
  difficulty: number[] | null;
}

function posInt(v: string | null): number | null {
  const n = Number(v);
  return v !== null && Number.isInteger(n) && n > 0 ? n : null;
}

function difficulties(v: string | null): number[] | null {
  if (!v) return null;
  const out = new Set<number>();
  for (const part of v.split(',')) {
    const m = /^\s*([1-4])\s*(?:-\s*([1-4]))?\s*$/.exec(part);
    if (!m) continue;
    const a = Number(m[1]);
    const b = Number(m[2] ?? m[1]);
    for (let d = Math.min(a, b); d <= Math.max(a, b); d++) out.add(d);
  }
  return out.size ? [...out].sort() : null;
}

function isQuestion(q: unknown): q is PoolQuestion {
  const o = q as PoolQuestion;
  return typeof o === 'object' && o !== null && typeof o.id === 'string' && typeof o.html === 'string' &&
    typeof o.topic === 'string' && isMcType(o.type);
}

function lastAttemptDay(e: McEntry): string | null {
  const t = e.attempts.at(-1)?.t;
  return t ? dayOf(new Date(t)) : null;
}

export class SkQuiz extends HTMLElement {
  private ready = false;
  private mode: QuizMode = 'practice';
  private all: PoolQuestion[] = [];
  private errors: string[] = [];
  private settings: Settings = { n: null, minutes: null, topics: null, difficulty: null };
  private seed = randomSeed();
  private list: PoolQuestion[] = [];
  private index = 0;
  private items: SkMc[] = [];
  private results = new Map<string, McAnswerDetail>();
  private startedAt = 0;
  private endedAt = 0;
  private deadline: number | null = null;
  /** A "Retry mistakes" round: the solutions were shown, so nothing is recorded. */
  private practiceRound = false;
  private timedOut = false;
  private timer: number | null = null;
  private screen: HTMLElement = h('div', { class: 'sk-quiz-screen' });
  private live: HTMLElement = h('p', { class: 'sk-vh', 'aria-live': 'polite' });
  private stage: HTMLElement | null = null;
  private nextBtn: HTMLButtonElement | null = null;
  private posEl: HTMLElement | null = null;
  private bar: HTMLElement | null = null;
  private timeEl: HTMLElement | null = null;
  /** Recounts the start screen (null while a quiz runs or shows its result). */
  private refreshStart: (() => void) | null = null;
  private unsubscribe: (() => void) | null = null;

  private get course(): string {
    return this.dataset.course || courseOf(this);
  }

  private get store() {
    return storeFor(this.course);
  }

  private get titles(): Record<string, string> {
    return parseJson<Record<string, string>>(this.dataset.topicTitles, {});
  }

  connectedCallback(): void {
    // Answers given elsewhere (another quiz on the MC hub, another tab) change what the
    // mistakes and due modes offer: the start screen recounts.
    this.unsubscribe ??= this.store.subscribe(() => this.refreshStart?.());
    if (this.ready) return;
    this.ready = true;
    const url = new URLSearchParams(location.search);
    const valid = (m: string | null | undefined): m is QuizMode => MODES.includes(m as QuizMode);
    const urlMode = url.get('mode');
    const own = this.dataset.mode;
    const alone = document.querySelectorAll('sk-quiz').length <= 1;
    this.mode = alone
      ? valid(urlMode) ? urlMode : valid(own) ? own : 'practice'
      : valid(own) ? own : valid(urlMode) ? urlMode : 'practice';
    const q = alone || !valid(urlMode) || urlMode === this.mode ? url : new URLSearchParams();
    const topics = q.get('topics')?.split(',').map((t) => t.trim()).filter(Boolean) ?? [];
    this.settings = {
      n: posInt(q.get('n')) ?? posInt(this.dataset.n ?? null),
      minutes: posInt(q.get('minutes')),
      topics: topics.length ? topics : null,
      difficulty: difficulties(q.get('difficulty')),
    };
    this.replaceChildren(this.live, this.screen); // drop the no-JS fallback
    this.classList.add('sk-quiz-ready');
    this.addEventListener('sk:next', (e) => {
      e.preventDefault();
      this.next();
    });
    this.addEventListener('sk:answer', (e) => this.onAnswer(e as CustomEvent<McAnswerDetail>));
    this.addEventListener('sk:change', () => this.updateNext());
    this.screen.replaceChildren(h('p', { class: 'sk-quiz-loading' }, 'Loading questions…'));
    void this.load();
  }

  disconnectedCallback(): void {
    this.stopTimer();
    this.unsubscribe?.();
    this.unsubscribe = null;
  }

  private async load(): Promise<void> {
    const urls = parseJson<unknown[]>(this.dataset.pools, []).filter((u): u is string => typeof u === 'string');
    const seen = new Set<string>();
    const results = await Promise.allSettled(
      urls.map(async (url) => {
        const res = await fetch(url, { headers: { accept: 'application/json' } });
        if (!res.ok) throw new Error(`${res.status}`);
        return (await res.json()) as { questions?: unknown[] };
      }),
    );
    results.forEach((r, i) => {
      if (r.status === 'rejected') {
        this.errors.push(urls[i] ?? '');
        return;
      }
      for (const q of r.value.questions ?? []) {
        if (!isQuestion(q) || seen.has(q.id)) continue;
        seen.add(q.id);
        this.all.push({ ...q, difficulty: Number(q.difficulty) || 0 });
      }
    });
    this.renderStart();
  }

  // --- selecting questions ----------------------------------------------------------

  private filtered(s: Settings): PoolQuestion[] {
    // null: no filter; an empty choice (every box unticked) matches nothing
    let qs = this.all;
    if (s.topics) qs = qs.filter((q) => s.topics!.includes(q.topic));
    if (s.difficulty) qs = qs.filter((q) => s.difficulty!.includes(q.difficulty));
    const items = this.store.read().items;
    const entry = (q: PoolQuestion) => items[`mc:${q.id}`] as McEntry | undefined;
    const day = today();
    const exam = examDate();
    if (this.mode === 'due') {
      const due = qs.filter((q) => {
        const e = entry(q);
        return e ? isDue(e.due, lastAttemptDay(e), day, exam) : false;
      });
      const key = (q: PoolQuestion) => {
        const e = entry(q);
        return `${e ? (effectiveDue(e.due, lastAttemptDay(e), exam) ?? '') : ''}|${e?.box ?? 9}`;
      };
      return due.sort((a, b) => (key(a) < key(b) ? -1 : key(a) > key(b) ? 1 : 0));
    }
    if (this.mode === 'mistakes') {
      const wrong = qs.filter((q) => {
        const last = entry(q)?.attempts.at(-1);
        return last !== undefined && !isCorrect(last.score);
      });
      const rank = (q: PoolQuestion) => (entry(q)?.attempts.at(-1)?.conf === 'sure' ? 0 : 1);
      return shuffled(wrong, this.seed).sort((a, b) => rank(a) - rank(b));
    }
    return shuffled(qs, this.seed);
  }

  /** The next due day among attempted questions (for the "nothing due" message). */
  private nextDue(): string | null {
    let best: string | null = null;
    const items = this.store.read().items;
    for (const q of this.all) {
      const e = items[`mc:${q.id}`] as McEntry | undefined;
      const d = e ? effectiveDue(e.due, lastAttemptDay(e), examDate()) : null;
      if (d && d > today() && (best === null || d < best)) best = d;
    }
    return best;
  }

  // --- start screen -------------------------------------------------------------------

  private renderStart(): void {
    this.stopTimer();
    const info = INFO[this.mode];
    const topics = [...new Set(this.all.map((q) => q.topic))];
    const levels = [...new Set(this.all.map((q) => q.difficulty))].filter((d) => d >= 1).sort();
    const form = h('form', { class: 'sk-quiz-form' });
    const count = h('p', { class: 'sk-quiz-count', role: 'status' });
    const nInput = h('input', { type: 'number', min: '1', step: '1', inputmode: 'numeric', class: 'sk-input sk-input-short' });
    const minutes = h('input', { type: 'number', min: '0', step: '1', inputmode: 'numeric', class: 'sk-input sk-input-short', placeholder: 'none' });
    if (this.settings.minutes) minutes.value = String(this.settings.minutes);
    const topicBoxes = topics.map((t) =>
      h('input', { type: 'checkbox', value: t, checked: !this.settings.topics || this.settings.topics.includes(t) }));
    const levelBoxes = levels.map((d) =>
      h('input', { type: 'checkbox', value: String(d), checked: !this.settings.difficulty || this.settings.difficulty.includes(d) }));
    const start = h('button', { type: 'submit', class: 'sk-btn sk-btn-primary' }, 'Start');

    const current = (): Settings => ({
      n: posInt(nInput.value),
      minutes: posInt(minutes.value),
      topics: topicBoxes.length > 1 ? topicBoxes.filter((b) => b.checked).map((b) => b.value) : null,
      difficulty: levelBoxes.length > 1 ? levelBoxes.filter((b) => b.checked).map((b) => Number(b.value)) : null,
    });
    // The question count follows the mode's default until the student changes it.
    let nChosen = false;
    nInput.addEventListener('input', () => (nChosen = true));
    const controls: HTMLElement[] = [];
    const update = () => {
      const available = this.filtered(current()).length;
      // Nothing due or wrong at all: no form to fill in, only the message.
      const none = available === 0 && this.filtered({ n: null, minutes: null, topics: null, difficulty: null }).length === 0;
      for (const c of controls) c.hidden = none;
      nInput.max = String(Math.max(1, available));
      if (!nChosen || !nInput.value || Number(nInput.value) > available) {
        const want = this.settings.n ?? info.n ?? available;
        nInput.value = String(Math.max(1, Math.min(want, available)));
      }
      start.disabled = available === 0;
      count.textContent = this.emptyText(available) ?? `${available} question${available === 1 ? '' : 's'} available.`;
    };

    form.append(count);
    if (this.all.length > 0) {
      controls.push(h('div', { class: 'sk-quiz-fields' },
        h('label', { class: 'sk-field' }, h('span', {}, 'Questions'), nInput),
        this.mode === 'test' ? h('label', { class: 'sk-field' }, h('span', {}, 'Time limit (minutes)'), minutes) : null,
      ));
      if (topicBoxes.length > 1) {
        controls.push(h('fieldset', { class: 'sk-quiz-filter' }, h('legend', {}, 'Topics'),
          ...topicBoxes.map((b) => h('label', { class: 'sk-check-chip' }, b, h('span', {}, this.titles[b.value] ?? b.value)))));
      }
      if (levelBoxes.length > 1) {
        controls.push(h('fieldset', { class: 'sk-quiz-filter' }, h('legend', {}, 'Difficulty'),
          ...levelBoxes.map((b) => h('label', { class: 'sk-check-chip' }, b, h('span', {}, `Level ${b.value}`)))));
      }
      controls.push(h('div', { class: 'sk-quiz-actions' }, start));
      form.append(...controls);
    }
    form.addEventListener('change', update);
    form.addEventListener('input', update);
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const s = current();
      const picked = this.filtered(s);
      this.begin(picked.slice(0, s.n ?? picked.length), this.mode === 'test' ? s.minutes : null, false);
    });
    update();
    this.refreshStart = update;
    const intro = this.dataset.intro !== 'false';
    this.screen.replaceChildren(
      h('div', { class: 'sk-quiz-start' },
        intro ? h('p', { class: 'sk-quiz-mode' }, info.title) : null,
        intro ? h('p', { class: 'sk-quiz-desc' }, info.text) : null,
        this.errors.length
          ? h('p', { class: 'sk-quiz-error', role: 'alert' }, `Some questions could not be loaded (${this.errors.length} of ${this.errors.length + new Set(this.all.map((q) => q.topic)).size} banks).`)
          : null,
        form),
    );
  }

  private emptyText(available: number): string | null {
    if (available > 0) return null;
    if (this.all.length === 0) return 'There are no questions here yet.';
    if (this.mode === 'due') {
      const next = this.nextDue();
      return `Nothing is due today.${next ? ` The next review is ${relativeDay(next)} (${next}).` : ''}`;
    }
    if (this.mode === 'mistakes') return 'No mistakes to review: every question you answered was right last time.';
    return 'No question matches these filters.';
  }

  // --- running ------------------------------------------------------------------------

  private begin(list: PoolQuestion[], minutes: number | null, practiceRound: boolean): void {
    if (list.length === 0) return;
    this.refreshStart = null;
    this.practiceRound = practiceRound;
    this.list = list;
    this.index = 0;
    this.items = [];
    this.results.clear();
    this.timedOut = false;
    this.startedAt = Date.now();
    this.deadline = minutes ? this.startedAt + minutes * 60_000 : null;
    this.posEl = h('span', { class: 'sk-quiz-pos' });
    this.bar = h('span', { class: 'sk-quiz-bar-fill' });
    this.timeEl = h('span', { class: 'sk-quiz-time', role: 'timer', 'aria-live': 'off' });
    this.stage = h('div', { class: 'sk-quiz-stage' });
    this.nextBtn = h('button', { type: 'button', class: 'sk-btn sk-btn-primary' }, 'Next');
    const end = h('button', { type: 'button', class: 'sk-btn sk-btn-quiet' }, 'End quiz');
    this.nextBtn.addEventListener('click', () => this.next());
    end.addEventListener('click', () => this.finish());
    this.screen.replaceChildren(
      h('div', { class: 'sk-quiz-run' },
        h('div', { class: 'sk-quiz-status' },
          this.posEl,
          h('span', { class: 'sk-quiz-bar', role: 'progressbar', 'aria-label': 'Progress', 'aria-valuemin': '0', 'aria-valuemax': String(list.length) }, this.bar),
          this.timeEl),
        practiceRound
          ? h('p', { class: 'sk-quiz-practice' },
              'Retry round: you have seen the solutions, so these answers are not recorded.')
          : null,
        this.stage,
        h('div', { class: 'sk-quiz-nav' }, end, this.nextBtn)),
    );
    this.timer = window.setInterval(() => this.tick(), 1000);
    this.tick();
    this.show();
  }

  private show(): void {
    const q = this.list[this.index];
    if (!q || !this.stage) return;
    const tpl = document.createElement('template');
    tpl.innerHTML = q.html.trim();
    const el = tpl.content.querySelector('sk-mc');
    if (!el) {
      this.index++;
      this.show();
      return;
    }
    if (!el.hasAttribute('data-h') && q.h) el.setAttribute('data-h', q.h);
    el.setAttribute('data-mode', this.mode === 'test' ? 'deferred' : 'practice');
    el.setAttribute('data-retry', 'false'); // one answer per question; "Retry mistakes" comes at the end
    if (this.practiceRound) el.setAttribute('data-record', 'false');
    el.id ||= `q-${q.id}`;
    this.stage.replaceChildren(el);
    const mc = el as SkMc;
    this.items[this.index] = mc;
    mc.start();
    const n = this.list.length;
    if (this.posEl) this.posEl.textContent = `Question ${this.index + 1} of ${n}`;
    this.bar?.parentElement?.setAttribute('aria-valuenow', String(this.index));
    if (this.bar) this.bar.style.width = `${(this.index / n) * 100}%`;
    announce(this.live, `Question ${this.index + 1} of ${n}`);
    this.updateNext();
    mc.focus({ preventScroll: true });
    if (this.getBoundingClientRect().top < 0) this.scrollIntoView({ block: 'start' });
  }

  private updateNext(): void {
    const mc = this.items[this.index];
    if (!this.nextBtn || !mc) return;
    const last = this.index === this.list.length - 1;
    this.nextBtn.textContent = last ? 'See result' : 'Next';
    const ready = this.mode === 'test' ? mc.isComplete() || Boolean(mc.result) : Boolean(mc.result);
    this.nextBtn.setAttribute('aria-disabled', String(!ready));
  }

  private onAnswer(e: CustomEvent<McAnswerDetail>): void {
    if (this.results.has(e.detail.id)) return; // the first answer is the quiz result
    this.results.set(e.detail.id, e.detail);
    this.updateNext();
    if (this.mode !== 'test') this.nextBtn?.focus({ preventScroll: true });
  }

  private next(): void {
    const mc = this.items[this.index];
    if (!mc) return;
    if (!mc.result) {
      if (this.mode !== 'test') return;
      if (!mc.submit({ reveal: false })) return; // <sk-mc> says what is missing
    }
    if (this.index >= this.list.length - 1) {
      this.finish();
      return;
    }
    this.index++;
    this.show();
  }

  private tick(): void {
    const now = Date.now();
    if (!this.timeEl) return;
    if (this.deadline !== null) {
      const left = this.deadline - now;
      this.timeEl.textContent = `Time left ${clock(left)}`;
      this.timeEl.classList.toggle('is-low', left <= 60_000);
      if (left <= 0) {
        this.timedOut = true;
        this.finish();
      }
    } else {
      this.timeEl.textContent = clock(now - this.startedAt);
    }
  }

  private stopTimer(): void {
    if (this.timer !== null) window.clearInterval(this.timer);
    this.timer = null;
  }

  // --- result -------------------------------------------------------------------------

  private finish(): void {
    this.stopTimer();
    this.endedAt = Date.now();
    // In test mode a complete but unsubmitted answer still counts.
    const mc = this.items[this.index];
    if (mc && !mc.result && this.mode === 'test' && mc.isComplete()) mc.submit({ reveal: false });
    this.renderResult();
  }

  private renderResult(): void {
    const titles = this.titles;
    const base = this.dataset.summaryBase;
    const link = (topic: string) =>
      base ? h('a', { href: `${base.replace(/\/?$/, '/')}${topic}/` }, `Read “${titles[topic] ?? topic}”`) : null;
    let total = 0;
    const byTopic = new Map<string, { score: number; n: number }>();
    for (const q of this.list) {
      const r = this.results.get(q.id);
      const t = byTopic.get(q.topic) ?? { score: 0, n: 0 };
      t.n++;
      t.score += r?.score ?? 0;
      total += r?.score ?? 0;
      byTopic.set(q.topic, t);
    }
    const n = this.list.length;
    const answered = this.results.size;
    const misconceptions = this.list.filter((q) => this.results.get(q.id)?.misconception);
    const wrong = this.list.filter((q) => !this.results.get(q.id)?.correct);

    const rows = [...byTopic].map(([topic, t]) =>
      h('tr', {},
        h('th', { scope: 'row' }, titles[topic] ?? topic),
        h('td', { class: 'sk-num' }, `${pts(t.score)} / ${t.n}`),
        h('td', { class: 'sk-quiz-bar-cell' },
          h('span', { class: 'sk-meter', role: 'img', 'aria-label': percent(t.score / t.n) },
            h('span', { class: 'sk-meter-fill', style: `width:${(t.score / t.n) * 100}%` }))),
        h('td', {}, link(topic))));

    const review = h('ol', { class: 'sk-quiz-review' });
    this.items.forEach((mc, i) => {
      const q = this.list[i];
      if (!q) return;
      const r = this.results.get(q.id);
      if (!r) mc.grade(); // not answered: show the answer without recording anything
      else if (this.mode === 'test') mc.reveal();
      const verdict = !r ? 'not answered' : r.correct ? 'correct' : r.score > 0 ? 'partly correct' : 'wrong';
      const icon = !r ? '–' : r.correct ? '✓' : r.score > 0 ? '◐' : '✗';
      const details = h('details', { class: `sk-quiz-item is-${r?.correct ? 'ok' : r && r.score > 0 ? 'partial' : 'bad'}` },
        h('summary', {},
          h('span', { class: 'sk-quiz-item-icon', 'aria-hidden': 'true' }, icon),
          h('span', { class: 'sk-vh' }, `${verdict}: `),
          h('span', { class: 'sk-quiz-item-text' }, excerpt(mc.querySelector('.sk-stem'), 90))),
        mc);
      if (!r?.correct) details.open = this.mode === 'test';
      review.append(h('li', { id: `review-${q.id}` }, details));
    });

    const retry = h('button', { type: 'button', class: 'sk-btn' }, `Retry mistakes (${wrong.length})`);
    retry.hidden = wrong.length === 0;
    retry.addEventListener('click', () => {
      this.seed = randomSeed();
      this.begin(shuffled(wrong, this.seed), null, true);
    });
    const again = h('button', { type: 'button', class: 'sk-btn sk-btn-primary' }, 'New quiz');
    again.addEventListener('click', () => {
      this.seed = randomSeed();
      this.renderStart();
    });

    const heading = h('h2', { class: 'sk-quiz-title', tabindex: '-1' }, 'Result');
    this.screen.replaceChildren(
      h('div', { class: 'sk-quiz-result' },
        heading,
        h('p', { class: 'sk-quiz-score' },
          h('strong', {}, `${pts(total)} / ${n}`), ` points · ${percent(n ? total / n : 0)}`),
        h('p', { class: 'sk-quiz-meta' },
          `${this.practiceRound ? 'Retry round, not recorded' : INFO[this.mode].title} · ${answered} of ${n} answered · time ${duration(this.endedAt - this.startedAt)}`,
          this.timedOut ? h('strong', {}, ' · time is up') : null),
        h('h3', {}, 'By topic'),
        h('table', { class: 'sk-quiz-topics' },
          h('thead', {}, h('tr', {}, h('th', { scope: 'col' }, 'Topic'), h('th', { scope: 'col' }, 'Score'),
            h('th', { scope: 'col' }, h('span', { class: 'sk-vh' }, 'Share')), h('th', { scope: 'col' }, h('span', { class: 'sk-vh' }, 'Summary')))),
          h('tbody', {}, ...rows)),
        h('h3', {}, 'Misconceptions'),
        misconceptions.length
          ? h('ul', { class: 'sk-quiz-misconceptions' }, ...misconceptions.map((q) =>
              h('li', {},
                h('a', { href: `#review-${q.id}` }, excerpt(this.items[this.list.indexOf(q)]?.querySelector('.sk-stem') ?? null, 100)),
                base ? h('span', { class: 'sk-quiz-mis-topic' }, link(q.topic)) : null)))
          : h('p', { class: 'sk-quiz-none' }, 'None: no answer was both sure and wrong.'),
        h('div', { class: 'sk-quiz-actions' }, again, retry),
        h('h3', {}, 'Your answers'),
        review),
    );
    heading.focus();
    announce(this.live, `Result: ${pts(total)} of ${n} points.`);
    emit(this, 'sk:quiz-done', { mode: this.mode, total, n, misconceptions: misconceptions.map((q) => q.id) });
  }
}
