// <sk-exam data-exam data-duration-min data-points data-pass-points data-aids='[…]'
//          data-mc-scoring data-negative-marking="true|false">
//   <section class="sk-exam-task" data-task data-title data-points data-h
//            data-rubric='[{criterion, criterion_html, points}]'>…</section>
//   <section class="sk-exam-mc" data-points data-points-each><sk-mc>…</sk-mc>…</section>
// </sk-exam>                                               (docs/architecture.md §2.7, §3.2)
// data-mc-scoring and data-negative-marking fall back to <body>'s (the course's exam);
// criterion_html is the criterion with its math rendered at build time.
//
// 1. A cover page shows duration, points, pass mark and allowed aids.
// 2. Start stores the start time (session state), so a reload keeps the timer running. While
//    the exam runs a beforeunload warning is set, and alerts come at 10 and at 1 minute left.
// 3. Hints and solutions stay hidden and `inert` until Submit or time-up.
// 4. Then each task gets its rubric as checkboxes; the MC part is scored automatically with
//    the exam's multi rule (data-mc-scoring) and, if the exam has it, negative marking
//    (scoring.examScore; the MC part never goes below 0).
// 5. The result shows total, pass/fail, a grade estimate and the time per task: all time
//    on the exam clock goes to the part that was on screen, including gaps between late
//    ticks (a sleeping laptop, a throttled background tab while the student reads a
//    formula sheet) and the time a reload or a closed tab took. The attempt is saved as
//    exam:<id> and updated while grading. Without JS the tasks and solutions are plain
//    content.
// The exam's own text (cover, bar, dialog, rubric, result) is English; tasks, aids, task
// titles and rubric criteria keep the course language.

import { examPartPoints, examPoints, gradeEstimate, multiRule, type MultiRule } from '../lib/scoring.ts';
import type { ExamEntry } from '../lib/store.ts';
import type { McSelection, SkMc } from './sk-mc.ts';
import { clock, duration, emit, h, langs, parseJson, percent, pts, renderInline, storeOf, uid } from './util.ts';

interface RubricItem {
  criterion: string;
  /** The criterion with its math rendered at build time (the site shell). */
  criterion_html?: string | undefined;
  points: number;
}

interface Task {
  id: string;
  title: string;
  points: number;
  rubric: RubricItem[];
  el: HTMLElement;
  output: HTMLElement | null;
}

interface ExamSession {
  started: string;
  submitted?: string;
  reason?: 'submit' | 'time';
  mc?: Record<string, McSelection>;
  rubric?: Record<string, number[]>;
  task_ms?: Record<string, number>;
  /** Epoch ms up to which time has been given to a part, and the part on screen then. */
  tick_at?: number;
  active?: string;
  warned?: number[];
}

const RULE_TEXT: Record<MultiRule, string> = {
  'all-or-nothing': 'multiple-answer questions count only when completely right',
  partial: 'multiple-answer questions earn partial credit',
  kprim: 'multiple-answer questions use the Kprim rule (one mistake: half the points)',
};

const WARNINGS = [10, 1];
const MC_ID = 'mc';

export class SkExam extends HTMLElement {
  private ready = false;
  private examId = '';
  private durationMs = 0;
  private points = 0;
  private pass: number | null = null;
  private aids: string[] = [];
  private rule: MultiRule = 'all-or-nothing';
  private negative = false;
  private tasks: Task[] = [];
  private mcEl: HTMLElement | null = null;
  private mcPoints = 0;
  /** Points per MC question (data-points-each, else the part's points shared equally). */
  private mcEach = 0;
  private body: HTMLElement = h('div', { class: 'sk-exam-body' });
  private head: HTMLElement = h('div', { class: 'sk-exam-head' });
  private alertText: HTMLElement = h('span', { class: 'sk-exam-alert-text', role: 'alert' });
  private alertEl: HTMLElement = h('div', { class: 'sk-exam-alert' }, this.alertText);
  private clockEl: HTMLElement | null = null;
  private timer: number | null = null;
  private lastTick = 0;
  private ticks = 0;
  private visible = new Map<string, number>();
  private observer: IntersectionObserver | null = null;
  /**
   * Keeps --sk-exam-head at the sticky head's height (scroll-margin of the parts) and the
   * page's scroll-padding-top below it, so a control that gets focus is never under it.
   */
  private headSize: ResizeObserver | null = null;
  private session: ExamSession | null = null;
  private announceTimeUp = false;
  /** lang for the exam's own (English) text and for course text inside it. */
  private ui: string | undefined;
  private content: string | undefined;
  private onBeforeUnload = (e: BeforeUnloadEvent) => {
    e.preventDefault();
    // older browsers only warn when returnValue is set (deprecated, so set it untyped)
    (e as { returnValue: unknown }).returnValue = '';
  };
  private onPageHide = () => {
    this.account();
    this.save();
  };
  private onVisibility = () => {
    if (document.visibilityState !== 'hidden') return;
    this.account();
    this.save();
  };

  private get sessionKey(): string {
    return `exam:${this.examId}`;
  }

  private get mcs(): SkMc[] {
    return this.mcEl ? [...this.mcEl.querySelectorAll<SkMc>('sk-mc')] : [];
  }

  connectedCallback(): void {
    if (this.ready) return;
    this.ready = true;
    // The MC part calls <sk-mc> methods, so wait for its definition if index.ts is not used.
    if (this.querySelector('sk-mc') && !customElements.get('sk-mc')) {
      void customElements.whenDefined('sk-mc').then(() => this.init());
    } else {
      this.init();
    }
  }

  private init(): void {
    this.examId = this.dataset.exam ?? 'exam';
    this.durationMs = Math.max(1, Number(this.dataset.durationMin) || 60) * 60_000;
    this.pass = Number.isFinite(Number.parseFloat(this.dataset.passPoints ?? '')) ? Number(this.dataset.passPoints) : null;
    this.aids = parseJson<unknown[]>(this.dataset.aids, []).filter((a): a is string => typeof a === 'string');
    const body = document.body?.dataset ?? {};
    this.rule = multiRule(this.dataset.mcScoring ?? body.mcScoring);
    this.negative = (this.dataset.negativeMarking ?? body.negativeMarking) === 'true';

    ({ ui: this.ui, content: this.content } = langs(this));
    if (this.ui) this.head.lang = this.ui;
    this.body.append(...this.childNodes);
    this.append(this.head, this.body);
    this.alertEl.hidden = true;
    this.classList.add('sk-exam-ready');

    for (const el of this.body.querySelectorAll<HTMLElement>('section.sk-exam-task')) {
      const id = el.dataset.task ?? uid('task');
      el.id ||= `task-${id}`;
      const heading = el.querySelector('h1, h2, h3, h4');
      this.tasks.push({
        id,
        title: el.dataset.title?.trim() || heading?.textContent?.trim() || `Task ${this.tasks.length + 1}`,
        points: Number(el.dataset.points) || 0,
        rubric: parseJson<unknown[]>(el.dataset.rubric, [])
          .filter((r): r is RubricItem => typeof (r as RubricItem)?.criterion === 'string')
          .map((r) => ({
            criterion: r.criterion,
            criterion_html: typeof r.criterion_html === 'string' ? r.criterion_html : undefined,
            points: Number(r.points) || 0,
          })),
        el,
        output: null,
      });
    }
    this.mcEl = this.body.querySelector<HTMLElement>('section.sk-exam-mc');
    if (this.mcEl) {
      this.mcEl.id ||= 'exam-mc';
      this.mcPoints = Number(this.mcEl.dataset.points) || 0;
      const n = this.mcEl.querySelectorAll('sk-mc').length;
      this.mcEach = Number(this.mcEl.dataset.pointsEach) || (n ? this.mcPoints / n : 0);
      this.mcPoints ||= this.mcEach * n;
      for (const mc of this.mcEl.querySelectorAll('sk-mc')) mc.setAttribute('data-mode', 'exam');
      this.mcEl.addEventListener('sk:change', () => this.saveMc());
    }
    this.points = Number(this.dataset.points) || this.tasks.reduce((s, t) => s + t.points, 0) + this.mcPoints;

    this.session = storeOf(this).session<ExamSession>(this.sessionKey) ?? null;
    if (!this.session?.started) this.renderCover();
    else if (this.session.submitted) this.renderGraded();
    else if (this.left() <= 0) {
      this.resumeClock(Date.now());
      this.submit('time');
    } else this.run();
  }

  disconnectedCallback(): void {
    this.stop();
  }

  private save(): void {
    if (this.session) storeOf(this).setSession(this.sessionKey, this.session);
  }

  private left(now = Date.now()): number {
    return this.session ? Date.parse(this.session.started) + this.durationMs - now : this.durationMs;
  }

  private lockables(): HTMLElement[] {
    return [...this.body.querySelectorAll<HTMLElement>(
      'details.sk-solution, details.sk-hint, sk-reveal, sk-hints, sk-answer-check, sk-self-assess',
    )];
  }

  private setLocked(locked: boolean): void {
    for (const el of this.lockables()) {
      el.inert = locked;
      el.hidden = locked;
    }
  }

  // --- cover --------------------------------------------------------------------------

  private renderCover(): void {
    this.setLocked(true);
    this.body.hidden = true;
    const n = this.mcs.length;
    const parts = [
      `${this.tasks.length} ${this.tasks.length === 1 ? 'task' : 'tasks'}`,
      n ? `multiple-choice part with ${n} ${n === 1 ? 'question' : 'questions'} (${pts(this.mcPoints)} points)` : '',
    ].filter(Boolean);
    const fact = (term: string, value: string) => h('div', {}, h('dt', {}, term), h('dd', {}, value));
    const attempts = storeOf(this).get<ExamEntry>(this.sessionKey)?.attempts ?? [];
    const last = attempts.at(-1);
    const start = h('button', { type: 'button', class: 'sk-btn sk-btn-primary sk-btn-large' }, 'Start exam');
    start.addEventListener('click', () => {
      this.session = { started: new Date().toISOString(), task_ms: {}, warned: [] };
      this.save();
      this.body.hidden = false;
      this.run();
      // The button is gone now: focus goes to the first part, where reading starts.
      const first = this.tasks[0]?.el ?? this.mcEl;
      first?.scrollIntoView({ block: 'start' });
      const target = first?.querySelector<HTMLElement>('h1, h2, h3, h4') ?? first;
      if (target) {
        if (target.tabIndex < 0) target.tabIndex = -1;
        target.focus({ preventScroll: true });
      }
    });
    const titleId = uid('cover');
    this.head.classList.remove('is-sticky');
    this.head.replaceChildren(
      h('section', { class: 'sk-exam-cover', 'aria-labelledby': titleId },
        h('h2', { id: titleId }, 'Before you start'),
        h('dl', { class: 'sk-exam-facts' },
          fact('Duration', `${Math.round(this.durationMs / 60_000)} min`),
          fact('Points', pts(this.points)),
          this.pass !== null ? fact('Pass mark', `${pts(this.pass)} points`) : null,
          fact('Contents', parts.join(', '))),
        h('h3', {}, 'Allowed aids'),
        this.aids.length
          ? h('ul', { class: 'sk-exam-aids', lang: this.content }, ...this.aids.map((a) => h('li', {}, a)))
          : h('p', {}, 'No aids.'),
        h('h3', {}, 'How it works'),
        h('ul', { class: 'sk-exam-rules' },
          h('li', {}, 'The timer starts when you press Start and keeps running if you reload or leave the page.'),
          h('li', {}, 'Work on paper. Hints and solutions stay locked until you submit or the time is up.'),
          h('li', {}, `Then you grade each task with its rubric. The multiple-choice part is scored automatically: ${RULE_TEXT[this.rule]}, ${
            this.negative
              ? 'and a wrong answer costs as many points as a right one earns (the part never goes below 0)'
              : 'no negative marking'
          }.`)),
        last
          ? h('p', { class: 'sk-exam-last' },
              `Last attempt: ${pts(last.total)} of ${pts(this.points)} points on ${new Date(last.started).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}`,
              attempts.length > 1 ? ` (${attempts.length} attempts).` : '.')
          : null,
        start),
      this.alertEl,
    );
  }

  // --- running ------------------------------------------------------------------------

  private run(): void {
    this.setLocked(true);
    this.body.hidden = false;
    this.restoreMc();
    this.clockEl = h('span', { class: 'sk-exam-clock', role: 'timer', 'aria-live': 'off', 'aria-atomic': 'true' });
    const submit = h('button', { type: 'button', class: 'sk-btn sk-btn-primary' }, 'Submit');
    submit.addEventListener('click', () => this.confirmSubmit(submit));
    const nav = h('nav', { class: 'sk-exam-nav', 'aria-label': 'Tasks' },
      ...this.tasks.map((t, i) => h('a', { href: `#${t.el.id}`, title: t.title }, String(i + 1))),
      this.mcEl ? h('a', { href: `#${this.mcEl.id}`, title: 'Multiple choice' }, 'MC') : null);
    // The head (bar and alerts) sticks to the top while the exam runs.
    this.head.classList.add('is-sticky');
    this.head.replaceChildren(
      h('div', { class: 'sk-exam-bar' },
        h('span', { class: 'sk-exam-time' }, this.clockEl, h('span', { class: 'sk-exam-time-label' }, ' left')),
        nav,
        submit),
      this.alertEl,
    );
    window.addEventListener('beforeunload', this.onBeforeUnload);
    window.addEventListener('pagehide', this.onPageHide);
    document.addEventListener('visibilitychange', this.onVisibility);
    this.observe();
    // now (the Start button scrolls to the first task right away) and on every resize
    const headHeight = () => {
      const px = `${this.head.offsetHeight}px`;
      this.style.setProperty('--sk-exam-head', px);
      document.documentElement.style.scrollPaddingTop = `calc(${px} + 0.5rem)`;
    };
    headHeight();
    if (typeof ResizeObserver !== 'undefined') {
      this.headSize = new ResizeObserver(headHeight);
      this.headSize.observe(this.head);
    }
    this.resumeClock(Date.now());
    this.timer = window.setInterval(() => this.tick(), 1000);
    this.tick();
  }

  private observe(): void {
    if (typeof IntersectionObserver === 'undefined') return;
    const sections = [...this.tasks.map((t) => t.el), ...(this.mcEl ? [this.mcEl] : [])];
    this.observer = new IntersectionObserver(
      (entries) => {
        for (const e of entries) this.visible.set(this.sectionId(e.target as HTMLElement), e.intersectionRect.height);
      },
      { threshold: [0, 0.1, 0.25, 0.5, 0.75, 1] },
    );
    for (const s of sections) this.observer.observe(s);
  }

  private sectionId(el: HTMLElement): string {
    return el === this.mcEl ? MC_ID : (this.tasks.find((t) => t.el === el)?.id ?? '');
  }

  /** The task with the most visible pixels: it gets the time. */
  private activeSection(): string | null {
    let best: string | null = null;
    let most = 0;
    for (const [id, px] of this.visible) {
      if (px > most) {
        most = px;
        best = id;
      }
    }
    return best ?? this.tasks[0]?.id ?? null;
  }

  /** Give `from`…`to` (epoch ms, cut at the end of the exam) to part `id`. */
  private credit(id: string, from: number, to: number): void {
    const s = this.session;
    if (!s) return;
    const ms = Math.min(to, Date.parse(s.started) + this.durationMs) - from;
    if (!(ms > 0)) return;
    s.task_ms ??= {};
    s.task_ms[id] = (s.task_ms[id] ?? 0) + ms;
  }

  /** Time that passed while no page ran the clock goes to the part on screen before it. */
  private resumeClock(now: number): void {
    const s = this.session;
    if (s?.tick_at && s.active) this.credit(s.active, s.tick_at, now);
    this.lastTick = now;
    if (s) s.tick_at = now;
  }

  /** Give all time since the last tick to the part on screen now (ticks can come late). */
  private account(now = Date.now()): void {
    const s = this.session;
    if (!s || s.submitted || this.lastTick === 0) return;
    const active = this.activeSection();
    if (active) {
      this.credit(active, this.lastTick, now);
      s.active = active;
    }
    this.lastTick = now;
    s.tick_at = now;
  }

  private tick(): void {
    const s = this.session;
    if (!s || !this.clockEl) return;
    const now = Date.now();
    const left = this.left(now);
    this.clockEl.textContent = clock(left);
    this.classList.toggle('is-low', left <= 10 * 60_000);
    this.account(now);
    const warned = (s.warned ??= []);
    for (const m of WARNINGS) {
      if (left <= m * 60_000 && left > 0 && !warned.includes(m)) {
        // Crossing the 1-minute mark also settles the 10-minute warning (late reload).
        warned.push(...WARNINGS.filter((w) => w >= m && !warned.includes(w)));
        this.alert(m === 1 ? '1 minute left.' : `${m} minutes left.`);
        this.save();
      }
    }
    if (left <= 0) {
      this.submit('time');
      return;
    }
    if (++this.ticks % 5 === 0) this.save();
  }

  private alert(text: string): void {
    const dismiss = h('button', { type: 'button', class: 'sk-btn sk-btn-quiet sk-exam-alert-close' }, 'Dismiss');
    dismiss.addEventListener('click', () => {
      this.alertEl.hidden = true;
      this.head.querySelector<HTMLElement>('.sk-exam-bar .sk-btn-primary')?.focus();
    });
    this.alertText.textContent = text;
    this.alertEl.replaceChildren(this.alertText, dismiss);
    this.alertEl.hidden = false;
  }

  private stop(): void {
    if (this.timer !== null) window.clearInterval(this.timer);
    this.timer = null;
    this.observer?.disconnect();
    this.observer = null;
    this.headSize?.disconnect();
    this.headSize = null;
    this.style.removeProperty('--sk-exam-head');
    document.documentElement.style.removeProperty('scroll-padding-top');
    this.lastTick = 0;
    window.removeEventListener('beforeunload', this.onBeforeUnload);
    window.removeEventListener('pagehide', this.onPageHide);
    document.removeEventListener('visibilitychange', this.onVisibility);
  }

  private confirmSubmit(trigger: HTMLElement): void {
    const left = this.left();
    const dialog = h('dialog', { class: 'sk-dialog', lang: this.ui, 'aria-labelledby': uid('dlg') });
    const yes = h('button', { type: 'button', class: 'sk-btn sk-btn-primary' }, 'Submit now');
    const no = h('button', { type: 'button', class: 'sk-btn' }, 'Keep working');
    dialog.append(
      h('h2', { id: dialog.getAttribute('aria-labelledby') ?? '' }, 'Submit the exam?'),
      h('p', {}, `${clock(left)} of ${Math.round(this.durationMs / 60_000)} minutes are left. After submitting you cannot change your answers.`),
      h('div', { class: 'sk-dialog-actions' }, no, yes),
    );
    const close = () => {
      dialog.close();
      dialog.remove();
    };
    yes.addEventListener('click', () => {
      close();
      this.submit('submit');
    });
    no.addEventListener('click', () => {
      close();
      trigger.focus();
    });
    // Escape: the same as "Keep working" (removing the dialog would lose focus)
    dialog.addEventListener('cancel', (e) => {
      e.preventDefault();
      close();
      trigger.focus();
    });
    this.append(dialog);
    if (typeof dialog.showModal === 'function') dialog.showModal();
    no.focus();
  }

  private saveMc(): void {
    if (!this.session || this.session.submitted) return;
    this.session.mc = Object.fromEntries(this.mcs.map((m) => [m.qid, m.selection()]));
    this.save();
  }

  private restoreMc(): void {
    const saved = this.session?.mc ?? {};
    for (const m of this.mcs) {
      const sel = saved[m.qid];
      if (sel) m.setSelection(sel);
    }
  }

  // --- grading ------------------------------------------------------------------------

  private submit(reason: 'submit' | 'time'): void {
    if (!this.session) return;
    this.saveMcFinal();
    this.account();
    this.stop();
    this.session.submitted = new Date().toISOString();
    this.session.reason = reason;
    this.save();
    this.announceTimeUp = reason === 'time';
    this.renderGraded();
    this.head.querySelector<HTMLElement>('.sk-exam-result h2')?.focus();
    emit(this, 'sk:exam-submitted', { exam: this.examId, reason });
  }

  private saveMcFinal(): void {
    if (this.session && !this.session.submitted && this.mcs.length) {
      this.session.mc = Object.fromEntries(this.mcs.map((m) => [m.qid, m.selection()]));
    }
  }

  private renderGraded(): void {
    const s = this.session;
    if (!s) return;
    this.stop();
    this.head.classList.remove('is-sticky');
    this.alertEl.hidden = true; // a "10 minutes left" from the run is stale now
    this.body.hidden = false;
    this.classList.add('is-graded');
    this.classList.remove('is-low');
    this.setLocked(false);
    for (const d of this.body.querySelectorAll<HTMLDetailsElement>('details.sk-solution')) d.open = true;
    this.restoreMc();
    for (const m of this.mcs) if (!m.result) m.grade(this.rule, this.mcEach, this.negative);
    if (this.mcEl && !this.mcEl.querySelector('.sk-exam-mc-total')) {
      this.mcEl.append(h('p', { class: 'sk-exam-mc-total', lang: this.ui }));
    }
    for (const t of this.tasks) this.renderRubric(t);
    this.renderResult();
  }

  private renderRubric(t: Task): void {
    if (t.el.querySelector('.sk-rubric')) return;
    const checked = new Set(this.session?.rubric?.[t.id] ?? []);
    const legendId = uid('rubric');
    t.output = h('output', { class: 'sk-rubric-total' });
    const fs = h('fieldset', { class: 'sk-rubric', lang: this.ui, 'aria-labelledby': legendId },
      h('legend', { id: legendId }, `Grade this task (${pts(t.points)} points)`));
    if (t.rubric.length === 0) {
      fs.append(h('p', {}, 'This task has no rubric.'));
    }
    t.rubric.forEach((r, i) => {
      const box = h('input', { type: 'checkbox', checked: checked.has(i), 'data-index': String(i) });
      const text = h('span', { class: 'sk-rubric-criterion', lang: this.content });
      renderInline(text, r.criterion, r.criterion_html);
      box.addEventListener('change', () => this.onRubric(t, fs));
      fs.append(h('label', { class: 'sk-rubric-item' }, box, h('span', { class: 'sk-rubric-points' }, `${pts(r.points)} P`), text));
    });
    fs.append(t.output);
    t.el.append(fs);
  }

  private onRubric(t: Task, fs: HTMLElement): void {
    if (!this.session) return;
    this.session.rubric ??= {};
    this.session.rubric[t.id] = [...fs.querySelectorAll<HTMLInputElement>('input[type=checkbox]')]
      .filter((b) => b.checked)
      .map((b) => Number(b.dataset.index));
    this.save();
    this.renderResult();
  }

  private taskPoints(t: Task): number {
    const checked = this.session?.rubric?.[t.id] ?? [];
    return Math.min(t.points, checked.reduce((sum, i) => sum + (t.rubric[i]?.points ?? 0), 0));
  }

  private renderResult(): void {
    const s = this.session;
    if (!s?.submitted) return;
    const mcTotal = examPartPoints(this.mcs.map((m) => examPoints(m.result?.score ?? 0, this.mcEach)));
    const points: Record<string, number> = {};
    for (const t of this.tasks) {
      points[t.id] = this.taskPoints(t);
      if (t.output) t.output.textContent = `${pts(points[t.id] ?? 0)} of ${pts(t.points)} points`;
    }
    if (this.mcEl) {
      points[MC_ID] = Math.round(mcTotal * 100) / 100;
      const out = this.mcEl.querySelector('.sk-exam-mc-total');
      if (out) out.textContent = `Multiple choice: ${pts(mcTotal)} of ${pts(this.mcPoints)} points.`;
    }
    const total = Math.round(Object.values(points).reduce((a, b) => a + b, 0) * 100) / 100;
    const used = Math.min(this.durationMs, Date.parse(s.submitted) - Date.parse(s.started));
    storeOf(this).saveExamAttempt(this.examId, {
      started: s.started,
      duration_s: Math.max(0, Math.round(used / 1000)),
      points,
      total,
    });
    const grade = gradeEstimate(total, this.points, this.pass);
    const passed = this.pass === null ? null : total >= this.pass;
    const graded = this.tasks.every((t) => (s.rubric?.[t.id]?.length ?? 0) > 0) || this.tasks.length === 0;
    const rows = [
      ...this.tasks.map((t, i) => [h('span', {}, `${i + 1}. `, h('span', { lang: this.content }, t.title)), points[t.id] ?? 0, t.points, s.task_ms?.[t.id] ?? 0] as const),
      ...(this.mcEl ? [['Multiple choice', points[MC_ID] ?? 0, this.mcPoints, s.task_ms?.[MC_ID] ?? 0] as const] : []),
    ];
    const retake = h('button', { type: 'button', class: 'sk-btn' }, 'Retake exam');
    retake.addEventListener('click', () => {
      storeOf(this).setSession(this.sessionKey, null);
      location.reload();
    });
    const titleId = uid('result');
    this.head.replaceChildren(
      h('section', { class: 'sk-exam-result', 'aria-labelledby': titleId },
        h('h2', { id: titleId, tabindex: '-1' }, 'Result'),
        s.reason === 'time'
          ? h('p', { class: 'sk-exam-timeup', role: this.announceTimeUp ? 'alert' : null },
              'Time was up; the exam was submitted automatically.')
          : null,
        h('p', { class: 'sk-exam-total' },
          h('strong', {}, `${pts(total)} / ${pts(this.points)}`), ` points · ${percent(this.points ? total / this.points : 0)}`,
          passed === null ? null : h('span', { class: `sk-badge ${passed ? 'is-ok' : 'is-bad'}` },
            passed ? `passed (pass mark ${pts(this.pass ?? 0)})` : `not passed (pass mark ${pts(this.pass ?? 0)})`)),
        grade !== null
          ? h('p', { class: 'sk-exam-grade' }, 'Grade estimate: ', h('strong', {}, grade.toFixed(1)),
              h('span', { class: 'sk-muted' }, ' (pass mark = 4.0, full points = 1.0, linear in between)'))
          : null,
        h('p', {}, `Time used: ${duration(used)} of ${Math.round(this.durationMs / 60_000)} min.`),
        h('table', { class: 'sk-exam-table' },
          h('thead', {}, h('tr', {}, h('th', { scope: 'col' }, 'Part'), h('th', { scope: 'col' }, 'Points'), h('th', { scope: 'col' }, 'Time'))),
          h('tbody', {}, ...rows.map(([name, got, max, ms]) =>
            h('tr', {}, h('th', { scope: 'row' }, name), h('td', { class: 'sk-num' }, `${pts(got)} / ${pts(max)}`), h('td', { class: 'sk-num' }, duration(ms)))))),
        h('p', { class: 'sk-exam-hint', role: 'status' },
          graded
            ? 'Saved to your progress. Change a rubric tick and the result updates.'
            : 'Saved to your progress. Grade each task below with its rubric; the total updates as you tick.'),
        h('div', { class: 'sk-exam-actions' }, retake)),
      this.alertEl,
    );
    this.announceTimeUp = false;
  }
}
