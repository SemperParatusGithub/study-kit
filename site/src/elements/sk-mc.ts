// <sk-mc>: one multiple-choice question (docs/architecture.md §2.6, §3.2).
//
// Markup (from mcq.lua, plus data-h from the site loader):
//   <sk-mc data-id data-type="single|multi|kprim" data-difficulty data-topic data-pin-last data-h>
//     <div class="sk-stem">…</div>
//     <sk-opt data-key="A" data-correct="true|false"><div class="sk-opt-text">…</div>
//       <div class="sk-why" hidden>…</div></sk-opt> …
//     <div class="sk-explanation" hidden>…</div>
//   </sk-mc>
// Optional attributes set by containers: data-mode="practice|deferred|exam" (default
// practice), data-scoring (multi rule; else the nearest [data-mc-scoring]), data-record="false",
// data-shuffle="false".
//
// Options are shown in the mc.pdf order (shuffle.ts) with display letters A–F; answers are
// stored by source key. Single → radio buttons, multi → checkboxes, Kprim → a true/false
// pair per statement. "Sure" or "Unsure" is required before Check. Checking shows every
// option's why and the explanation, records the attempt (Leitner) and emits `sk:answer`
// (detail: McAnswerDetail). Keyboard: 1–6 choose (Kprim: cycle true/false), S/U sure or
// unsure, Enter check, N next (`sk:next`, cancelable; otherwise focus the next question).

import { dayOf, type Conf } from '../lib/leitner.ts';
import { LETTERS, optionOrder } from '../lib/shuffle.ts';
import {
  isCorrect,
  isMcType,
  isMisconception,
  multiRule,
  score as scoreOf,
  type McType,
  type MultiRule,
} from '../lib/scoring.ts';
import type { McEntry } from '../lib/store.ts';
import {
  contentChanged,
  emit,
  examDate,
  h,
  hashOf,
  isTyping,
  pts,
  relativeDay,
  storeOf,
  uid,
} from './util.ts';

export type McMode = 'practice' | 'deferred' | 'exam';

export interface McSelection {
  /** Keys selected (single, multi) or judged true (Kprim), in source keys. */
  chosen: string[];
  /** Keys with a judgement (Kprim); all keys for single and multi. */
  answered: string[];
}

export interface McAnswerDetail extends McSelection {
  id: string;
  item: string;
  topic: string;
  type: McType;
  score: number;
  conf: Conf | null;
  ms: number;
  correct: boolean;
  misconception: boolean;
  box: number | null;
  due: string | null;
}

interface Opt {
  key: string;
  correct: boolean;
  el: HTMLElement;
  why: HTMLElement | null;
  mark: HTMLElement;
  inputs: HTMLInputElement[];
}

const TYPE_LABEL: Record<McType, string> = {
  single: 'Single choice',
  multi: 'Multiple choice',
  kprim: 'Kprim',
};

const INSTRUCTIONS: Record<McType, string> = {
  single: 'Choose one answer.',
  multi: 'Choose every correct answer.',
  kprim: 'Judge each statement as true or false.',
};

export class SkMc extends HTMLElement {
  qid = '';
  type: McType = 'single';
  topic = '';
  result: McAnswerDetail | null = null;

  private ready = false;
  private name = uid('mc');
  private opts: Opt[] = [];
  private conf: Conf | null = null;
  private confInputs: HTMLInputElement[] = [];
  private checkBtn: HTMLButtonElement | null = null;
  private retryBtn: HTMLButtonElement | null = null;
  private status: HTMLElement | null = null;
  private feedback: HTMLElement | null = null;
  private note: HTMLElement | null = null;
  private explanation: HTMLElement | null = null;
  private startedAt: number | null = null;

  get mode(): McMode {
    const m = this.dataset.mode;
    if (m === 'deferred' || m === 'exam' || m === 'practice') return m;
    return this.closest('sk-exam') ? 'exam' : 'practice';
  }

  get rule(): MultiRule {
    return multiRule(
      this.dataset.scoring ?? this.closest('[data-mc-scoring]')?.getAttribute('data-mc-scoring'),
    );
  }

  private get records(): boolean {
    return this.mode !== 'exam' && this.dataset.record !== 'false';
  }

  connectedCallback(): void {
    if (this.ready) return;
    this.ready = true;
    this.build();
  }

  // --- building ---------------------------------------------------------------------

  private build(): void {
    this.qid = this.dataset.id ?? '';
    this.type = isMcType(this.dataset.type) ? this.dataset.type : 'single';
    this.topic = this.dataset.topic ?? '';
    const stem = this.querySelector<HTMLElement>(':scope > .sk-stem');
    const raw = [...this.querySelectorAll<HTMLElement>(':scope > sk-opt')];
    if (!stem || raw.length === 0) return;
    this.explanation = this.querySelector<HTMLElement>(':scope > .sk-explanation');

    stem.id ||= uid('stem');
    this.setAttribute('role', 'group');
    this.setAttribute('aria-labelledby', stem.id);
    this.tabIndex = -1;
    this.classList.add('sk-mc-ready');

    const difficulty = Number(this.dataset.difficulty);
    const head = h(
      'div',
      { class: 'sk-mc-head' },
      h('span', { class: 'sk-mc-type' }, TYPE_LABEL[this.type]),
      difficulty >= 1 && difficulty <= 4
        ? h(
            'span',
            { class: 'sk-mc-difficulty', title: `Difficulty ${difficulty} of 4` },
            h('span', { 'aria-hidden': 'true' }, '●'.repeat(difficulty) + '○'.repeat(4 - difficulty)),
            h('span', { class: 'sk-vh' }, `Difficulty ${difficulty} of 4`),
          )
        : null,
    );
    this.note = h('p', { class: 'sk-mc-note', hidden: true });
    this.insertBefore(head, stem);
    this.insertBefore(this.note, stem);

    const instr = h('p', { class: 'sk-mc-instr', id: uid('instr') }, INSTRUCTIONS[this.type]);
    const list = h('div', {
      class: `sk-mc-options sk-mc-${this.type}`,
      role: this.type === 'single' ? 'radiogroup' : 'group',
      'aria-labelledby': `${stem.id} ${instr.id}`,
    });
    const order =
      this.dataset.shuffle === 'false'
        ? raw.map((_, i) => i)
        : optionOrder(this.qid, raw.length, this.dataset.pinLast === 'true');
    order.forEach((src, i) => {
      const el = raw[src];
      if (el) list.append(this.buildOption(el, LETTERS[i] ?? '?'));
    });
    this.insertBefore(instr, this.explanation);
    this.insertBefore(list, this.explanation);

    if (this.mode !== 'exam') this.insertBefore(this.buildConfidence(), this.explanation);

    this.checkBtn = h('button', { type: 'button', class: 'sk-btn sk-btn-primary' }, 'Check');
    this.retryBtn = h('button', { type: 'button', class: 'sk-btn', hidden: true }, 'Try again');
    this.status = h('p', { class: 'sk-mc-status', id: uid('status'), 'aria-live': 'polite' });
    this.checkBtn.setAttribute('aria-describedby', this.status.id);
    const actions = h(
      'div',
      { class: 'sk-mc-actions' },
      this.mode === 'practice' ? this.checkBtn : null,
      this.retryBtn,
      this.mode === 'exam'
        ? null
        : h('span', { class: 'sk-mc-keys', 'aria-hidden': 'true' },
            h('kbd', {}, '1'), '–', h('kbd', {}, String(Math.min(6, raw.length))), ' choose · ',
            h('kbd', {}, 'S'), '/', h('kbd', {}, 'U'), ' sure · ',
            ...(this.mode === 'deferred'
              ? [h('kbd', {}, 'Enter'), '/', h('kbd', {}, 'N'), ' next']
              : [h('kbd', {}, 'Enter'), ' check · ', h('kbd', {}, 'N'), ' next'])),
    );
    this.feedback = h('div', { class: 'sk-mc-feedback', role: 'status', tabindex: '-1' });
    this.insertBefore(actions, this.explanation);
    this.insertBefore(this.status, this.explanation);
    this.insertBefore(this.feedback, this.explanation);
    if (this.explanation && !this.explanation.querySelector(':scope > .sk-mc-expl-title')) {
      this.explanation.prepend(h('p', { class: 'sk-mc-expl-title' }, 'Explanation'));
    }

    this.checkBtn.addEventListener('click', () => this.submit());
    this.retryBtn.addEventListener('click', () => this.reset());
    this.addEventListener('change', (e) => this.onChange(e));
    this.addEventListener('keydown', (e) => this.onKey(e));
    this.addEventListener('pointerdown', () => this.start());
    this.addEventListener('focusin', () => this.start());
    this.updateState();
    if (this.mode !== 'exam') this.showHistory();
  }

  private buildOption(el: HTMLElement, letter: string): HTMLElement {
    const key = el.dataset.key ?? letter;
    const text = el.querySelector<HTMLElement>(':scope > .sk-opt-text');
    const why = el.querySelector<HTMLElement>(':scope > .sk-why');
    const letterEl = h('span', { class: 'sk-opt-letter', id: uid('letter') }, letter);
    const textId = text ? (text.id ||= uid('opt')) : '';
    const mark = h('p', { class: 'sk-opt-mark', hidden: true });
    el.classList.add('sk-opt');
    el.dataset.letter = letter;
    const opt: Opt = { key, correct: el.dataset.correct === 'true', el, why, mark, inputs: [] };
    if (this.type === 'kprim') {
      const group = h('span', {
        class: 'sk-kprim',
        role: 'radiogroup',
        'aria-labelledby': `${letterEl.id} ${textId}`,
      });
      for (const value of ['true', 'false']) {
        const input = h('input', { type: 'radio', name: `${this.name}-${key}`, value });
        opt.inputs.push(input);
        group.append(
          h('label', { class: 'sk-kprim-choice' }, input, h('span', {}, value === 'true' ? 'True' : 'False')),
        );
      }
      el.replaceChildren(letterEl, ...(text ? [text] : []), group, mark, ...(why ? [why] : []));
    } else {
      const input = h('input', {
        type: this.type === 'single' ? 'radio' : 'checkbox',
        name: this.name,
        value: key,
        class: 'sk-opt-input',
        'aria-labelledby': `${letterEl.id} ${textId}`,
      });
      opt.inputs.push(input);
      const control = h('span', { class: 'sk-opt-control' }, input, letterEl);
      el.replaceChildren(control, ...(text ? [text] : []), mark, ...(why ? [why] : []));
      // The whole row toggles the input (the option text cannot sit inside a <label>:
      // it may hold links and block content).
      el.addEventListener('click', (e) => {
        const target = e.target as HTMLElement;
        if (this.result || target.closest('input, a, button, label, summary')) return;
        if (window.getSelection()?.toString()) return;
        input.click();
      });
    }
    this.opts.push(opt);
    return el;
  }

  private buildConfidence(): HTMLElement {
    const fs = h('fieldset', { class: 'sk-mc-conf' }, h('legend', {}, 'How sure are you?'));
    for (const [value, label] of [['sure', 'Sure'], ['unsure', 'Unsure']] as const) {
      const input = h('input', { type: 'radio', name: `${this.name}-conf`, value });
      this.confInputs.push(input);
      fs.append(h('label', { class: 'sk-mc-conf-choice' }, input, h('span', {}, label)));
    }
    return fs;
  }

  // --- state --------------------------------------------------------------------------

  /** Start the answer clock (first interaction, or when a quiz shows the question). */
  start(): void {
    this.startedAt ??= Date.now();
  }

  selection(): McSelection {
    const chosen: string[] = [];
    const answered: string[] = [];
    for (const o of this.opts) {
      if (this.type === 'kprim') {
        const picked = o.inputs.find((i) => i.checked);
        if (picked) {
          answered.push(o.key);
          if (picked.value === 'true') chosen.push(o.key);
        }
      } else {
        answered.push(o.key);
        if (o.inputs[0]?.checked) chosen.push(o.key);
      }
    }
    return { chosen, answered };
  }

  /** Restore a selection (exam reload). */
  setSelection(sel: Partial<McSelection>): void {
    const chosen = new Set(sel.chosen ?? []);
    const answered = new Set(sel.answered ?? sel.chosen ?? []);
    for (const o of this.opts) {
      if (this.type === 'kprim') {
        for (const i of o.inputs) i.checked = answered.has(o.key) && (i.value === 'true') === chosen.has(o.key);
      } else if (o.inputs[0]) {
        o.inputs[0].checked = chosen.has(o.key);
      }
    }
    this.updateState();
  }

  private answerComplete(): boolean {
    const { chosen, answered } = this.selection();
    if (this.type === 'kprim') return answered.length === this.opts.length;
    return this.type === 'single' ? chosen.length === 1 : chosen.length >= 1;
  }

  /** The answer is complete and, outside exams, the confidence is set. */
  isComplete(): boolean {
    return this.answerComplete() && (this.mode === 'exam' || this.conf !== null);
  }

  private missing(): string {
    if (!this.answerComplete()) {
      if (this.type === 'kprim') return 'Judge all four statements first.';
      return this.type === 'single' ? 'Choose an answer first.' : 'Choose at least one answer first.';
    }
    return this.conf === null ? 'Say whether you are sure before checking.' : '';
  }

  private updateState(): void {
    for (const o of this.opts) {
      const on = o.inputs.some((i) => i.checked);
      o.el.classList.toggle('is-selected', this.type !== 'kprim' && on);
      o.el.classList.toggle('is-judged', this.type === 'kprim' && on);
    }
    if (this.checkBtn) this.checkBtn.setAttribute('aria-disabled', String(!this.isComplete()));
    if (this.status && this.isComplete()) this.status.textContent = '';
  }

  private onChange(e: Event): void {
    const t = e.target as HTMLInputElement;
    if (this.confInputs.includes(t)) this.conf = t.value === 'sure' ? 'sure' : 'unsure';
    this.start();
    this.updateState();
    emit(this, 'sk:change', { id: this.qid, ...this.selection(), conf: this.conf, complete: this.isComplete() });
  }

  private setConf(conf: Conf): void {
    const input = this.confInputs.find((i) => i.value === conf);
    if (!input || this.result) return;
    input.checked = true;
    input.dispatchEvent(new Event('change', { bubbles: true }));
  }

  private pick(index: number): void {
    const o = this.opts[index];
    if (!o || this.result) return;
    if (this.type === 'kprim') {
      const [yes, no] = o.inputs;
      if (!yes || !no) return;
      const next = yes.checked ? no : yes; // none → true → false → true
      next.checked = true;
      next.focus();
      next.dispatchEvent(new Event('change', { bubbles: true }));
      return;
    }
    const input = o.inputs[0];
    if (!input) return;
    if (this.type === 'single') input.checked = true;
    else input.checked = !input.checked;
    input.focus();
    input.dispatchEvent(new Event('change', { bubbles: true }));
  }

  private onKey(e: KeyboardEvent): void {
    if (isTyping(e)) return;
    const k = e.key;
    if (/^[1-9]$/.test(k)) {
      if (Number(k) <= this.opts.length && !this.result) {
        e.preventDefault();
        this.pick(Number(k) - 1);
      }
    } else if ((k === 's' || k === 'S' || k === 'u' || k === 'U') && this.mode !== 'exam') {
      e.preventDefault();
      this.setConf(k.toLowerCase() === 's' ? 'sure' : 'unsure');
    } else if (k === 'Enter') {
      const t = e.target as HTMLElement;
      if (t.closest('button, a, summary')) return;
      e.preventDefault();
      if (this.result || this.mode === 'deferred') this.next();
      else if (this.mode === 'practice') this.submit();
    } else if (k === 'n' || k === 'N') {
      e.preventDefault();
      this.next();
    }
  }

  /** Ask the container for the next question; without one, focus the next <sk-mc>. */
  next(): void {
    const handled = !emit(this, 'sk:next', { id: this.qid }, true);
    if (handled) return;
    const all = [...document.querySelectorAll<HTMLElement>('sk-mc')];
    const following = all[all.indexOf(this) + 1];
    if (following) {
      following.focus();
      following.scrollIntoView({ block: 'start', behavior: 'auto' });
    }
  }

  // --- checking -----------------------------------------------------------------------

  /** Score, record and (unless reveal is false) show the result. Null if incomplete. */
  submit(options: { reveal?: boolean } = {}): McAnswerDetail | null {
    if (this.result) return this.result;
    if (!this.isComplete()) {
      if (this.status) this.status.textContent = this.missing();
      return null;
    }
    const sel = this.selection();
    const value = scoreOf(this.type, this.opts, sel.chosen, this.rule, sel.answered);
    const detail: McAnswerDetail = {
      id: this.qid,
      item: `mc:${this.qid}`,
      topic: this.topic,
      type: this.type,
      ...sel,
      score: value,
      conf: this.conf,
      ms: this.startedAt === null ? 0 : Date.now() - this.startedAt,
      correct: isCorrect(value),
      misconception: this.conf !== null && isMisconception(value, this.conf),
      box: null,
      due: null,
    };
    if (this.records && this.conf) {
      const r = storeOf(this).recordMc(
        this.qid,
        { h: this.dataset.h ?? hashOf(this), chosen: sel.chosen, score: value, conf: this.conf, ms: detail.ms },
        { examDate: examDate() },
      );
      detail.box = r.review.box;
      detail.due = r.review.due;
    }
    this.result = detail;
    this.lock();
    if (options.reveal !== false) this.reveal();
    emit(this, 'sk:answer', detail);
    return detail;
  }

  /** Exam scoring: whatever is selected counts (open Kprim statements are wrong). */
  grade(rule: MultiRule = this.rule, pointsEach?: number): number {
    const sel = this.selection();
    const value = scoreOf(this.type, this.opts, sel.chosen, rule, sel.answered);
    this.result = {
      id: this.qid,
      item: `mc:${this.qid}`,
      topic: this.topic,
      type: this.type,
      ...sel,
      score: value,
      conf: null,
      ms: 0,
      correct: isCorrect(value),
      misconception: false,
      box: null,
      due: null,
    };
    this.lock();
    this.reveal(pointsEach);
    return value;
  }

  private lock(): void {
    for (const o of this.opts) for (const i of o.inputs) i.disabled = true;
    for (const i of this.confInputs) i.disabled = true;
    this.classList.add('is-locked');
    this.checkBtn?.setAttribute('hidden', '');
  }

  /** Show every why, the explanation and the verdict. */
  reveal(pointsEach?: number): void {
    const r = this.result;
    if (!r) return;
    const chosen = new Set(r.chosen);
    const answered = new Set(r.answered);
    for (const o of this.opts) {
      const picked = chosen.has(o.key);
      let ok: boolean;
      let text: string;
      if (this.type === 'kprim') {
        const truth = o.correct ? 'True' : 'False';
        ok = answered.has(o.key) && picked === o.correct;
        const said = answered.has(o.key) ? `you said ${picked ? 'true' : 'false'}` : 'not judged';
        text = `${truth}, ${said}`;
        o.el.classList.add(ok ? 'is-right' : 'is-wrong');
      } else {
        ok = picked === o.correct;
        text = o.correct
          ? picked ? 'Correct, your choice' : 'Missed: this answer is correct'
          : picked ? 'Wrong, your choice' : 'Wrong';
        o.el.classList.add(o.correct ? 'is-correct' : 'is-incorrect');
        if (picked) o.el.classList.add(ok ? 'is-right' : 'is-wrong');
        else if (o.correct) o.el.classList.add('is-missed');
      }
      const symbol = this.type === 'kprim' || picked || o.correct ? (ok ? '✓' : '✗') : '·';
      o.mark.replaceChildren(h('span', { 'aria-hidden': 'true' }, symbol), ' ', text);
      o.mark.hidden = false;
      if (o.why) o.why.hidden = false;
    }
    if (this.explanation) this.explanation.hidden = false;
    this.classList.add('is-checked');
    const verdict =
      r.correct ? 'Correct.' : r.score > 0 ? `Partly correct: ${pts(r.score)} of 1 point.` : 'Not correct.';
    const parts: string[] = [verdict];
    if (pointsEach !== undefined) parts.push(`${pts(r.score * pointsEach)} of ${pts(pointsEach)} points.`);
    if (r.misconception) {
      parts.push('You were sure, so this counts as a misconception; it comes back today.');
    } else if (r.due) {
      parts.push(`Next review ${relativeDay(r.due)}.`);
    }
    if (this.feedback) {
      this.feedback.className = `sk-mc-feedback ${r.correct ? 'is-ok' : r.score > 0 ? 'is-partial' : 'is-bad'}`;
      this.feedback.replaceChildren(
        h('span', { class: 'sk-mc-verdict-icon', 'aria-hidden': 'true' }, r.correct ? '✓' : r.score > 0 ? '◐' : '✗'),
        ' ',
        parts.join(' '),
      );
    }
    if (this.mode === 'practice' && this.retryBtn) this.retryBtn.hidden = false;
    if (this.contains(document.activeElement) || document.activeElement === document.body) {
      this.feedback?.focus({ preventScroll: true });
    }
  }

  /** Clear the answer for another attempt. */
  reset(): void {
    this.result = null;
    this.conf = null;
    this.startedAt = null;
    for (const o of this.opts) {
      for (const i of o.inputs) {
        i.checked = false;
        i.disabled = false;
      }
      o.el.classList.remove('is-correct', 'is-incorrect', 'is-right', 'is-wrong', 'is-missed');
      o.mark.hidden = true;
      if (o.why) o.why.hidden = true;
    }
    for (const i of this.confInputs) {
      i.checked = false;
      i.disabled = false;
    }
    if (this.explanation) this.explanation.hidden = true;
    this.classList.remove('is-checked', 'is-locked');
    this.checkBtn?.removeAttribute('hidden');
    if (this.retryBtn) this.retryBtn.hidden = true;
    if (this.feedback) {
      this.feedback.className = 'sk-mc-feedback';
      this.feedback.replaceChildren();
    }
    this.updateState();
    this.showHistory();
    this.opts[0]?.inputs[0]?.focus();
  }

  /** "Last time: …" or "Content changed since your attempt." */
  private showHistory(): void {
    if (!this.note || this.dataset.history === 'false') return;
    const entry = storeOf(this).get<McEntry>(`mc:${this.qid}`);
    const last = entry?.attempts.at(-1);
    this.note.hidden = true;
    this.note.classList.remove('is-warning');
    if (!entry || !last) return;
    if (contentChanged(entry.h, this.dataset.h ?? hashOf(this))) {
      this.note.textContent = 'Content changed since your attempt.';
      this.note.classList.add('is-warning');
      this.note.hidden = false;
      return;
    }
    const verdict = isCorrect(last.score) ? 'correct' : last.score > 0 ? 'partly correct' : 'wrong';
    const when = relativeDay(dayOf(new Date(last.t)));
    const due = entry.due ? ` · next review ${relativeDay(entry.due)}` : '';
    this.note.textContent = `Last time: ${verdict} (${last.conf}), ${when}${due}.`;
    this.note.hidden = false;
  }
}
