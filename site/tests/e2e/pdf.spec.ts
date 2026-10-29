// Built PDFs and source documents (docs/architecture.md §3.2, §3.3): the routes serve
// _build/pdf/ and sources/raw/ byte for byte, and each page links exactly the documents that
// _build/pdf/manifest.json lists, with their page count and size. The suite checks whatever
// the build had: the pipeline's PDFs, the fake ones of tests/fake-pdfs.mjs, or none at all,
// in which case no page shows a trace of them.
import { createHash } from 'node:crypto';
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test, type Locator, type Page } from '@playwright/test';
import { formatBytes } from '../../src/lib/pdf.ts';
import { C, COURSE, elementsReady, freezeDay } from './helpers.ts';

interface Doc {
  id: string;
  kind: string;
  file: string;
  title: string;
  pages: number;
  bytes: number;
  exam?: string;
  max_pages?: number;
  density?: number;
}

const SITE = fileURLToPath(new URL('../../', import.meta.url));
const DIST = join(SITE, 'dist');
// The sample course the build read: in STUDYKIT_COURSES_DIR, else in examples/ (`just e2e`
// exports the variable, by default as courses/, which holds no sample course).
const COURSE_DIR =
  [process.env.STUDYKIT_COURSES_DIR, 'examples']
    .filter((dir): dir is string => Boolean(dir))
    .map((dir) => join(resolve(SITE, '..', dir), COURSE))
    .find((dir) => existsSync(join(dir, 'course.yaml'))) ?? join(SITE, '..', 'examples', COURSE);
const ls = (dir: string) => (existsSync(dir) ? readdirSync(dir, { recursive: true, encoding: 'utf8' }).sort() : []);
const sha = (bytes: Buffer) => createHash('sha256').update(bytes).digest('hex');

const builtPdfs = ls(join(DIST, 'c', COURSE, 'pdf'));
const builtSources = ls(join(DIST, 'c', COURSE, 'src'));
const manifestPath = join(COURSE_DIR, '_build', 'pdf', 'manifest.json');
if (builtPdfs.length && !existsSync(manifestPath)) {
  throw new Error(`site/dist has PDFs of ${COURSE}, but ${manifestPath} is gone: rebuild the site`);
}
const docs: Doc[] = builtPdfs.length ? JSON.parse(readFileSync(manifestPath, 'utf8')).docs : [];
const doc = (kind: string, exam?: string) => docs.find((d) => d.kind === kind && (!exam || d.exam === exam));
const EXAM = 'probeklausur-1';

/** Every page of the course that may link a PDF: path, kind, label (exam for exam kinds). */
const LINKS: Array<[string, string, string, string?]> = [
  [`${C}/`, 'overview', 'PDF'],
  [`${C}/summary/`, 'summary', 'PDF'],
  [`${C}/summary/spannungsteiler/`, 'summary', 'Summary PDF'],
  [`${C}/summary/rc-filter/`, 'summary', 'Summary PDF'],
  [`${C}/exercises/`, 'exercises', 'PDF with solutions'],
  [`${C}/exercises/`, 'exercises-blank', 'PDF without solutions'],
  [`${C}/mc/`, 'mc', 'PDF with answer key'],
  [`${C}/exams/`, 'exam', 'Exam PDF', EXAM],
  [`${C}/exams/${EXAM}/`, 'exam', 'Exam PDF', EXAM],
  [`${C}/cheatsheet/`, 'cheatsheet', 'PDF'],
  [`${C}/plan/`, 'plan', 'PDF'],
];

/** "PDF · 4 pages · 120 kB" (the cheat sheet shows its pages in the badge instead). */
function label(d: Doc, name: string): string {
  const pages = d.kind === 'cheatsheet' ? '' : ` · ${d.pages} ${d.pages === 1 ? 'page' : 'pages'}`;
  return `${name}${pages} · ${formatBytes(d.bytes)}`;
}

async function expectLink(link: Locator, d: Doc, name: string): Promise<void> {
  await expect(link).toHaveText(label(d, name));
  await expect(link).toHaveAttribute('href', `${C}/pdf/${d.file}`);
  await expect(link).toHaveAttribute('download', `${COURSE}-${d.file}`);
  await expect(link).toHaveAttribute('type', 'application/pdf');
}

async function open(page: Page, path: string): Promise<void> {
  await freezeDay(page);
  await page.goto(path);
  await elementsReady(page);
}

test.describe('with built PDFs', () => {
  test.skip(builtPdfs.length === 0, 'the build has no PDFs (tests/fake-pdfs.mjs makes some)');

  test('the build has exactly the PDFs of the manifest, byte for byte, served inline', async ({ request }) => {
    expect(builtPdfs).toEqual(docs.map((d) => d.file).sort());
    for (const d of docs) {
      const source = readFileSync(join(COURSE_DIR, '_build', 'pdf', d.file));
      expect(d.bytes).toBe(source.length);
      const res = await request.get(`${C}/pdf/${d.file}`);
      expect(res.status(), d.file).toBe(200);
      expect(res.headers()['content-type']).toMatch(/^application\/pdf/);
      expect(res.headers()['content-disposition'] ?? '').not.toMatch(/attachment/);
      expect(sha(await res.body()), d.file).toBe(sha(source));
    }
    expect((await request.get(`${C}/pdf/manifest.json`)).status()).toBe(404);
  });

  for (const [path, kind, name, exam] of LINKS) {
    test(`${path} links the ${kind} PDF when it is built`, async ({ page }) => {
      await open(page, path);
      const links = page.locator(`a.pdf-link[data-sk-pdf="${kind}"]`);
      const d = doc(kind, exam);
      if (!d) {
        await expect(links).toHaveCount(0);
        return;
      }
      await expect(links).toHaveCount(1);
      await expect(links).toBeVisible();
      await expectLink(links, d, name);
      // English UI text, kept out of the search index
      await expect(links.locator('xpath=ancestor-or-self::*[@lang][1]')).toHaveAttribute('lang', 'en');
      await expect(links).toHaveAttribute('data-pagefind-ignore', '');
    });
  }

  test('pages without a PDF of their own link none', async ({ page }) => {
    for (const path of [`${C}/progress/`, `${C}/exercises/ex-rc-tp-grenzfrequenz/`, `${C}/mc/rc-filter/`, '/']) {
      await open(page, path);
      await expect(page.locator('a.pdf-link')).toHaveCount(0);
    }
  });

  test('exam solutions: behind a label on the index, on the exam page only after submitting', async ({ page }) => {
    const d = doc('exam-solutions', EXAM);
    test.skip(!d, 'no solutions PDF built');
    if (!d) return;
    await open(page, `${C}/exams/`);
    const spoiler = page.locator('details.pdf-spoiler');
    const hidden = spoiler.locator('a.pdf-link[data-sk-pdf="exam-solutions"]');
    await expect(hidden).toBeHidden();
    await spoiler.getByText('Solutions PDF, for after the exam').click();
    await expect(hidden).toBeVisible();
    await expectLink(hidden, d, 'Solutions PDF');

    page.on('dialog', (dialog) => void dialog.accept());
    await open(page, `${C}/exams/${EXAM}/`);
    const exam = page.locator('sk-exam');
    const link = page.locator('a.pdf-link[data-sk-pdf="exam-solutions"]');
    await expect(link).toHaveCount(1);
    await expect(link).toBeHidden();
    await exam.getByRole('button', { name: 'Start exam' }).click();
    await expect(page.locator('.sk-exam-clock')).toBeVisible();
    await expect(link).toBeHidden();
    await exam.getByRole('button', { name: 'Submit' }).click();
    await page.getByRole('dialog').getByRole('button', { name: 'Submit now' }).click();
    await expect(exam.getByRole('heading', { name: 'Result' })).toBeVisible();
    await expect(link).toBeVisible();
    await expectLink(link, d, 'Solutions PDF');
  });

  test('the cheat sheet badge shows the page count against the limit from the manifest', async ({ page }) => {
    const d = doc('cheatsheet');
    test.skip(!d, 'no cheat-sheet PDF built');
    if (!d) return;
    await open(page, `${C}/cheatsheet/`);
    const badge = page.locator('[data-sk-pdf-pages]');
    const max = d.max_pages ?? 2;
    await expect(badge).toHaveText(`${d.pages} / ${max} ${max === 1 ? 'page' : 'pages'}${d.pages > max ? ' · over the limit' : ''}`);
    await expect(badge).toHaveAttribute('data-pages', String(d.pages));
    await expect(badge).toHaveAttribute('data-max', String(max));
    await expect(page.getByText('PDF not built yet')).toHaveCount(0);
  });

  test('a download is the PDF itself, named after the course', async ({ page }) => {
    const d = doc('summary') ?? docs[0];
    test.skip(!d, 'no PDF built');
    if (!d) return;
    await open(page, `${C}/summary/`);
    const link = page.locator('a.pdf-link').first();
    const download = page.waitForEvent('download');
    await link.click();
    const file = await download;
    const want = (await link.getAttribute('download')) ?? '';
    expect(file.suggestedFilename()).toBe(want);
    const kind = await link.getAttribute('data-sk-pdf');
    const source = readFileSync(join(COURSE_DIR, '_build', 'pdf', docs.find((x) => x.kind === kind)?.file ?? ''));
    expect(sha(readFileSync((await file.path()) ?? ''))).toBe(sha(source));
  });

  test('printing a page leaves its PDF links out', async ({ page }) => {
    await open(page, `${C}/exercises/`);
    const links = page.locator('a.pdf-link');
    test.skip((await links.count()) === 0, 'no exercise PDFs built');
    await expect(links.first()).toBeVisible();
    await page.emulateMedia({ media: 'print' });
    for (const link of await links.all()) await expect(link).toBeHidden();
    await page.emulateMedia({ media: 'screen' });
  });
});

test.describe('without built PDFs', () => {
  test.skip(builtPdfs.length > 0, 'the build has PDFs');

  test('no page links a PDF, and there are no PDF routes', async ({ page, request }) => {
    const html = ls(DIST).filter((f) => f.endsWith('.html') && !f.startsWith('pagefind'));
    expect(html.length).toBeGreaterThan(20);
    for (const f of html) {
      const text = readFileSync(join(DIST, f), 'utf8');
      expect(text, f).not.toContain('pdf-link');
      expect(text, f).not.toContain(`${C}/pdf/`);
      expect(text, f).not.toContain('data-sk-exam-solutions');
    }
    expect((await request.get(`${C}/pdf/summary.pdf`)).status()).toBe(404);
    await open(page, `${C}/cheatsheet/`);
    await expect(page.locator('[data-sk-pdf-pages]')).toHaveText('PDF not built yet · limit 2 pages');
    await open(page, `${C}/exams/`);
    await expect(page.locator('.exam-pdfs')).toHaveCount(0);
  });
});

test('source documents are served byte for byte as listed in sources/manifest.yaml', async ({ request }) => {
  test.skip(builtSources.length === 0, 'the course has no source documents (tests/fake-pdfs.mjs --sources adds two)');
  const yaml = readFileSync(join(COURSE_DIR, 'sources', 'manifest.yaml'), 'utf8');
  for (const name of builtSources) {
    const id = name.replace(/\.pdf$/, '');
    // the entry's file inside sources/raw/ (`file:`), else <id>.pdf
    const entry = new RegExp(`id: ${id}\\b[^}\\n]*`).exec(yaml)?.[0] ?? '';
    const file = /file: ([^,}\s]+)/.exec(entry)?.[1] ?? `${id}.pdf`;
    const res = await request.get(`${C}/src/${name}`);
    expect(res.status(), name).toBe(200);
    // inline, so the browser's PDF viewer opens it and honours #page=<n>
    expect(res.headers()['content-type']).toMatch(/^application\/pdf/);
    expect(res.headers()['content-disposition'] ?? '').not.toMatch(/attachment/);
    expect(sha(await res.body()), name).toBe(sha(readFileSync(join(COURSE_DIR, 'sources', 'raw', file))));
  }
});

test('search never finds the text of a PDF', async ({ page }) => {
  await page.goto('/search/');
  const found = await page.evaluate(async () => {
    const pagefind = await import(/* @vite-ignore */ '/pagefind/pagefind.js');
    await pagefind.init?.();
    const urls: string[] = [];
    // a word only the fake PDFs hold, and words every course PDF has on its pages
    for (const term of ['Platzhalterdokument', 'Seite', 'Probeklausur']) {
      const search = await pagefind.search(term);
      for (const r of search.results) urls.push((await r.data()).url as string);
    }
    return urls;
  });
  expect(found.length).toBeGreaterThan(0); // "Probeklausur" is on the exam page
  expect(found.filter((u) => /\.pdf(?:$|[?#])/i.test(u))).toEqual([]);
  expect(found.filter((u) => u.includes('/pdf/') || u.includes('/src/'))).toEqual([]);
});
