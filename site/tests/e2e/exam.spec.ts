// Exam mode (docs/architecture.md §4.4, flows 3 and 4): start the mock exam, reload, the
// timer keeps running; submit, solutions and rubrics appear, the MC part is scored with the
// exam's rule.
import { expect, test, type Page } from '@playwright/test';
import { answer, C, elementsReady, freezeDay, NOW, progress, SESSION_KEY } from './helpers.ts';

const EXAM = 'probeklausur-1';

/** Seconds left on the exam clock ("1:49:58" → 6598). */
async function clockSeconds(page: Page): Promise<number> {
  const text = (await page.locator('.sk-exam-clock').textContent()) ?? '';
  return text.split(':').map(Number).reduce((acc, n) => acc * 60 + n, 0);
}

test('the timer survives a reload; submitting shows solutions, rubrics and the scored MC part', async ({ page }) => {
  page.on('dialog', (d) => void d.accept()); // leaving a running exam asks first (beforeunload)
  await freezeDay(page);
  await page.goto(`${C}/exams/${EXAM}/`);
  await elementsReady(page);
  const exam = page.locator('sk-exam');
  const minutes = Number(await exam.getAttribute('data-duration-min'));
  const points = Number(await exam.getAttribute('data-points'));
  const tasks = exam.locator('section.sk-exam-task');
  const mcPart = exam.locator('section.sk-exam-mc');
  const mcs = mcPart.locator('sk-mc');
  const mcPoints = Number(await mcPart.getAttribute('data-points'));

  // cover page: the tasks stay hidden until Start
  const cover = exam.locator('.sk-exam-cover');
  await expect(cover.getByRole('heading', { name: 'Before you start' })).toBeVisible();
  await expect(cover.locator('.sk-exam-facts')).toContainText(`Duration${minutes} min`);
  await expect(cover.locator('.sk-exam-facts')).toContainText(`Points${points}`);
  await expect(tasks.first()).toBeHidden();
  await exam.getByRole('button', { name: 'Start exam' }).click();
  await expect(tasks.first()).toBeVisible();
  expect(await clockSeconds(page)).toBeGreaterThan(minutes * 60 - 5);

  // hints and solutions are hidden and inert while the exam runs; MC has no Check
  const solutions = exam.locator('details.sk-solution');
  const nTasks = await tasks.count();
  await expect(solutions).toHaveCount(nTasks);
  for (let i = 0; i < nTasks; i++) {
    await expect(solutions.nth(i)).toBeHidden();
    expect(await solutions.nth(i).evaluate((d) => (d as HTMLElement).inert)).toBe(true);
  }
  await expect(mcs.first().getByRole('button', { name: 'Check' })).toHaveCount(0);

  // answer the MC part: the first question wrong, the rest right
  const n = await mcs.count();
  let right = 0;
  for (let i = 0; i < n; i++) right += await answer(mcs.nth(i), i === 0 ? 'wrong' : 'right');
  const firstChecked = await mcs.first().locator('input:checked').count();

  // ten minutes pass, then the page is reloaded: the clock goes on from where it was
  const started = async () =>
    page.evaluate(
      ([key, id]) => JSON.parse(localStorage.getItem(key) ?? '{}')[`exam:${id}`]?.started as string,
      [SESSION_KEY, EXAM] as const,
    );
  const startedAt = await started();
  expect(Date.parse(startedAt) - NOW.getTime()).toBeLessThan(60_000);
  await page.clock.fastForward('10:00');
  await expect.poll(() => clockSeconds(page)).toBeLessThanOrEqual((minutes - 10) * 60);
  const before = await clockSeconds(page);
  expect(before).toBeGreaterThan((minutes - 10) * 60 - 10);
  await page.reload();
  await elementsReady(page);
  await expect(exam.locator('.sk-exam-cover')).toHaveCount(0);
  await expect(page.locator('.sk-exam-clock')).not.toBeEmpty();
  const after = await clockSeconds(page);
  expect(after).toBeLessThanOrEqual(before);
  expect(after).toBeGreaterThan(before - 10);
  expect(await started()).toBe(startedAt);
  await expect(mcs.first().locator('input:checked')).toHaveCount(firstChecked); // answers restored

  // submit
  await exam.getByRole('button', { name: 'Submit', exact: true }).click();
  const dialog = page.getByRole('dialog', { name: 'Submit the exam?' });
  await expect(dialog).toBeVisible();
  await dialog.getByRole('button', { name: 'Submit now' }).click();
  const result = exam.locator('.sk-exam-result');
  await expect(result.getByRole('heading', { name: 'Result' })).toBeVisible();

  // solutions open and usable, one rubric per task
  for (let i = 0; i < nTasks; i++) {
    await expect(solutions.nth(i)).toBeVisible();
    await expect(solutions.nth(i)).toHaveAttribute('open');
    expect(await solutions.nth(i).evaluate((d) => (d as HTMLElement).inert)).toBe(false);
  }
  const rubrics = tasks.locator('fieldset.sk-rubric');
  await expect(rubrics).toHaveCount(nTasks);
  for (let i = 0; i < nTasks; i++) {
    const criteria = JSON.parse((await tasks.nth(i).getAttribute('data-rubric')) ?? '[]') as unknown[];
    await expect(rubrics.nth(i).getByRole('checkbox')).toHaveCount(criteria.length);
  }

  // the MC part is scored automatically: all-or-nothing, points shared equally
  const each = mcPoints / n;
  const mcTotal = right * each;
  await expect(mcPart.locator('.sk-exam-mc-total')).toHaveText(`Multiple choice: ${mcTotal} of ${mcPoints} points.`);
  await expect(mcs.first().locator('.sk-mc-feedback')).toContainText(`Not correct. 0 of ${each} points.`);
  await expect(mcs.nth(1).locator('.sk-mc-feedback')).toContainText(`Correct. ${each} of ${each} points.`);
  await expect(result.locator('.sk-exam-total strong')).toHaveText(`${mcTotal} / ${points}`);
  const mcRow = result.locator('.sk-exam-table tbody tr').filter({ hasText: 'Multiple choice' });
  await expect(mcRow.locator('td').first()).toHaveText(`${mcTotal} / ${mcPoints}`);
  await expect(result).toContainText(`Time used: 10 min of ${minutes} min.`);

  // ticking a rubric criterion adds its points and is saved with the attempt
  const first = JSON.parse((await tasks.first().getAttribute('data-rubric')) ?? '[]') as Array<{ points: number }>;
  const gained = first[0]?.points ?? 0;
  await rubrics.first().getByRole('checkbox').first().check();
  await expect(rubrics.first().locator('output')).toHaveText(
    `${gained} of ${await tasks.first().getAttribute('data-points')} points`,
  );
  await expect(result.locator('.sk-exam-total strong')).toHaveText(`${mcTotal + gained} / ${points}`);
  const attempts = (await progress(page)).items[`exam:${EXAM}`].attempts;
  expect(attempts).toHaveLength(1);
  expect(attempts[0].points.mc).toBe(mcTotal);
  expect(attempts[0].total).toBe(mcTotal + gained);

  // the graded exam stays graded after a reload
  await page.reload();
  await expect(exam.locator('.sk-exam-result').getByRole('heading', { name: 'Result' })).toBeVisible();
  await expect(rubrics.first().getByRole('checkbox').first()).toBeChecked();
});
