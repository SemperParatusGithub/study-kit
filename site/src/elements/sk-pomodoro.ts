// <sk-pomodoro>: a pomodoro timer in the header (docs/architecture.md §3.2).
//
// A button at the right of the bar opens a panel with the controls (start, pause, skip,
// reset) and the settings (focus, short and long break in minutes, a long break after n
// focus phases, auto-start, sound, desktop notification). Once a cycle is under way the
// button shows the phase and the time left, on every page: the state lives in
// localStorage (studykit:pomodoro, lib/pomodoro.ts) with the time the phase ends, so it
// runs on across page loads, and other tabs follow through the storage event. While it
// runs, the page title starts with the time left. At the end of a phase it beeps and, when
// allowed, shows a notification.

import {
  advance,
  configure,
  isActive,
  isRunning,
  LIMITS,
  pause,
  parse,
  PHASE_LABELS,
  remaining,
  reset,
  serialize,
  skip,
  start,
  type Phase,
  type Pomodoro,
  type Settings,
} from '../lib/pomodoro.ts';
import { getPomodoro, POMODORO_KEY, setPomodoro } from '../lib/store.ts';
import { clock, emit, h, uid } from './util.ts';

const ICON =
  '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="13.5" r="7.5"/><path d="M12 9.5v4l2.5 1.8M10 3h4M12 3v2.5"/></svg>';

const SHORT: Record<Phase, string> = { focus: 'Focus', short: 'Break', long: 'Break' };

const NUMBERS = [
  ['focus', 'Focus', 'min'],
  ['short', 'Short break', 'min'],
  ['long', 'Long break', 'min'],
  ['longEvery', 'Long break after', 'focus phases'],
] as const;

const FLAGS = [
  ['autoStart', 'Start the next phase by itself'],
  ['sound', 'Sound at the end of a phase'],
  ['notify', 'Desktop notification'],
] as const;

export class SkPomodoro extends HTMLElement {
  private ready = false;
  private state: Pomodoro = parse(null);
  private timer: number | undefined;
  private baseTitle = '';
  private toggle!: HTMLButtonElement;
  private chip!: HTMLSpanElement;
  private panel!: HTMLDivElement;
  private phaseOut!: HTMLElement;
  private timeOut!: HTMLElement;
  private doneOut!: HTMLElement;
  private runBtn!: HTMLButtonElement;
  private skipBtn!: HTMLButtonElement;
  private resetBtn!: HTMLButtonElement;
  private numbers = new Map<keyof Settings, HTMLInputElement>();
  private flags = new Map<keyof Settings, HTMLInputElement>();
  private notifyNote!: HTMLElement;

  private onStorage = (e: StorageEvent) => {
    if (e.key === POMODORO_KEY || e.key === null) this.load();
  };
  private onDocClick = (e: MouseEvent) => {
    if (!this.panel.hidden && !e.composedPath().includes(this)) this.close(false);
  };
  private onKey = (e: KeyboardEvent) => {
    if (e.key === 'Escape' && !this.panel.hidden) {
      e.preventDefault();
      this.close(true);
    }
  };

  connectedCallback(): void {
    window.addEventListener('storage', this.onStorage);
    document.addEventListener('click', this.onDocClick);
    this.addEventListener('keydown', this.onKey);
    if (!this.ready) {
      this.ready = true;
      this.baseTitle = document.title;
      this.build();
    }
    this.load();
  }

  disconnectedCallback(): void {
    window.removeEventListener('storage', this.onStorage);
    document.removeEventListener('click', this.onDocClick);
    this.removeEventListener('keydown', this.onKey);
    window.clearInterval(this.timer);
    this.timer = undefined;
  }

  // --- markup ---------------------------------------------------------------------------

  private build(): void {
    const panelId = uid('pomodoro');
    this.chip = h('span', { class: 'sk-pomo-chip' });
    const icon = h('span', { class: 'sk-pomo-icon' });
    icon.innerHTML = ICON;
    this.toggle = h(
      'button',
      { type: 'button', class: 'sk-pomo-toggle', 'aria-expanded': 'false', 'aria-controls': panelId },
      icon,
      this.chip,
    );
    this.toggle.addEventListener('click', () => (this.panel.hidden ? this.open() : this.close(true)));

    this.phaseOut = h('span', { class: 'sk-pomo-phase' });
    this.timeOut = h('span', { class: 'sk-pomo-time sk-num' });
    this.doneOut = h('span', { class: 'sk-pomo-done sk-muted' });
    this.runBtn = h('button', { type: 'button', class: 'sk-btn sk-btn-primary' });
    this.runBtn.addEventListener('click', () => {
      const now = Date.now();
      this.save(isRunning(this.state) ? pause(this.state, now) : start(this.state, now));
      if (isRunning(this.state)) this.prepareSound();
    });
    this.skipBtn = h('button', { type: 'button', class: 'sk-btn' }, 'Skip');
    this.skipBtn.addEventListener('click', () => this.save(skip(this.state, Date.now())));
    this.resetBtn = h('button', { type: 'button', class: 'sk-btn sk-btn-quiet' }, 'Reset');
    this.resetBtn.addEventListener('click', () => this.save(reset(this.state)));

    const settings = h('fieldset', { class: 'sk-pomo-settings' }, h('legend', {}, 'Settings'));
    for (const [key, label, unit] of NUMBERS) {
      const id = uid('pomo');
      const [min, max] = LIMITS[key];
      const input = h('input', { id, type: 'number', min, max, step: 1, inputmode: 'numeric', class: 'sk-pomo-num' });
      input.addEventListener('change', () => this.changeSettings());
      settings.append(
        h('div', { class: 'sk-pomo-row' }, h('label', { for: id }, label), h('span', { class: 'sk-pomo-field' }, input, h('span', { class: 'sk-muted' }, unit))),
      );
      this.numbers.set(key, input);
    }
    for (const [key, label] of FLAGS) {
      const input = h('input', { type: 'checkbox' });
      input.addEventListener('change', () => void this.changeFlag(key, input));
      settings.append(h('label', { class: 'sk-pomo-check' }, input, label));
      this.flags.set(key, input);
    }
    this.notifyNote = h('p', { class: 'sk-pomo-note sk-muted', hidden: true });
    settings.append(this.notifyNote);

    this.panel = h(
      'div',
      { id: panelId, class: 'sk-pomo-panel', role: 'group', 'aria-label': 'Pomodoro timer', hidden: true },
      h('div', { class: 'sk-pomo-head' }, this.phaseOut, this.timeOut, this.doneOut),
      h('div', { class: 'sk-pomo-actions' }, this.runBtn, this.skipBtn, this.resetBtn),
      settings,
    );
    this.replaceChildren(this.toggle, this.panel);
  }

  private open(): void {
    this.panel.hidden = false;
    this.toggle.setAttribute('aria-expanded', 'true');
    this.runBtn.focus();
  }

  private close(focusToggle: boolean): void {
    this.panel.hidden = true;
    this.toggle.setAttribute('aria-expanded', 'false');
    if (focusToggle) this.toggle.focus();
  }

  // --- state ----------------------------------------------------------------------------

  private load(): void {
    this.state = parse(getPomodoro());
    this.tick(false);
  }

  private save(state: Pomodoro): void {
    this.state = state;
    setPomodoro(serialize(state));
    emit(this, 'sk:pomodoro', { state });
    this.render();
    this.schedule();
  }

  /** Finish phases that have ended; `alert` plays the sound and notifies for them. */
  private tick(alert = true): void {
    const { state, finished } = advance(this.state, Date.now());
    if (finished.length) {
      this.save(state);
      if (alert) this.alert(finished[finished.length - 1] as Phase);
      return;
    }
    this.render();
    this.schedule();
  }

  private schedule(): void {
    if (isRunning(this.state)) {
      this.timer ??= window.setInterval(() => this.tick(), 1000);
    } else if (this.timer !== undefined) {
      window.clearInterval(this.timer);
      this.timer = undefined;
    }
  }

  private render(): void {
    const s = this.state;
    const running = isRunning(s);
    const active = isActive(s);
    const left = clock(remaining(s, Date.now()));
    const phase = s.timer.phase;
    this.dataset.phase = phase;
    this.toggleAttribute('data-running', running);
    this.toggleAttribute('data-active', active);
    this.chip.replaceChildren();
    if (active) {
      this.chip.append(h('span', { class: 'sk-pomo-chip-phase' }, SHORT[phase]), h('span', { class: 'sk-num' }, left));
    }
    const state = running ? 'running' : active ? 'paused' : 'ready';
    this.toggle.setAttribute('aria-label', `Pomodoro timer: ${PHASE_LABELS[phase]}, ${left} left, ${state}`);
    this.toggle.title = active ? `${PHASE_LABELS[phase]} · ${left}` : 'Pomodoro timer';
    this.phaseOut.textContent = PHASE_LABELS[phase];
    this.timeOut.textContent = left;
    this.doneOut.textContent = `${s.timer.done} focus ${s.timer.done === 1 ? 'phase' : 'phases'} done`;
    this.runBtn.textContent = running ? 'Pause' : active && s.timer.left < s.settings[phase] * 60_000 ? 'Resume' : 'Start';
    this.resetBtn.disabled = !active;
    for (const [key, input] of this.numbers) {
      if (document.activeElement !== input) input.value = String(s.settings[key]);
    }
    for (const [key, input] of this.flags) input.checked = Boolean(s.settings[key]);
    document.title = running ? `${left} ${SHORT[phase]} · ${this.baseTitle}` : this.baseTitle;
  }

  // --- settings ---------------------------------------------------------------------------

  private changeSettings(): void {
    const next = { ...this.state.settings };
    for (const [key, input] of this.numbers) {
      const [min, max] = LIMITS[key as keyof typeof LIMITS];
      const v = Math.round(Number(input.value));
      (next as Record<string, number | boolean>)[key] = Number.isFinite(v) ? Math.min(max, Math.max(min, v)) : next[key];
    }
    this.save(configure(this.state, next));
  }

  private async changeFlag(key: keyof Settings, input: HTMLInputElement): Promise<void> {
    let on = input.checked;
    this.notifyNote.hidden = true;
    if (key === 'notify' && on) on = await this.askNotify();
    if (key === 'sound' && on) this.prepareSound();
    this.save(configure(this.state, { ...this.state.settings, [key]: on }));
  }

  private async askNotify(): Promise<boolean> {
    if (typeof Notification === 'undefined') return this.note('This browser has no notifications.');
    if (Notification.permission === 'granted') return true;
    if (Notification.permission === 'denied') return this.note('Notifications are blocked for this site.');
    const answer = await Notification.requestPermission();
    return answer === 'granted' || this.note('Notifications were not allowed.');
  }

  private note(text: string): false {
    this.notifyNote.textContent = text;
    this.notifyNote.hidden = false;
    return false;
  }

  // --- end of a phase ---------------------------------------------------------------------

  private audio: AudioContext | null = null;

  /** Create the audio context in a click, so the browser lets it play later. */
  private prepareSound(): void {
    if (!this.state.settings.sound || this.audio || typeof AudioContext === 'undefined') return;
    try {
      this.audio = new AudioContext();
    } catch {
      this.audio = null;
    }
  }

  private alert(ended: Phase): void {
    const next = this.state.timer.phase;
    const text = `${PHASE_LABELS[ended]} is over. ${PHASE_LABELS[next]}: ${this.state.settings[next]} min.`;
    if (this.state.settings.sound) this.beep();
    if (this.state.settings.notify && typeof Notification !== 'undefined' && Notification.permission === 'granted') {
      try {
        new Notification('study-kit pomodoro', { body: text, tag: 'studykit-pomodoro' });
      } catch {
        // some browsers only notify from a service worker
      }
    }
    emit(this, 'sk:pomodoro-end', { ended, next });
  }

  private beep(): void {
    // after a page load without a click the context may stay suspended: then it is silent
    this.prepareSound();
    const ctx = this.audio;
    if (!ctx) return;
    void ctx.resume?.();
    const t0 = ctx.currentTime;
    for (const [i, freq] of [880, 660, 880].entries()) {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.frequency.value = freq;
      const t = t0 + i * 0.25;
      gain.gain.setValueAtTime(0.0001, t);
      gain.gain.exponentialRampToValueAtTime(0.2, t + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.2);
      osc.connect(gain).connect(ctx.destination);
      osc.start(t);
      osc.stop(t + 0.22);
    }
  }
}
