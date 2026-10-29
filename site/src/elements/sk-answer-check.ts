// <sk-answer-check data-item="ex:<id>"
//   data-answers='[{key,label,label_html,value,unit,rtol,atol,expr,symbols}]'>
// (docs/architecture.md §2.5, §3.2). label_html is the label with its math rendered at
// build time by the shell; the content hash is the nearest data-h (the exercise <article>).
//
// One input per answer: numbers in German or English notation with unit and SI prefix
// ("1,59 kHz"), or an expression in the given symbols. Each answer gets its own verdict,
// the reading of the input ("Read as …") and, for typical mistakes, a hint (2π, √2, power
// of ten, dB). The result is stored as `answer_ok` (true only when every answer is right)
// and announced as `sk:answer-check` {item, ok}.

import { check, parseAnswers, toleranceHint, type AnswerSpec } from '../lib/answer.ts';
import type { ExEntry } from '../lib/store.ts';
import { emit, h, hashOf, langs, renderInline, storeOf, uid } from './util.ts';

interface Row {
  spec: AnswerSpec;
  input: HTMLInputElement;
  result: HTMLElement;
}

export class SkAnswerCheck extends HTMLElement {
  private ready = false;
  private rows: Row[] = [];
  private summary: HTMLElement | null = null;

  get item(): string {
    return this.dataset.item ?? '';
  }

  connectedCallback(): void {
    if (this.ready) return;
    this.ready = true;
    const answers = parseAnswers(this.dataset.answers);
    if (answers.length === 0) return;
    const titleId = uid('check');
    const lang = langs(this);
    const form = h('form', { class: 'sk-check', lang: lang.ui, novalidate: true, 'aria-labelledby': titleId });
    form.append(h('p', { class: 'sk-check-title', id: titleId }, answers.length > 1 ? 'Check your answers' : 'Check your answer'));
    for (const spec of answers) {
      const id = uid('answer');
      const label = h('label', { class: 'sk-check-label', for: id, lang: lang.content });
      renderInline(label, spec.label || spec.key, spec.label_html);
      const hintId = uid('hint');
      const hint = spec.expr
        ? `Expression in ${(spec.symbols ?? []).join(', ')}`
        : [spec.unit ? `in ${spec.unit}` : 'no unit', toleranceHint(spec)].filter(Boolean).join(' · ');
      const input = h('input', {
        id,
        type: 'text',
        class: 'sk-check-input',
        autocomplete: 'off',
        autocapitalize: 'off',
        spellcheck: 'false',
        enterkeyhint: 'done',
        'aria-describedby': hintId,
        placeholder: spec.expr ? 'e.g. 1/(1 + s*R*C)' : spec.unit ? `e.g. 1,5 ${spec.unit}` : 'e.g. 0,25',
      });
      const result = h('div', { class: 'sk-check-result', role: 'status' });
      form.append(
        h('div', { class: 'sk-check-row' },
          label,
          h('div', { class: 'sk-check-field' }, input, h('span', { class: 'sk-check-hint', id: hintId }, hint)),
          result),
      );
      this.rows.push({ spec, input, result });
    }
    this.summary = h('p', { class: 'sk-check-summary', role: 'status' });
    form.append(
      h('div', { class: 'sk-check-actions' }, h('button', { type: 'submit', class: 'sk-btn sk-btn-primary' }, 'Check'), this.summary),
    );
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      this.run();
    });
    this.append(form);
    const prev = this.item ? storeOf(this).get<ExEntry>(this.item) : undefined;
    if (prev?.answer_ok === true) this.summary.textContent = 'You solved this before.';
  }

  private run(): void {
    let ok = true;
    let first: HTMLInputElement | null = null;
    for (const row of this.rows) {
      const v = check(row.input.value, row.spec);
      ok &&= v.ok;
      if (!v.ok && !first) first = row.input;
      row.input.setAttribute('aria-invalid', String(!v.ok));
      row.result.className = `sk-check-result ${v.ok ? 'is-ok' : 'is-bad'}`;
      row.result.replaceChildren(
        h('span', { class: 'sk-check-icon', 'aria-hidden': 'true' }, v.ok ? '✓' : '✗'),
        ' ',
        h('span', {},
          v.message,
          v.read ? h('span', { class: 'sk-check-read' }, ` Read as ${v.read}.`) : null,
          !v.ok && v.hint ? h('span', { class: 'sk-check-tip' }, ` ${v.hint}`) : null),
      );
    }
    const id = this.item.replace(/^ex:/, '');
    if (id) storeOf(this).updateEx(id, hashOf(this), { answer_ok: ok });
    if (this.summary) {
      this.summary.textContent = ok
        ? this.rows.length > 1 ? 'All answers are correct.' : ''
        : '';
    }
    if (first) first.focus();
    emit(this, 'sk:answer-check', { item: this.item, ok });
  }
}
