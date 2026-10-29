// Screenshots of every element in light and dark, for review by eye:
//   SK_SHOTS_DIR=/some/dir pnpm -C site exec playwright test -c tests/elements screenshots
import { join, resolve } from 'node:path';
import { expect, test, type Page } from '@playwright/test';
import { answer, seed, SESSION_KEY } from './helpers.ts';

const DIR = process.env.SK_SHOTS_DIR ?? resolve(import.meta.dirname, '../../node_modules/.cache/sk-elements/shots');
const shot = (page: Page, name: string, fullPage = true) =>
  page.screenshot({ path: join(DIR, `${name}.png`), fullPage, animations: 'disabled' });

const PROGRESS = {
  'mc:mc-rc-tiefpass-001': { h: 'aaaaaaaa', box: 3, due: '2026-11-20', attempts: [
    { t: '2026-11-01T10:00:00Z', chosen: ['B'], score: 0, conf: 'unsure', ms: 1 },
    { t: '2026-11-03T10:00:00Z', chosen: ['A'], score: 1, conf: 'sure', ms: 1 },
  ] },
  'mc:mc-rc-tiefpass-002': { h: 'bbbbbbbb', box: 0, due: '2026-11-05', attempts: [
    { t: '2026-11-05T10:00:00Z', chosen: ['A', 'C'], score: 0, conf: 'sure', ms: 1 },
  ] },
  'mc:mc-rc-filter-003': { h: 'cccccccc', box: 2, due: '2026-11-08', attempts: [
    { t: '2026-11-05T11:00:00Z', chosen: ['A'], score: 1, conf: 'sure', ms: 1 },
  ] },
  'exam:probeklausur-1': { attempts: [
    { started: '2026-11-04T09:00:00Z', duration_s: 3300, points: { 'pk1-t1': 9, mc: 6 }, total: 15 },
  ] },
};

for (const scheme of ['light', 'dark'] as const) {
  test.describe(scheme, () => {
    test.use({ colorScheme: scheme, viewport: { width: 900, height: 900 } });

    test(`mc ${scheme}`, async ({ page }) => {
      await page.goto('/mc.html');
      const qs = page.locator('sk-mc');
      await answer(qs.nth(0), true, 'Sure');
      await qs.nth(0).getByRole('button', { name: 'Check' }).click();
      await qs.nth(1).locator('sk-opt[data-key="A"] input').check();
      await qs.nth(1).locator('sk-opt[data-key="C"] input').check();
      await qs.nth(1).getByLabel('Sure', { exact: true }).check();
      await qs.nth(1).getByRole('button', { name: 'Check' }).click();
      const k = qs.nth(2);
      for (const [key, v] of [['A', 'true'], ['B', 'true'], ['C', 'true'], ['D', 'false']]) {
        await k.locator(`sk-opt[data-key="${key}"] input[value="${v}"]`).check();
      }
      await k.getByLabel('Unsure').check();
      await k.getByRole('button', { name: 'Check' }).click();
      await qs.nth(3).locator('sk-opt').nth(1).locator('input').check();
      await qs.nth(3).getByRole('button', { name: 'Check' }).click({ force: true });
      await qs.nth(4).focus();
      await page.keyboard.press('3');
      await shot(page, `mc-${scheme}`);
    });

    test(`quiz ${scheme}`, async ({ page }) => {
      await page.goto('/quiz.html?mode=mixed');
      await expect(page.locator('.sk-quiz-count')).toHaveText('6 questions available.');
      await shot(page, `quiz-start-${scheme}`);
      await page.getByRole('button', { name: 'Start' }).click();
      const mc = page.locator('.sk-quiz-stage sk-mc');
      await answer(mc, false, 'Sure');
      await mc.getByRole('button', { name: 'Check' }).click();
      await shot(page, `quiz-practice-${scheme}`);

      await page.goto('/quiz.html?mode=test&n=4&minutes=10');
      await page.getByRole('button', { name: 'Start' }).click();
      for (let i = 0; i < 4; i++) {
        const q = page.locator('.sk-quiz-stage sk-mc');
        await answer(q, i % 2 === 0, i === 1 ? 'Sure' : 'Unsure');
        if (i === 0) await shot(page, `quiz-test-${scheme}`, false);
        await page.locator('.sk-quiz-nav .sk-btn-primary').click();
      }
      await expect(page.locator('.sk-quiz-result')).toBeVisible();
      await shot(page, `quiz-result-${scheme}`);
    });

    test(`exercise ${scheme}`, async ({ page }) => {
      await page.goto('/exercise.html');
      await page.getByRole('button', { name: 'Show hint 1 of 2' }).click();
      await page.getByRole('button', { name: 'Show hint 2 of 2' }).click();
      const check = page.locator('sk-answer-check').first();
      await check.getByRole('textbox').fill('10 kHz');
      await check.getByRole('button', { name: 'Check' }).click();
      const more = page.locator('#more-answers');
      const [a, b] = await more.getByRole('textbox').all();
      await a!.fill('-3,01 dB');
      await b!.fill('1/(1+sRC)');
      await more.getByRole('button', { name: 'Check' }).click();
      await page.locator('sk-self-assess').getByRole('button', { name: 'Partly' }).click();
      await shot(page, `exercise-${scheme}`);
      await page.evaluate(() => localStorage.clear()); // a fresh exercise asks first
      await page.goto('/exercise.html');
      await page.locator('sk-reveal summary').click();
      await expect(page.getByText('Tried it?')).toBeVisible();
      await shot(page, `exercise-reveal-${scheme}`);
    });

    test(`exam ${scheme}`, async ({ page }) => {
      await seed(page, PROGRESS);
      await page.goto('/exam.html');
      await shot(page, `exam-cover-${scheme}`);
      await page.getByRole('button', { name: 'Start exam' }).click();
      await page.goto('/health');
      await page.evaluate((key) => {
        const all = JSON.parse(localStorage.getItem(key) ?? '{}');
        const s = all['exam:probeklausur-1'];
        s.started = new Date(Date.now() - 50.6 * 60_000).toISOString();
        localStorage.setItem(key, JSON.stringify(all));
      }, SESSION_KEY);
      await page.goto('/exam.html');
      await expect(page.locator('.sk-exam-alert-text')).toHaveText('10 minutes left.');
      const mcs = page.locator('sk-exam sk-mc');
      await answer(mcs.nth(0), true);
      await answer(mcs.nth(1), false);
      await page.locator('#exam-mc').scrollIntoViewIfNeeded();
      await shot(page, `exam-running-${scheme}`, false);
      await page.getByRole('button', { name: 'Submit' }).click();
      await shot(page, `exam-submit-dialog-${scheme}`, false);
      await page.getByRole('button', { name: 'Submit now' }).click();
      await page.locator('.sk-rubric').getByRole('checkbox').first().check();
      await page.evaluate(() => window.scrollTo(0, 0));
      await shot(page, `exam-graded-${scheme}`);
    });

    test(`progress ${scheme}`, async ({ page }) => {
      await page.clock.install({ time: new Date('2026-11-10T12:00:00') });
      await seed(page, PROGRESS);
      await page.goto('/progress.html');
      await page.locator('sk-plan').getByRole('checkbox').first().check();
      await shot(page, `progress-${scheme}`);
    });
  });
}

test.describe('phone width', () => {
  test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });

  test('mc and exercise, light', async ({ page }) => {
    await page.goto('/mc.html');
    const k = page.locator('sk-mc').nth(2);
    await answer(k, false, 'Sure');
    await k.getByRole('button', { name: 'Check' }).click();
    await shot(page, 'mc-phone-light');
    await page.goto('/exercise.html');
    await page.getByRole('button', { name: 'Show hint 1 of 2' }).click();
    await page.locator('sk-answer-check').first().getByRole('textbox').fill('1,59 kHz');
    await page.locator('sk-answer-check').first().getByRole('button', { name: 'Check' }).click();
    await shot(page, 'exercise-phone-light');
  });

  test.describe('dark', () => {
    test.use({ colorScheme: 'dark' });
    test('quiz and progress, dark', async ({ page }) => {
      await page.goto('/quiz.html?mode=test&n=2');
      await page.getByRole('button', { name: 'Start' }).click();
      await answer(page.locator('.sk-quiz-stage sk-mc'), true);
      await shot(page, 'quiz-phone-dark', false);
      await page.clock.install({ time: new Date('2026-11-10T12:00:00') });
      await seed(page, PROGRESS);
      await page.goto('/progress.html');
      await shot(page, 'progress-phone-dark');
    });
  });
});
