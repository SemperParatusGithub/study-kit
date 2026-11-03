// <sk-cards>: a round of flash cards, its ratings in the store, and what comes back when.
import { expect, test, type Page } from '@playwright/test';
import { KEY } from './helpers.ts';

const cards = (page: Page) => page.locator('sk-cards');
const panel = (page: Page) => cards(page).locator('.sk-card-panel');
const entry = (page: Page, id: string) =>
  page.evaluate(([key, item]) => JSON.parse(localStorage.getItem(key as string) ?? '{"items":{}}').items[item as string], [KEY, `card:${id}`]);

test.beforeEach(async ({ page }) => {
  await page.clock.setFixedTime(new Date('2026-11-03T10:00:00+01:00'));
});

test('new cards come in their order; think, turn, rate', async ({ page }) => {
  await page.goto('/cards.html');
  await expect(cards(page).locator('.sk-cards-counts')).toHaveText('0 due · 3 new · 0 known · 3 in all');
  await expect(panel(page)).toContainText('Card 1 of 3');
  await expect(panel(page)).toContainText('Front one');
  await expect(panel(page)).not.toContainText('Back one');

  await page.getByRole('button', { name: /Show answer/ }).click();
  await expect(panel(page)).toContainText('Back one');
  await page.getByRole('button', { name: /Knew it/ }).click();
  await expect(panel(page)).toContainText('Front two');
  expect(await entry(page, 'card-one-001')).toEqual({ h: 'aaaaaaaa', box: 2, due: '2026-11-06', reviews: 1 });
  await expect(cards(page).locator('.sk-cards-counts')).toHaveText('0 due · 2 new · 0 known · 3 in all');
});

test('a card you did not know comes back once, without a second rating', async ({ page }) => {
  await page.goto('/cards.html?topic=two');
  await expect(panel(page)).toContainText('Card 1 of 1');
  await page.getByRole('button', { name: /Show answer/ }).click();
  await page.getByRole('button', { name: /Didn't know/ }).click();
  await expect(panel(page)).toContainText('Card 2 of 2');
  await expect(panel(page)).toContainText('Front three');
  expect(await entry(page, 'card-two-001')).toMatchObject({ box: 1, due: '2026-11-04', reviews: 1 });
  await page.getByRole('button', { name: /Show answer/ }).click();
  await page.getByRole('button', { name: /Knew it/ }).click();
  await expect(panel(page)).toContainText('Round done');
  await expect(panel(page)).toContainText('0 known, 1 to practise again.');
  await expect(panel(page)).toContainText('Next review tomorrow.');
  expect(await entry(page, 'card-two-001')).toMatchObject({ box: 1, reviews: 1 });
});

test('the keyboard works the round, and a rated card waits for its day', async ({ page }) => {
  await page.goto('/cards.html');
  for (const front of ['Front one', 'Front two', 'Front three']) {
    await expect(panel(page)).toContainText(front);
    await page.keyboard.press('Space');
    await expect(panel(page)).toHaveAttribute('data-turned', 'true');
    await page.keyboard.press('2');
  }
  await expect(panel(page)).toContainText('Round done');
  await expect(panel(page)).toContainText('3 known, 0 to practise again.');

  await page.reload();
  await expect(panel(page)).toContainText('Nothing due today');
  await expect(panel(page)).toContainText('Next review in 3 days.');
  await page.getByRole('button', { name: 'Go through all cards' }).click();
  await expect(panel(page)).toContainText('Card 1 of 3');

  await page.clock.setFixedTime(new Date('2026-11-06T10:00:00+01:00'));
  await page.reload();
  await expect(cards(page).locator('.sk-cards-counts')).toHaveText('3 due · 0 new · 0 known · 3 in all');
  await expect(panel(page)).toContainText('Card 1 of 3');
});

test('the chapter filter narrows the round, and the list shows every answer', async ({ page }) => {
  await page.goto('/cards.html');
  await cards(page).getByLabel('Chapter').selectOption('two');
  await expect(panel(page)).toContainText('Card 1 of 1');
  await expect(cards(page).locator('.sk-cards-counts')).toHaveText('0 due · 1 new · 0 known · 1 in all');

  const list = cards(page).locator('.sk-cards-list');
  await expect(list).toBeHidden();
  await page.getByRole('button', { name: 'Show all as a list' }).click();
  await expect(list).toBeVisible();
  await expect(list).toContainText('Back two');
  await page.getByRole('button', { name: 'Hide the list' }).click();
  await expect(list).toBeHidden();
});

test('typing in the chapter filter does not rate a card', async ({ page }) => {
  await page.goto('/cards.html');
  await cards(page).getByLabel('Chapter').focus();
  await page.keyboard.press('Space');
  await page.keyboard.press('Escape');
  await expect(panel(page)).toHaveAttribute('data-turned', 'false');
});
