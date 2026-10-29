// The PDF routes' data (src/lib/pdf.ts): the built-PDF manifest (schema studykit-pdf/1),
// the source manifest, the labels, and reading both from a course directory on disk.
// The PDFs here are small stand-ins (make-pdf.mjs); e2e/pdf.spec.ts checks the real ones.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import {
  densityPt,
  expectedPdfFiles,
  findPdf,
  firstPage,
  formatBytes,
  parsePdfManifest,
  parseSourceManifest,
  pdfFile,
  pdfHref,
  pdfMeta,
  pdfResponse,
  PDF_SCHEMA,
  readPdfs,
  readSources,
  sourceFile,
  sourceHref,
} from '../../src/lib/pdf.ts';
import { makePdf, PRODUCER } from './make-pdf.mjs';

const sizes: Record<string, number> = {
  'overview.pdf': 81234,
  'summary.pdf': 120_400,
  'probeklausur-1.pdf': 52_000,
  'probeklausur-1-solutions.pdf': 61_000,
  'cheatsheet.pdf': 70_000,
};
const sizeOf = (file: string) => sizes[file] ?? null;

const manifest = (docs: unknown[], extra: Record<string, unknown> = {}) => ({
  schema: PDF_SCHEMA,
  course: 'get2',
  docs,
  ...extra,
});

test('the manifest contract: every listed document whose file exists', () => {
  const { docs, problems } = parsePdfManifest(
    manifest([
      { id: 'overview', kind: 'overview', file: 'overview.pdf', title: 'Überblick', pages: 3, bytes: 81234 },
      { id: 'summary', kind: 'summary', file: 'summary.pdf', title: 'Zusammenfassung', pages: 24, bytes: 120_400 },
      {
        id: 'probeklausur-1',
        kind: 'exam',
        file: 'probeklausur-1.pdf',
        title: 'Probeklausur 1',
        pages: 6,
        bytes: 52_000,
        exam: 'probeklausur-1',
      },
      {
        id: 'probeklausur-1-solutions',
        kind: 'exam-solutions',
        file: 'probeklausur-1-solutions.pdf',
        title: 'Probeklausur 1: Lösungen',
        pages: 8,
        bytes: 61_000,
        exam: 'probeklausur-1',
      },
      {
        id: 'cheatsheet',
        kind: 'cheatsheet',
        file: 'cheatsheet.pdf',
        title: 'Formelblatt',
        pages: 2,
        bytes: 70_000,
        max_pages: 2,
        density: 1,
      },
    ]),
    'get2',
    sizeOf,
  );
  assert.deepEqual(problems, []);
  assert.deepEqual(
    docs.map((d) => [d.id, d.kind, d.file, d.pages, d.bytes, d.exam, d.maxPages, d.density]),
    [
      ['overview', 'overview', 'overview.pdf', 3, 81234, null, null, null],
      ['summary', 'summary', 'summary.pdf', 24, 120_400, null, null, null],
      ['probeklausur-1', 'exam', 'probeklausur-1.pdf', 6, 52_000, 'probeklausur-1', null, null],
      ['probeklausur-1-solutions', 'exam-solutions', 'probeklausur-1-solutions.pdf', 8, 61_000, 'probeklausur-1', null, null],
      ['cheatsheet', 'cheatsheet', 'cheatsheet.pdf', 2, 70_000, null, 2, 1],
    ],
  );
  assert.equal(findPdf(docs, 'exam', 'probeklausur-1')?.file, 'probeklausur-1.pdf');
  assert.equal(findPdf(docs, 'exam-solutions', 'probeklausur-1')?.pages, 8);
  assert.equal(findPdf(docs, 'exam', 'probeklausur-2'), null);
});

test('a missing, other-schema or other-course manifest yields no documents', () => {
  for (const raw of [null, [], 'x', manifest([], { schema: 'studykit-pdf/2' }), manifest([], { course: 'other' })]) {
    const { docs, problems } = parsePdfManifest(raw, 'get2', sizeOf);
    assert.deepEqual(docs, []);
    assert.equal(problems.length, 1, JSON.stringify(raw));
  }
  assert.equal(parsePdfManifest(manifest([], { docs: {} }), 'get2', sizeOf).docs.length, 0);
});

test('entries that cannot be served are left out, with a reason', () => {
  const entry = (over: Record<string, unknown>) => ({
    id: 'summary',
    kind: 'summary',
    file: 'summary.pdf',
    title: 'Zusammenfassung',
    pages: 24,
    bytes: 120_400,
    ...over,
  });
  const bad = [
    entry({ kind: 'slides' }), // unknown kind
    entry({ file: '../summary.pdf' }), // not a plain name
    entry({ file: 'sub/summary.pdf' }),
    entry({ file: 'summary.html' }),
    entry({ pages: 0 }),
    entry({ pages: 2.5 }),
    entry({ id: 'plan', kind: 'plan', file: 'plan.pdf' }), // file missing on disk
    entry({ id: 'probeklausur-1', kind: 'exam', file: 'probeklausur-1.pdf' }), // no exam id
    entry({ id: '' }),
    'summary.pdf',
  ];
  const { docs, problems } = parsePdfManifest(manifest(bad), 'get2', sizeOf);
  assert.deepEqual(docs, []);
  assert.equal(problems.length, bad.length);
});

test('duplicates keep the first; bytes and title fall back; a size mismatch is reported', () => {
  const { docs, problems } = parsePdfManifest(
    manifest([
      { id: 'summary', kind: 'summary', file: 'summary.pdf', pages: 24 },
      { id: 'summary', kind: 'summary', file: 'summary.pdf', pages: 25 },
      { id: 'overview', kind: 'overview', file: 'overview.pdf', title: ' ', pages: 3, bytes: 99 },
      { id: 'cheatsheet', kind: 'cheatsheet', file: 'cheatsheet.pdf', pages: 2, max_pages: 0, density: 7 },
    ]),
    'get2',
    sizeOf,
  );
  assert.deepEqual(
    docs.map((d) => [d.id, d.title, d.pages, d.bytes, d.maxPages, d.density]),
    [
      ['summary', 'summary', 24, 120_400, null, null],
      ['overview', 'overview', 3, 99, null, null],
      ['cheatsheet', 'cheatsheet', 2, 70_000, null, null],
    ],
  );
  assert.equal(problems.length, 2); // the duplicate and the size mismatch
});

test('source manifest: list or mapping, file defaults to <id>.pdf inside sources/raw', () => {
  const files = new Set(['vl-01.pdf', 'uebungen/ue-01.pdf', 'Skript.PDF']);
  const size = (f: string) => (files.has(f) ? 1000 : null);
  const list = parseSourceManifest(
    {
      schema: 1,
      documents: [
        { id: 'vl-01', title: 'Vorlesung 1', pages: 20 },
        { id: 'ue-01', title: 'Übung 1', pages: 4, file: 'uebungen/ue-01.pdf' },
        { id: 'skript', file: 'raw/Skript.PDF' },
        { id: 'vl-02', title: 'Vorlesung 2', pages: 24 }, // not copied yet: no route
        { id: 'evil', file: '../course.yaml' },
        { id: 'evil-2', file: 'sub/../../x.pdf' },
        { id: 'evil-3', file: '/etc/x.pdf' },
        { id: 'Not_Kebab' },
        { title: 'no id' },
      ],
    },
    size,
  );
  assert.deepEqual(list.docs, [
    { id: 'vl-01', title: 'Vorlesung 1', pages: 20, file: 'vl-01.pdf' },
    { id: 'ue-01', title: 'Übung 1', pages: 4, file: 'uebungen/ue-01.pdf' },
    { id: 'skript', title: 'skript', pages: null, file: 'Skript.PDF' },
  ]);
  assert.equal(list.problems.length, 4);

  const mapping = parseSourceManifest({ docs: { 'vl-01': { title: 'Vorlesung 1', pages: 20 } } }, size);
  assert.deepEqual(mapping.docs, [{ id: 'vl-01', title: 'Vorlesung 1', pages: 20, file: 'vl-01.pdf' }]);
  assert.deepEqual(parseSourceManifest(null, size), { docs: [], problems: [] });
  assert.equal(parseSourceManifest({ documents: 'x' }, size).docs.length, 0);
});

test('labels: sizes in SI units, page counts, cheat-sheet density in pt', () => {
  assert.equal(formatBytes(0), '0 B');
  assert.equal(formatBytes(999), '999 B');
  assert.equal(formatBytes(1000), '1 kB');
  assert.equal(formatBytes(120_400), '120 kB');
  assert.equal(formatBytes(999_499), '999 kB');
  assert.equal(formatBytes(999_500), '1.0 MB');
  assert.equal(formatBytes(1_234_567), '1.2 MB');
  assert.equal(formatBytes(9_949_999), '9.9 MB');
  assert.equal(formatBytes(23_456_789), '23 MB');
  assert.equal(pdfMeta({ pages: 4, bytes: 120_400 }), '4 pages · 120 kB');
  assert.equal(pdfMeta({ pages: 1, bytes: 812 }), '1 page · 812 B');
  assert.equal(pdfMeta({ pages: 2, bytes: 81_234 }, false), '81 kB');
  assert.deepEqual([0, 1, 2, 3, 4].map(densityPt), [9, 8.5, 8, 7.5, 7]);
  assert.equal(densityPt(null), null);
  assert.equal(densityPt(5), null);
});

test('routes, source pages and the files dev may serve', () => {
  assert.equal(pdfHref('get2', 'summary.pdf'), '/c/get2/pdf/summary.pdf');
  assert.equal(sourceHref('get2', 'vl-05'), '/c/get2/src/vl-05.pdf');
  assert.equal(sourceHref('get2', 'vl-05', 3), '/c/get2/src/vl-05.pdf#page=3');
  assert.deepEqual([7, '3-7', '12', null, undefined, 0, 'x'].map(firstPage), [7, 3, 12, null, null, null, null]);
  assert.deepEqual(expectedPdfFiles(['probeklausur-1']), [
    'overview.pdf',
    'summary.pdf',
    'exercises.pdf',
    'exercises-blank.pdf',
    'mc.pdf',
    'probeklausur-1.pdf',
    'probeklausur-1-solutions.pdf',
    'cheatsheet.pdf',
    'plan.pdf',
  ]);
});

/** Each xref offset points at its object, and the trailer's startxref at the table. */
function assertWellFormed(pdf: Buffer, pages: number): void {
  const text = pdf.toString('latin1');
  assert.ok(text.startsWith('%PDF-1.7\n'));
  assert.ok(text.endsWith('%%EOF\n'));
  const startxref = Number(/startxref\n(\d+)\n%%EOF\n$/.exec(text)?.[1]);
  assert.ok(text.slice(startxref).startsWith('xref\n'));
  const offsets = [...text.slice(startxref).matchAll(/^(\d{10}) 00000 n $/gm)].map((m) => Number(m[1]));
  offsets.forEach((offset, i) => assert.ok(text.slice(offset).startsWith(`${i + 1} 0 obj\n`), `object ${i + 1}`));
  assert.equal(text.match(/\/Type \/Page /g)?.length, pages);
  assert.ok(text.includes(`/Count ${pages} `));
  for (const m of text.matchAll(/<< \/Length (\d+) >>\nstream\n/g)) {
    const start = (m.index ?? 0) + m[0].length;
    assert.ok(text.slice(start + Number(m[1])).startsWith('\nendstream'));
  }
}

test('test PDFs are well-formed, deterministic and carry their producer', () => {
  const pdf = makePdf([['Probeklausur 1', 'Seite 1 von 2'], ['Lösungen (Teil 2)', 'Seite 2 von 2']], 'Lösungen');
  assertWellFormed(pdf, 2);
  assert.ok(pdf.includes(PRODUCER));
  assert.ok(pdf.includes(Buffer.from('(L\xf6sungen \\(Teil 2\\)) Tj', 'latin1')));
  assert.deepEqual(makePdf([['a']], 't'), makePdf([['a']], 't'));
});

/** A throwaway course directory with course.yaml and the given files. */
function tempCourse(files: Record<string, string>): { root: string; course: string } {
  const root = mkdtempSync(join(tmpdir(), 'sk-pdf-'));
  const course = join(root, 'get2');
  for (const [rel, text] of Object.entries({
    'course.yaml': 'id: get2\ntitle: GET 2\n',
    ...files,
  })) {
    mkdirSync(join(course, rel, '..'), { recursive: true });
    writeFileSync(join(course, rel), text);
  }
  return { root, course };
}

/** Write `pages` test pages to `path` (inside `course`), returning the size in bytes. */
function writePdf(course: string, path: string, pages: number, title: string): number {
  const bytes = makePdf(
    Array.from({ length: pages }, (_, i) => [title, `Seite ${i + 1} von ${pages}`]),
    title,
  );
  mkdirSync(join(course, path, '..'), { recursive: true });
  writeFileSync(join(course, path), bytes);
  return bytes.length;
}

test('reading a course: built PDFs and sources are served, absent ones are not', (t) => {
  const { root, course } = tempCourse({});
  const before = process.env.STUDYKIT_COURSES_DIR;
  process.env.STUDYKIT_COURSES_DIR = root;
  t.after(() => {
    if (before === undefined) delete process.env.STUDYKIT_COURSES_DIR;
    else process.env.STUDYKIT_COURSES_DIR = before;
    rmSync(root, { recursive: true, force: true });
  });

  // a course without _build/pdf/ and sources/: nothing to serve, so no route and no link
  assert.deepEqual(readPdfs('get2'), []);
  assert.deepEqual(readSources('get2'), []);
  assert.equal(pdfFile('get2', 'summary.pdf'), null);
  assert.equal(sourceFile('get2', 'vl-01'), null);

  const built = [
    { id: 'summary', kind: 'summary', file: 'summary.pdf', title: 'Zusammenfassung', pages: 9 },
    { id: 'pk-1', kind: 'exam', file: 'pk-1.pdf', title: 'Probeklausur 1', pages: 6, exam: 'pk-1' },
    {
      id: 'cheatsheet',
      kind: 'cheatsheet',
      file: 'cheatsheet.pdf',
      title: 'Formelblatt',
      pages: 2,
      max_pages: 2,
      density: 1,
    },
  ].map((d) => ({ ...d, bytes: writePdf(course, join('_build', 'pdf', d.file), d.pages, d.title) }));
  writeFileSync(join(course, '_build', 'pdf', 'manifest.json'), JSON.stringify(manifest(built)));
  writePdf(course, 'sources/raw/vl-01.pdf', 5, 'Vorlesung 1');
  writePdf(course, 'sources/raw/uebungen/ue-01.pdf', 3, 'Übung 1');
  writeFileSync(
    join(course, 'sources', 'manifest.yaml'),
    "documents:\n  - {id: vl-01, title: 'Vorlesung 1', pages: 5}\n" +
      "  - {id: ue-01, title: 'Übung 1', pages: 3, file: uebungen/ue-01.pdf}\n",
  );

  const docs = readPdfs('get2');
  assert.deepEqual(docs.map((d) => [d.kind, d.file, d.pages]), [
    ['summary', 'summary.pdf', 9],
    ['exam', 'pk-1.pdf', 6],
    ['cheatsheet', 'cheatsheet.pdf', 2],
  ]);
  assert.equal(findPdf(docs, 'cheatsheet')?.maxPages, 2);
  assert.equal(findPdf(docs, 'plan'), null); // not built
  for (const d of docs) {
    const bytes = readFileSync(join(course, '_build', 'pdf', d.file));
    assert.equal(d.bytes, bytes.length);
    assertWellFormed(bytes, d.pages);
  }
  assert.equal(pdfFile('get2', 'summary.pdf'), join(course, '_build', 'pdf', 'summary.pdf'));
  assert.equal(pdfFile('get2', 'pk-1-solutions.pdf'), null);
  assert.equal(pdfFile('get2', 'manifest.json'), null);
  assert.deepEqual(readSources('get2').map((s) => [s.id, s.file, s.pages]), [
    ['vl-01', 'vl-01.pdf', 5],
    ['ue-01', 'uebungen/ue-01.pdf', 3],
  ]);
  assert.equal(sourceFile('get2', 'ue-01'), join(course, 'sources', 'raw', 'uebungen', 'ue-01.pdf'));
  assert.equal(sourceFile('get2', 'vl-02'), null);
});

test('a route answers with the file, byte for byte; a missing file is a 404 in dev only', async (t) => {
  const { root, course } = tempCourse({});
  t.after(() => rmSync(root, { recursive: true, force: true }));
  const path = join(course, 'x.pdf');
  const pdf = makePdf([['x']], 'x');
  writeFileSync(path, pdf);
  const res = pdfResponse(path, 'x.pdf', false);
  assert.equal(res.status, 200);
  assert.equal(res.headers.get('content-type'), 'application/pdf');
  assert.deepEqual(Buffer.from(await res.arrayBuffer()), pdf);
  assert.equal(pdfResponse(null, 'x.pdf', true).status, 404);
  assert.equal(pdfResponse(join(course, 'gone.pdf'), 'gone.pdf', true).status, 404);
  assert.throws(() => pdfResponse(null, 'x.pdf', false), /x\.pdf is missing/);
});
