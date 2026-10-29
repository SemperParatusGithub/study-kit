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

const QQUAD = /^\\qquad(?![A-Za-z])/;
/** A `.base` that KaTeX ended at a top-level \allowbreak (and the glue after it). */
const ENDS_AT_BREAK = /<span class="mspace allowbreak"><\/span>(?:<span class="mspace"[^>]*><\/span>)*<\/span>$/;
const DISPLAY_OPEN = '<span class="katex-display">';

/**
 * `\allowbreak` before every `\qquad` outside braces (where math mode is certain; KaTeX
 * rejects it in text mode). It changes nothing on screen, but KaTeX ends a `.base` there.
 */
export function markQquadBreaks(tex: string): string {
  let out = '';
  let depth = 0;
  for (let i = 0; i < tex.length; i++) {
    const ch = tex[i];
    if (ch === '\\') {
      if (depth === 0 && QQUAD.test(tex.slice(i))) out += '\\allowbreak';
      const name = /^\\(?:[A-Za-z]+|.)/s.exec(tex.slice(i))?.[0] ?? ch;
      out += name;
      i += name.length - 1;
      continue;
    }
    if (ch === '{') depth++;
    else if (ch === '}') depth = Math.max(0, depth - 1);
    out += ch;
  }
  return out;
}

/**
 * A display formula that sets several formulas apart with `\qquad` ("a = b, \qquad c = d")
 * may wrap between them, never inside one: the bases up to each `\allowbreak` that
 * markQquadBreaks put in go into one no-wrap group. Where display math may wrap at all is
 * up to the CSS (the cheat sheet's narrow columns, content.css); elsewhere it stays on one
 * line and scrolls. For any other shape of output the plain rendering is kept.
 */
function groupDisplay(plain: string, marked: string): string {
  const parts = (html: string) =>
    html.startsWith(DISPLAY_OPEN) && html.endsWith('</span>')
      ? splitBases(html.slice(DISPLAY_OPEN.length, -'</span>'.length))
      : null;
  const original = parts(plain);
  const split = parts(marked);
  if (!original || !split) return plain;
  const groups: string[][] = [[]];
  for (const base of split.bases) {
    groups.at(-1)?.push(base);
    if (ENDS_AT_BREAK.test(base)) groups.push([]);
  }
  const filled = groups.filter((g) => g.length > 0);
  if (filled.length < 2) return plain;
  const inner = filled.map((g) => (g.length > 1 ? `<span class="sk-nobr">${g.join('')}</span>` : g[0])).join('');
  // the MathML (and its TeX annotation) of the formula as written
  return `${DISPLAY_OPEN}<span class="katex">${original.mathml}${HTML_OPEN}${inner}${KATEX_CLOSE}</span>`;
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
    if (!display) return glue(out, lead, trail);
    const marked = markQquadBreaks(tex);
    if (marked !== tex) {
      try {
        out = groupDisplay(out, renderTex(marked, true));
      } catch {
        // keep the plain rendering
      }
    }
    return lead + out + trail;
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
