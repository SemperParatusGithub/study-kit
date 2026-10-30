// <sk-pomodoro> in the harness header: the panel, the running timer on the button, across a
// reload, the end of a phase and the settings (lib/pomodoro.ts holds the rules).
import { expect, test, type Page } from '@playwright/test';

const KEY = 'studykit:pomodoro';

const stored = (page: Page) => page.evaluate((key) => JSON.parse(localStorage.getItem(key) ?? 'null'), KEY);

test.beforeEach(async ({ page }) => {
  await page.clock.install({ time: new Date('2026-11-10T09:00:00') });
});

test('start shows the time left top right and it survives a reload', async ({ page }) => {
  await page.goto('/index.html');
  const timer = page.locator('sk-pomodoro');
  const toggle = timer.locator('.sk-pomo-toggle');
  await expect(toggle).toHaveAccessibleName(/Pomodoro timer: Focus, 25:00 left, ready/);
  await expect(timer.locator('.sk-pomo-chip')).toBeEmpty();

  await toggle.click();
  await expect(toggle).toHaveAttribute('aria-expanded', 'true');
  await page.getByRole('button', { name: 'Start', exact: true }).click();
  await page.clock.runFor(61_000);
  await expect(timer.locator('.sk-pomo-chip')).toHaveText('Focus23:59');
  await expect(timer).toHaveAttribute('data-running', '');
  await expect(page).toHaveTitle(/^23:59 Focus · /);

  // Escape closes the panel; the button keeps counting
  await page.keyboard.press('Escape');
  await expect(timer.locator('.sk-pomo-panel')).toBeHidden();
  await expect(toggle).toBeFocused();

  // the clock runs on while the page reloads, so allow a few seconds
  await page.reload();
  await page.clock.runFor(1_000);
  await expect(timer.locator('.sk-pomo-chip')).toHaveText(/^Focus23:5[0-8]$/);

  await toggle.click();
  await page.getByRole('button', { name: 'Pause', exact: true }).click();
  const paused = await timer.locator('.sk-pomo-chip').textContent();
  await page.clock.runFor(10_000);
  await expect(timer.locator('.sk-pomo-chip')).toHaveText(paused ?? '');
  await expect(page.getByRole('button', { name: 'Resume', exact: true })).toBeVisible();
  await expect(page).not.toHaveTitle(/^\d+:\d\d Focus/);
  await page.getByRole('button', { name: 'Reset', exact: true }).click();
  await expect(timer.locator('.sk-pomo-chip')).toBeEmpty();
  expect((await stored(page)).timer).toEqual({ phase: 'focus', done: 0, endsAt: null, left: 25 * 60_000 });
});

test('the end of focus counts it and waits at the break', async ({ page }) => {
  await page.goto('/index.html');
  const timer = page.locator('sk-pomodoro');
  await timer.locator('.sk-pomo-toggle').click();
  const ended = page.evaluate(
    () => new Promise((resolve) => document.addEventListener('sk:pomodoro-end', (e) => resolve((e as CustomEvent).detail), { once: true })),
  );
  await page.getByRole('button', { name: 'Start', exact: true }).click();
  await page.clock.runFor(25 * 60_000 + 1_000);
  expect(await ended).toEqual({ ended: 'focus', next: 'short' });
  await expect(timer.locator('.sk-pomo-phase')).toHaveText('Short break');
  await expect(timer.locator('.sk-pomo-time')).toHaveText('5:00');
  await expect(timer.locator('.sk-pomo-done')).toHaveText('1 focus phase done');
  await expect(timer).not.toHaveAttribute('data-running', '');
  await expect(page.getByRole('button', { name: 'Start', exact: true })).toBeVisible();
});

test('settings change the phase lengths and are kept', async ({ page }) => {
  await page.goto('/index.html');
  const timer = page.locator('sk-pomodoro');
  await timer.locator('.sk-pomo-toggle').click();
  await page.getByLabel('Focus', { exact: true }).fill('50');
  await page.getByLabel('Focus', { exact: true }).press('Tab');
  await expect(timer.locator('.sk-pomo-time')).toHaveText('50:00');
  await page.getByLabel('Long break after').fill('99');
  await page.getByLabel('Long break after').press('Tab');
  await expect(page.getByLabel('Long break after')).toHaveValue('12');
  await page.getByLabel('Start the next phase by itself').check();
  const settings = (await stored(page)).settings;
  expect(settings).toMatchObject({ focus: 50, longEvery: 12, autoStart: true });

  // a click outside closes the panel
  await page.mouse.click(10, 500);
  await expect(timer.locator('.sk-pomo-panel')).toBeHidden();
});
