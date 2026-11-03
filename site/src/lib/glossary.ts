// The glossary of a topic (docs/architecture.md §5.6): every titled `::: definition` box of
// its chapters. The fragments come from our own filter (blocks.lua), whose shape is fixed
// and tested, and boxes never nest, so an anchored regular expression is enough.

export interface GlossaryEntry {
  term: string;
  /** the term as HTML, with its math */
  termHtml: string;
  /** the definition's body as HTML */
  html: string;
  /** the id of the section it stands in, or null before the first heading */
  heading: string | null;
}

const DEFINITION =
  /<aside class="sk-block sk-definition"[^>]*>\s*<div class="sk-block-title">([\s\S]*?)<\/div>([\s\S]*?)<\/aside>/g;
const HEADING = /<h[2-4]\b[^>]*\bid="([^"]+)"/g;
// the title blocks.lua gives a box without its own (lib/i18n.lua): not a term
const UNTITLED = new Set(['definition']);

function plainText(html: string): string {
  return html
    .replace(/<annotation\b[^>]*>[\s\S]*?<\/annotation>/g, '')
    .replace(/<[^>]+>/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

/** The titled definitions of a chapter's HTML, in the order they appear. */
export function definitions(html: string): GlossaryEntry[] {
  const headings = [...html.matchAll(HEADING)].map((m) => ({ at: m.index, id: m[1] ?? '' }));
  const out: GlossaryEntry[] = [];
  for (const m of html.matchAll(DEFINITION)) {
    const termHtml = (m[1] ?? '').trim();
    const term = plainText(termHtml);
    if (!term || UNTITLED.has(term.toLowerCase())) continue;
    const before = headings.filter((h) => h.at < m.index);
    out.push({ term, termHtml, html: (m[2] ?? '').trim(), heading: before.at(-1)?.id ?? null });
  }
  return out;
}

/** One entry per term, ignoring case: the first, so where the teaching order introduces it. */
export function uniqueTerms<T extends { term: string }>(entries: readonly T[]): T[] {
  const seen = new Set<string>();
  return entries.filter((entry) => {
    const key = entry.term.toLowerCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

/** Entries sorted for the reader, grouped by their first letter ('#' for anything else). */
export function byLetter<T extends { term: string }>(entries: readonly T[], lang: string): [string, T[]][] {
  const sorted = [...entries].sort((a, b) => a.term.localeCompare(b.term, lang, { sensitivity: 'base' }));
  const groups = new Map<string, T[]>();
  for (const entry of sorted) {
    const first = entry.term.normalize('NFD').charAt(0).toUpperCase();
    const letter = /^\p{L}$/u.test(first) ? first : '#';
    groups.set(letter, [...(groups.get(letter) ?? []), entry]);
  }
  return [...groups];
}

/** An anchor for a term. */
export function termSlug(term: string): string {
  const slug = term
    .normalize('NFD')
    .replace(/\p{M}/gu, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
  return `term-${slug || 'x'}`;
}
