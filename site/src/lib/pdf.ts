// The course's PDFs as the site serves them (docs/architecture.md §3.2, §3.3):
//   /c/<c>/pdf/<file>        <course>/_build/pdf/<file>, for every document listed in
//                            _build/pdf/manifest.json (written by `studykit pdf`)
//   /c/<c>/src/<doc>.pdf     <course>/sources/raw/<file>, for every document listed in
//                            sources/manifest.yaml (§2.1); refs.lua links `src:` here, with
//                            #page=<n> for the browser's PDF viewer
// A document that is not built, is not listed, or whose file is missing is simply absent:
// no route and no link. Build time only (files through sys.mjs).
//
// The manifest contract, shared with the PDF pipeline:
//   {"schema": "studykit-pdf/1", "course": "<course id>",
//    "docs": [{"id", "kind", "file", "title", "pages", "bytes",
//              "exam"?            (kinds exam and exam-solutions),
//              "max_pages"?, "density"? (cheatsheet only)}]}
import { parse } from 'yaml';
import { coursesDir, fileSize, isInside, joinPath, readBytes, readJson, readText } from './sys.mjs';

export const PDF_SCHEMA = 'studykit-pdf/1';

export const PDF_KINDS = [
  'overview',
  'summary',
  'exercises',
  'exercises-blank',
  'mc',
  'exam',
  'exam-solutions',
  'cheatsheet',
  'plan',
] as const;

export type PdfKind = (typeof PDF_KINDS)[number];

export interface PdfDoc {
  id: string;
  kind: PdfKind;
  /** File name in _build/pdf/, served at /c/<c>/pdf/<file>. */
  file: string;
  title: string;
  pages: number;
  bytes: number;
  /** The exam id, for kinds exam and exam-solutions. */
  exam: string | null;
  /** Cheat sheet only: its page limit and the density level (0–4) it was set at. */
  maxPages: number | null;
  density: number | null;
}

export interface SourceDoc {
  /** Document id (sources/manifest.yaml), served at /c/<c>/src/<id>.pdf. */
  id: string;
  title: string;
  pages: number | null;
  /** Path of the file inside sources/raw/. */
  file: string;
}

export interface Parsed<T> {
  docs: T[];
  /** Why entries (or the whole file) were left out, for a build warning. */
  problems: string[];
}

/** A file size, or null when the file is not there. */
export type SizeOf = (file: string) => number | null;

const KEBAB = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
/** A plain file name in _build/pdf/: no directories, ends in .pdf. */
const PDF_FILE = /^[A-Za-z0-9][A-Za-z0-9._-]*\.pdf$/;
const EXAM_KINDS: ReadonlySet<string> = new Set(['exam', 'exam-solutions']);

const isObject = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v);
const isInt = (v: unknown, min: number): v is number => typeof v === 'number' && Number.isInteger(v) && v >= min;

/** URL of a built PDF. */
export function pdfHref(course: string, file: string): string {
  return `/c/${course}/pdf/${file}`;
}

/** URL of a source document, opened at `page` when given (the `src:` route of refs.lua). */
export function sourceHref(course: string, doc: string, page?: number | null): string {
  return `/c/${course}/src/${doc}.pdf${page ? `#page=${page}` : ''}`;
}

/**
 * The documents of a parsed `_build/pdf/manifest.json` that can be served. `sizeOf` gives the
 * size of a file in _build/pdf/ (null: missing). An entry needs a known kind, a plain .pdf
 * file name that exists, a page count, and an exam id for the exam kinds; `bytes` falls back
 * to the file's size. A manifest of another schema or course yields nothing.
 */
export function parsePdfManifest(raw: unknown, course: string, sizeOf: SizeOf): Parsed<PdfDoc> {
  const problems: string[] = [];
  if (!isObject(raw)) return { docs: [], problems: ['not a JSON object'] };
  if (raw.schema !== PDF_SCHEMA) {
    return { docs: [], problems: [`schema is ${JSON.stringify(raw.schema)}, not "${PDF_SCHEMA}"`] };
  }
  if (raw.course !== course) {
    return { docs: [], problems: [`it is the manifest of course ${JSON.stringify(raw.course)}`] };
  }
  if (!Array.isArray(raw.docs)) return { docs: [], problems: ['"docs" is not a list'] };
  const docs: PdfDoc[] = [];
  const ids = new Set<string>();
  const files = new Set<string>();
  raw.docs.forEach((entry, i) => {
    const where = `docs[${i}]`;
    if (!isObject(entry)) return void problems.push(`${where} is not an object`);
    const { id, kind, file, title, pages, bytes, exam, max_pages: maxPages, density } = entry;
    if (typeof id !== 'string' || !id) return void problems.push(`${where} has no id`);
    if (typeof kind !== 'string' || !(PDF_KINDS as readonly string[]).includes(kind)) {
      return void problems.push(`${id}: unknown kind ${JSON.stringify(kind)}`);
    }
    if (typeof file !== 'string' || !PDF_FILE.test(file)) {
      return void problems.push(`${id}: file ${JSON.stringify(file)} is not a plain .pdf file name`);
    }
    if (!isInt(pages, 1)) return void problems.push(`${id}: pages ${JSON.stringify(pages)} is not a page count`);
    if (EXAM_KINDS.has(kind) && (typeof exam !== 'string' || !KEBAB.test(exam))) {
      return void problems.push(`${id}: an ${kind} document needs its exam id`);
    }
    if (ids.has(id) || files.has(file)) return void problems.push(`${id}: listed twice`);
    const size = sizeOf(file);
    if (size === null) return void problems.push(`${id}: ${file} is not in _build/pdf/`);
    if (isInt(bytes, 0) && bytes !== size) problems.push(`${id}: ${file} has ${size} bytes, the manifest says ${bytes}`);
    ids.add(id);
    files.add(file);
    docs.push({
      id,
      kind: kind as PdfKind,
      file,
      title: typeof title === 'string' && title.trim() ? title : id,
      pages,
      bytes: isInt(bytes, 0) ? bytes : size,
      exam: EXAM_KINDS.has(kind) ? (exam as string) : null,
      maxPages: kind === 'cheatsheet' && isInt(maxPages, 1) ? maxPages : null,
      density: kind === 'cheatsheet' && isInt(density, 0) && density <= 4 ? density : null,
    });
  });
  return { docs, problems };
}

/** A path inside sources/raw/ from a manifest entry, or null when it is not one. */
function rawPath(value: string): string | null {
  const path = value.replace(/^\.\//, '').replace(/^(?:sources\/)?raw\//, '');
  if (!path || path.startsWith('/') || path.includes('\\')) return null;
  if (path.split('/').some((part) => part === '' || part === '.' || part === '..')) return null;
  return /\.pdf$/i.test(path) ? path : null;
}

/**
 * The documents of a parsed `sources/manifest.yaml` whose file exists. The manifest has no
 * model yet (§2.1); it is read like studykit's content.py reads it: `documents` (or `docs`)
 * as a list of `{id, title, pages}` or a mapping from id to `{title, pages}`. The file is
 * `file` (or `path`) inside sources/raw/ when given, else `<id>.pdf`; `sizeOf` gives its
 * size (null: missing).
 */
export function parseSourceManifest(raw: unknown, sizeOf: SizeOf): Parsed<SourceDoc> {
  const problems: string[] = [];
  if (!isObject(raw)) return { docs: [], problems: raw == null ? [] : ['not a mapping'] };
  let entries = raw.documents ?? raw.docs;
  if (isObject(entries)) {
    entries = Object.entries(entries).map(([id, v]) => (isObject(v) ? { id, ...v } : { id }));
  }
  if (!Array.isArray(entries)) return { docs: [], problems: ['"documents" is not a list'] };
  const docs: SourceDoc[] = [];
  const seen = new Set<string>();
  for (const entry of entries) {
    if (!isObject(entry) || typeof entry.id !== 'string') continue;
    const id = entry.id;
    if (!KEBAB.test(id)) {
      problems.push(`${id}: not a document id`);
      continue;
    }
    const given = typeof entry.file === 'string' ? entry.file : typeof entry.path === 'string' ? entry.path : null;
    const file = rawPath(given ?? `${id}.pdf`);
    if (file === null) {
      problems.push(`${id}: file ${JSON.stringify(given)} is not a .pdf inside sources/raw/`);
      continue;
    }
    if (seen.has(id)) {
      problems.push(`${id}: listed twice`);
      continue;
    }
    if (sizeOf(file) === null) continue; // not copied (yet): nothing to serve
    seen.add(id);
    const title = entry.title;
    docs.push({
      id,
      title: typeof title === 'string' && title.trim() ? title : id,
      pages: isInt(entry.pages, 1) ? entry.pages : null,
      file,
    });
  }
  return { docs, problems };
}

const warned = new Set<string>();

function warn(course: string, what: string, problems: string[]): void {
  for (const p of problems) {
    const line = `[studykit] ${course}/${what}: ${p}`;
    if (warned.has(line)) continue;
    warned.add(line);
    console.warn(line);
  }
}

/** Directory of the built PDFs of a course. */
export function pdfDir(course: string): string {
  return joinPath(coursesDir(), course, '_build', 'pdf');
}

/** Directory of the course's source documents. */
export function rawDir(course: string): string {
  return joinPath(coursesDir(), course, 'sources', 'raw');
}

/** The built PDFs of a course, read now (none without a manifest). */
export function readPdfs(course: string): PdfDoc[] {
  const dir = pdfDir(course);
  const raw = readJson(joinPath(dir, 'manifest.json'));
  if (raw === null) return [];
  const { docs, problems } = parsePdfManifest(raw, course, (file) => fileSize(joinPath(dir, file)));
  warn(course, '_build/pdf/manifest.json', problems);
  return docs;
}

/** The source documents of a course that are there to serve, read now. */
export function readSources(course: string): SourceDoc[] {
  const text = readText(joinPath(coursesDir(), course, 'sources', 'manifest.yaml'));
  if (text === null) return [];
  let raw: unknown;
  try {
    raw = parse(text);
  } catch (e) {
    warn(course, 'sources/manifest.yaml', [`not valid YAML: ${(e as Error).message.split('\n')[0]}`]);
    return [];
  }
  const dir = rawDir(course);
  const { docs, problems } = parseSourceManifest(raw, (file) => {
    const path = joinPath(dir, file);
    return isInside(dir, path) ? fileSize(path) : null;
  });
  warn(course, 'sources/manifest.yaml', problems);
  return docs;
}

/** The absolute path of a served PDF, or null when the course has no such document now. */
export function pdfFile(course: string, file: string): string | null {
  return readPdfs(course).some((d) => d.file === file) ? joinPath(pdfDir(course), file) : null;
}

/** The absolute path of a served source document, or null when there is none now. */
export function sourceFile(course: string, doc: string): string | null {
  const hit = readSources(course).find((d) => d.id === doc);
  return hit ? joinPath(rawDir(course), hit.file) : null;
}

/**
 * The response of a PDF route: the file's bytes as they are on disk. A file that is gone is
 * a 404 in dev and fails the build (a static route must not write an error text as a PDF).
 */
export function pdfResponse(path: string | null, what: string, dev: boolean): Response {
  const bytes = path ? readBytes(path) : null;
  if (!bytes) {
    if (!dev) throw new Error(`${what} is missing`);
    return new Response(`${what} is not there\n`, {
      status: 404,
      headers: { 'Content-Type': 'text/plain; charset=utf-8' },
    });
  }
  return new Response(bytes, { headers: { 'Content-Type': 'application/pdf' } });
}

/** File names the PDF pipeline writes for a course with these exams (§3.3). */
export function expectedPdfFiles(exams: string[]): string[] {
  return [
    'overview.pdf',
    'summary.pdf',
    'exercises.pdf',
    'exercises-blank.pdf',
    'mc.pdf',
    ...exams.flatMap((e) => [`${e}.pdf`, `${e}-solutions.pdf`]),
    'cheatsheet.pdf',
    'plan.pdf',
  ];
}

/** The built PDF of a kind (and exam), if there is one. */
export function findPdf(docs: PdfDoc[], kind: PdfKind, exam?: string): PdfDoc | null {
  return docs.find((d) => d.kind === kind && (exam === undefined || d.exam === exam)) ?? null;
}

/** 812 -> "812 B", 120_400 -> "120 kB", 1_234_567 -> "1.2 MB", 23_456_789 -> "23 MB" (SI units). */
export function formatBytes(bytes: number): string {
  if (bytes < 1000) return `${bytes} B`;
  const kb = Math.round(bytes / 1000);
  if (kb < 1000) return `${kb} kB`;
  const mb = bytes / 1e6;
  return mb < 9.95 ? `${mb.toFixed(1)} MB` : `${Math.round(mb)} MB`;
}

/** "4 pages · 120 kB" (or only the size). */
export function pdfMeta(doc: Pick<PdfDoc, 'pages' | 'bytes'>, pages = true): string {
  const size = formatBytes(doc.bytes);
  return pages ? `${doc.pages} ${doc.pages === 1 ? 'page' : 'pages'} · ${size}` : size;
}

/** Font size of a cheat-sheet density level (§3.3: 0–4 is 9, 8.5, 8, 7.5 and 7 pt). */
export function densityPt(density: number | null | undefined): number | null {
  return typeof density === 'number' && density >= 0 && density <= 4 ? 9 - density / 2 : null;
}

/** The first page of a page spec from frontmatter (`7`, `'3-7'`), or null. */
export function firstPage(spec: number | string | null | undefined): number | null {
  if (typeof spec === 'number') return Number.isInteger(spec) && spec > 0 ? spec : null;
  const m = /^\s*(\d+)/.exec(spec ?? '');
  const n = m ? Number(m[1]) : 0;
  return n > 0 ? n : null;
}
