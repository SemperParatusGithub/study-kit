// String helpers for the filter's HTML contract (docs/architecture.md §3.1). The fragments
// come from our own Lua filter, whose output shape is fixed and tested, so a few anchored
// regular expressions are enough: <sk-mc> never nests, and neither do hints or solutions.
import { sha256 } from './sys.mjs';

const ESCAPES: Record<string, string> = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;',
};

export function escapeHtml(text: string): string {
  return text.replace(/[&<>"']/g, (c) => ESCAPES[c]);
}

/** First 8 hex digits of sha256(text): the content hash `h` of progress items (§2.11). */
export function hash8(text: string): string {
  return sha256(text).slice(0, 8);
}

export interface MetaHeading {
  level: number;
  id: string;
  text: string;
}

export interface MetaItem {
  id: string;
  kind: string;
  topic: string | null;
  difficulty: number | null;
  type?: string;
}

export interface SkMeta {
  headings: MetaHeading[];
  items: MetaItem[];
}

const META = /<script type="application\/json" id="sk-meta">([\s\S]*?)<\/script>\s*$/;

/** Split the trailing sk-meta script (meta.lua) off a fragment. */
export function extractMeta(html: string): { html: string; meta: SkMeta } {
  const m = META.exec(html);
  if (!m) return { html, meta: { headings: [], items: [] } };
  let meta: SkMeta = { headings: [], items: [] };
  try {
    const parsed = JSON.parse(m[1]) as Partial<SkMeta>;
    meta = { headings: parsed.headings ?? [], items: parsed.items ?? [] };
  } catch {
    // keep the empty meta; the page still renders
  }
  return { html: html.slice(0, m.index).trimEnd() + '\n', meta };
}

const SK_MC = /<sk-mc\b[^>]*>[\s\S]*?<\/sk-mc>/g;
const ATTR = /\s([a-z][a-z0-9-]*)="([^"]*)"/g;

export function attributes(openTag: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const m of openTag.matchAll(ATTR)) out[m[1]] = m[2];
  return out;
}

/** Add data-h (hash of the element as the filter wrote it) to every <sk-mc>. */
export function addMcHashes(html: string): string {
  return html.replace(SK_MC, (outer) => outer.replace(/^<sk-mc\b/, `<sk-mc data-h="${hash8(outer)}"`));
}

export interface McElement {
  id: string;
  type: string;
  difficulty: number | null;
  topic: string | null;
  h: string;
  html: string;
}

/** Every <sk-mc> element of a fragment with its attributes. */
export function mcElements(html: string): McElement[] {
  return [...html.matchAll(SK_MC)].map((m) => {
    const open = m[0].slice(0, m[0].indexOf('>') + 1);
    const a = attributes(open);
    const difficulty = Number.parseInt(a['data-difficulty'] ?? '', 10);
    return {
      id: a['data-id'] ?? '',
      type: a['data-type'] ?? 'single',
      difficulty: Number.isFinite(difficulty) ? difficulty : null,
      topic: a['data-topic'] || null,
      h: a['data-h'] ?? '',
      html: m[0],
    };
  });
}

const HINT = /<details class="sk-hint"[^>]*>[\s\S]*?<\/details>\s*/g;
const SOLUTION = /<details class="sk-solution"[^>]*>[\s\S]*?<\/details>\s*/g;

/** An exercise or exam task cut into statement, hints and solution (blocks.lua). */
export function splitExercise(html: string): { body: string; hints: string[]; solution: string | null } {
  const hints = [...html.matchAll(HINT)].map((m) => m[0].trim());
  const solutions = [...html.matchAll(SOLUTION)].map((m) => m[0].trim());
  const body = html.replace(HINT, '').replace(SOLUTION, '').trim();
  return { body, hints, solution: solutions.length ? solutions.join('\n') : null };
}

/**
 * Wrap each top-level `<h2>` and what follows it up to the next one in
 * `<section class="{cls}">`, so a CSS column never separates a heading from its content.
 */
export function sectionize(html: string, cls: string): string {
  const parts = html.split(/(?=<h2[\s>])/);
  return parts
    .map((part) => (part.startsWith('<h2') ? `<section class="${cls}">\n${part.trim()}\n</section>\n` : part))
    .join('');
}

/** 1-based line of the first source line that contains `needle` (1 when not found). */
export function lineOf(source: string, needle: string): number {
  const first = needle
    .split('\n')
    .map((s) => s.trim())
    .find(Boolean);
  if (!first) return 1;
  const at = source.indexOf(first);
  return at < 0 ? 1 : source.slice(0, at).split('\n').length;
}
