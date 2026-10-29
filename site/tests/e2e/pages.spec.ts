// Every built page of the sample course loads its scripts and assets without errors.
import { readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { expect, test } from '@playwright/test';
import { elementsReady, freezeDay } from './helpers.ts';

const DIST = fileURLToPath(new URL('../../dist/', import.meta.url));

/** Site paths of the built pages: dist/a/b/index.html → /a/b/ */
const pages = readdirSync(DIST, { recursive: true, encoding: 'utf8' })
  .filter((f) => f.endsWith('.html') && !f.startsWith('pagefind'))
  .map((f) => `/${f.replace(/(^|\/)index\.html$/, '$1')}`)
  .sort();

test('the build has the pages of the sample course; unknown paths get the 404 page', async ({ page }) => {
  expect(pages).toContain('/c/sample-course/');
  expect(pages).toContain('/c/sample-course/exams/probeklausur-1/');
  expect(pages.length).toBeGreaterThan(20);
  const res = await page.goto('/c/sample-course/no-such-page/');
  expect(res?.status()).toBe(404);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Page not found');
});

for (const path of pages) {
  test(`${path} loads without errors`, async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`));
    page.on('console', (m) => {
      if (m.type() === 'error') errors.push(`console: ${m.text()}`);
    });
    page.on('requestfailed', (r) => errors.push(`failed: ${r.url()} ${r.failure()?.errorText ?? ''}`));
    page.on('response', (r) => {
      if (r.status() >= 400 && r.url() !== page.url()) errors.push(`${r.status()}: ${r.url()}`);
    });
    await freezeDay(page);
    const res = await page.goto(path, { waitUntil: 'load' });
    expect(res?.status()).toBe(200);
    await elementsReady(page);
    await page.waitForLoadState('networkidle');
    expect(errors).toEqual([]);
  });
}
