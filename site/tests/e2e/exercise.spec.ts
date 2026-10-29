// An exercise page (docs/architecture.md §3.2): the hint ladder counts hints, the answer
// check reads German notation within the tolerance and names a 2π mistake, the solution
// asks "Tried it?" first, and more than one hint caps the self-assessment at "Partly".
import { expect, test, type Page } from '@playwright/test';
import { C, elementsReady, freezeDay, progress } from './helpers.ts';

const ID = 'ex-rc-tp-grenzfrequenz';

interface AnswerSpec {
  key: string;
  value: number | null;
  unit: string | null;
  rtol: number | null;
  atol: number | null;
}

/** A number in German notation with `digits` decimals: 1,54 */
const de = (x: number, digits: number) => x.toFixed(digits).replace('.', ',');

async function open(page: Page): Promise<void> {
  await freezeDay(page);
  await page.goto(`${C}/exercises/${ID}/`);
  await elementsReady(page);
}

async function specs(page: Page): Promise<AnswerSpec[]> {
  return JSON.parse((await page.locator('sk-answer-check').getAttribute('data-answers')) ?? '[]');
}

test('hints are shown one at a time and counted; two hints cap the rating at "Partly"', async ({ page }) => {
  await open(page);
  const hints = page.locator('sk-hints');
  const ladder = hints.locator('details.sk-hint');
  const total = await ladder.count();
  expect(total).toBe(2);
  for (let i = 0; i < total; i++) await expect(ladder.nth(i)).toBeHidden();
  const assess = page.locator('sk-self-assess');
  const solved = assess.getByRole('button', { name: 'Solved' });
  const partly = assess.getByRole('button', { name: 'Partly' });

  await hints.getByRole('button', { name: `Show hint 1 of ${total}` }).click();
  await expect(ladder.nth(0)).toBeVisible();
  await expect(ladder.nth(1)).toBeHidden();
  await expect(hints.locator('.sk-hints-status')).toHaveText(`1 of ${total} hints used.`);
  expect((await progress(page)).items[`ex:${ID}`].hints).toBe(1);

  // one hint still allows "Solved" (a new exercise goes from box 1 to box 2: three days)
  await expect(solved).toHaveAttribute('aria-disabled', 'false');
  await solved.click();
  await expect(solved).toHaveAttribute('aria-pressed', 'true');
  await expect(assess.locator('.sk-assess-status')).toHaveText('Saved: Solved, review again in 3 days.');

  // the second hint turns that "Solved" into "Partly" and locks "Solved"
  await hints.getByRole('button', { name: `Show hint 2 of ${total}` }).click();
  await expect(ladder.nth(1)).toBeVisible();
  await expect(hints.locator('.sk-hints-status')).toHaveText(`All ${total} hints shown.`);
  await expect(hints.getByRole('button', { name: /Show hint/ })).toBeHidden();
  await expect(solved).toHaveAttribute('aria-disabled', 'true');
  await expect(assess.locator('.sk-assess-note')).toHaveText('You used 2 hints, so the best rating is “Partly”.');
  await expect(partly).toHaveAttribute('aria-pressed', 'true');
  await expect(assess.locator('.sk-assess-status')).toHaveText('Saved: Partly, review again tomorrow.');
  await solved.click({ force: true }); // aria-disabled: the click is refused
  await expect(assess.locator('.sk-assess-note')).toBeFocused();
  await expect(partly).toHaveAttribute('aria-pressed', 'true');
  expect((await progress(page)).items[`ex:${ID}`]).toMatchObject({ hints: 2, rating: 'partial', box: 1 });

  // after a reload the used hints stay open and the cap stays
  await page.reload();
  await elementsReady(page);
  for (let i = 0; i < total; i++) await expect(ladder.nth(i)).toBeVisible();
  await expect(hints.locator('.sk-hints-status')).toHaveText(`All ${total} hints shown.`);
  await expect(solved).toHaveAttribute('aria-disabled', 'true');
  await expect(partly).toHaveAttribute('aria-pressed', 'true');
});

test('the answer check reads "1,54 kHz" within the tolerance and names a 2π mistake', async ({ page }) => {
  await open(page);
  const all = await specs(page);
  const fgIndex = all.findIndex((s) => s.key === 'fg');
  const fg = all[fgIndex];
  expect(fg?.unit).toBe('Hz');
  const want = fg?.value ?? 0;
  const rows = page.locator('sk-answer-check .sk-check-row');
  await expect(rows).toHaveCount(all.length);
  const row = rows.nth(fgIndex);
  const check = page.locator('sk-answer-check').getByRole('button', { name: 'Check' });

  // ω instead of f: off by 2π
  await row.getByRole('textbox').fill(`${de((want * 2 * Math.PI) / 1000, 2)} kHz`);
  await check.click();
  await expect(row.locator('.sk-check-result')).toHaveClass(/is-bad/);
  await expect(row.locator('.sk-check-result')).toContainText('Not correct');
  await expect(row.locator('.sk-check-tip')).toContainText('Off by a factor of 2π');
  expect((await progress(page)).items[`ex:${ID}`].answer_ok).toBe(false);

  // the rounded value with a decimal comma and a prefixed unit is within the tolerance
  const typed = `${de(want / 1000, 2)} kHz`;
  const read = Number(de(want / 1000, 2).replace(',', '.')) * 1000;
  expect(Math.abs(read - want) / want).toBeLessThanOrEqual(fg?.rtol ?? 0);
  await row.getByRole('textbox').fill(typed);
  await check.click();
  await expect(row.locator('.sk-check-result')).toHaveClass(/is-ok/);
  await expect(row.locator('.sk-check-result')).toContainText('Correct.');

  // every answer right (value with decimal comma and unit): the exercise counts as solved
  for (const [i, s] of all.entries()) {
    if (i === fgIndex || s.value === null) continue;
    await rows.nth(i).getByRole('textbox').fill(`${String(s.value).replace('.', ',')} ${s.unit ?? ''}`.trim());
  }
  await check.click();
  for (let i = 0; i < all.length; i++) await expect(rows.nth(i).locator('.sk-check-result')).toHaveClass(/is-ok/);
  await expect(page.locator('sk-answer-check .sk-check-summary')).toHaveText('All answers are correct.');
  expect((await progress(page)).items[`ex:${ID}`].answer_ok).toBe(true);

  // after an attempt the solution opens without asking
  await page.reload();
  await elementsReady(page);
  await expect(page.locator('sk-answer-check .sk-check-summary')).toHaveText('You solved this before.');
  const solution = page.locator('sk-reveal details.sk-solution');
  await solution.locator('summary').click();
  await expect(solution).toHaveAttribute('open');
  await expect(page.locator('sk-reveal .sk-reveal-confirm')).toHaveCount(0);
});

test('the solution asks "Tried it?" before it opens', async ({ page }) => {
  await open(page);
  const reveal = page.locator('sk-reveal');
  const solution = reveal.locator('details.sk-solution');
  const summary = solution.locator('summary');
  await summary.click();
  await expect(solution).not.toHaveAttribute('open');
  const confirm = reveal.locator('.sk-reveal-confirm');
  await expect(confirm).toContainText('Tried it?');
  await confirm.getByRole('button', { name: 'Keep trying' }).click();
  await expect(confirm).toHaveCount(0);
  await expect(solution).not.toHaveAttribute('open');

  await summary.click();
  await reveal.getByRole('button', { name: 'Yes, show the solution' }).click();
  await expect(solution).toHaveAttribute('open');
  await expect(solution.locator('p').first()).toBeVisible();
  await expect(reveal.locator('.sk-reveal-confirm')).toHaveCount(0);
});
