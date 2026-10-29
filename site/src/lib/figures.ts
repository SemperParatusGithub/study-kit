// Figures are swapped in when a page renders (docs/architecture.md §3.2), never cached with
// the content: each <figure class="sk-fig" data-slug> placeholder from figures.lua gets the
// current <course>/_build/figures/<slug>.web.svg inline. Its colours are var(--fig-*), so
// the theme recolours figures too. A figure missing from the manifest or the directory is
// an error card in dev and fails a strict build.
import { errorCard, StrictError, type Finding } from './findings';
import { coursesDir, displayPath, joinPath, readJson, readText, strict } from './sys.mjs';

const SLOT = /<figure class="sk-fig" data-slug="([a-z0-9][a-z0-9-]*)"><div class="sk-fig-slot"><\/div>/g;
const VIEWBOX = /viewBox="\s*[-\d.]+\s+[-\d.]+\s+([\d.]+)\s+([\d.]+)\s*"/;

export function figureDir(course: string): string {
  return joinPath(coursesDir(), course, '_build', 'figures');
}

function missing(course: string, slug: string, why: string): Finding {
  return {
    path: displayPath(joinPath(figureDir(course), `${slug}.web.svg`)),
    line: 1,
    col: 1,
    code: 'SK-FIG-BUILD',
    message: `figure '${slug}' is not available: ${why}`,
    fix: `run \`studykit fig build ${course}\` (or \`just figures ${course}\`)`,
    severity: 'error',
  };
}

function escapeAttr(text: string): string {
  return text.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
}

/** The SVG for one figure, sized from its viewBox and labelled with its alt text. */
function figureSvg(dir: string, slug: string): string | null {
  const svg = readText(joinPath(dir, `${slug}.web.svg`));
  if (svg === null) return null;
  const facts = readJson(joinPath(dir, `${slug}.facts.json`)) as { alt?: unknown } | null;
  const alt = typeof facts?.alt === 'string' ? facts.alt : '';
  const box = VIEWBOX.exec(svg);
  const style = box ? ` style="--fig-w: ${box[1]}; aspect-ratio: ${box[1]} / ${box[2]}"` : '';
  const label = alt ? ` role="img" aria-label="${escapeAttr(alt)}"` : ' aria-hidden="true"';
  return svg.trim().replace(/^<svg\b/, `<svg${label}${style}`);
}

/** Fill every figure slot in `html` with the course's current web SVG. */
export function inlineFigures(html: string, course: string): string {
  if (!html.includes('class="sk-fig"')) return html;
  const dir = figureDir(course);
  const manifest = (readJson(joinPath(dir, 'manifest.json')) ?? {}) as Record<string, unknown>;
  const problems: Finding[] = [];
  const out = html.replace(SLOT, (whole, slug: string) => {
    const svg = slug in manifest ? figureSvg(dir, slug) : null;
    if (svg !== null) return whole.replace('<div class="sk-fig-slot"></div>', `<div class="sk-fig-slot">${svg}</div>`);
    const finding = missing(course, slug, slug in manifest ? 'its SVG is missing' : 'not in the figure manifest');
    problems.push(finding);
    const card = errorCard([finding], 'Figure not available');
    return whole.replace('<div class="sk-fig-slot"></div>', `<div class="sk-fig-slot">${card}</div>`);
  });
  if (problems.length && strict()) throw new StrictError(problems);
  return out;
}
