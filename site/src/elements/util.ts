// Small helpers shared by the custom elements (docs/architecture.md §3.2).

import { isDay, dayOf, daysBetween } from '../lib/leitner.ts';
import { storeFor, UNKNOWN_HASH, type ProgressStore } from '../lib/store.ts';

export { storeFor };

type Child = Node | string | null | undefined | false;
type AttrValue = string | number | boolean | null | undefined;

/** Create an element: attributes (false/null/undefined are skipped) and children. */
export function h<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  attrs: Record<string, AttrValue> = {},
  ...children: Child[]
): HTMLElementTagNameMap[K] {
  const el = document.createElement(tag);
  for (const [name, value] of Object.entries(attrs)) {
    if (value === false || value === null || value === undefined) continue;
    if (name === 'class') el.className = String(value);
    else el.setAttribute(name, value === true ? '' : String(value));
  }
  for (const child of children) {
    if (child === null || child === undefined || child === false) continue;
    el.append(child);
  }
  return el;
}

let counter = 0;
export function uid(prefix = 'sk'): string {
  counter += 1;
  return `${prefix}-${counter.toString(36)}`;
}

/** The course an element belongs to: the nearest data-course, else <body data-course>. */
export function courseOf(el: Element): string {
  const own = el.closest('[data-course]')?.getAttribute('data-course');
  return own || document.body?.dataset.course || 'default';
}

export function storeOf(el: Element): ProgressStore {
  return storeFor(courseOf(el));
}

const ENGLISH = /^en(?:-|$)/i;

/** The language `el` is in: its nearest lang attribute, else the page's. */
export function langOf(el: Element): string {
  return el.closest('[lang]')?.getAttribute('lang') || document.documentElement.lang || '';
}

/**
 * Languages for what an element generates (§3.2: the UI is English, content follows the
 * course), as values for h() attributes, where undefined adds nothing:
 *   ui       "en" when the element sits in another language, for its English UI text;
 *   content  that language, for course text placed inside the UI (titles, labels).
 * `lang` overrides the language of the content (a quiz in an English box shows course
 * questions).
 */
export function langs(el: Element, lang?: string): { ui: string | undefined; content: string | undefined } {
  const here = langOf(el);
  const course = lang || here;
  return {
    ui: here && !ENGLISH.test(here) ? 'en' : undefined,
    content: course && !ENGLISH.test(course) ? course : undefined,
  };
}

/** <body data-exam-date="YYYY-MM-DD"> or null when empty or invalid. */
export function examDate(): string | null {
  const v = document.body?.dataset.examDate ?? '';
  return isDay(v) ? v : null;
}

export function today(): string {
  return dayOf();
}

/** The build-time content hash of an item: data-h on the element or an ancestor. */
export function hashOf(el: Element): string | undefined {
  const v = el.closest('[data-h]')?.getAttribute('data-h');
  return v || undefined;
}

/** True when both hashes are known and differ: "content changed since your attempt". */
export function contentChanged(stored: string | undefined, current: string | undefined): boolean {
  return Boolean(stored && current && stored !== UNKNOWN_HASH && stored !== current);
}

export function parseJson<T>(text: string | null | undefined, fallback: T): T {
  if (!text) return fallback;
  try {
    return JSON.parse(text) as T;
  } catch {
    return fallback;
  }
}

/** "4:05", "1:02:03" for a duration in milliseconds. */
export function clock(ms: number): string {
  const total = Math.max(0, Math.round(ms / 1000));
  const s = total % 60;
  const m = Math.floor(total / 60) % 60;
  const hrs = Math.floor(total / 3600);
  const mm = hrs > 0 ? String(m).padStart(2, '0') : String(m);
  return `${hrs > 0 ? `${hrs}:` : ''}${mm}:${String(s).padStart(2, '0')}`;
}

/** "12 min", "1 h 5 min", "45 s". */
export function duration(ms: number): string {
  const s = Math.round(ms / 1000);
  if (s < 60) return `${s} s`;
  const min = Math.round(s / 60);
  if (min < 60) return `${min} min`;
  return `${Math.floor(min / 60)} h ${min % 60} min`;
}

/** "today", "tomorrow", "in 3 days", "yesterday", "3 days ago". */
export function relativeDay(day: string, from: string = today()): string {
  const d = daysBetween(from, day);
  if (d === 0) return 'today';
  if (d === 1) return 'tomorrow';
  if (d === -1) return 'yesterday';
  return d > 0 ? `in ${d} days` : `${-d} days ago`;
}

export function percent(x: number): string {
  return `${Math.round(x * 100)}%`;
}

/** Format points: 12, 7.5, 0.33. */
export function pts(x: number): string {
  return String(Math.round(x * 100) / 100);
}

/** Put text into a live region so screen readers announce it even when it repeats. */
export function announce(region: HTMLElement, text: string): void {
  region.textContent = '';
  requestAnimationFrame(() => {
    region.textContent = text;
  });
}

export function emit<T>(el: Element, type: string, detail: T, cancelable = false): boolean {
  return el.dispatchEvent(new CustomEvent(type, { detail, bubbles: true, composed: true, cancelable }));
}

/** Keyboard shortcuts must not fire while the user types or holds a modifier. */
export function isTyping(e: KeyboardEvent): boolean {
  if (e.altKey || e.ctrlKey || e.metaKey) return true;
  const t = e.target as HTMLElement | null;
  if (!t) return false;
  if (t.isContentEditable) return true;
  if (t instanceof HTMLTextAreaElement || t instanceof HTMLSelectElement) return true;
  return t instanceof HTMLInputElement && !['radio', 'checkbox', 'button', 'submit'].includes(t.type);
}

/**
 * Answer labels and rubric criteria are plain text plus inline $…$ math (§2.5). The shell
 * renders them at build time (label_html, criterion_html: escaped text and KaTeX output);
 * that HTML is used when present. Without it the text goes in as text, each formula as its
 * TeX source, so no KaTeX is loaded in the browser.
 */
export function renderInline(target: HTMLElement, text: string, html?: string | null): void {
  if (typeof html === 'string' && html) {
    target.innerHTML = html;
    return;
  }
  target.replaceChildren();
  text.split(/\$([^$]+)\$/g).forEach((part, i) => {
    if (i % 2 === 0) {
      if (part) target.append(part);
    } else {
      target.append(h('span', { class: 'sk-inline-math' }, part));
    }
  });
}

let printing = false;
if (typeof window !== 'undefined') {
  window.addEventListener('beforeprint', () => (printing = true));
  window.addEventListener('afterprint', () => (printing = false));
}

/** True between beforeprint and afterprint (print.css opens every <details>). */
export function isPrinting(): boolean {
  return printing || (typeof matchMedia === 'function' && matchMedia('print').matches);
}

/** Define a custom element once (index.ts may be imported by several layouts). */
export function define(name: string, ctor: CustomElementConstructor): void {
  if (typeof customElements !== 'undefined' && !customElements.get(name)) {
    customElements.define(name, ctor);
  }
}

/** Plain-text excerpt of an element (for result lists). */
export function excerpt(el: Element | null, max = 110): string {
  if (!el) return '';
  const copy = el.cloneNode(true) as Element;
  for (const hidden of copy.querySelectorAll('.katex-mathml, [hidden]')) hidden.remove();
  const text = (copy.textContent ?? '').replace(/\s+/g, ' ').trim();
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}
