import { readFile } from 'node:fs/promises';
import { expect, test } from '@playwright/test';
import { COURSE, progress, seed } from './helpers.ts';

const attempt = (t: string, score: number, conf: 'sure' | 'unsure', chosen = ['A']) => ({ t, chosen, score, conf, ms: 1000 });

const ITEMS = {
  'mc:mc-rc-tiefpass-001': { h: 'aaaaaaaa', box: 3, due: '2026-11-20', attempts: [
    attempt('2026-11-01T10:00:00Z', 0, 'unsure', ['B']), attempt('2026-11-03T10:00:00Z', 1, 'sure'),
  ] },
  'mc:mc-rc-tiefpass-002': { h: 'bbbbbbbb', box: 0, due: '2026-11-05', attempts: [
    attempt('2026-11-05T10:00:00Z', 0, 'sure', ['A', 'C']),
  ] },
  'mc:mc-rc-filter-003': { h: 'cccccccc', box: 2, due: '2026-11-08', attempts: [
    attempt('2026-11-05T11:00:00Z', 1, 'sure'),
  ] },
  'mc:pk1-mc-01': { h: 'dddddddd', box: null, due: null, attempts: [attempt('2026-11-06T10:00:00Z', 1, 'unsure')] },
  'ex:ex-rc-tp-grenzfrequenz': { h: 'eeeeeeee', hints: 1, answer_ok: true, rating: 'solved', box: 2, due: '2026-11-09' },
  'exam:probeklausur-1': { attempts: [
    { started: '2026-11-04T09:00:00Z', duration_s: 3300, points: { 'pk1-t1': 9, mc: 6 }, total: 15 },
  ] },
};

test.describe('sk-progress', () => {
  test.beforeEach(async ({ page }) => {
    await page.clock.install({ time: new Date('2026-11-10T12:00:00') });
    await seed(page, ITEMS);
    await page.goto('/progress.html');
  });

  test('topic bars, calibration and exam history', async ({ page }) => {
    const p = page.locator('sk-progress');
    // rc-tiefpass: last attempts 0, 1, 0 → 33%; rc-filter: 1 → 100%; overall 2 of 4 → 50%
    await expect(p.locator('.sk-ring')).toHaveAttribute('aria-label', '50% right in the last 10 answers per topic');
    await expect(p.locator('.sk-stats')).toContainText('5 answers');
    await expect(p.locator('.sk-stats')).toContainText('2 reviews due'); // 002, filter-003
    await expect(p.locator('.sk-stats')).toContainText('1 exercise to review');
    await expect(p.locator('.sk-stats')).toContainText('1 misconception');
    await expect(p.locator('.sk-stats')).toContainText('1 exercise solved');
    const topics = p.locator('.sk-topic');
    await expect(topics).toHaveCount(3);
    await expect(topics.nth(0)).toContainText('Spannungsteiler');
    await expect(topics.nth(0)).toContainText('not started');
    await expect(topics.nth(1)).toContainText('RC-Tiefpass');
    await expect(topics.nth(1).locator('.sk-topic-value')).toHaveText('33%');
    await expect(topics.nth(1).locator('.sk-topic-meta')).toHaveText('2 questions answered · 1 due · 1 misconception');
    await expect(topics.nth(2).locator('.sk-topic-value')).toHaveText('100%');
    const calib = p.locator('.sk-calib-row');
    await expect(calib.nth(0)).toContainText('When sure');
    await expect(calib.nth(0).locator('.sk-topic-value')).toHaveText('67%');
    await expect(calib.nth(1).locator('.sk-topic-value')).toHaveText('50%');
    await expect(p.locator('.sk-exam-history tbody tr')).toHaveText([/Probeklausur 1.*4 Nov 2026.*15 \/ 20.*55 min/]);
  });

  test('updates when progress changes on the page', async ({ page }) => {
    await page.evaluate(async () => {
      const { storeFor } = await import('/build/lib/store.js' as string);
      storeFor('mini').recordMc('mc-spannungsteiler-001', { chosen: ['A'], score: 1, conf: 'sure', ms: 1 });
    });
    await expect(page.locator('sk-progress .sk-topic').nth(0)).toContainText('100%');
    await expect(page.locator('sk-progress .sk-stats')).toContainText('6 answers');
  });
});

test('sk-plan: done checkboxes persist and the behind-schedule banner counts past sessions', async ({ page }) => {
  await page.clock.install({ time: new Date('2026-11-10T12:00:00') });
  await page.goto('/progress.html');
  const plan = page.locator('sk-plan');
  const boxes = plan.getByRole('checkbox');
  await expect(boxes).toHaveCount(3);
  const banner = plan.locator('.sk-plan-behind');
  await expect(banner).toContainText('Behind schedule: 2 past sessions are not done.');
  await expect(banner.locator('code')).toHaveText(`/regenerate ${COURSE} plan`);
  await boxes.first().check();
  await expect(banner).toContainText('1 past session is not done.');
  await expect(plan.locator('li').first()).toHaveClass(/is-done/);
  expect((await progress(page)).items['plan:s-2026-11-02-a']).toEqual({ done: true });
  await boxes.nth(1).check();
  await expect(banner).toBeHidden();
  await page.reload();
  await expect(boxes.first()).toBeChecked();
  await expect(boxes.nth(2)).not.toBeChecked();
});

test('sk-export: export downloads the progress file, import merges a file', async ({ page }) => {
  await page.clock.install({ time: new Date('2026-11-10T12:00:00') });
  await seed(page, { 'plan:s-2026-11-02-a': { done: false }, 'mc:mc-rc-tiefpass-001': ITEMS['mc:mc-rc-tiefpass-001'] });
  await page.goto('/progress.html');
  const ex = page.locator('sk-export');
  const download = page.waitForEvent('download');
  await ex.getByRole('button', { name: 'Export progress' }).click();
  const file = await download;
  expect(file.suggestedFilename()).toBe('studykit-progress-mini-2026-11-10.json');
  const data = JSON.parse(await readFile((await file.path()) ?? '', 'utf8'));
  expect(data).toMatchObject({ schema: 'studykit-progress/1', course: 'mini' });
  expect(Object.keys(data.items).sort()).toEqual(['mc:mc-rc-tiefpass-001', 'plan:s-2026-11-02-a']);
  await expect(ex.locator('.sk-export-status')).toHaveText('Saved studykit-progress-mini-2026-11-10.json.');

  const incoming = {
    schema: 'studykit-progress/1', course: 'mini', exported_at: '2026-11-09T10:00:00Z',
    items: {
      'plan:s-2026-11-02-a': { done: true },
      'mc:mc-rc-tiefpass-001': { h: 'aaaaaaaa', box: 4, due: '2026-11-30', attempts: [attempt('2026-11-09T10:00:00Z', 1, 'sure')] },
      'mc:mc-rc-filter-011': { h: 'ffffffff', box: 2, due: '2026-11-12', attempts: [attempt('2026-11-09T10:05:00Z', 1, 'sure')] },
    },
  };
  await ex.locator('input[type=file]').setInputFiles({
    name: 'other.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(incoming)),
  });
  await expect(ex.locator('.sk-export-status')).toHaveText('Imported 3 items (1 new, 2 merged).');
  const items = (await progress(page)).items;
  expect(items['plan:s-2026-11-02-a']).toEqual({ done: true });
  expect(items['mc:mc-rc-tiefpass-001'].attempts).toHaveLength(3);
  expect(items['mc:mc-rc-tiefpass-001'].box).toBe(4);
  await expect(page.locator('sk-plan').getByRole('checkbox').first()).toBeChecked(); // live update

  await ex.locator('input[type=file]').setInputFiles({
    name: 'wrong.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify({ ...incoming, course: 'get2' })),
  });
  await expect(ex.locator('.sk-export-status')).toHaveText('This file belongs to the course “get2”, not “mini”.');
  await expect(ex.locator('.sk-export-status')).toHaveClass(/is-bad/);
});

test('full storage: stored progress stays visible and exportable, new progress lives for the page', async ({ page }) => {
  await page.clock.install({ time: new Date('2026-11-10T12:00:00') });
  await seed(page, ITEMS);
  await page.goto('/progress.html');
  // Another site on the same origin (localhost:4321) uses up the quota.
  const probeOk = await page.evaluate(() => {
    let chunk = 'x'.repeat(1 << 20);
    for (let i = 0; chunk.length > 0; ) {
      try {
        localStorage.setItem(`filler-${i++}`, chunk);
      } catch {
        chunk = chunk.slice(0, chunk.length / 2);
      }
    }
    try {
      localStorage.setItem('studykit:probe', '1');
      return true;
    } catch {
      return false;
    }
  });
  expect(probeOk).toBe(false);
  await page.reload();
  const p = page.locator('sk-progress');
  await expect(p.locator('.sk-stats')).toContainText('5 answers');
  await expect(page.locator('.sk-export-note')).toContainText('storage for this site is full');
  await page.locator('sk-plan').getByRole('checkbox').first().check(); // only in memory
  await expect(page.locator('sk-plan').getByRole('checkbox').first()).toBeChecked();

  const download = page.waitForEvent('download');
  await page.locator('sk-export').getByRole('button', { name: 'Export progress' }).click();
  const data = JSON.parse(await readFile((await (await download).path()) ?? '', 'utf8'));
  expect(Object.keys(data.items).sort()).toEqual([...Object.keys(ITEMS), 'plan:s-2026-11-02-a'].sort());
  expect(data.items['plan:s-2026-11-02-a']).toEqual({ done: true });
});

test('sk-theme: light, dark and system are stored and applied', async ({ page }) => {
  await page.goto('/progress.html');
  const theme = page.locator('sk-theme');
  await expect(theme.getByRole('radio', { name: 'System' })).toBeChecked();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'system');
  await theme.getByRole('radio', { name: 'Dark' }).check();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  expect(await page.evaluate(() => localStorage.getItem('studykit:theme'))).toBe('dark');
  const bg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
  expect(bg).toBe('rgb(14, 18, 23)');
  await page.reload();
  await expect(theme.getByRole('radio', { name: 'Dark' })).toBeChecked();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await theme.getByRole('radio', { name: 'Light' }).focus();
  await page.keyboard.press('Space');
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  await theme.getByRole('radio', { name: 'System' }).check();
  expect(await page.evaluate(() => localStorage.getItem('studykit:theme'))).toBe('system');
});

test('sk-theme: one rule with the head script and the CSS; system follows the OS', async ({ page }) => {
  const meta = page.locator('meta[name="color-scheme"]');
  const bg = () => page.evaluate(() => getComputedStyle(document.body).backgroundColor);
  // The theme is on <html> before <body> exists: no flash of the wrong theme on reload.
  await page.addInitScript(() => {
    new MutationObserver((_, observer) => {
      if (!document.body) return;
      (window as unknown as { themeAtBody: string }).themeAtBody = document.documentElement.dataset.theme ?? '';
      observer.disconnect();
    }).observe(document, { childList: true, subtree: true });
  });

  await page.emulateMedia({ colorScheme: 'dark' });
  await page.goto('/progress.html');
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'system');
  await expect(meta).toHaveAttribute('content', 'light dark');
  expect(await bg()).toBe('rgb(14, 18, 23)'); // system + dark OS → dark
  await page.emulateMedia({ colorScheme: 'light' });
  expect(await bg()).toBe('rgb(255, 255, 255)');

  // light chosen while the OS is dark: light, also right after a reload
  await page.emulateMedia({ colorScheme: 'dark' });
  await page.locator('sk-theme').getByRole('radio', { name: 'Light' }).check();
  await expect(meta).toHaveAttribute('content', 'light');
  expect(await bg()).toBe('rgb(255, 255, 255)');
  await page.reload();
  expect(await page.evaluate(() => (window as unknown as { themeAtBody: string }).themeAtBody)).toBe('light');
  await expect(meta).toHaveAttribute('content', 'light');
  expect(await bg()).toBe('rgb(255, 255, 255)');

  // an unknown stored value is 'system' everywhere
  await page.evaluate(() => localStorage.setItem('studykit:theme', 'sepia'));
  await page.reload();
  expect(await page.evaluate(() => (window as unknown as { themeAtBody: string }).themeAtBody)).toBe('system');
  await expect(page.locator('sk-theme').getByRole('radio', { name: 'System' })).toBeChecked();
  expect(await bg()).toBe('rgb(14, 18, 23)');
});
