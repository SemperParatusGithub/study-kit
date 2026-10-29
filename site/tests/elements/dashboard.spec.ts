// The shell's progress placeholders, filled by elements/dashboard.ts from the store and the
// course info (pages/dashboard.html mirrors the markup of src/pages and src/components).
import { expect, test } from '@playwright/test';
import { progress, seed } from './helpers.ts';

const attempt = (t: string, score: number, conf: 'sure' | 'unsure', chosen = ['A']) => ({ t, chosen, score, conf, ms: 1000 });

const ITEMS = {
  // not due (box 3, due 20 Nov)
  'mc:mc-rc-tiefpass-001': { h: 'aaaaaaaa', box: 3, due: '2026-11-20', attempts: [
    attempt('2026-11-01T10:00:00Z', 0, 'unsure', ['B']), attempt('2026-11-03T10:00:00Z', 1, 'sure'),
  ] },
  // sure but wrong: box 0, due
  'mc:mc-rc-tiefpass-002': { h: 'bbbbbbbb', box: 0, due: '2026-11-05', attempts: [
    attempt('2026-11-05T10:00:00Z', 0, 'sure', ['A', 'C']),
  ] },
  // due since 8 Nov
  'mc:mc-rc-filter-003': { h: 'cccccccc', box: 2, due: '2026-11-08', attempts: [attempt('2026-11-05T11:00:00Z', 1, 'sure')] },
  // retired: not in any bank of the course info, so never counted
  'mc:mc-rc-filter-099': { h: 'cccccccc', box: 0, due: '2026-11-01', attempts: [attempt('2026-11-01T11:00:00Z', 0, 'sure')] },
  // exam-only question
  'mc:pk1-mc-01': { h: 'dddddddd', box: null, due: null, attempts: [attempt('2026-11-06T10:00:00Z', 1, 'unsure')] },
  'ex:ex-rc-tp-grenzfrequenz': { h: 'eeeeeeee', hints: 1, answer_ok: true, rating: 'solved', box: 2, due: '2026-11-09' },
  'exam:probeklausur-1': { attempts: [
    { started: '2026-11-04T09:00:00Z', duration_s: 3300, points: { 'pk1-t1': 9, mc: 6 }, total: 15 },
  ] },
};

test.beforeEach(async ({ page }) => {
  await page.clock.install({ time: new Date('2026-11-10T12:00:00') });
});

test('placeholders show the figures of the stored progress', async ({ page }) => {
  await seed(page, ITEMS);
  await page.goto('/dashboard.html');
  await expect(page.locator('#due-all')).toHaveText('2');
  const row = (topic: string) => page.locator(`[data-topic-row="${topic}"]`);
  await expect(row('rc-tiefpass').locator('[data-sk-accuracy]')).toHaveText('33%'); // 0, 1, 0
  await expect(row('rc-tiefpass').locator('[data-sk-due-count]')).toHaveText('1');
  await expect(row('rc-filter').locator('[data-sk-accuracy]')).toHaveText('100%');
  await expect(row('rc-filter').locator('[data-sk-due-count]')).toHaveText('1');
  await expect(row('spannungsteiler').locator('[data-sk-accuracy]')).toBeEmpty(); // CSS shows "—"
  await expect(row('spannungsteiler').locator('[data-sk-due-count]')).toHaveText('0');

  const weak = page.locator('[data-sk-weakest] li');
  await expect(weak).toHaveText(['RC-Tiefpass 33%', 'RC-Filter und Bode-Diagramm 100%']);
  await expect(weak.first().getByRole('link')).toHaveAttribute('href', '/c/mini/summary/rc-tiefpass/');
  await expect(weak.nth(1).getByRole('link')).toHaveCount(0); // no summary for this topic
  await expect(page.locator('[data-sk-weakest-empty]')).toBeHidden();

  // 0.3 · 0 + 0.3 · 1/3 + 0.4 · 1
  await expect(page.locator('#ring .mastery-value')).toHaveText('50%');
  await expect(page.locator('#ring')).toHaveAttribute('aria-label', 'Mastery 50%, from your answers in this browser');
  await expect(page.locator('#ring circle')).toHaveCount(2);

  await expect(page.locator('[data-sk-exam-best]')).toHaveText('15 / 20 points (4 Nov)');

  const rows = page.locator('#exercises li');
  await expect(rows.nth(0)).toHaveAttribute('data-status', 'solved');
  await expect(rows.nth(0).locator('[data-sk-status]')).toHaveText('Solved');
  await expect(rows.nth(1)).toHaveAttribute('data-status', 'new');
  await expect(rows.nth(1).locator('[data-sk-status]')).toBeEmpty();

  // 2 and 4 Nov are past: the next session is 10 Feb
  await expect(page.locator('#next [data-session-date]:visible')).toHaveText(['Wed 10 Feb']);
});

test('without progress: zero due, no weak topics, empty ring', async ({ page }) => {
  await page.goto('/dashboard.html');
  await expect(page.locator('#due-all')).toHaveText('0');
  await expect(page.locator('[data-sk-weakest] li')).toHaveCount(0);
  await expect(page.locator('[data-sk-weakest-empty]')).toBeVisible();
  await expect(page.locator('#ring .mastery-value')).toHaveText('—');
  await expect(page.locator('#ring circle')).toHaveCount(1); // no fill, not even a dot
  await expect(page.locator('[data-sk-exam-best]')).toHaveText('not taken yet');
  await expect(page.locator('#exercises li').first()).toHaveAttribute('data-status', 'new');
});

test('placeholders follow progress recorded on the page and in other tabs', async ({ page, context }) => {
  await seed(page, ITEMS);
  await page.goto('/dashboard.html');
  await expect(page.locator('#due-all')).toHaveText('2');
  // right this time: out of box 0, due tomorrow
  await page.evaluate(async () => {
    const { storeFor } = await import('/build/lib/store.js' as string);
    storeFor('mini').recordMc('mc-rc-tiefpass-002', { chosen: ['B'], score: 1, conf: 'unsure', ms: 1 }, { examDate: '2027-02-15' });
  });
  await expect(page.locator('#due-all')).toHaveText('1');
  await expect(page.locator('[data-topic-row="rc-tiefpass"] [data-sk-accuracy]')).toHaveText('50%');
  await expect(page.locator('#ring .mastery-value')).toHaveText('55%');

  // a second tab rates the other exercise
  const other = await context.newPage();
  await other.goto('/dashboard.html');
  await other.evaluate(async () => {
    const { storeFor } = await import('/build/lib/store.js' as string);
    storeFor('mini').rateEx('ex-st-teiler', 'ffffffff', 'partial');
  });
  await expect(page.locator('#exercises li').nth(1)).toHaveAttribute('data-status', 'partial');
  await expect(page.locator('#exercises li').nth(1).locator('[data-sk-status]')).toHaveText('Partly');
});

test('sk-plan uses the shell slot for its checkbox and the shell banner', async ({ page }) => {
  await page.goto('/dashboard.html');
  const plan = page.locator('sk-plan');
  const sessions = plan.locator('li.session');
  await expect(sessions.first().locator('[data-sk-plan-slot] input[type=checkbox]')).toHaveCount(1);
  await expect(sessions.first().getByRole('checkbox')).toHaveAccessibleName('Done: Die Teilerregel sicher anwenden');
  await expect(plan.locator('.sk-plan-behind')).toHaveCount(0); // no second banner
  const banner = plan.locator('[data-sk-behind]');
  await expect(banner).toBeVisible();
  await expect(banner.locator('[data-sk-behind-text]')).toHaveText('2 past sessions are not done.');
  await sessions.first().getByRole('checkbox').check();
  await expect(banner.locator('[data-sk-behind-text]')).toHaveText('1 past session is not done.');
  await sessions.nth(1).getByRole('checkbox').check();
  await expect(banner).toBeHidden();
  // the last session done: no next session left
  await sessions.nth(2).getByRole('checkbox').check();
  await expect(page.locator('#next [data-session-date]:visible')).toHaveCount(0);
  await expect(page.locator('#next [data-no-session]')).toBeVisible();
  expect((await progress(page)).items['plan:s-2027-02-10-a']).toEqual({ done: true });
});
