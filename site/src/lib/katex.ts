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

// Punctuation written right against inline math: opening marks before it, closing marks
// after it. Each KaTeX `.base` is an inline-block, and Chromium allows a line break next to
// one, so without help "U = 10 V" can end a line and the next one start with ".".
const LEAD = '(\\[{„‚«‹“‘';
const TRAIL = '.,;:!?…)\\]}»›“”‘’/%‰°\\-–—';
const SK_MATH = new RegExp(
  `([${LEAD}]*)<sk-math data-tex="([A-Za-z0-9+/=]*)" data-display="([01])"></sk-math>([${TRAIL}]*)`,
  'g',
);

/** UTF-8 text from base64 (the encoding math.lua uses for data-tex). */
export function decodeBase64(b64: string): string {
  const bin = atob(b64);
  const bytes = Uint8Array.from(bin, (c) => c.charCodeAt(0));
  return new TextDecoder().decode(bytes);
}

function encodeBase64(text: string): string {
  return btoa(String.fromCharCode(...new TextEncoder().encode(text)));
}

export function renderTex(tex: string, display: boolean): string {
  return katex.renderToString(tex, { ...KATEX_OPTIONS, displayMode: display });
}

export interface MathError {
  tex: string;
  display: boolean;
  message: string;
}

const HTML_OPEN = '<span class="katex-html" aria-hidden="true">';
const KATEX_CLOSE = '</span></span>';
const SPAN_TAG = /<(\/?)span\b[^>]*>/g;

/** The top-level `.base` spans of inline KaTeX output, or null for any other shape. */
function splitBases(html: string): { mathml: string; bases: string[] } | null {
  const at = html.indexOf(HTML_OPEN);
  if (!html.startsWith('<span class="katex">') || at < 0 || !html.endsWith(KATEX_CLOSE)) return null;
  const mathml = html.slice('<span class="katex">'.length, at);
  const inner = html.slice(at + HTML_OPEN.length, html.length - KATEX_CLOSE.length);
  const bases: string[] = [];
  let depth = 0;
  let start = 0;
  for (const m of inner.matchAll(SPAN_TAG)) {
    if (m[1]) {
      depth--;
      if (depth === 0) {
        bases.push(inner.slice(start, m.index + m[0].length));
        start = m.index + m[0].length;
      }
    } else {
      if (depth === 0 && m.index !== start) return null;
      depth++;
    }
  }
  if (depth !== 0 || start !== inner.length) return null;
  return bases.every((b) => b.startsWith('<span class="base">')) ? { mathml, bases } : null;
}

/**
 * Keep punctuation on the line of the formula it touches: the opening marks go into a
 * no-wrap group with the first `.base`, the closing ones with the last. The bases in between
 * keep KaTeX's own break points, so a long formula still wraps after = or +. Pieces are
 * separate `.katex` spans (KaTeX's CSS needs that ancestor); the MathML for assistive
 * technology stays whole in the first one.
 */
function glue(html: string, lead: string, trail: string): string {
  if (!lead && !trail) return html;
  const split = splitBases(html);
  if (!split || split.bases.length < 2) return `<span class="sk-nobr">${lead}${html}${trail}</span>`;
  const { mathml, bases } = split;
  const piece = (inner: string[], withMathml: boolean) =>
    `<span class="katex">${withMathml ? mathml : ''}${HTML_OPEN}${inner.join('')}${KATEX_CLOSE}`;
  const head = lead ? bases.slice(0, 1) : [];
  const tail = trail ? bases.slice(-1) : [];
  const middle = bases.slice(head.length, bases.length - tail.length);
  let out = '';
  if (head.length) out += `<span class="sk-nobr">${lead}${piece(head, true)}</span>`;
  if (middle.length) out += piece(middle, !head.length);
  if (tail.length) out += `<span class="sk-nobr">${piece(tail, !head.length && !middle.length)}${trail}</span>`;
  return out;
}

/**
 * Replace every <sk-math> in `html` with KaTeX output. A formula KaTeX rejects becomes a
 * marked <code> element and is passed to `onError`.
 */
export function renderMath(html: string, onError: (err: MathError) => void): string {
  return html.replace(SK_MATH, (_m, lead: string, b64: string, flag: string, trail: string) => {
    const tex = decodeBase64(b64);
    const display = flag === '1';
    let out: string;
    try {
      out = renderTex(tex, display);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      onError({ tex, display, message });
      return `${lead}<code class="sk-math-error" title="${escapeHtml(message)}">${escapeHtml(tex)}</code>${trail}`;
    }
    return display ? lead + out + trail : glue(out, lead, trail);
  });
}

/**
 * A label (plain text with inline $…$ math, docs/architecture.md §2.5) as HTML: the text
 * is escaped and each formula goes through KaTeX like body math. `\$` is a literal dollar.
 */
export function renderLabel(text: string, onError: (err: MathError) => void = () => {}): string {
  let out = '';
  let i = 0;
  while (i < text.length) {
    const start = findDollar(text, i);
    if (start < 0) break;
    const end = findDollar(text, start + 1);
    if (end < 0) break;
    out += escapeHtml(unescapeDollars(text.slice(i, start)));
    out += `<sk-math data-tex="${encodeBase64(text.slice(start + 1, end))}" data-display="0"></sk-math>`;
    i = end + 1;
  }
  return renderMath(out + escapeHtml(unescapeDollars(text.slice(i))), onError);
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
