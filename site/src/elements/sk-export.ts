// <sk-export data-course>: export and import of the progress document
// (docs/architecture.md §2.11).
//
// Export downloads studykit-progress-<course>-<date>.json; import reads such a file and
// merges it into the stored progress as a union (store.ts). Also reports whether the
// browser keeps the storage (navigator.storage.persist()).

import { requestPersist } from '../lib/store.ts';
import { courseOf, h, storeFor } from './util.ts';

export class SkExport extends HTMLElement {
  private ready = false;

  private get course(): string {
    return this.dataset.course || courseOf(this);
  }

  connectedCallback(): void {
    if (this.ready) return;
    this.ready = true;
    const store = storeFor(this.course);
    const status = h('p', { class: 'sk-export-status', role: 'status' });
    const note = h('p', { class: 'sk-export-note' },
      'Progress is stored in this browser only. Export it to keep a copy or to move it to another browser.');
    const exportBtn = h('button', { type: 'button', class: 'sk-btn sk-btn-primary' }, 'Export progress');
    const importBtn = h('button', { type: 'button', class: 'sk-btn' }, 'Import progress…');
    const file = h('input', { type: 'file', accept: '.json,application/json', hidden: true, 'aria-hidden': 'true', tabindex: '-1' });

    exportBtn.addEventListener('click', () => {
      const { filename, text } = store.exportFile();
      const url = URL.createObjectURL(new Blob([text], { type: 'application/json' }));
      const a = h('a', { href: url, download: filename, hidden: true });
      document.body.append(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 10_000);
      status.className = 'sk-export-status is-ok';
      status.textContent = `Saved ${filename}.`;
    });
    importBtn.addEventListener('click', () => file.click());
    file.addEventListener('change', async () => {
      const f = file.files?.[0];
      if (!f) return;
      let text = '';
      try {
        text = await f.text();
      } catch {
        text = '';
      }
      const r = store.importText(text);
      status.className = `sk-export-status ${r.ok ? 'is-ok' : 'is-bad'}`;
      status.textContent = r.message;
      file.value = '';
    });

    this.replaceChildren(
      h('div', { class: 'sk-export' },
        h('div', { class: 'sk-export-actions' }, exportBtn, importBtn, file),
        status,
        note),
    );
    if (!store.persistent) {
      note.textContent = store.readable
        ? 'The browser’s storage for this site is full, so new progress is kept only while this page is open. Export it before you close the page.'
        : 'This browser does not let the site store progress. Export it before you close the page.';
      return;
    }
    void requestPersist().then((granted) => {
      if (granted === true) note.append(' The browser keeps this storage.');
      else if (granted === false) note.append(' The browser may clear it when space runs low, so export now and then.');
    });
  }
}
