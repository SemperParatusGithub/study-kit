import { expect, test } from '@playwright/test';
import { progress } from './helpers.ts';

const ITEM = 'ex:ex-rc-tp-grenzfrequenz';

test.beforeEach(async ({ page }) => {
  await page.goto('/exercise.html');
  await expect(page.locator('sk-hints.sk-hints-ready')).toHaveCount(1);
});

test('hints are revealed one at a time and counted', async ({ page }) => {
  const hints = page.locator('sk-hints');
  const details = hints.locator('details.sk-hint');
  await expect(details.nth(0)).toBeHidden();
  await expect(details.nth(1)).toBeHidden();
  await hints.getByRole('button', { name: 'Show hint 1 of 2' }).click();
  await expect(details.nth(0)).toBeVisible();
  await expect(details.nth(0)).toHaveAttribute('open', '');
  await expect(details.nth(1)).toBeHidden();
  await expect(hints.locator('.sk-hints-status')).toHaveText('1 of 2 hints used.');
  expect((await progress(page)).items[ITEM]).toMatchObject({ hints: 1, h: '450eee78' });

  await hints.getByRole('button', { name: 'Show hint 2 of 2' }).click();
  await expect(details.nth(1)).toBeVisible();
  await expect(hints.locator('.sk-hints-status')).toHaveText('All 2 hints shown.');
  await expect(hints.getByRole('button')).toBeHidden();
  expect((await progress(page)).items[ITEM].hints).toBe(2);

  await page.reload();
  await expect(details.nth(0)).toBeVisible();
  await expect(details.nth(1)).toBeVisible();
});

test('opening every <details> for printing does not count as using hints', async ({ page }) => {
  await page.evaluate(() => {
    window.dispatchEvent(new Event('beforeprint'));
    for (const d of document.querySelectorAll('details')) d.open = true;
  });
  await page.waitForTimeout(50); // toggle events are async
  await page.evaluate(() => window.dispatchEvent(new Event('afterprint')));
  expect((await progress(page))?.items?.[ITEM]?.hints ?? 0).toBe(0);
  await expect(page.locator('sk-hints .sk-hints-status')).toHaveText('');
});

test('self-assessment: more than one hint caps the rating at Partly', async ({ page }) => {
  const assess = page.locator('sk-self-assess');
  const solved = assess.getByRole('button', { name: 'Solved' });
  await expect(solved).toHaveAttribute('aria-disabled', 'false');
  await page.getByRole('button', { name: 'Show hint 1 of 2' }).click();
  await expect(solved).toHaveAttribute('aria-disabled', 'false');
  await page.getByRole('button', { name: 'Show hint 2 of 2' }).click();
  await expect(solved).toHaveAttribute('aria-disabled', 'true');
  await expect(assess.locator('.sk-assess-note')).toHaveText('You used 2 hints, so the best rating is “Partly”.');
  await solved.click({ force: true });
  expect((await progress(page)).items[ITEM].rating).toBeNull();
  await assess.getByRole('button', { name: 'Partly' }).click();
  await expect(assess.getByRole('button', { name: 'Partly' })).toHaveAttribute('aria-pressed', 'true');
  await expect(assess.locator('.sk-assess-status')).toHaveText('Saved: Partly, review again tomorrow.');
  expect((await progress(page)).items[ITEM]).toMatchObject({ rating: 'partial', box: 1, hints: 2 });
});

test('self-assessment: hints opened after "Solved" cap it at Partly', async ({ page }) => {
  const assess = page.locator('sk-self-assess');
  const solved = assess.getByRole('button', { name: 'Solved' });
  const partly = assess.getByRole('button', { name: 'Partly' });
  await solved.click();
  await page.getByRole('button', { name: 'Show hint 1 of 2' }).click();
  await expect(solved).toHaveAttribute('aria-pressed', 'true'); // one hint is fine
  await page.getByRole('button', { name: 'Show hint 2 of 2' }).click();
  await expect(solved).toHaveAttribute('aria-pressed', 'false');
  await expect(solved).toHaveAttribute('aria-disabled', 'true');
  await expect(partly).toHaveAttribute('aria-pressed', 'true');
  await expect(assess.locator('.sk-assess-status')).toHaveText('Saved: Partly, review again tomorrow.');
  expect((await progress(page)).items[ITEM]).toMatchObject({ rating: 'partial', box: 1, hints: 2 });
  await page.reload();
  await expect(partly).toHaveAttribute('aria-pressed', 'true');
});

test('self-assessment without hints: Solved schedules a later review', async ({ page }) => {
  const assess = page.locator('sk-self-assess');
  await assess.getByRole('button', { name: 'Solved' }).click();
  await expect(assess.locator('.sk-assess-status')).toHaveText('Saved: Solved, review again in 3 days.');
  expect((await progress(page)).items[ITEM]).toMatchObject({ rating: 'solved', box: 2 });
  await page.reload();
  await expect(assess.getByRole('button', { name: 'Solved' })).toHaveAttribute('aria-pressed', 'true');
});

test('answer check: decimal comma, prefixes and a hint for a forgotten 2π', async ({ page }) => {
  const check = page.locator('sk-answer-check').first();
  await expect(check.locator('.sk-check-label .katex')).toBeVisible(); // label math via KaTeX
  const input = check.getByRole('textbox');
  await expect(input).toHaveAccessibleDescription('in Hz · ±0.1 %');
  await input.fill('10 kHz');
  await check.getByRole('button', { name: 'Check' }).click();
  const result = check.locator('.sk-check-result');
  await expect(result).toContainText('✗ Not correct within ±0.1 %.');
  await expect(result).toContainText('Off by a factor of 2π');
  await expect(input).toHaveAttribute('aria-invalid', 'true');
  expect((await progress(page)).items[ITEM].answer_ok).toBe(false);

  await input.fill('1,59 kHz');
  await page.keyboard.press('Enter');
  await expect(result).toContainText('✓ Correct. Read as 1,59 kHz = 1590 Hz.');
  expect((await progress(page)).items[ITEM].answer_ok).toBe(true);

  await input.fill('1,59 kV');
  await page.keyboard.press('Enter');
  await expect(result).toContainText('The unit “kV” does not fit; the answer is asked in Hz.');
  await input.fill('ungefähr 1600');
  await page.keyboard.press('Enter');
  await expect(result).toContainText('This is not a number I can read.');
});

test('answer check: dB with an absolute tolerance and a symbolic answer', async ({ page }) => {
  const check = page.locator('#more-answers');
  const [hdb, expr] = await check.getByRole('textbox').all();
  await hdb!.fill('-3,01 dB');
  await expr!.fill('1/(1+sRC)');
  await check.getByRole('button', { name: 'Check' }).click();
  await expect(check.locator('.sk-check-result').nth(0)).toContainText('✓ Correct.');
  await expect(check.locator('.sk-check-result').nth(1)).toContainText('✓ Correct. Read as 1/(1 + s·R·C).');
  await expect(check.locator('.sk-check-summary')).toHaveText('All answers are correct.');
  await expr!.fill('1/(1+s*L)');
  await check.getByRole('button', { name: 'Check' }).click();
  await expect(check.locator('.sk-check-result').nth(1)).toContainText('Unknown name “L”. Use the symbols s, R, C.');
  await expr!.fill('s*R*C/(1+s*R*C)');
  await check.getByRole('button', { name: 'Check' }).click();
  await expect(check.locator('.sk-check-result').nth(1)).toContainText('Not equivalent');
  await expect(expr!).toBeFocused();
});

test('reveal asks "Tried it?" before the solution opens', async ({ page }) => {
  const reveal = page.locator('sk-reveal');
  const details = reveal.locator('details.sk-solution');
  const summary = details.locator('summary');
  await summary.click();
  await expect(details).not.toHaveAttribute('open', '');
  await expect(reveal.getByText('Tried it?')).toBeVisible();
  await expect(reveal.getByRole('button', { name: 'Yes, show the solution' })).toBeFocused();
  // every button name in an exercise is unique (the rating has a "Not yet")
  const names = await page.locator('article.sk-exercise').getByRole('button').evaluateAll(
    (bs) => bs.filter((b) => (b as HTMLElement).offsetParent !== null).map((b) => b.textContent?.trim()));
  expect(new Set(names).size).toBe(names.length);
  await reveal.getByRole('button', { name: 'Keep trying' }).click();
  await expect(reveal.locator('.sk-reveal-confirm')).toHaveCount(0);
  await expect(details).not.toHaveAttribute('open', '');
  await expect(summary).toBeFocused();
  await page.keyboard.press('Enter'); // keyboard path through the same confirmation
  await reveal.getByRole('button', { name: 'Yes, show the solution' }).click();
  await expect(details).toHaveAttribute('open', '');
  await expect(details.locator('.katex').first()).toBeVisible();
  await expect(reveal.locator('.sk-reveal-confirm')).toHaveCount(0);
});

test('after using the answer check the solution opens directly', async ({ page }) => {
  const check = page.locator('sk-answer-check').first();
  await check.getByRole('textbox').fill('1,6 kHz');
  await check.getByRole('button', { name: 'Check' }).click();
  const details = page.locator('sk-reveal details.sk-solution');
  await details.locator('summary').click();
  await expect(details).toHaveAttribute('open', '');
  await expect(page.locator('.sk-reveal-confirm')).toHaveCount(0);
});

test('changed content is flagged on the self-assessment', async ({ page }) => {
  await page.locator('sk-self-assess').getByRole('button', { name: 'Not yet' }).click();
  await page.evaluate((item) => {
    const doc = JSON.parse(localStorage.getItem('studykit:v1:mini') ?? '{}');
    doc.items[item].h = 'deadbeef';
    localStorage.setItem('studykit:v1:mini', JSON.stringify(doc));
  }, ITEM);
  await page.reload();
  await expect(page.locator('sk-self-assess .sk-assess-changed')).toBeVisible();
});
