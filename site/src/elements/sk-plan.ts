// <sk-plan data-course> wrapping <li data-session="<id>" [data-date="YYYY-MM-DD"]>
// (docs/architecture.md §2.9, §3.2).
//
// Adds a "done" checkbox to every session, stored as plan:<id> {done}. When sessions carry
// data-date, past sessions that are not done show a "behind schedule" banner that suggests
// replanning with /regenerate <course> plan.

import type { PlanEntry } from '../lib/store.ts';
import { courseOf, excerpt, h, storeFor, today } from './util.ts';

export class SkPlan extends HTMLElement {
  private ready = false;
  private rows: Array<{ id: string; li: HTMLElement; box: HTMLInputElement }> = [];
  private banner: HTMLElement = h('p', { class: 'sk-plan-behind', role: 'status', hidden: true });
  private unsubscribe: (() => void) | null = null;

  private get course(): string {
    return this.dataset.course || courseOf(this);
  }

  connectedCallback(): void {
    if (!this.ready) {
      this.ready = true;
      for (const li of this.querySelectorAll<HTMLElement>('li[data-session]')) {
        const id = li.dataset.session ?? '';
        const box = h('input', { type: 'checkbox', class: 'sk-plan-done', 'aria-label': `Done: ${excerpt(li, 80)}` });
        box.addEventListener('change', () => {
          storeFor(this.course).setPlanDone(id, box.checked);
          this.render();
        });
        li.prepend(h('label', { class: 'sk-plan-check', title: 'Mark as done' }, box));
        li.classList.add('sk-plan-item');
        this.rows.push({ id, li, box });
      }
      this.prepend(this.banner);
      this.classList.add('sk-plan-ready');
    }
    this.unsubscribe ??= storeFor(this.course).subscribe(() => this.render());
    this.render();
  }

  disconnectedCallback(): void {
    this.unsubscribe?.();
    this.unsubscribe = null;
  }

  private render(): void {
    const items = storeFor(this.course).read().items;
    const day = today();
    let behind = 0;
    for (const { id, li, box } of this.rows) {
      const done = (items[`plan:${id}`] as PlanEntry | undefined)?.done === true;
      box.checked = done;
      li.classList.toggle('is-done', done);
      const date = li.dataset.date;
      const past = Boolean(date && date < day);
      li.classList.toggle('is-past', past);
      if (past && !done) behind++;
    }
    this.banner.hidden = behind === 0;
    if (behind > 0) {
      this.banner.replaceChildren(
        h('strong', {}, 'Behind schedule: '),
        `${behind} past ${behind === 1 ? 'session is' : 'sessions are'} not done. To replan, run `,
        h('code', {}, `/regenerate ${this.course} plan`),
        ' in Claude Code.',
      );
    }
  }
}
