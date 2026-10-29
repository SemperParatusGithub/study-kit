// Build-time math (docs/architecture.md §3.1, §3.2): every <sk-math data-tex="<base64>"
// data-display="0|1"></sk-math> from math.lua becomes KaTeX HTML, with the same options
// as scripts/check-math.mjs (strict, no trust), so what lint accepts renders here.
import katex from 'katex';
import { escapeHtml } from './html';

export const KATEX_OPTIONS = {
  throwOnError: true,
  strict: 'error',
  trust: false,
} as const;

const SK_MATH = /<sk-math data-tex="([A-Za-z0-9+/=]*)" data-display="([01])"><\/sk-math>/g;

/** UTF-8 text from base64 (the encoding math.lua uses for data-tex). */
export function decodeBase64(b64: string): string {
  const bin = atob(b64);
  const bytes = Uint8Array.from(bin, (c) => c.charCodeAt(0));
  return new TextDecoder().decode(bytes);
}

export function renderTex(tex: string, display: boolean): string {
  return katex.renderToString(tex, { ...KATEX_OPTIONS, displayMode: display });
}

export interface MathError {
  tex: string;
  display: boolean;
  message: string;
}

/**
 * Replace every <sk-math> in `html` with KaTeX output. A formula KaTeX rejects becomes a
 * marked <code> element and is passed to `onError`.
 */
export function renderMath(html: string, onError: (err: MathError) => void): string {
  return html.replace(SK_MATH, (_m, b64: string, flag: string) => {
    const tex = decodeBase64(b64);
    const display = flag === '1';
    try {
      return renderTex(tex, display);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      onError({ tex, display, message });
      return `<code class="sk-math-error" title="${escapeHtml(message)}">${escapeHtml(tex)}</code>`;
    }
  });
}

/**
 * A label (plain text with inline $…$ math, docs/architecture.md §2.5) as HTML: the text
 * is escaped and each formula goes through KaTeX. `\$` is a literal dollar.
 */
export function renderLabel(text: string, onError?: (err: MathError) => void): string {
  let out = '';
  let i = 0;
  while (i < text.length) {
    const start = findDollar(text, i);
    if (start < 0) break;
    const end = findDollar(text, start + 1);
    if (end < 0) break;
    out += escapeHtml(unescapeDollars(text.slice(i, start)));
    const tex = text.slice(start + 1, end);
    try {
      out += renderTex(tex, false);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      onError?.({ tex, display: false, message });
      out += `<code class="sk-math-error">${escapeHtml(tex)}</code>`;
    }
    i = end + 1;
  }
  return out + escapeHtml(unescapeDollars(text.slice(i)));
}

function findDollar(text: string, from: number): number {
  for (let k = from; k < text.length; k++) {
    if (text[k] === '\\') k++;
    else if (text[k] === '$') return k;
  }
  return -1;
}

function unescapeDollars(text: string): string {
  return text.replace(/\\\$/g, '$');
}
