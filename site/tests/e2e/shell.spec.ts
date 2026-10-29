// The site shell: the theme toggle persists without a flash of the wrong theme, and search
// finds German course content (docs/architecture.md §3.2, §3.5).
import { expect, test } from '@playwright/test';
import { C, elementsReady } from './helpers.ts';

const bodyBackground = () => getComputedStyle(document.body).backgroundColor;

test('the theme choice persists across a reload and applies before any module script runs', async ({ page }) => {
  await page.goto(`${C}/`);
  await elementsReady(page);
  const html = page.locator('html');
  const theme = page.locator('sk-theme');
  await expect(html).toHaveAttribute('data-theme', 'system');
  await expect(theme.getByRole('radio', { name: 'System' })).toBeChecked();
  const light = await page.evaluate(bodyBackground); // the browser prefers light

  await theme.getByRole('radio', { name: 'Dark' }).check();
  await expect(html).toHaveAttribute('data-theme', 'dark');
  expect(await page.evaluate(() => localStorage.getItem('studykit:theme'))).toBe('dark');
  const dark = await page.evaluate(bodyBackground);
  expect(dark).not.toBe(light);

  // Hold back every module script on the reload: what the page shows then comes from the
  // inline head script and the stylesheets alone, i.e. the first paint.
  let release: () => void = () => {};
  const held = new Promise<void>((resolve) => (release = resolve));
  await page.route('**/_astro/*.js', async (route) => {
    await held;
    await route.continue();
  });
  await page.reload({ waitUntil: 'commit' });
  await page.waitForFunction(() => document.body !== null, undefined, { polling: 50 });
  await expect(html).toHaveAttribute('data-theme', 'dark');
  await expect.poll(() => page.evaluate(bodyBackground)).toBe(dark);
  const early = await page.evaluate(() => ({
    readyState: document.readyState,
    upgraded: customElements.get('sk-theme') !== undefined,
  }));
  expect(early.upgraded).toBe(false);
  expect(early.readyState).not.toBe('complete');

  release();
  await page.waitForLoadState('load');
  await elementsReady(page);
  await expect(theme.getByRole('radio', { name: 'Dark' })).toBeChecked();
  await page.unroute('**/_astro/*.js');

  // back to the system theme: the stored choice follows
  await theme.getByRole('radio', { name: 'System' }).check();
  await page.reload();
  await expect(html).toHaveAttribute('data-theme', 'system');
  expect(await page.evaluate(bodyBackground)).toBe(light);
});

test('search finds a German term of the sample course', async ({ page }) => {
  await page.goto(`${C}/`);
  await elementsReady(page);
  // "/" focuses the header search box; Enter opens the search page with the query
  await page.keyboard.press('/');
  const box = page.getByRole('searchbox', { name: 'Search course content' });
  await expect(box).toBeFocused();
  await box.fill('Spannungsteiler');
  await box.press('Enter');
  await expect(page).toHaveURL(/\/search\/?\?q=Spannungsteiler$/);
  const results = page.locator('pagefind-results');
  const summary = results.getByRole('link').filter({ hasText: 'Spannungsteiler' });
  await expect(summary.first()).toBeVisible({ timeout: 10_000 });
  const hrefs = await results.getByRole('link').evaluateAll((links) => links.map((a) => a.getAttribute('href')));
  expect(hrefs.length).toBeGreaterThan(0);
  expect(hrefs.every((h) => h?.startsWith(`${C}/`))).toBe(true);
  expect(hrefs).toContain(`${C}/summary/spannungsteiler/`);
});

test('search never shows hints, which a running mock exam keeps locked', async ({ page }) => {
  await page.goto('/search/');
  // words of the sample course's hints; a hint's own label reads "Hinweis 1", "Hinweis 2"
  const found = await page.evaluate(async () => {
    const pagefind = await import(/* @vite-ignore */ '/pagefind/pagefind.js');
    await pagefind.init?.();
    const out: string[] = [];
    for (const q of ['Hinweis', 'Lösen', 'Fassen', 'Grenzfrequenz', 'entspricht dem Betrag']) {
      const r = await pagefind.search(q);
      for (const result of r.results as Array<{ data: () => Promise<{ url: string; excerpt: string }> }>) {
        const d = await result.data();
        if (/Hinweis \d/.test(d.excerpt.replace(/<[^>]+>/g, ''))) out.push(`${q}: ${d.url}`);
      }
    }
    return out;
  });
  expect(found).toEqual([]);
});

test('a malformed #fragment breaks none of the shell scripts', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(`${C}/summary/rc-filter/#%E0%A4%A`);
  await elementsReady(page);
  // the scripts after the hash handling still run: printing opens every <details>
  await page.evaluate(() => window.dispatchEvent(new Event('beforeprint')));
  expect(await page.locator('details:not([open])').count()).toBe(0);
  expect(errors).toEqual([]);
});
