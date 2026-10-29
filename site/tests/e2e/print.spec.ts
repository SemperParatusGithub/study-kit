// Printing a page (styles/print.css, scripts/site.ts): content prints, interactive leftovers
// do not.
import { expect, test, type Page } from '@playwright/test';
import { C, elementsReady, freezeDay, progress } from './helpers.ts';

async function print(page: Page): Promise<void> {
  await page.emulateMedia({ media: 'print' });
  await page.evaluate(() => window.dispatchEvent(new Event('beforeprint')));
}

async function unprint(page: Page): Promise<void> {
  await page.evaluate(() => window.dispatchEvent(new Event('afterprint')));
  await page.emulateMedia({ media: 'screen' });
}

test.beforeEach(async ({ page }) => {
  await freezeDay(page);
});

test('an exercise prints its hints and solution; printing does not count as using hints', async ({ page }) => {
  await page.goto(`${C}/exercises/ex-rc-tp-grenzfrequenz/`);
  await elementsReady(page);
  const hints = page.locator('details.sk-hint');
  await expect(hints).toHaveCount(2);
  await expect(hints.first()).toBeHidden();
  await print(page);
  for (const hint of await hints.all()) {
    await expect(hint).toBeVisible();
    await expect(hint).toHaveAttribute('open');
  }
  await expect(page.locator('details.sk-solution')).toBeVisible();
  await unprint(page);
  await expect(hints.first()).toBeHidden();
  await expect(page.getByRole('button', { name: 'Show hint 1 of 2' })).toBeVisible();
  expect((await progress(page))?.items?.['ex:ex-rc-tp-grenzfrequenz']?.hints ?? 0).toBe(0);
});
