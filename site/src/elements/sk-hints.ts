// <sk-hints data-item="ex:<id>">: the hint ladder (docs/architecture.md §3.2).
//
// Wraps the filter's <details class="sk-hint" data-index="n">. Unused hints are hidden and
// revealed one at a time ("Show hint 2 of 3"); the number used is stored as `hints` of the
// exercise entry (the maximum ever used) and announced as `sk:hint` {item, used, total}.
// Hints used earlier stay visible after a reload. Without JS the hints are plain
// collapsible <details>.

import type { ExEntry } from '../lib/store.ts';
import { emit, h, hashOf, isPrinting, storeOf } from './util.ts';

export class SkHints extends HTMLElement {
  private ready = false;
  private hints: HTMLDetailsElement[] = [];
  private used = 0;
  private button: HTMLButtonElement | null = null;
  private status: HTMLElement | null = null;

  get item(): string {
    return this.dataset.item ?? '';
  }

  private get exId(): string {
    return this.item.replace(/^ex:/, '');
  }

  connectedCallback(): void {
    if (this.ready) return;
    this.ready = true;
    this.hints = [...this.querySelectorAll<HTMLDetailsElement>('details.sk-hint')].sort(
      (a, b) => Number(a.dataset.index ?? 0) - Number(b.dataset.index ?? 0),
    );
    if (this.hints.length === 0) return;
    this.classList.add('sk-hints-ready');
    const stored = this.exId ? (storeOf(this).get<ExEntry>(this.item)?.hints ?? 0) : 0;
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
    this.append(h('div', { class: 'sk-hints-bar' }, this.button, this.status));
    this.render(false);
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
    if (this.exId) {
      const store = storeOf(this);
      const prev = store.get<ExEntry>(this.item)?.hints ?? 0;
      store.updateEx(this.exId, hashOf(this), { hints: Math.max(prev, n) });
    }
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
