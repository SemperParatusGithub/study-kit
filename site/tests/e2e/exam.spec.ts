// Exam mode (docs/architecture.md §4.4, flows 3 and 4): start the mock exam, reload, the
// timer keeps running; submit, solutions and rubrics appear, the MC part is scored with the
// exam's rule.
import { expect, test, type Page } from '@playwright/test';
import { answer, C, elementsReady, freezeDay, NOW, progress, SESSION_KEY, type How } from './helpers.ts';

const EXAM = 'probeklausur-1';

/** Seconds left on the exam clock ("1:49:58" → 6598). */
async function clockSeconds(page: Page): Promise<number> {
  const text = (await page.locator('.sk-exam-clock').textContent()) ?? '';
  return text.split(':').map(Number).reduce((acc, n) => acc * 60 + n, 0);
}

test('the timer survives a reload; submitting shows solutions, rubrics and the scored MC part', async ({ page }) => {
  page.on('dialog', (d) => void d.accept()); // leaving a running exam asks first (beforeunload)
  await freezeDay(page);
  // Page time stands still: it moves only with fastForward, so the clock checks below do
  // not depend on how fast this machine answers the MC part.
  await page.clock.pauseAt(new Date(NOW.getTime() + 1000));
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

  // answer the MC part: the first question wrong, the first multi and the first Kprim
  // question with one decision wrong, the rest right. The exam's rule decides what the
  // multi answer earns: nothing under all-or-nothing, part of the points under partial or
  // the Kprim rule.
  await expect(exam).toHaveAttribute('data-mc-scoring', 'all-or-nothing');
  const n = await mcs.count();
  const types = await mcs.evaluateAll((els) => els.map((e) => e.getAttribute('data-type')));
  const plan: How[] = types.map((_, i) => (i === 0 ? 'wrong' : 'right'));
  for (const type of ['multi', 'kprim']) {
    const i = types.indexOf(type, 1);
    expect(i, `the exam has a ${type} question after the first`).toBeGreaterThan(0);
    plan[i] = 'one-off';
  }
  const scores: number[] = [];
  for (let i = 0; i < n; i++) scores.push(await answer(mcs.nth(i), plan[i] ?? 'right'));
  const scored = scores.reduce((s, x) => s + x, 0);
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

  // the MC part is scored automatically: all-or-nothing for multi, the Kprim rule for
  // Kprim, points shared equally
  const each = mcPoints / n;
  const mcTotal = scored * each;
  await expect(mcPart.locator('.sk-exam-mc-total')).toHaveText(`Multiple choice: ${mcTotal} of ${mcPoints} points.`);
  const verdicts: Record<string, string> = {
    wrong: `Not correct. 0 of ${each} points.`,
    right: `Correct. ${each} of ${each} points.`,
    'one-off:multi': `Not correct. 0 of ${each} points.`,
    'one-off:kprim': `Partly correct: 0.5 of 1 point. ${each / 2} of ${each} points.`,
  };
  for (let i = 0; i < n; i++) {
    const how = plan[i] ?? 'right';
    const verdict = verdicts[how === 'one-off' ? `${how}:${types[i]}` : how] ?? '';
    await expect(mcs.nth(i).locator('.sk-mc-feedback')).toContainText(verdict);
  }
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

test('keyboard: focus moves to the first task on Start and back to Submit after Escape', async ({ page }) => {
  page.on('dialog', (d) => void d.accept());
  await freezeDay(page);
  await page.goto(`${C}/exams/${EXAM}/`);
  await elementsReady(page);
  const exam = page.locator('sk-exam');
  await exam.getByRole('button', { name: 'Start exam' }).focus();
  await page.keyboard.press('Enter');
  const firstHeading = exam.locator('section.sk-exam-task').first().getByRole('heading').first();
  await expect(firstHeading).toBeFocused();

  // while the exam runs, a control that gets focus is scrolled below the sticky head
  const head = await exam.locator('.sk-exam-head').evaluate((el) => el.getBoundingClientRect().height);
  const padding = await page.evaluate(() => Number.parseFloat(getComputedStyle(document.documentElement).scrollPaddingTop));
  expect(padding).toBeGreaterThanOrEqual(head);

  const submit = exam.getByRole('button', { name: 'Submit', exact: true });
  await submit.focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('dialog', { name: 'Submit the exam?' })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(submit).toBeFocused();

  // submitted: the page's own scroll padding is back
  await submit.click();
  await page.getByRole('dialog').getByRole('button', { name: 'Submit now' }).click();
  await expect(exam.locator('.sk-exam-result').getByRole('heading', { name: 'Result' })).toBeFocused();
  expect(await page.evaluate(() => document.documentElement.style.scrollPaddingTop)).toBe('');
});

test('two tabs: a submission in one is never undone by the other, rubric ticks reach both', async ({ page, context }) => {
  page.on('dialog', (d) => void d.accept());
  await freezeDay(page);
  await page.goto(`${C}/exams/${EXAM}/`);
  await elementsReady(page);
  await page.getByRole('button', { name: 'Start exam' }).click();
  await expect(page.locator('.sk-exam-clock')).not.toBeEmpty();

  // the same exam in a second tab resumes the running session
  const other = await context.newPage();
  other.on('dialog', (d) => void d.accept());
  await freezeDay(other);
  await other.goto(`${C}/exams/${EXAM}/`);
  await expect(other.locator('.sk-exam-clock')).not.toBeEmpty();

  const stored = (p: typeof page) =>
    p.evaluate(([key, id]) => JSON.parse(localStorage.getItem(key) ?? '{}')[`exam:${id}`], [SESSION_KEY, EXAM] as const);
  await page.getByRole('button', { name: 'Submit', exact: true }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Submit now' }).click();
  const submitted = (await stored(page)).submitted as string;
  expect(submitted).toBeTruthy();

  // the other tab follows at once and its later saves keep the submission
  await expect(other.locator('.sk-exam-result').getByRole('heading', { name: 'Result' })).toBeVisible();
  await other.clock.runFor(12_000);
  expect((await stored(page)).submitted).toBe(submitted);

  // a rubric tick in one tab shows in the other and survives its ticks
  await page.locator('fieldset.sk-rubric').first().getByRole('checkbox').first().check();
  await expect(other.locator('fieldset.sk-rubric').first().getByRole('checkbox').first()).toBeChecked();
  await other.locator('fieldset.sk-rubric').nth(1).getByRole('checkbox').first().check();
  const ticks = (await stored(page)).rubric as Record<string, number[]>;
  expect(Object.values(ticks).filter((t) => t.length > 0)).toHaveLength(2);

  await page.reload();
  await expect(page.locator('.sk-exam-result').getByRole('heading', { name: 'Result' })).toBeVisible();
  await other.close();
});
