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

test('summary, MC topic and exam pages print without their quizzes and buttons', async ({ page }) => {
  page.on('dialog', (d) => void d.accept());
  await page.goto(`${C}/summary/rc-filter/`);
  await elementsReady(page);
  await print(page);
  await expect(page.locator('details.toc-mobile')).toBeHidden();
  await expect(page.locator('#test-yourself')).toBeHidden();

  await page.goto(`${C}/mc/rc-filter/`);
  await elementsReady(page);
  await print(page);
  await expect(page.locator('section.practice')).toBeHidden();
  expect(await page.locator('.question-meta').first().evaluate((el) => getComputedStyle(el).breakAfter)).toBe('avoid');

  await page.goto(`${C}/exams/probeklausur-1/`);
  await elementsReady(page);
  const exam = page.locator('sk-exam');
  await print(page);
  await expect(exam.getByRole('button', { name: 'Start exam' })).toBeHidden();
  await unprint(page);
  await exam.getByRole('button', { name: 'Start exam' }).click();
  await print(page);
  // the running exam's sticky head prints no empty strip; its hints stay locked
  const head = exam.locator('.sk-exam-head');
  expect(await head.evaluate((el) => getComputedStyle(el).backgroundColor)).toBe('rgba(0, 0, 0, 0)');
  await expect(exam.locator('details.sk-hint').first()).toBeHidden();
  await unprint(page);
  await exam.getByRole('button', { name: 'Submit', exact: true }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Submit now' }).click();
  await print(page);
  await expect(exam.getByRole('button', { name: 'Retake exam' })).toBeHidden();
});
