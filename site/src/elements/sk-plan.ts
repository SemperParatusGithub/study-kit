// <sk-plan data-course> wrapping <li data-session="<id>" [data-date="YYYY-MM-DD"]>
// (docs/architecture.md §2.9, §3.2).
//
// Adds a "done" checkbox to every session, stored as plan:<id> {done}: into the session's
// [data-sk-plan-slot] when the shell provides one, else at the start of the <li>. When
// sessions carry data-date, past sessions that are not done show the "behind schedule"
// banner that suggests replanning with /regenerate <course> plan: the shell's
// [data-sk-behind] notice (its [data-sk-behind-text] gets the count), else one of its own.

import type { PlanEntry } from '../lib/store.ts';
import { behindCount } from '../lib/stats.ts';
import { courseOf, excerpt, h, storeFor, today } from './util.ts';

export class SkPlan extends HTMLElement {
  private ready = false;
  private rows: Array<{ id: string; li: HTMLElement; box: HTMLInputElement }> = [];
  private banner: HTMLElement | null = null;
  private own = false;
  private unsubscribe: (() => void) | null = null;

  private get course(): string {
    return this.dataset.course || courseOf(this);
  }

  connectedCallback(): void {
    if (!this.ready) {
      this.ready = true;
      for (const li of this.querySelectorAll<HTMLElement>('li[data-session]')) {
        const id = li.dataset.session ?? '';
        const label = excerpt(li.querySelector('.session-goal') ?? li, 80);
        const box = h('input', { type: 'checkbox', class: 'sk-plan-done', 'aria-label': `Done: ${label}` });
        box.addEventListener('change', () => {
          storeFor(this.course).setPlanDone(id, box.checked);
          this.render();
        });
        const check = h('label', { class: 'sk-plan-check', title: 'Mark as done' }, box);
        const slot = li.querySelector<HTMLElement>('[data-sk-plan-slot]');
        if (slot) slot.replaceChildren(check);
        else li.prepend(check);
        li.classList.add('sk-plan-item');
        if (slot) li.classList.add('has-slot');
        this.rows.push({ id, li, box });
      }
      this.banner = this.querySelector<HTMLElement>('[data-sk-behind]');
      if (!this.banner) {
        this.own = true;
        this.banner = h('p', { class: 'sk-plan-behind', role: 'status', hidden: true });
        this.prepend(this.banner);
      } else {
        this.banner.setAttribute('role', 'status');
      }
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
    for (const { id, li, box } of this.rows) {
      const done = (items[`plan:${id}`] as PlanEntry | undefined)?.done === true;
      box.checked = done;
      li.classList.toggle('is-done', done);
      const date = li.dataset.date;
      li.classList.toggle('is-past', Boolean(date && date < day));
    }
    const sessions = this.rows
      .map(({ id, li }) => ({ id, date: li.dataset.date ?? '' }))
      .filter((s) => s.date);
    const behind = behindCount(sessions, items, day);
    const banner = this.banner;
    if (!banner) return;
    banner.hidden = behind === 0;
    banner.dataset.count = String(behind);
    if (behind === 0) return;
    const count = `${behind} past ${behind === 1 ? 'session is' : 'sessions are'} not done.`;
    if (!this.own) {
      const text = banner.querySelector<HTMLElement>('[data-sk-behind-text]');
      if (text) text.textContent = count;
      return;
    }
    banner.replaceChildren(
      h('strong', {}, 'Behind schedule: '),
      `${count} To replan, run `,
      h('code', {}, `/regenerate ${this.course} plan`),
      ' in Claude Code.',
    );
  }
}
