// Content loader for course documents (docs/architecture.md §3.2).
//
// pandoc runs in Python, through `studykit render <course> --known - --json` (the render
// bridge, src/studykit/render.py), so the pandoc argv and the filter metadata exist once.
// Per course and sync the loader:
//   1. sends the digests it already stores; the bridge rewrites _build/index.json, and
//      returns `cached` for files whose digest (format, pandoc version, filter tree, index,
//      file bytes) is unchanged, and HTML plus validated frontmatter for the rest; the stored
//      digest is prefixed with a STAMP of this loader's own inputs (its version, KaTeX, and
//      the sources in SHAPING_SOURCES), so editing those rebuilds every entry too;
//   2. removes the trailing sk-meta script and keeps its headings;
//   3. hashes each <sk-mc> and each exercise or exam-task fragment as the filter wrote it
//      (first 8 hex of sha256) for the progress content hash `h` (§2.11);
//   4. renders every <sk-math> with KaTeX (lib/katex.ts), and the inline math of the
//      frontmatter labels (answer labels, rubric criteria, objectives) into `labels`;
//   5. stores {id: '<course>/<rel>', data, rendered: {html, metadata: {headings}}}.
// Findings (filter, schema, KaTeX in the body or a label) become a red error card at the top
// of the document; with STUDYKIT_STRICT=1 the load throws instead. In dev the watcher re-syncs a course when one
// of its files changes; only the changed files (or all, if the index changed) re-render.
// Figures are not part of the cache: pages inline them at render time (lib/figures.ts).
import type { Loader, LoaderContext } from 'astro/loaders';
import katex from 'katex';
import { errorCard, StrictError, type Finding } from '../lib/findings';
import { addMcHashes, extractMeta, hash8, lineOf, mcElements } from '../lib/html';
import { renderLabel, renderMath, type MathError } from '../lib/katex';
import {
  displayPath,
  fromFileUrl,
  isAbsolutePath,
  isFile,
  joinPath,
  listDir,
  readText,
  relativePath,
  repoRoot,
  run,
  sha256,
  siteRoot,
  strict,
} from '../lib/sys.mjs';
import type { DocData, DocKind } from '../lib/types';

// Bump when this file changes what it stores, so cached entries are rebuilt.
const LOADER_VERSION = 4;
// The sources that shape a stored entry; editing any of them rebuilds every entry.
const SHAPING_SOURCES = ['src/loaders/pandoc.ts', 'src/lib/katex.ts', 'src/lib/html.ts', 'src/lib/findings.ts'];
const STAMP = `sk${LOADER_VERSION}-katex${katex.version}-${sourcesHash()}:`;
const RENDER_SCHEMA = 1;
const HASHED_KINDS: DocKind[] = ['exercise', 'exam-task'];
const MC_KINDS: DocKind[] = ['mc', 'exam-mc'];
// Course subdirectories whose changes never affect a rendered document.
const IGNORED_DIRS = /^(?:_build|_history|state|progress|checks|sources|analysis)\//;

/** First 12 hex of the sha256 over SHAPING_SOURCES ('' for a source that cannot be read). */
function sourcesHash(): string {
  return sha256(...SHAPING_SOURCES.map((rel) => readText(joinPath(siteRoot, rel)) ?? '')).slice(0, 12);
}

interface BridgeFile {
  rel: string;
  kind: DocKind;
  digest: string;
  cached: boolean;
  data: Record<string, unknown> | null;
  html: string | null;
  findings: Finding[];
}

interface BridgeResult {
  schema: number;
  course: string;
  lang: string;
  root: string;
  pandoc: string;
  files: BridgeFile[];
  skipped: { rel: string; reason: string }[];
}

export interface PandocLoaderOptions {
  /** Courses directory, absolute or relative to the site root. */
  base: string;
}

export function pandocLoader({ base }: PandocLoaderOptions): Loader {
  return {
    name: 'studykit-pandoc',
    load: async (ctx) => {
      const dir = isAbsolutePath(base) ? base : joinPath(fromFileUrl(ctx.config.root), base);
      await syncAll(ctx, dir);
      if (strict()) {
        const errors = ctx.store
          .values()
          .flatMap((e) => (e.data as unknown as DocData).findings)
          .filter((f) => f.severity === 'error');
        if (errors.length) throw new StrictError(errors);
      }
      if (ctx.watcher) watch(ctx, dir);
    },
  };
}

function courseIds(dir: string): string[] {
  return listDir(dir).filter((name) => isFile(joinPath(dir, name, 'course.yaml')));
}

async function syncAll(ctx: LoaderContext, dir: string): Promise<void> {
  const ids = courseIds(dir);
  if (!ids.length) {
    // A strict build without a course is a wrong STUDYKIT_COURSES_DIR, not an empty site.
    const message =
      `no courses in ${dir}: set STUDYKIT_COURSES_DIR to the directory that holds ` +
      `<course>/course.yaml (a relative value is relative to site/; just makes it absolute)`;
    if (strict()) throw new Error(message);
    ctx.logger.warn(message);
  }
  for (const key of ctx.store.keys()) {
    if (!ids.includes(key.split('/')[0])) ctx.store.delete(key);
  }
  for (const id of ids) await syncCourse(ctx, dir, id);
}

async function bridge(courseDir: string, known: Record<string, string>): Promise<BridgeResult> {
  const args = ['render', courseDir, '--known', '-', '--json'];
  const input = JSON.stringify(known);
  let res;
  try {
    res = await run('uv', ['run', '--frozen', 'studykit', ...args], { input });
  } catch {
    // no uv on PATH: use the project environment directly
    res = await run(joinPath(repoRoot, '.venv', 'bin', 'studykit'), args, { input });
  }
  if (res.code !== 0) {
    throw new Error(`studykit render ${courseDir} failed (exit ${res.code}):\n${res.stderr.trim()}`);
  }
  const result = JSON.parse(res.stdout) as BridgeResult;
  if (result.schema !== RENDER_SCHEMA) {
    throw new Error(`studykit render returned schema ${result.schema}, expected ${RENDER_SCHEMA}`);
  }
  return result;
}

async function syncCourse(ctx: LoaderContext, dir: string, course: string): Promise<void> {
  const courseDir = joinPath(dir, course);
  const prefix = `${course}/`;
  const known: Record<string, string> = {};
  for (const [id, entry] of ctx.store.entries()) {
    if (id.startsWith(prefix) && entry.digest?.toString().startsWith(STAMP)) {
      known[id.slice(prefix.length)] = entry.digest.toString().slice(STAMP.length);
    }
  }
  let result: BridgeResult;
  try {
    result = await bridge(courseDir, known);
  } catch (err) {
    if (strict()) throw err;
    ctx.logger.error(err instanceof Error ? err.message : String(err));
    return;
  }
  const seen = new Set<string>();
  let rendered = 0;
  for (const file of result.files) {
    const id = prefix + file.rel;
    seen.add(id);
    if (file.cached && ctx.store.has(id)) continue;
    const { data, html, headings } = buildEntry(course, courseDir, file);
    const parsed = await ctx.parseData({ id, data: data as unknown as Record<string, unknown> });
    ctx.store.set({
      id,
      data: parsed,
      digest: STAMP + file.digest,
      rendered: { html, metadata: { headings } },
    });
    rendered++;
    for (const f of data.findings) {
      if (f.severity === 'error') ctx.logger.warn(`${f.path}:${f.line}:${f.col} ${f.code} ${f.message}`);
    }
  }
  for (const key of ctx.store.keys()) {
    if (key.startsWith(prefix) && !seen.has(key)) ctx.store.delete(key);
  }
  ctx.logger.info(`${course}: ${rendered} rendered, ${result.files.length - rendered} cached`);
  const broken = ctx.store
    .entries()
    .filter(([id, e]) => id.startsWith(prefix) && (e.data as unknown as DocData).findings.some((f) => f.severity === 'error'));
  if (broken.length && !strict()) {
    ctx.logger.warn(`${course}: ${broken.length} file(s) with content errors; their pages show error cards`);
  }
}

const PARTS: [DocKind, RegExp][] = [
  ['summary', /^summary\/(?<nn>\d{2})-(?<topic>[a-z0-9-]+)\.md$/],
  ['exercise', /^exercises\/(?<topic>[a-z0-9-]+)\/(?<id>ex-[a-z0-9-]+)\.md$/],
  ['mc', /^mc\/(?<topic>[a-z0-9-]+)\.md$/],
  ['exam', /^exams\/(?<exam>[a-z0-9-]+)\/exam\.yaml$/],
  ['exam-mc', /^exams\/(?<exam>[a-z0-9-]+)\/mc\.md$/],
  ['exam-task', /^exams\/(?<exam>[a-z0-9-]+)\/(?<nn>\d{2})-(?<id>[a-z0-9-]+)\.md$/],
];

function str(value: unknown): string | null {
  return typeof value === 'string' && value ? value : null;
}

/** Frontmatter strings that hold a label with inline math (docs/architecture.md §2.5). */
function labelTexts(fm: Record<string, unknown>): string[] {
  const out: string[] = [];
  const field = (list: unknown, key: string | null) => {
    if (!Array.isArray(list)) return;
    for (const item of list) {
      const value = key === null ? item : (item as Record<string, unknown> | null)?.[key];
      if (typeof value === 'string') out.push(value);
    }
  };
  field(fm.answers, 'label');
  field(fm.rubric, 'criterion');
  field(fm.objectives, null);
  return out;
}

/** Line and column of a label formula in the frontmatter (1:1 when it cannot be found). */
function frontmatterPosition(source: string, tex: string): { line: number; col: number } {
  const end = source.startsWith('---') ? source.indexOf('\n---', 3) : -1;
  const head = end > 0 ? source.slice(0, end) : source;
  // as written, or with the backslashes doubled inside a double-quoted YAML string
  for (const needle of [`$${tex}$`, `$${tex.replace(/\\/g, '\\\\')}$`]) {
    const at = head.indexOf(needle);
    if (at < 0) continue;
    const lines = head.slice(0, at).split('\n');
    return { line: lines.length, col: lines[lines.length - 1].length + 1 };
  }
  return { line: 1, col: 1 };
}

function buildEntry(course: string, courseDir: string, file: BridgeFile) {
  const fm = file.data ?? {};
  const groups = PARTS.find(([kind, rx]) => kind === file.kind && rx.test(file.rel))?.[1].exec(file.rel)
    ?.groups ?? {};
  const findings = [...file.findings];
  const path = joinPath(courseDir, file.rel);
  const source = readText(path) ?? '';
  const { html: fragment, meta } = extractMeta(file.html ?? '');
  const h = HASHED_KINDS.includes(file.kind) && file.html !== null ? hash8(fragment) : null;
  const mathFinding = (err: MathError, at: { line: number; col: number }, where: string) =>
    findings.push({
      path: displayPath(path),
      ...at,
      code: 'SK-MATH-KATEX',
      message: `KaTeX rejects ${err.display ? 'display' : 'inline'} math${where}: ${err.message}`,
      fix: 'follow the KaTeX message; words go in \\text{…}, units in \\mathrm{…}',
      severity: 'error',
    });
  const labels: Record<string, string> = Object.create(null);
  for (const text of labelTexts(fm)) {
    labels[text] ??= renderLabel(text, (err) =>
      mathFinding(err, frontmatterPosition(source, err.tex), ' in a frontmatter label'),
    );
  }
  let html = renderMath(addMcHashes(fragment), (err) =>
    mathFinding(err, { line: lineOf(source, err.tex), col: 1 }, ''),
  );
  const questions = MC_KINDS.includes(file.kind) ? mcElements(html) : [];
  const errors = findings.filter((f) => f.severity === 'error');
  if (errors.length) html = errorCard(errors) + html;
  const id = str(fm.id) ?? groups.id ?? null;
  const data: DocData = {
    course,
    rel: file.rel,
    kind: file.kind,
    title: str(fm.title) ?? id ?? file.rel,
    id,
    topic: str(fm.topic) ?? groups.topic ?? null,
    exam: groups.exam ?? null,
    order: groups.nn ? Number.parseInt(groups.nn, 10) : null,
    fm,
    labels,
    h,
    headings: meta.headings,
    questions,
    findings,
  };
  return { data, html, headings: meta.headings.map((x) => ({ depth: x.level, slug: x.id, text: x.text })) };
}

function watch(ctx: LoaderContext, dir: string): void {
  const watcher = ctx.watcher;
  if (!watcher) return;
  watcher.add(dir);
  const timers = new Map<string, ReturnType<typeof setTimeout>>();
  watcher.on('all', (_event: string, changed: string) => {
    const rel = relativePath(dir, changed);
    if (rel.startsWith('..')) return;
    const [course, ...rest] = rel.split('/');
    const sub = rest.join('/');
    if (!sub || !/\.(?:md|ya?ml)$/.test(sub) || IGNORED_DIRS.test(sub)) return;
    clearTimeout(timers.get(course));
    timers.set(
      course,
      setTimeout(() => {
        timers.delete(course);
        const work = isFile(joinPath(dir, course, 'course.yaml'))
          ? syncCourse(ctx, dir, course)
          : syncAll(ctx, dir);
        work.catch((err: unknown) => ctx.logger.error(err instanceof Error ? err.message : String(err)));
      }, 150),
    );
  });
}
