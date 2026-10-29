// <sk-theme>: light / dark / system (docs/architecture.md §3.2).
//
// One rule everywhere: the choice is stored under studykit:theme (through store.ts) as
// light, dark or system and mirrored to <html data-theme>. tokens.css styles only
// [data-theme=light] and [data-theme=dark]; 'system' keeps color-scheme: light dark, so
// the page follows prefers-color-scheme. The shell's inline head script applies the stored
// value (and the color-scheme meta tag) before first paint; applyTheme does the same here.

import { getTheme, setTheme, THEME_KEY, type Theme } from '../lib/store.ts';
import { emit, h, uid } from './util.ts';

const ICONS: Record<Theme, string> = {
  light:
    '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4.5"/><path d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M4.9 19.1l1.8-1.8M17.3 6.7l1.8-1.8"/></svg>',
  dark:
    '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5z"/></svg>',
  system:
    '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/></svg>',
};

const LABELS: Record<Theme, string> = { light: 'Light', dark: 'Dark', system: 'System' };

export function applyTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme;
  document
    .querySelector('meta[name="color-scheme"]')
    ?.setAttribute('content', theme === 'system' ? 'light dark' : theme);
}

export class SkTheme extends HTMLElement {
  private ready = false;
  private inputs: HTMLInputElement[] = [];
  private onStorage = (e: StorageEvent) => {
    if (e.key === THEME_KEY || e.key === null) this.sync();
  };

  connectedCallback(): void {
    window.addEventListener('storage', this.onStorage);
    if (this.ready) return;
    this.ready = true;
    const name = uid('theme');
    const fs = h('fieldset', { class: 'sk-theme' }, h('legend', { class: 'sk-vh' }, 'Colour theme'));
    for (const theme of ['light', 'dark', 'system'] as const) {
      const input = h('input', { type: 'radio', name, value: theme, class: 'sk-theme-input' });
      input.addEventListener('change', () => {
        if (!input.checked) return;
        setTheme(theme);
        applyTheme(theme);
        emit(this, 'sk:theme', { theme });
      });
      const icon = h('span', { class: 'sk-theme-icon' });
      icon.innerHTML = ICONS[theme];
      fs.append(h('label', { class: 'sk-theme-opt', title: LABELS[theme] }, input, icon, h('span', { class: 'sk-vh' }, LABELS[theme])));
      this.inputs.push(input);
    }
    this.replaceChildren(fs);
    this.sync();
  }

  disconnectedCallback(): void {
    window.removeEventListener('storage', this.onStorage);
  }

  private sync(): void {
    const theme = getTheme();
    for (const i of this.inputs) i.checked = i.value === theme;
    applyTheme(theme);
  }
}
