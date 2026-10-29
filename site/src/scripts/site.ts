// Small progressive enhancements of the shell. Nothing here reads or writes progress
// (that is lib/store.ts, used by the custom elements); every page works without it.

const DAY_MS = 86_400_000;

function todayIso(): string {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}

function daysUntil(iso: string): number {
  const a = Date.parse(`${todayIso()}T00:00:00Z`);
  const b = Date.parse(`${iso.slice(0, 10)}T00:00:00Z`);
  return Math.round((b - a) / DAY_MS);
}

/** "/" focuses the header search box (unless the user is typing somewhere). */
function searchShortcut(): void {
  const input = document.querySelector<HTMLInputElement>('[data-search-shortcut]');
  if (!input) return;
  document.addEventListener('keydown', (event) => {
    if (event.key !== '/' || event.metaKey || event.ctrlKey || event.altKey) return;
    const target = event.target as HTMLElement | null;
    if (target?.closest('input, textarea, select, [contenteditable=""], [contenteditable="true"]')) return;
    event.preventDefault();
    input.focus();
  });
}

/** <time data-countdown datetime="YYYY-MM-DD"> gets "in N days" relative to today. */
function countdowns(): void {
  for (const el of document.querySelectorAll<HTMLElement>('[data-countdown]')) {
    const iso = el.getAttribute('datetime') ?? el.dataset.countdown ?? '';
    if (!/^\d{4}-\d{2}-\d{2}/.test(iso)) continue;
    const n = daysUntil(iso);
    const text =
      n > 1 ? `in ${n} days` : n === 1 ? 'tomorrow' : n === 0 ? 'today' : n === -1 ? 'yesterday' : `${-n} days ago`;
    const out = el.querySelector<HTMLElement>('[data-countdown-text]') ?? el;
    out.textContent = text;
    el.dataset.days = String(n);
  }
}

/**
 * Upcoming sessions are rendered at build time as hidden cards; show the first one that is
 * today or later, and the fallback when none is left.
 */
function nextSessions(): void {
  const today = todayIso();
  for (const box of document.querySelectorAll<HTMLElement>('[data-next-session]')) {
    const cards = [...box.querySelectorAll<HTMLElement>('[data-session-date]')];
    const next = cards.find((c) => (c.dataset.sessionDate ?? '') >= today);
    for (const c of cards) c.hidden = c !== next;
    const none = box.querySelector<HTMLElement>('[data-no-session]');
    if (none) none.hidden = Boolean(next);
  }
}

/** Client-side filters for lists: <form data-filter-form> over [data-filter-row] items. */
function filters(): void {
  for (const form of document.querySelectorAll<HTMLFormElement>('[data-filter-form]')) {
    const scope = form.closest('[data-filter-scope]') ?? document;
    const rows = [...scope.querySelectorAll<HTMLElement>('[data-filter-row]')];
    const groups = [...scope.querySelectorAll<HTMLElement>('[data-filter-group]')];
    const count = form.querySelector('output');
    const selects = [...form.querySelectorAll<HTMLSelectElement>('select[name]')];
    const params = new URLSearchParams(location.search);
    for (const s of selects) {
      const v = params.get(s.name);
      if (v && [...s.options].some((o) => o.value === v)) s.value = v;
    }
    const apply = () => {
      let shown = 0;
      for (const row of rows) {
        const ok = selects.every((s) => !s.value || (row.dataset[s.name] || 'new') === s.value);
        row.hidden = !ok;
        if (ok) shown++;
      }
      for (const g of groups) g.hidden = !g.querySelector('[data-filter-row]:not([hidden])');
      if (count) count.textContent = `${shown} of ${rows.length}`;
      const next = new URLSearchParams(location.search);
      for (const s of selects) (s.value ? next.set(s.name, s.value) : next.delete(s.name));
      const qs = next.toString();
      history.replaceState(null, '', qs ? `?${qs}` : location.pathname);
    };
    form.addEventListener('change', apply);
    form.addEventListener('submit', (e) => e.preventDefault());
    form.hidden = false;
    // progress data may arrive later (custom elements set data-status on the rows)
    new MutationObserver(apply).observe(scope, { subtree: true, attributeFilter: ['data-status'] });
    apply();
  }
}

/** Highlight the table-of-contents entry of the section being read. */
function tocSpy(): void {
  const links = [...document.querySelectorAll<HTMLAnchorElement>('.toc a[href^="#"]')];
  if (!links.length || !('IntersectionObserver' in window)) return;
  const byId = new Map(links.map((a) => [decodeURIComponent(a.hash.slice(1)), a]));
  const visible = new Set<string>();
  const observer = new IntersectionObserver(
    (entries) => {
      for (const e of entries) (e.isIntersecting ? visible.add(e.target.id) : visible.delete(e.target.id));
      const first = [...byId.keys()].find((id) => visible.has(id));
      if (!first) return;
      for (const [id, a] of byId) {
        if (id === first) a.setAttribute('aria-current', 'location');
        else a.removeAttribute('aria-current');
      }
    },
    { rootMargin: '0px 0px -60% 0px' },
  );
  for (const id of byId.keys()) {
    const target = document.getElementById(id);
    if (target) observer.observe(target);
  }
}

/** Print with every <details> open (hints, solutions), then restore. */
function printDetails(): void {
  let opened: HTMLDetailsElement[] = [];
  addEventListener('beforeprint', () => {
    opened = [...document.querySelectorAll<HTMLDetailsElement>('details:not([open])')];
    for (const d of opened) d.open = true;
  });
  addEventListener('afterprint', () => {
    for (const d of opened) d.open = false;
    opened = [];
  });
}

searchShortcut();
countdowns();
nextSessions();
filters();
tocSpy();
printDetails();
