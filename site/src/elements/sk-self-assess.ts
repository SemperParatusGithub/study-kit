// <sk-self-assess data-item="ex:<id>">: Solved / Partly / Not yet (docs/architecture.md §3.2).
//
// The rating is stored as `rating` and schedules the exercise for review (Leitner: solved
// moves up a box, partly and not yet go to box 1). Using more than one hint in this attempt
// caps the rating at "Partly", also a "Solved" given before the hints (the store applies the
// cap; this element listens to `sk:hint` and shows it at once). A review is a new attempt:
// the hints of the rating before it no longer count (store.exHints).

import { HINT_CAP, type ExEntry, type Rating } from '../lib/store.ts';
import { contentChanged, examDate, h, hashOf, relativeDay, storeOf, uid } from './util.ts';

const CHOICES: ReadonlyArray<readonly [Rating, string]> = [
  ['solved', 'Solved'],
  ['partial', 'Partly'],
  ['not-yet', 'Not yet'],
];
const LABEL = new Map(CHOICES);

export class SkSelfAssess extends HTMLElement {
  private ready = false;
  private buttons = new Map<Rating, HTMLButtonElement>();
  private note: HTMLElement | null = null;
  private status: HTMLElement | null = null;
  private changed: HTMLElement | null = null;
  private onHint = (e: Event) => {
    const d = (e as CustomEvent<{ item: string }>).detail;
    if (d?.item === this.item) this.render(false);
  };

  get item(): string {
    return this.dataset.item ?? '';
  }

  private get exId(): string {
    return this.item.replace(/^ex:/, '');
  }

  connectedCallback(): void {
    document.addEventListener('sk:hint', this.onHint);
    if (this.ready) return;
    this.ready = true;
    const titleId = uid('assess');
    const group = h('div', { class: 'sk-assess-choices', role: 'group', 'aria-labelledby': titleId });
    for (const [rating, label] of CHOICES) {
      const b = h('button', { type: 'button', class: 'sk-btn sk-assess-choice', 'data-rating': rating, 'aria-pressed': 'false' }, label);
      b.addEventListener('click', () => this.rate(rating));
      this.buttons.set(rating, b);
      group.append(b);
    }
    this.note = h('p', { class: 'sk-assess-note', id: uid('note'), tabindex: '-1', hidden: true });
    this.status = h('p', { class: 'sk-assess-status', role: 'status' });
    this.changed = h('p', { class: 'sk-assess-changed', hidden: true }, 'Content changed since your attempt.');
    this.append(
      h('div', { class: 'sk-assess' },
        h('p', { class: 'sk-assess-title', id: titleId }, 'How did it go?'),
        group, this.note, this.changed, this.status),
    );
    this.render(false);
  }

  disconnectedCallback(): void {
    document.removeEventListener('sk:hint', this.onHint);
  }

  private entry(): ExEntry | undefined {
    return this.exId ? storeOf(this).get<ExEntry>(this.item) : undefined;
  }

  /** Hints used in the current attempt. */
  private hints(): number {
    return this.exId ? storeOf(this).exHints(this.exId, { examDate: examDate() }) : 0;
  }

  private capped(): boolean {
    return this.hints() > HINT_CAP;
  }

  private rate(rating: Rating): void {
    if (!this.exId) return;
    if (rating === 'solved' && this.capped()) {
      this.note?.focus();
      return;
    }
    storeOf(this).rateEx(this.exId, hashOf(this), rating, { examDate: examDate() });
    this.render(true);
  }

  private render(announce: boolean): void {
    const entry = this.entry();
    const capped = this.capped();
    for (const [rating, b] of this.buttons) {
      b.setAttribute('aria-pressed', String(entry?.rating === rating));
      if (rating === 'solved') {
        b.setAttribute('aria-disabled', String(capped));
        if (capped && this.note) b.setAttribute('aria-describedby', this.note.id);
        else b.removeAttribute('aria-describedby');
      }
    }
    if (this.note) {
      this.note.hidden = !capped;
      this.note.textContent = capped ? `You used ${this.hints()} hints, so the best rating is “Partly”.` : '';
    }
    if (this.changed) this.changed.hidden = !contentChanged(entry?.h, hashOf(this));
    if (this.status) {
      const text = entry?.rating
        ? `Saved: ${LABEL.get(entry.rating) ?? entry.rating}${entry.due ? `, review again ${relativeDay(entry.due)}` : ''}.`
        : '';
      if (announce || this.status.textContent !== text) this.status.textContent = text;
    }
  }
}
