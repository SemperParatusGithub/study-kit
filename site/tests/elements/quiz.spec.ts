import { expect, test, type Page } from '@playwright/test';
import { answer, progress, seed } from './helpers.ts';

const quiz = (page: Page) => page.locator('sk-quiz');
const current = (page: Page) => page.locator('sk-quiz .sk-quiz-stage sk-mc');

async function started(page: Page, url: string, available: string): Promise<void> {
  await page.goto(url);
  await expect(quiz(page).locator('.sk-quiz-count')).toHaveText(available);
  await quiz(page).getByRole('button', { name: 'Start' }).click();
}

test('practice: feedback per question, result per topic with summary links', async ({ page }) => {
  await started(page, '/quiz.html?n=3&topics=rc-tiefpass', '3 questions available.');
  const q = quiz(page);
  for (let i = 1; i <= 3; i++) {
    await expect(q.locator('.sk-quiz-pos')).toHaveText(`Question ${i} of 3`);
    const mc = current(page);
    await expect(mc).toBeFocused();
    await expect(q.getByRole('button', { name: i === 3 ? 'See result' : 'Next' })).toHaveAttribute('aria-disabled', 'true');
    await answer(mc, i !== 2, 'Sure');
    await mc.getByRole('button', { name: 'Check' }).click();
    await expect(mc.locator('.sk-mc-feedback')).toBeVisible();
    await expect(mc.locator('.sk-explanation')).toBeVisible();
    const next = q.getByRole('button', { name: i === 3 ? 'See result' : 'Next' });
    await expect(next).toHaveAttribute('aria-disabled', 'false');
    await expect(next).toBeFocused();
    await page.keyboard.press('Enter');
  }
  const result = q.locator('.sk-quiz-result');
  await expect(result.getByRole('heading', { name: 'Result' })).toBeFocused();
  await expect(result.locator('.sk-quiz-score')).toHaveText('2 / 3 points · 67 %');
  const row = result.locator('.sk-quiz-topics tbody tr');
  await expect(row).toHaveCount(1);
  await expect(row).toContainText('RC-Tiefpass');
  await expect(row).toContainText('2 / 3');
  await expect(row.getByRole('link')).toHaveAttribute('href', '/c/mini/summary/rc-tiefpass/');
  await expect(result.locator('.sk-quiz-misconceptions li')).toHaveCount(1);
  await expect(result.locator('.sk-quiz-misconceptions a').last()).toHaveAttribute('href', '/c/mini/summary/rc-tiefpass/');
  await expect(result.locator('.sk-quiz-review > li')).toHaveCount(3);
  // every answer was recorded with Leitner data
  const items = (await progress(page)).items;
  expect(Object.keys(items).filter((k) => k.startsWith('mc:mc-rc-tiefpass-')).length).toBe(3);

  // the review shows the answer, not a "Last time" note from before the quiz
  await expect(result.locator('.sk-mc-note')).toHaveCount(3);
  for (const note of await result.locator('.sk-mc-note').all()) await expect(note).toBeHidden();

  await result.getByRole('button', { name: 'Retry mistakes (1)' }).click();
  await expect(q.locator('.sk-quiz-pos')).toHaveText('Question 1 of 1');
});

test('N and Enter on the question move to the next one in practice', async ({ page }) => {
  await started(page, '/quiz.html?n=2&topics=rc-filter', '3 questions available.');
  const mc = current(page);
  await answer(mc, true);
  await mc.locator('input').first().focus();
  await page.keyboard.press('Enter'); // checks
  await expect(mc.locator('.sk-mc-feedback')).toContainText('Correct.');
  await mc.focus();
  await page.keyboard.press('n');
  await expect(quiz(page).locator('.sk-quiz-pos')).toHaveText('Question 2 of 2');
});

test('test mode: no feedback until the end, then every answer is revealed', async ({ page }) => {
  await started(page, '/quiz.html?mode=test&n=3&topics=rc-tiefpass', '3 questions available.');
  const q = quiz(page);
  await expect(q.locator('.sk-quiz-time')).toHaveText(/^\d+:\d\d$/);
  for (let i = 1; i <= 3; i++) {
    const mc = current(page);
    await expect(mc.getByRole('button', { name: 'Check' })).toHaveCount(0);
    const next = q.getByRole('button', { name: i === 3 ? 'See result' : 'Next' });
    await expect(next).toHaveAttribute('aria-disabled', 'true');
    await answer(mc, i === 1, i === 1 ? 'Unsure' : 'Sure');
    await expect(next).toHaveAttribute('aria-disabled', 'false');
    await next.click();
    if (i < 3) await expect(mc.locator('.sk-why').first()).toBeHidden();
  }
  const result = q.locator('.sk-quiz-result');
  await expect(result.locator('.sk-quiz-score')).toHaveText('1 / 3 points · 33 %');
  await expect(result.locator('.sk-quiz-misconceptions li')).toHaveCount(2);
  const wrong = result.locator('.sk-quiz-item.is-bad');
  await expect(wrong).toHaveCount(2);
  await expect(wrong.first()).toHaveAttribute('open', '');
  await expect(wrong.first().locator('.sk-why').first()).toBeVisible();
  await expect(wrong.first().locator('.sk-mc-feedback')).toContainText('Not correct.');
  const items = (await progress(page)).items;
  const scores = Object.values(items).map((e: any) => e.attempts[0].score).sort();
  expect(scores).toEqual([0, 0, 1]);
});

test('test mode with a time limit ends when the time is up', async ({ page }) => {
  await page.clock.install({ time: new Date('2026-11-02T10:00:00') });
  await started(page, '/quiz.html?mode=test&n=4&minutes=1', '6 questions available.');
  const q = quiz(page);
  await expect(q.locator('.sk-quiz-time')).toHaveText('Time left 1:00');
  await answer(current(page), true);
  await q.getByRole('button', { name: 'Next' }).click();
  await expect(q.locator('.sk-quiz-pos')).toHaveText('Question 2 of 4');
  await page.clock.runFor(61_000);
  const result = q.locator('.sk-quiz-result');
  await expect(result).toBeVisible();
  await expect(result.locator('.sk-quiz-meta')).toContainText('1 of 4 answered');
  await expect(result.locator('.sk-quiz-meta')).toContainText('time is up');
  await expect(result.locator('.sk-quiz-score')).toHaveText('1 / 4 points · 25 %');
  // the unanswered question is shown with its key but not recorded
  await expect(result.locator('.sk-quiz-item').nth(1)).toContainText('not answered');
  expect(Object.keys((await progress(page)).items)).toHaveLength(1);
});

test('mistakes mode: only questions whose last answer was not fully right', async ({ page }) => {
  await seed(page, {
    'mc:mc-rc-tiefpass-001': { h: '00000000', box: 2, due: '2026-12-01', attempts: [
      { t: '2026-10-20T10:00:00Z', chosen: ['B'], score: 0, conf: 'sure', ms: 1 },
      { t: '2026-10-21T10:00:00Z', chosen: ['A'], score: 1, conf: 'sure', ms: 1 },
    ] },
    'mc:mc-rc-tiefpass-003': { h: '00000000', box: 1, due: '2026-12-01', attempts: [
      { t: '2026-10-21T10:00:00Z', chosen: ['A'], score: 0.5, conf: 'unsure', ms: 1 },
    ] },
    'mc:mc-rc-filter-011': { h: '00000000', box: 0, due: '2026-12-01', attempts: [
      { t: '2026-10-21T10:00:00Z', chosen: ['C'], score: 0, conf: 'sure', ms: 1 },
    ] },
  });
  await started(page, '/quiz.html?mode=mistakes', '2 questions available.');
  // the sure-but-wrong one comes first
  await expect(current(page)).toHaveAttribute('data-id', 'mc-rc-filter-011');
});

test('due mode: questions the schedule has due, with the exam clamp', async ({ page }) => {
  await page.clock.install({ time: new Date('2027-02-08T09:00:00') }); // exam 2027-02-15
  await seed(page, {
    // due yesterday
    'mc:mc-rc-tiefpass-001': { h: '00000000', box: 2, due: '2027-02-07', attempts: [
      { t: '2027-02-04T10:00:00Z', chosen: ['A'], score: 1, conf: 'sure', ms: 1 },
    ] },
    // scheduled after the exam, reviewed before the last 10 days: due from 2027-02-05
    'mc:mc-rc-tiefpass-002': { h: '00000000', box: 5, due: '2027-03-01', attempts: [
      { t: '2027-01-30T10:00:00Z', chosen: ['A', 'B'], score: 1, conf: 'sure', ms: 1 },
    ] },
    // not due yet
    'mc:mc-rc-tiefpass-003': { h: '00000000', box: 1, due: '2027-02-09', attempts: [
      { t: '2027-02-08T08:00:00Z', chosen: ['A', 'B'], score: 1, conf: 'sure', ms: 1 },
    ] },
  });
  await started(page, '/quiz.html?mode=due', '2 questions available.');
  await expect(current(page)).toHaveAttribute('data-id', 'mc-rc-tiefpass-002'); // most overdue first
});

test('due mode: nothing due names the next review', async ({ page }) => {
  await page.clock.install({ time: new Date('2026-11-02T09:00:00') });
  await seed(page, {
    'mc:mc-rc-tiefpass-001': { h: '00000000', box: 2, due: '2026-11-05', attempts: [
      { t: '2026-11-02T08:00:00Z', chosen: ['A'], score: 1, conf: 'sure', ms: 1 },
    ] },
  });
  await page.goto('/quiz.html?mode=due');
  await expect(quiz(page).locator('.sk-quiz-count')).toHaveText('Nothing is due today. The next review is in 3 days (2026-11-05).');
  await expect(quiz(page).getByRole('button', { name: 'Start' })).toBeDisabled();
});

test('mixed mode and filters: every pool, topic and difficulty choices', async ({ page }) => {
  await page.goto('/quiz.html?mode=mixed');
  const q = quiz(page);
  await expect(q.locator('.sk-quiz-mode')).toHaveText('Mixed');
  await expect(q.locator('.sk-quiz-count')).toHaveText('6 questions available.');
  await expect(q.getByRole('spinbutton', { name: 'Questions' })).toHaveValue('6');
  await q.getByLabel('RC-Filter und Bode-Diagramm').uncheck();
  await expect(q.locator('.sk-quiz-count')).toHaveText('3 questions available.');
  await q.getByLabel('Level 2').uncheck();
  await expect(q.locator('.sk-quiz-count')).toHaveText('1 question available.');
  await q.getByRole('button', { name: 'Start' }).click();
  await expect(current(page)).toHaveAttribute('data-id', 'mc-rc-tiefpass-001');
});

test('URL parameters pre-fill the start form', async ({ page }) => {
  await page.goto('/quiz.html?mode=test&n=2&minutes=15&difficulty=1');
  const q = quiz(page);
  await expect(q.locator('.sk-quiz-mode')).toHaveText('Test');
  await expect(q.locator('.sk-quiz-count')).toHaveText('2 questions available.');
  await expect(q.getByRole('spinbutton', { name: 'Questions' })).toHaveValue('2');
  await expect(q.getByRole('spinbutton', { name: 'Time limit (minutes)' })).toHaveValue('15');
  await expect(q.getByLabel('Level 2')).not.toBeChecked();
});

test('without JavaScript the fallback text stays', async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();
  await page.goto('/quiz.html');
  await expect(page.getByText('The quiz needs JavaScript.')).toBeVisible();
  await context.close();
});
