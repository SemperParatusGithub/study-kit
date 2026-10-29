// <sk-hints data-item="ex:<id>">: the hint ladder (docs/architecture.md §3.2).
//
// Wraps the filter's <details class="sk-hint" data-index="n">. Unused hints are hidden and
// revealed one at a time ("Show hint 2 of 3"); the number used in this attempt is stored
// (store.useHints: more than one caps a "Solved" rating at "Partly") and announced as
// `sk:hint` {item, used, total}.
// Hints used in this attempt stay visible after a reload; once a rated exercise has come up
// for review, a new attempt starts with every hint closed again (store.exHints). Without JS
// the hints are plain collapsible <details>. A printed page shows every hint (scripts/site.ts
// opens every <details>), except in a running exam, where they stay locked; that is not
// using them.

import { emit, examDate, h, hashOf, isPrinting, langs, storeOf } from './util.ts';

export class SkHints extends HTMLElement {
  private ready = false;
  private hints: HTMLDetailsElement[] = [];
  private used = 0;
  private button: HTMLButtonElement | null = null;
  private status: HTMLElement | null = null;
  /** Hints shown only for printing, hidden again after it. */
  private printed: HTMLDetailsElement[] = [];
  private onBeforePrint = () => {
    if (this.closest('[inert]')) return; // a running exam keeps its hints locked
    this.printed = this.hints.filter((d) => d.hidden);
    for (const d of this.printed) d.hidden = false;
  };
  private onAfterPrint = () => {
    for (const d of this.printed) {
      d.hidden = true;
      d.open = false;
    }
    this.printed = [];
  };

  get item(): string {
    return this.dataset.item ?? '';
  }

  private get exId(): string {
    return this.item.replace(/^ex:/, '');
  }

  connectedCallback(): void {
    window.addEventListener('beforeprint', this.onBeforePrint);
    window.addEventListener('afterprint', this.onAfterPrint);
    if (this.ready) return;
    this.ready = true;
    this.hints = [...this.querySelectorAll<HTMLDetailsElement>('details.sk-hint')].sort(
      (a, b) => Number(a.dataset.index ?? 0) - Number(b.dataset.index ?? 0),
    );
    if (this.hints.length === 0) return;
    this.classList.add('sk-hints-ready');
    const stored = this.exId ? storeOf(this).exHints(this.exId, { examDate: examDate() }) : 0;
    this.used = Math.min(stored, this.hints.length);
    this.hints.forEach((d, i) => {
      const shown = i < this.used;
      d.hidden = !shown;
      d.open = shown;
      d.addEventListener('toggle', () => {
        // Opening every <details> for printing is not using a hint.
        if (d.open && i >= this.used && !isPrinting()) this.reveal(i + 1);
      });
    });
    this.button = h('button', { type: 'button', class: 'sk-btn' });
    this.status = h('p', { class: 'sk-hints-status', role: 'status' });
    this.button.addEventListener('click', () => this.revealNext());
    this.append(h('div', { class: 'sk-hints-bar', lang: langs(this).ui }, this.button, this.status));
    this.render(false);
  }

  disconnectedCallback(): void {
    window.removeEventListener('beforeprint', this.onBeforePrint);
    window.removeEventListener('afterprint', this.onAfterPrint);
  }

  private revealNext(): void {
    this.reveal(this.used + 1);
    const d = this.hints[this.used - 1];
    d?.querySelector('summary')?.focus();
  }

  private reveal(count: number): void {
    const n = Math.min(count, this.hints.length);
    if (n <= this.used) return;
    for (let i = this.used; i < n; i++) {
      const d = this.hints[i];
      if (!d) continue;
      d.hidden = false;
      d.open = true;
    }
    this.used = n;
    // More than one hint also caps an earlier "Solved" at "Partly" (store.useHints).
    if (this.exId) storeOf(this).useHints(this.exId, hashOf(this), n, { examDate: examDate() });
    this.render(true);
    emit(this, 'sk:hint', { item: this.item, used: this.used, total: this.hints.length });
  }

  private render(announce: boolean): void {
    const total = this.hints.length;
    if (!this.button || !this.status) return;
    if (this.used >= total) {
      this.button.hidden = true;
    } else {
      this.button.hidden = false;
      this.button.textContent = `Show hint ${this.used + 1} of ${total}`;
    }
    const text = this.used === 0 ? '' : this.used >= total
      ? `All ${total} hints shown.`
      : `${this.used} of ${total} hints used.`;
    if (announce || this.status.textContent !== text) this.status.textContent = text;
  }
}
