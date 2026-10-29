// Fake built PDFs for testing the site's PDF routes and links before the PDF pipeline
// (`studykit pdf`, docs/architecture.md §3.3) is there. From site/:
//
//   node tests/fake-pdfs.mjs [course] [--sources] [--omit kind,kind] [--force]
//   node tests/fake-pdfs.mjs [course] --clean
//
// It writes <courses>/<course>/_build/pdf/ (gitignored): one small, valid PDF per document
// the course has sources for, plus manifest.json in the shape the pipeline writes
// (schema studykit-pdf/1; lib/pdf.ts reads it). --sources also writes two lecture PDFs to
// sources/raw/ and lists them in sources/manifest.yaml, for the /c/<c>/src/ route.
// --omit leaves documents of these kinds out. --clean removes what this script wrote, and
// only that. The course defaults to sample-course and <courses> to STUDYKIT_COURSES_DIR, else
// the repository's examples/; courses/ is never touched. PDFs are generated, never committed.
//
// Then build and run the e2e suite against the build:
//   STUDYKIT_COURSES_DIR=examples just build sample-course && just e2e
//
// The PDFs are deterministic (same bytes on every run), German like the sample course, and
// carry the producer string below, which --clean checks before it deletes anything.

import { existsSync, mkdirSync, readFileSync, readdirSync, rmSync, rmdirSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const SITE = fileURLToPath(new URL('..', import.meta.url));
const REPO = resolve(SITE, '..');
export const PRODUCER = 'studykit site tests: fake PDF';
/** A word that is only in the fake PDFs: search must never find it (Pagefind skips PDFs). */
export const FAKE_WORD = 'Platzhalterdokument';

/** Text of a PDF string literal, encoded WinAnsi (latin1) with ( ) \ escaped. */
function pdfString(text) {
  return `(${text.replace(/[\\()]/g, (c) => `\\${c}`)})`;
}

/**
 * A valid PDF 1.7 with one page per entry of `pages` (each a list of text lines), set in
 * the standard Helvetica font, so every reader (pypdfium2, browsers) opens it.
 * @param {string[][]} pages
 * @param {string} title
 * @returns {Buffer}
 */
export function makePdf(pages, title) {
  const objects = [];
  const add = (body) => objects.push(body); // the new length: the object's number
  const catalog = add(null);
  const tree = add(null);
  const font = add('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>');
  const kids = [];
  for (const lines of pages) {
    const ops = ['BT', '/F1 22 Tf', '72 760 Td', '26 TL'];
    lines.forEach((line, i) => {
      if (i === 1) ops.push('/F1 12 Tf', '16 TL');
      ops.push(`${pdfString(line)} Tj`, 'T*');
    });
    ops.push('ET');
    const stream = Buffer.from(ops.join('\n'), 'latin1');
    const content = add(Buffer.concat([
      Buffer.from(`<< /Length ${stream.length} >>\nstream\n`, 'latin1'),
      stream,
      Buffer.from('\nendstream', 'latin1'),
    ]));
    kids.push(add(`<< /Type /Page /Parent ${tree} 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 ${font} 0 R >> >> /Contents ${content} 0 R >>`));
  }
  objects[catalog - 1] = `<< /Type /Catalog /Pages ${tree} 0 R >>`;
  objects[tree - 1] = `<< /Type /Pages /Kids [${kids.map((k) => `${k} 0 R`).join(' ')}] /Count ${kids.length} >>`;
  const info = add(`<< /Title ${pdfString(title)} /Producer ${pdfString(PRODUCER)} >>`);

  const chunks = [Buffer.from('%PDF-1.7\n%\xe2\xe3\xcf\xd3\n', 'latin1')];
  let offset = chunks[0].length;
  const offsets = [];
  objects.forEach((body, i) => {
    const chunk = Buffer.concat([
      Buffer.from(`${i + 1} 0 obj\n`, 'latin1'),
      Buffer.isBuffer(body) ? body : Buffer.from(body, 'latin1'),
      Buffer.from('\nendobj\n', 'latin1'),
    ]);
    offsets.push(offset);
    offset += chunk.length;
    chunks.push(chunk);
  });
  const xref = [
    'xref',
    `0 ${objects.length + 1}`,
    '0000000000 65535 f ',
    ...offsets.map((o) => `${String(o).padStart(10, '0')} 00000 n `),
    'trailer',
    `<< /Size ${objects.length + 1} /Root ${catalog} 0 R /Info ${info} 0 R >>`,
    'startxref',
    String(offset),
    '%%EOF',
    '',
  ].join('\n');
  chunks.push(Buffer.from(xref, 'latin1'));
  return Buffer.concat(chunks);
}

/** `n` pages of a fake document, "Seite i von n" on each. */
function fakePages(title, n, what) {
  return Array.from({ length: n }, (_, i) => [
    title,
    `Seite ${i + 1} von ${n}`,
    `${FAKE_WORD}: ${what}.`,
    'Erzeugt von site/tests/fake-pdfs.mjs, ohne echten Inhalt.',
  ]);
}

const has = (path) => existsSync(path);
const hasMarkdown = (dir) =>
  has(dir) && readdirSync(dir, { recursive: true, encoding: 'utf8' }).some((f) => f.endsWith('.md'));

/** A plain `key: value` of a YAML file (enough for the ids and titles of these files). */
function yamlValue(text, key) {
  const m = new RegExp(`^${key}:\\s*(.+?)\\s*$`, 'm').exec(text ?? '');
  return m ? m[1].replace(/^'(.*)'$/, '$1') : null;
}

/** The documents the pipeline would build for this course: kind, id, file, title, pages. */
export function plannedDocs(courseDir) {
  const course = readFileSync(join(courseDir, 'course.yaml'), 'utf8');
  const name = yamlValue(course, 'title') ?? 'Kurs';
  const docs = [];
  const doc = (kind, id, title, pages, extra = {}) =>
    docs.push({ id, kind, file: `${id}.pdf`, title, pages, ...extra });
  if (has(join(courseDir, 'overview.md'))) doc('overview', 'overview', `${name}: Überblick`, 2);
  if (hasMarkdown(join(courseDir, 'summary'))) doc('summary', 'summary', `${name}: Zusammenfassung`, 9);
  if (hasMarkdown(join(courseDir, 'exercises'))) {
    doc('exercises', 'exercises', `${name}: Übungen mit Hinweisen und Lösungen`, 12);
    doc('exercises-blank', 'exercises-blank', `${name}: Übungen`, 7);
  }
  if (hasMarkdown(join(courseDir, 'mc'))) doc('mc', 'mc', `${name}: Multiple Choice mit Lösungsschlüssel`, 14);
  const exams = join(courseDir, 'exams');
  for (const exam of has(exams) ? readdirSync(exams).sort() : []) {
    const yaml = join(exams, exam, 'exam.yaml');
    if (!has(yaml)) continue;
    const title = yamlValue(readFileSync(yaml, 'utf8'), 'title') ?? exam;
    doc('exam', exam, title, 6, { exam });
    doc('exam-solutions', `${exam}-solutions`, `${title}: Lösungen`, 8, { exam });
  }
  if (has(join(courseDir, 'cheatsheet.md'))) {
    const fm = readFileSync(join(courseDir, 'cheatsheet.md'), 'utf8');
    const max = Number(yamlValue(fm, 'max_pages') ?? 2);
    doc('cheatsheet', 'cheatsheet', yamlValue(fm, 'title') ?? 'Formelblatt', Math.min(2, max), {
      max_pages: max,
      density: 1,
    });
  }
  if (has(join(courseDir, 'plan.yaml'))) doc('plan', 'plan', `${name}: Lernplan`, 3);
  return docs;
}

/** The lecture PDFs written with --sources: id, title, pages, file in sources/raw/. */
export const SOURCES = [
  { id: 'vl-01', title: 'Vorlesung 1: Gleichstromnetze', pages: 5, file: 'vl-01.pdf' },
  { id: 'ue-01', title: 'Übung 1', pages: 3, file: 'uebungen/ue-01.pdf' },
];

function sourcesYaml() {
  const lines = ['# Written by site/tests/fake-pdfs.mjs --sources; --clean removes it.', 'schema: 1', 'documents:'];
  for (const s of SOURCES) {
    lines.push(`  - {id: ${s.id}, title: '${s.title}', pages: ${s.pages}${s.file === `${s.id}.pdf` ? '' : `, file: ${s.file}`}}`);
  }
  return `${lines.join('\n')}\n`;
}

const isFake = (path) => has(path) && readFileSync(path).includes(PRODUCER);

function removeEmptyDirs(dir, stop) {
  while (dir.startsWith(stop) && dir !== stop && has(dir) && readdirSync(dir).length === 0) {
    rmdirSync(dir);
    dir = dirname(dir);
  }
}

/**
 * Write the fake PDFs of a course. Returns the manifest written.
 * @param {string} courseDir
 * @param {{sources?: boolean, omit?: string[], force?: boolean}} [options]
 */
export function writeFakePdfs(courseDir, options = {}) {
  const id = yamlValue(readFileSync(join(courseDir, 'course.yaml'), 'utf8'), 'id');
  const out = join(courseDir, '_build', 'pdf');
  const real = (has(out) ? readdirSync(out) : []).filter((f) => f.endsWith('.pdf') && !isFake(join(out, f)));
  if (real.length && !options.force) {
    throw new Error(`${out} holds PDFs this script did not write (${real.join(', ')}); use --force to replace them`);
  }
  rmSync(out, { recursive: true, force: true });
  mkdirSync(out, { recursive: true });
  const omit = new Set(options.omit ?? []);
  const docs = [];
  for (const d of plannedDocs(courseDir).filter((x) => !omit.has(x.kind))) {
    const bytes = makePdf(fakePages(d.title, d.pages, `${d.kind} von ${id}`), d.title);
    writeFileSync(join(out, d.file), bytes);
    docs.push({ ...d, bytes: bytes.length });
  }
  const manifest = { schema: 'studykit-pdf/1', course: id, docs };
  writeFileSync(join(out, 'manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`);
  if (options.sources) {
    const raw = join(courseDir, 'sources', 'raw');
    const yaml = join(courseDir, 'sources', 'manifest.yaml');
    if (has(yaml) && readFileSync(yaml, 'utf8') !== sourcesYaml()) {
      throw new Error(`${yaml} exists and was not written by this script`);
    }
    for (const s of SOURCES) {
      const path = join(raw, s.file);
      if (has(path) && !isFake(path)) throw new Error(`${path} exists and was not written by this script`);
      mkdirSync(dirname(path), { recursive: true });
      writeFileSync(path, makePdf(fakePages(s.title, s.pages, `Quelle ${s.id}`), s.title));
    }
    writeFileSync(yaml, sourcesYaml());
  }
  return manifest;
}

/** Remove what writeFakePdfs wrote; anything else stays. */
export function cleanFakePdfs(courseDir) {
  const out = join(courseDir, '_build', 'pdf');
  const files = has(out) ? readdirSync(out) : [];
  if (files.some((f) => f.endsWith('.pdf') && !isFake(join(out, f)))) {
    throw new Error(`${out} holds PDFs this script did not write; remove them yourself`);
  }
  rmSync(out, { recursive: true, force: true });
  const sources = join(courseDir, 'sources');
  const yaml = join(sources, 'manifest.yaml');
  if (has(yaml) && readFileSync(yaml, 'utf8') === sourcesYaml()) rmSync(yaml);
  for (const s of SOURCES) {
    const path = join(sources, 'raw', s.file);
    if (isFake(path)) rmSync(path);
    removeEmptyDirs(dirname(path), courseDir);
  }
}

function main(argv) {
  const flag = (name) => argv.includes(`--${name}`);
  const omitAt = argv.indexOf('--omit');
  const omit = omitAt >= 0 ? (argv[omitAt + 1] ?? '').split(',').filter(Boolean) : [];
  const course = argv.find((a, i) => !a.startsWith('--') && !(omitAt >= 0 && i === omitAt + 1)) ?? 'sample-course';
  const coursesDir = resolve(REPO, process.env.STUDYKIT_COURSES_DIR ?? 'examples');
  if (coursesDir === resolve(REPO, 'courses')) {
    throw new Error('fake PDFs go to examples/ (or another test directory), never to courses/');
  }
  const courseDir = join(coursesDir, course);
  if (!has(join(courseDir, 'course.yaml'))) throw new Error(`no course at ${courseDir}`);
  if (flag('clean')) {
    cleanFakePdfs(courseDir);
    console.log(`fake-pdfs: removed from ${courseDir}`);
    return;
  }
  const manifest = writeFakePdfs(courseDir, { sources: flag('sources'), omit, force: flag('force') });
  const list = manifest.docs.map((d) => `${d.file} (${d.pages} p.)`).join(', ');
  console.log(`fake-pdfs: ${courseDir}/_build/pdf: ${list}${flag('sources') ? '; sources/raw: vl-01, ue-01' : ''}`);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    main(process.argv.slice(2));
  } catch (e) {
    console.error(`fake-pdfs: ${e.message}`);
    process.exit(1);
  }
}
