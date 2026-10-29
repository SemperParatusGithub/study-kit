import { expect, test, type Page } from '@playwright/test';
import { answer, progress, SESSION_KEY } from './helpers.ts';

const exam = (page: Page) => page.locator('sk-exam');
const clockSeconds = async (page: Page): Promise<number> => {
  const text = (await page.locator('.sk-exam-clock').textContent()) ?? '';
  return text.split(':').map(Number).reduce((acc, n) => acc * 60 + n, 0);
};

/**
 * Leave the exam page, move the stored start time and last tick back as if the page had
 * been closed for `minutes`, and open the exam again. The page saves its session on
 * pagehide, so the edit happens on another page of the same origin.
 */
async function elapse(page: Page, minutes: number): Promise<void> {
  await page.goto('/health');
  await page.evaluate(([key, min]) => {
    const all = JSON.parse(localStorage.getItem(key as string) ?? '{}');
    const s = all['exam:probeklausur-1'];
    s.started = new Date(Date.parse(s.started) - (min as number) * 60_000).toISOString();
    if (s.tick_at) s.tick_at -= (min as number) * 60_000;
    localStorage.setItem(key as string, JSON.stringify(all));
  }, [SESSION_KEY, minutes] as const);
  await page.goto('/exam.html');
}

/** The "Time" column of the result table, by part. */
async function partTimes(page: Page): Promise<Record<string, string>> {
  const rows = await exam(page).locator('.sk-exam-table tbody tr').all();
  const out: Record<string, string> = {};
  for (const r of rows) out[(await r.locator('th').textContent()) ?? ''] = (await r.locator('td').last().textContent()) ?? '';
  return out;
}

async function start(page: Page): Promise<void> {
  await page.goto('/exam.html');
  await exam(page).getByRole('button', { name: 'Start exam' }).click();
  await expect(page.locator('.sk-exam-clock')).toBeVisible();
}

test('the cover page shows duration, points, pass mark and aids; the tasks stay hidden', async ({ page }) => {
  await page.goto('/exam.html');
  const cover = exam(page).locator('.sk-exam-cover');
  await expect(cover.getByRole('heading', { name: 'Before you start' })).toBeVisible();
  await expect(cover.locator('.sk-exam-facts')).toContainText('Duration60 min');
  await expect(cover.locator('.sk-exam-facts')).toContainText('Points20');
  await expect(cover.locator('.sk-exam-facts')).toContainText('Pass mark10 points');
  await expect(cover.locator('.sk-exam-facts')).toContainText('1 task, multiple-choice part with 4 questions (8 points)');
  await expect(cover.locator('.sk-exam-aids li')).toHaveText(['Nicht programmierbarer Taschenrechner', 'Ein Blatt Formelsammlung']);
  await expect(page.getByText('Ein Spannungsteiler mit')).toBeHidden();
});

test('running: solutions are hidden and inert, MC has no Check, the timer survives a reload', async ({ page }) => {
  await start(page);
  await expect(page.getByText('Ein Spannungsteiler mit')).toBeVisible();
  const solution = exam(page).locator('details.sk-solution');
  await expect(solution).toBeHidden();
  expect(await solution.evaluate((d) => (d as HTMLElement).inert)).toBe(true);
  await expect(exam(page).locator('details.sk-hint')).toBeHidden();
  const mcs = exam(page).locator('sk-mc');
  await expect(mcs).toHaveCount(4);
  await expect(mcs.first().getByRole('button', { name: 'Check' })).toHaveCount(0);
  await expect(mcs.first().locator('.sk-mc-conf')).toHaveCount(0);
  expect(await clockSeconds(page)).toBeGreaterThan(59 * 60);

  // an MC answer and the start time survive a reload
  await mcs.first().locator('sk-opt input').first().check();
  const started = await page.evaluate((k) => JSON.parse(localStorage.getItem(k) ?? '{}')['exam:probeklausur-1'].started, SESSION_KEY);
  await elapse(page, 5);
  await expect(exam(page).locator('.sk-exam-cover')).toHaveCount(0);
  expect(await clockSeconds(page)).toBeLessThanOrEqual(55 * 60);
  expect(await clockSeconds(page)).toBeGreaterThan(54 * 60);
  await expect(mcs.first().locator('sk-opt input').first()).toBeChecked();
  const after = await page.evaluate((k) => JSON.parse(localStorage.getItem(k) ?? '{}')['exam:probeklausur-1'].started, SESSION_KEY);
  expect(Date.parse(after)).toBe(Date.parse(started) - 5 * 60_000);
});

test('leaving a running exam asks first', async ({ page }) => {
  await start(page);
  await page.locator('.sk-exam-nav a').first().click(); // a user gesture, required for beforeunload
  const dialog = page.waitForEvent('dialog');
  void page.close({ runBeforeUnload: true });
  const d = await dialog;
  expect(d.type()).toBe('beforeunload');
  await d.dismiss();
});

test('warnings at 10 and at 1 minute left', async ({ page }) => {
  await start(page);
  await expect(page.locator('.sk-exam-alert')).toBeHidden();
  await elapse(page, 50.5);
  await expect(page.locator('.sk-exam-alert-text')).toHaveText('10 minutes left.');
  await expect(exam(page)).toHaveClass(/is-low/);
  await elapse(page, 9);
  await expect(page.locator('.sk-exam-alert-text')).toHaveText('1 minute left.');
  await page.getByRole('button', { name: 'Dismiss' }).click();
  await expect(page.locator('.sk-exam-alert')).toBeHidden();
  await expect(exam(page).getByRole('button', { name: 'Submit' })).toBeFocused();
});

test('time-up submits automatically, also across a reload', async ({ page }) => {
  await start(page);
  await elapse(page, 61);
  await expect(exam(page).locator('.sk-exam-result')).toBeVisible();
  await expect(page.locator('.sk-exam-timeup')).toHaveText('Time was up; the exam was submitted automatically.');
  await expect(exam(page).locator('details.sk-solution')).toBeVisible();
  const attempt = (await progress(page)).items['exam:probeklausur-1'].attempts[0];
  expect(attempt.duration_s).toBe(3600);
  // the hour the page was closed goes to the part that was on screen
  expect(Object.values(await partTimes(page)).sort()).toEqual(['0 s', '1 h 0 min']);
});

test('time per part: late ticks count in full', async ({ page }) => {
  await page.setViewportSize({ width: 1000, height: 320 }); // task 1 is short: let it fill the screen
  const t0 = new Date('2026-11-10T09:00:00').getTime();
  await page.clock.install({ time: t0 });
  await start(page);
  /** Scroll a part to the top and wait until it counts as the one on screen. */
  const show = async (selector: string, id: string) => {
    await page.evaluate((sel) => document.querySelector(sel)?.scrollIntoView({ block: 'start' }), selector);
    await expect.poll(() => page.evaluate(() => (document.querySelector('sk-exam') as any).activeSection())).toBe(id);
  };
  await show('#task-pk1-t1', 'pk1-t1');
  // the laptop sleeps (or the tab is throttled in the background) for 3 minutes on task 1
  await page.clock.setSystemTime(t0 + 3 * 60_000);
  await page.clock.runFor(1_000);
  await show('#exam-mc', 'mc');
  await page.clock.setSystemTime(t0 + 10 * 60_000);
  await page.clock.runFor(1_000);
  await exam(page).getByRole('button', { name: 'Submit' }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Submit now' }).click();
  const times = await partTimes(page);
  expect(times).toEqual({ '1. Aufgabe 1: Spannungsteiler (12 P)': '3 min', 'Multiple choice': '7 min' });
  await expect(exam(page).locator('.sk-exam-result')).toContainText('Time used: 10 min of 60 min.');
});

test('submit: solutions open, rubric grading, MC auto-scored, result saved', async ({ page }) => {
  await start(page);
  const mcs = exam(page).locator('sk-mc');
  await answer(mcs.nth(0), true); // pk1-mc-01
  await answer(mcs.nth(1), true); // mc-rc-tiefpass-001
  await mcs.nth(2).locator('sk-opt[data-key="A"] input').check(); // multi, one of two: 0 (all-or-nothing)
  // the Kprim question stays open: 0
  await exam(page).getByRole('button', { name: 'Submit' }).click();
  const dialog = page.getByRole('dialog', { name: 'Submit the exam?' });
  await expect(dialog).toBeVisible();
  await dialog.getByRole('button', { name: 'Keep working' }).click();
  await expect(dialog).toHaveCount(0);
  await exam(page).getByRole('button', { name: 'Submit' }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Submit now' }).click();
  await expect(exam(page).getByRole('heading', { name: 'Result' })).toBeFocused();

  const solution = exam(page).locator('details.sk-solution');
  await expect(solution).toBeVisible();
  await expect(solution).toHaveAttribute('open', '');
  expect(await solution.evaluate((d) => (d as HTMLElement).inert)).toBe(false);
  await expect(exam(page).locator('.sk-exam-mc-total')).toHaveText('Multiple choice: 4 of 8 points.');
  await expect(mcs.nth(0).locator('.sk-mc-feedback')).toContainText('2 of 2 points.');
  await expect(mcs.nth(3).locator('sk-opt').first().locator('.sk-opt-mark')).toContainText('not judged');

  const rubric = exam(page).locator('.sk-rubric');
  await expect(rubric.getByRole('checkbox')).toHaveCount(2);
  await expect(rubric.locator('.sk-rubric-criterion .katex')).toHaveCount(1); // "Spannung $U_2$ korrekt"
  const result = exam(page).locator('.sk-exam-result');
  await expect(result.locator('.sk-exam-total')).toContainText('4 / 20 points · 20%');
  await expect(result.locator('.sk-exam-total')).toContainText('not passed (pass mark 10)');
  await expect(result.locator('.sk-exam-grade')).toContainText('Grade estimate: 5.0');

  await rubric.getByRole('checkbox').first().check();
  await expect(rubric.locator('.sk-rubric-total')).toHaveText('6 of 12 points');
  await expect(result.locator('.sk-exam-total')).toContainText('10 / 20 points · 50%');
  await expect(result.locator('.sk-exam-total')).toContainText('passed (pass mark 10)');
  await expect(result.locator('.sk-exam-grade')).toContainText('Grade estimate: 4.0');
  await expect(result.locator('.sk-exam-table tbody tr')).toHaveCount(2);
  await expect(result.locator('.sk-exam-table')).toContainText('Aufgabe 1: Spannungsteiler (12 P)');

  const attempts = (await progress(page)).items['exam:probeklausur-1'].attempts;
  expect(attempts).toHaveLength(1);
  expect(attempts[0]).toMatchObject({ points: { 'pk1-t1': 6, mc: 4 }, total: 10 });

  // grading survives a reload, then a retake starts from the cover
  await page.reload();
  await expect(exam(page).locator('.sk-rubric').getByRole('checkbox').first()).toBeChecked();
  await expect(exam(page).locator('.sk-exam-total')).toContainText('10 / 20');
  await exam(page).getByRole('button', { name: 'Retake exam' }).click();
  await expect(exam(page).locator('.sk-exam-last')).toContainText('Last attempt: 10 of 20 points');
  expect((await progress(page)).items['exam:probeklausur-1'].attempts).toHaveLength(1);
});

test('without JavaScript tasks and solutions are plain content', async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();
  await page.goto('/exam.html');
  await expect(page.getByText('Ein Spannungsteiler mit')).toBeVisible();
  await expect(page.locator('details.sk-solution summary')).toBeVisible();
  await context.close();
});
