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
  return `${Math.round(x * 100)} %`;
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

type Katex = typeof import('katex').default;
let katexLoad: Promise<Katex | null> | null = null;

function loadKatex(): Promise<Katex | null> {
  katexLoad ??= import('katex').then(
    (m) => (m as unknown as { default: Katex }).default ?? (m as unknown as Katex),
    () => null,
  );
  return katexLoad;
}

/**
 * Answer labels and rubric criteria are plain text plus inline $…$ math (§2.5). Text goes in
 * as text nodes; math is shown as its TeX at once and replaced by KaTeX when it has loaded.
 */
export function renderInline(target: HTMLElement, text: string): void {
  target.replaceChildren();
  const parts = text.split(/\$([^$]+)\$/g);
  const math: Array<[HTMLElement, string]> = [];
  parts.forEach((part, i) => {
    if (i % 2 === 0) {
      if (part) target.append(part);
      return;
    }
    const span = h('span', { class: 'sk-inline-math' }, part);
    math.push([span, part]);
    target.append(span);
  });
  if (math.length === 0) return;
  void loadKatex().then((katex) => {
    if (!katex) return;
    for (const [span, tex] of math) {
      try {
        span.innerHTML = katex.renderToString(tex, { throwOnError: false, displayMode: false });
      } catch {
        /* keep the TeX source */
      }
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
