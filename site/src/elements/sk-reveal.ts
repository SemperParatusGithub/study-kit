// <sk-reveal data-item="ex:<id>">: asks "Tried it?" before the solution opens
// (docs/architecture.md §3.2).
//
// Wraps the filter's <details class="sk-solution">. The first attempt to open it shows an
// inline confirmation instead; after "Yes, show the solution" (or once the answer check has
// been used) it opens normally. Opening it programmatically (exam mode, print) is not
// intercepted. Emits `sk:reveal` {item}. Without JS it is a plain <details>.

import type { ExEntry } from '../lib/store.ts';
import { emit, h, storeOf, uid } from './util.ts';

export class SkReveal extends HTMLElement {
  private ready = false;
  private confirmed = false;
  private panel: HTMLElement | null = null;

  get item(): string {
    return this.dataset.item ?? '';
  }

  connectedCallback(): void {
    if (this.ready) return;
    this.ready = true;
    const details = this.querySelector<HTMLDetailsElement>('details.sk-solution');
    const summary = details?.querySelector<HTMLElement>(':scope > summary');
    if (!details || !summary) return;
    this.classList.add('sk-reveal-ready');
    summary.addEventListener('click', (e) => {
      if (details.open || this.confirmed || this.tried()) return;
      e.preventDefault();
      this.ask(details, summary);
    });
    details.addEventListener('toggle', () => {
      if (details.open) {
        this.confirmed = true;
        this.panel?.remove();
        emit(this, 'sk:reveal', { item: this.item });
      }
    });
  }

  /** The answer check was used, so the student has made an attempt. */
  private tried(): boolean {
    if (!this.item) return false;
    return (storeOf(this).get<ExEntry>(this.item)?.answer_ok ?? null) !== null;
  }

  private ask(details: HTMLDetailsElement, summary: HTMLElement): void {
    if (this.panel?.isConnected) {
      this.panel.querySelector<HTMLButtonElement>('button')?.focus();
      return;
    }
    const textId = uid('reveal');
    const yes = h('button', { type: 'button', class: 'sk-btn sk-btn-primary' }, 'Yes, show the solution');
    // Not "Not yet": that is the self-assessment's rating button on the same page.
    const no = h('button', { type: 'button', class: 'sk-btn' }, 'Keep trying');
    this.panel = h(
      'div',
      { class: 'sk-reveal-confirm', role: 'group', 'aria-labelledby': textId },
      h('p', { id: textId },
        h('strong', {}, 'Tried it? '),
        'The solution helps most after your own attempt, even an incomplete one.'),
      h('div', { class: 'sk-reveal-actions' }, yes, no),
    );
    yes.addEventListener('click', () => {
      this.confirmed = true;
      details.open = true;
      summary.focus();
    });
    no.addEventListener('click', () => {
      this.panel?.remove();
      summary.focus();
    });
    details.after(this.panel);
    yes.focus();
  }
}
