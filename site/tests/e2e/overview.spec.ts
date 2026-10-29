// Progress shown outside the question pages (docs/architecture.md §3.2 routes): plan
// checkboxes, and the per-course numbers the shell leaves to the elements (due counts,
// weakest topics, MC accuracy, exercise status, last exam attempt).
import { expect, test, type Page } from '@playwright/test';
import { answer, C, elementsReady, freezeDay, pageDay, progress } from './helpers.ts';

test.beforeEach(async ({ page }) => {
  await freezeDay(page);
});

/** A sure but wrong answer: a misconception, in box 0 and due again today. */
async function misconception(page: Page, topic: string): Promise<void> {
  await page.goto(`${C}/mc/${topic}/`);
  await elementsReady(page);
  const mc = page.locator('ol.questions sk-mc[data-type="single"]').first();
  await answer(mc, 'wrong', 'Sure');
  await mc.getByRole('button', { name: 'Check' }).click();
  await expect(mc.locator('.sk-mc-feedback')).toContainText('it comes back today');
}

test('plan: session checkboxes persist and the behind-schedule banner counts past sessions', async ({ page }) => {
  await page.goto(`${C}/plan/`);
  await elementsReady(page);
  const today = await pageDay(page);
  const sessions = page.locator('sk-plan li[data-session]');
  const dates = await sessions.evaluateAll((els) => els.map((el) => (el as HTMLElement).dataset.date ?? ''));
  const past = dates.filter((d) => d < today).length;
  expect(past).toBeGreaterThan(1);
  const banner = page.locator('sk-plan .sk-plan-behind');
  await expect(banner).toContainText(`Behind schedule: ${past} past sessions are not done.`);
  await expect(banner.locator('code')).toHaveText(`/regenerate sample-course plan`);

  const first = sessions.first();
  const id = (await first.getAttribute('data-session')) ?? '';
  await first.getByRole('checkbox').check();
  await expect(first).toHaveClass(/is-done/);
  await expect(banner).toContainText(`${past - 1} past ${past - 1 === 1 ? 'session is' : 'sessions are'} not done.`);
  expect((await progress(page)).items[`plan:${id}`]).toEqual({ done: true });
  await page.reload();
  await elementsReady(page);
  await expect(first.getByRole('checkbox')).toBeChecked();
  await expect(sessions.nth(1).getByRole('checkbox')).not.toBeChecked();
});

test('the MC hub shows accuracy and due count per topic bank', async ({ page }) => {
  // Product bug: nothing fills the [data-sk-fill] placeholders of the site shell, so the
  // MC hub's "Accuracy" and "Due" columns always show "—" (§3.2 "MC hub: accuracy per
  // topic, due count").
  test.fail();
  await misconception(page, 'rc-filter');
  await page.goto(`${C}/mc/`);
  await elementsReady(page);
  const row = page.locator('table.data-table tbody tr').filter({ hasText: 'RC-Filter' });
  await expect(row.locator('[data-sk-accuracy]')).toHaveText('0 %', { timeout: 2_000 });
  await expect(row.locator('[data-sk-due-count]')).toHaveText('1', { timeout: 2_000 });
});

test('the course overview and the home page show reviews due and the weakest topics', async ({ page }) => {
  // Product bug: [data-sk-due-count] (course card on /, Today panel on /c/<c>/) and
  // [data-sk-weakest] (Today panel) are never filled (§3.2 routes / and /c/<c>/).
  test.fail();
  await misconception(page, 'rc-filter');
  await page.goto(`${C}/`);
  await elementsReady(page);
  await expect(page.locator('.today-reviews [data-sk-due-count]')).toHaveText('1', { timeout: 2_000 });
  await expect(page.locator('[data-sk-weakest] li').first()).toContainText('RC-Filter', { timeout: 2_000 });
  await expect(page.locator('[data-sk-weakest-empty]').first()).toBeHidden();
  await page.goto('/');
  await elementsReady(page);
  await expect(page.locator('[data-sk-due-count]').first()).toHaveText('1', { timeout: 2_000 });
});

test('"Start due reviews" on the course overview opens the Due mode', async ({ page }) => {
  // Product bug: the link goes to /c/<c>/mc/#due, but #due names a closed <details> of the
  // exclusive mode accordion; fragment navigation does not open it, so the hub shows
  // Practice open and Due collapsed.
  test.fail();
  await page.goto(`${C}/`);
  await elementsReady(page);
  await page.getByRole('link', { name: 'Start due reviews' }).click();
  await expect(page).toHaveURL(`${C}/mc/#due`);
  await expect(page.locator('details#due')).toHaveAttribute('open', { timeout: 2_000 });
});

test('the exercise list shows each exercise status and filters by it', async ({ page }) => {
  // Product bug: nothing sets data-status on the exercise rows or fills [data-sk-status], so
  // every exercise counts as "Not started" and the status filter never finds a rated one
  // (§3.2 "/c/<c>/exercises/: filters for topic, difficulty and status").
  test.fail();
  await page.goto(`${C}/exercises/ex-st-unbelastet/`);
  await elementsReady(page);
  await page.locator('sk-self-assess').getByRole('button', { name: 'Solved' }).click();
  await page.goto(`${C}/exercises/`);
  await elementsReady(page);
  const row = page.locator('[data-filter-row][data-item="ex:ex-st-unbelastet"]');
  await expect(row).toHaveAttribute('data-status', 'solved', { timeout: 2_000 });
  await page.getByRole('combobox', { name: 'Status' }).selectOption('solved');
  await expect(page.locator('[data-filter-row]:not([hidden])')).toHaveCount(1);
});

test('the exam list shows the last attempt', async ({ page }) => {
  // Product bug: [data-sk-exam-best] on /c/<c>/exams/ is never filled, so "Last attempt"
  // always shows "—" after an exam was graded.
  test.fail();
  page.on('dialog', (d) => void d.accept());
  await page.goto(`${C}/exams/probeklausur-1/`);
  await elementsReady(page);
  await page.getByRole('button', { name: 'Start exam' }).click();
  const mcs = page.locator('sk-exam section.sk-exam-mc sk-mc');
  for (let i = 0; i < (await mcs.count()); i++) await answer(mcs.nth(i), 'right');
  await page.locator('sk-exam').getByRole('button', { name: 'Submit', exact: true }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Submit now' }).click();
  await expect(page.locator('.sk-exam-result')).toBeVisible();
  const total = (await progress(page)).items['exam:probeklausur-1'].attempts[0].total as number;
  expect(total).toBeGreaterThan(0);
  await page.goto(`${C}/exams/`);
  await elementsReady(page);
  await expect(page.locator('[data-sk-exam-best]')).toHaveText(new RegExp(`\\b${total}\\b`), { timeout: 2_000 });
});
