// A topic (kind: topic, docs/architecture.md §5.6): examples/how-bitcoin-works in the built site.
import { expect, test } from '@playwright/test';
import { elementsReady, freezeDay } from './helpers.ts';

const T = '/c/how-bitcoin-works';
const CHAPTERS = ['why-bitcoin', 'keys-and-transactions', 'blocks-and-mining', 'network-and-consensus', 'scaling-and-limits'];
const PAGES = ['/', `${T}/`, `${T}/summary/`, ...CHAPTERS.map((c) => `${T}/summary/${c}/`), `${T}/cards/`, `${T}/glossary/`];

test('the home page lists it in its own section, without an exam', async ({ page }) => {
  await page.goto('/');
  const section = page.locator('.topic-section');
  await expect(section.getByRole('heading', { name: 'Your topics' })).toBeVisible();
  const card = section.locator('.topic-card');
  await expect(card.getByRole('link', { name: 'How Bitcoin works' })).toHaveAttribute('href', `${T}/`);
  await expect(card).not.toContainText('Exam');
  await elementsReady(page);
  await expect(card.locator('[data-sk-cards-due]')).toHaveText(/^[1-9][0-9]*$/);
  await expect(page.locator('.course-cards').first().getByRole('link', { name: /Grundlagen RC/ })).toBeVisible();
});

test('it has the tabs of a topic and none of a course', async ({ page }) => {
  await page.goto(`${T}/`);
  await expect(page.locator('.course-nav a')).toHaveText(['Overview', 'Explanation', 'Cards', 'Glossary']);
  for (const missing of ['plan', 'mc', 'exams', 'exercises', 'cheatsheet', 'progress']) {
    const response = await page.goto(`${T}/${missing}/`);
    expect(response?.status(), missing).toBe(404);
  }
});

test('the overview shows the chapters and the concept map', async ({ page }) => {
  await page.goto(`${T}/`);
  await expect(page.locator('.topic-chapters li')).toHaveCount(5);
  await expect(page.locator('.overview figure')).toHaveCount(1);
  await expect(page.locator('.overview')).toContainText('Concept map');
  await expect(page.getByRole('heading', { name: 'Exam at a glance' })).toHaveCount(0);
});

test('a chapter explains and leads to its flash cards', async ({ page }) => {
  await page.goto(`${T}/summary/blocks-and-mining/`);
  await expect(page.locator('.sk-definition').first()).toBeVisible();
  await expect(page.locator('#test-yourself')).toHaveCount(0);
  await page.getByRole('link', { name: 'Flash cards for this chapter' }).click();
  await expect(page).toHaveURL(/\/cards\/\?topic=blocks-and-mining$/);
  await elementsReady(page);
  await expect(page.getByLabel('Chapter')).toHaveValue('blocks-and-mining');
});

test('flash cards turn, rate and wait for their day', async ({ page }) => {
  await freezeDay(page);
  await page.goto(`${T}/cards/`);
  await elementsReady(page);
  const cards = page.locator('sk-cards');
  await expect(cards.locator('.sk-card-face-back')).toHaveCount(0);
  await page.getByRole('button', { name: /Show answer/ }).click();
  await expect(cards.locator('.sk-card-face-back')).toBeVisible();
  const id = await cards.locator('.sk-card-panel').getAttribute('data-card');
  await page.getByRole('button', { name: /Knew it/ }).click();
  const stored = await page.evaluate(
    (item) => JSON.parse(localStorage.getItem('studykit:v1:how-bitcoin-works') ?? '{}').items[item],
    `card:${id}`,
  );
  expect(stored).toMatchObject({ box: 2, reviews: 1 });
  expect(stored.h).toMatch(/^[0-9a-f]{8}$/);
  await page.reload();
  await elementsReady(page);
  await expect(cards.locator('.sk-card-panel')).not.toHaveAttribute('data-card', id ?? '');
});

test.describe('without JavaScript', () => {
  test.use({ javaScriptEnabled: false });

  test('the cards are a list with their answers', async ({ page }) => {
    await page.goto(`${T}/cards/`);
    await expect(page.locator('sk-card').first()).toBeVisible();
    await expect(page.locator('sk-card .sk-card-back').first()).toBeVisible();
  });
});

test('on paper the cards are a list with their answers', async ({ page }) => {
  await page.goto(`${T}/cards/`);
  await elementsReady(page);
  await page.emulateMedia({ media: 'print' });
  await expect(page.locator('.sk-cards-list')).toBeVisible();
  await expect(page.locator('.sk-cards-bar')).toBeHidden();
  await expect(page.locator('.sk-cards-stage')).toBeHidden();
});

test('the glossary lists the terms from A to Z and links to their chapter', async ({ page }) => {
  await page.goto(`${T}/glossary/`);
  const terms = await page.locator('.glossary dt').allTextContents();
  expect(terms.length).toBeGreaterThan(10);
  expect(terms).toEqual(expect.arrayContaining(['Merkle tree']));
  const folded = terms.map((t) => t.trim().toLowerCase());
  expect(folded.indexOf('merkle tree')).toBeGreaterThan(0);
  const merkle = page.locator('.glossary-entry', { hasText: 'Merkle tree' }).first();
  await merkle.getByRole('link').click();
  await expect(page).toHaveURL(/\/summary\/blocks-and-mining\//);
});

test('at 320 px no page of a topic scrolls sideways', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 800 });
  for (const path of PAGES) {
    await page.goto(path);
    expect(await page.evaluate(() => document.documentElement.scrollWidth), path).toBeLessThanOrEqual(320);
  }
});
