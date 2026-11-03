// <sk-cards>: a topic's flash cards, one at a time (docs/architecture.md §5.6).
//
// The page holds every card as a list (<sk-card data-id data-h data-topic> with its front and
// back, lib: flashcards.lua), which stays as it is without JavaScript and on paper. The
// element hides that list and drills the round lib/cards.ts picks: think, turn the card, say
// whether you knew it. A rating reschedules the card (Leitner, lib/leitner.ts, no exam clamp)
// in the progress store as `card:<id>`. A card you did not know comes back at the end of the
// round without being rated a second time, so one lucky repeat cannot move it up a box.
// Keyboard, unless the focus is in a form field: Space or Enter turn the card, 1 "Didn't
// know", 2 "Knew it". `?topic=<chapter>` opens one chapter.

import { cardCounts, cardQueue, nextReview, type CardMode, type CardRef } from '../lib/cards.ts';
import { randomSeed } from '../lib/shuffle.ts';
import type { ProgressStore } from '../lib/store.ts';
import { announce, emit, h, isTyping, langs, relativeDay, storeOf, today } from './util.ts';

interface Card extends CardRef {
  hash: string | undefined;
  front: string;
  back: string;
}

export class SkCards extends HTMLElement {
  private ready = false;
  private cards: Card[] = [];
  private mode: CardMode = 'due';
  private topic: string | null = null;
  private queue: Card[] = [];
  private index = 0;
  private turned = false;
  private repeats = new Set<string>();
  private knew = 0;
  private notYet = 0;
  private store!: ProgressStore;
  private unsubscribe: (() => void) | null = null;
  private list!: HTMLElement;
  private stage!: HTMLElement;
  private counts!: HTMLElement;
  private live!: HTMLElement;
  private browse!: HTMLButtonElement;
  private onKey = (e: KeyboardEvent) => this.key(e);

  connectedCallback(): void {
    document.addEventListener('keydown', this.onKey);
    if (!this.ready) {
      this.ready = true;
      this.store = storeOf(this);
      this.build();
    }
    this.unsubscribe = this.store.subscribe(() => this.showCounts());
  }

  disconnectedCallback(): void {
    document.removeEventListener('keydown', this.onKey);
    this.unsubscribe?.();
    this.unsubscribe = null;
  }

  private build(): void {
    const { ui } = langs(this);
    const chapters = [...this.querySelectorAll<HTMLElement>('.sk-cards-chapter')];
    this.cards = [...this.querySelectorAll<HTMLElement>('sk-card')].map((el) => ({
      id: el.dataset.id ?? '',
      topic: el.dataset.topic || null,
      hash: el.dataset.h,
      front: el.querySelector(':scope > .sk-card-front')?.innerHTML ?? '',
      back: el.querySelector(':scope > .sk-card-back')?.innerHTML ?? '',
    }));
    this.list = h('div', { class: 'sk-cards-list', hidden: true });
    this.list.append(...chapters);

    const wanted = new URLSearchParams(location.search).get('topic');
    const topics = chapters.map((c) => c.dataset.topic ?? '');
    this.topic = wanted && topics.includes(wanted) ? wanted : null;

    const bar = h('div', { class: 'sk-cards-bar', lang: ui });
    const modes = h('div', { class: 'sk-cards-modes', role: 'group', 'aria-label': 'Which cards' });
    for (const [mode, label] of [['due', 'Due today'], ['all', 'All cards']] as const) {
      const button = h('button', { type: 'button', class: 'sk-btn', 'data-mode': mode, 'aria-pressed': String(mode === this.mode) }, label);
      button.addEventListener('click', () => {
        this.mode = mode;
        for (const b of modes.querySelectorAll('button')) b.setAttribute('aria-pressed', String(b === button));
        this.startRound();
      });
      modes.append(button);
    }
    bar.append(modes);
    if (chapters.length > 1) {
      const select = h('select', { class: 'sk-cards-chapter-select', 'aria-label': 'Chapter' }, h('option', { value: '' }, 'All chapters'));
      for (const c of chapters) {
        select.append(h('option', { value: c.dataset.topic ?? '' }, c.dataset.title ?? c.dataset.topic ?? ''));
      }
      select.value = this.topic ?? '';
      select.addEventListener('change', () => {
        this.topic = select.value || null;
        this.startRound();
      });
      bar.append(select);
    }
    this.browse = h('button', { type: 'button', class: 'sk-btn sk-btn-quiet sk-cards-browse', 'aria-expanded': 'false' }, 'Show all as a list');
    this.browse.addEventListener('click', () => {
      this.list.hidden = !this.list.hidden;
      this.browse.setAttribute('aria-expanded', String(!this.list.hidden));
      this.browse.textContent = this.list.hidden ? 'Show all as a list' : 'Hide the list';
    });
    bar.append(this.browse);

    this.counts = h('p', { class: 'sk-cards-counts sk-muted', lang: ui });
    this.stage = h('div', { class: 'sk-cards-stage', tabindex: -1 });
    this.live = h('p', { class: 'sk-vh', 'aria-live': 'polite', lang: ui });
    this.replaceChildren(bar, this.counts, this.stage, this.live, this.list);
    this.startRound();
  }

  private ids(): string[] {
    return this.cards.filter((c) => !this.topic || c.topic === this.topic).map((c) => c.id);
  }

  private showCounts(): void {
    const c = cardCounts(this.ids(), this.store.read().items, today());
    this.counts.textContent = `${c.due} due · ${c.fresh} new · ${c.known} known · ${c.total} in all`;
  }

  private startRound(): void {
    const items = this.store.read().items;
    this.queue = cardQueue(this.cards, items, this.mode, this.topic, today(), randomSeed());
    this.index = 0;
    this.turned = false;
    this.repeats.clear();
    this.knew = 0;
    this.notYet = 0;
    this.showCounts();
    this.render();
  }

  private render(): void {
    const card = this.queue[this.index];
    if (!card) {
      this.renderDone();
      return;
    }
    const { ui, content } = langs(this);
    const left = this.queue.length - this.index;
    const head = h('p', { class: 'sk-card-progress sk-muted', lang: ui }, `Card ${this.index + 1} of ${this.queue.length}`);
    const front = h('div', { class: 'sk-card-face sk-card-face-front', lang: content });
    front.innerHTML = card.front;
    const panel = h('div', { class: 'sk-card-panel', 'data-card': card.id, 'data-turned': String(this.turned) }, head, front);
    if (this.turned) {
      const back = h('div', { class: 'sk-card-face sk-card-face-back', lang: content });
      back.innerHTML = card.back;
      const no = h('button', { type: 'button', class: 'sk-btn sk-card-rate', 'data-rate': 'no', lang: ui }, "Didn't know ", h('kbd', {}, '1'));
      const yes = h('button', { type: 'button', class: 'sk-btn sk-btn-primary sk-card-rate', 'data-rate': 'yes', lang: ui }, 'Knew it ', h('kbd', {}, '2'));
      no.addEventListener('click', () => this.rate(false));
      yes.addEventListener('click', () => this.rate(true));
      panel.append(back, h('div', { class: 'sk-card-actions' }, no, yes));
      announce(this.live, `Answer shown. ${left} card${left === 1 ? '' : 's'} left.`);
    } else {
      const turn = h('button', { type: 'button', class: 'sk-btn sk-btn-primary sk-card-turn', lang: ui }, 'Show answer ', h('kbd', {}, 'Space'));
      turn.addEventListener('click', () => this.turn());
      panel.append(h('div', { class: 'sk-card-actions' }, turn));
    }
    this.stage.replaceChildren(panel);
  }

  private renderDone(): void {
    const { ui } = langs(this);
    const items = this.store.read().items;
    const rated = this.knew + this.notYet;
    const next = nextReview(this.ids(), items, today());
    const again = h('button', { type: 'button', class: 'sk-btn' }, 'Go through all cards');
    again.addEventListener('click', () => {
      this.mode = 'all';
      for (const b of this.querySelectorAll<HTMLButtonElement>('.sk-cards-modes button')) {
        b.setAttribute('aria-pressed', String(b.dataset.mode === 'all'));
      }
      this.startRound();
    });
    const panel = h(
      'div',
      { class: 'sk-card-panel sk-card-done', lang: ui },
      h('h2', {}, rated ? 'Round done' : 'Nothing due today'),
      rated ? h('p', {}, `${this.knew} known, ${this.notYet} to practise again.`) : null,
      next ? h('p', { class: 'sk-muted' }, `Next review ${relativeDay(next)}.`) : null,
      h('div', { class: 'sk-card-actions' }, again),
    );
    this.stage.replaceChildren(panel);
    announce(this.live, rated ? 'Round done.' : 'Nothing due today.');
    emit(this, 'sk:cards-done', { knew: this.knew, notYet: this.notYet });
  }

  private turn(): void {
    if (this.turned || !this.queue[this.index]) return;
    this.turned = true;
    this.render();
    this.stage.focus({ preventScroll: true });
  }

  private rate(knew: boolean): void {
    const card = this.queue[this.index];
    if (!card || !this.turned) return;
    // a repeat in the same round only ends when it is known; the first answer was the rating
    if (!this.repeats.has(card.id)) {
      this.store.recordCard(card.id, card.hash, knew);
      if (knew) this.knew++;
      else this.notYet++;
    }
    if (!knew) {
      this.repeats.add(card.id);
      this.queue.push(card);
    }
    emit(this, 'sk:card', { id: card.id, knew });
    this.index++;
    this.turned = false;
    this.showCounts();
    this.render();
    this.stage.focus({ preventScroll: true });
  }

  private key(e: KeyboardEvent): void {
    if (isTyping(e) || !this.queue[this.index]) return;
    const onControl = (e.target as HTMLElement | null)?.closest?.('button, a, summary');
    if (e.key === ' ' || e.key === 'Enter') {
      if (onControl || this.turned) return; // a focused control does its own thing
      e.preventDefault();
      this.turn();
    } else if (this.turned && (e.key === '1' || e.key === '2')) {
      e.preventDefault();
      this.rate(e.key === '2');
    }
  }
}
