// Language of parts (WCAG 3.1.2, docs/architecture.md §3.2): the UI is English, the
// sample course is German. Screen readers pick their voice from the nearest lang, so every
// text must resolve to the language it is written in, also the text the elements generate.
import { expect, test, type Locator } from '@playwright/test';
import { C, current, elementsReady, freezeDay } from './helpers.ts';

/** The language `loc` is read in: its nearest lang attribute. */
function langOf(loc: Locator): Promise<string | null> {
  return loc.evaluate((el) => el.closest('[lang]')?.getAttribute('lang') ?? null);
}

async function expectLang(loc: Locator, lang: string): Promise<void> {
  await expect(loc).toBeAttached();
  expect(await langOf(loc), (await loc.textContent())?.trim().slice(0, 60)).toBe(lang);
}

test.beforeEach(async ({ page }) => {
  await freezeDay(page);
});

test('quiz questions and topic names keep the course language inside the English quiz', async ({ page }) => {
  await page.goto(`${C}/mc/`);
  await elementsReady(page);
  const quiz = page.locator('.modes sk-quiz').first();
  await expectLang(quiz.locator('.sk-check-chip span').first(), 'de');
  await expectLang(quiz.getByRole('button', { name: 'Start' }), 'en');
  await quiz.getByRole('button', { name: 'Start' }).click();
  const mc = current(quiz);
  await expectLang(mc.locator('.sk-stem'), 'de');
  await expectLang(mc.locator('.sk-opt-text').first(), 'de');
  await expectLang(mc.locator('.sk-mc-instr'), 'en');
  await expectLang(mc.locator('.sk-mc-conf legend'), 'en');
  await expectLang(quiz.getByRole('button', { name: 'End quiz' }), 'en');

  // the same on the MC topic page and in a chapter's "Test yourself"
  await page.goto(`${C}/mc/rc-filter/`);
  const practice = page.locator('.practice sk-quiz');
  await practice.getByRole('button', { name: 'Start' }).click();
  await expectLang(current(practice).locator('.sk-stem'), 'de');
  await page.goto(`${C}/summary/rc-filter/`);
  const yourself = page.locator('#test-yourself sk-quiz');
  await yourself.getByRole('button', { name: 'Start' }).click();
  await expectLang(current(yourself).locator('.sk-stem'), 'de');
});

test('the elements mark their own text English inside German content', async ({ page }) => {
  await page.goto(`${C}/mc/rc-filter/`);
  await elementsReady(page);
  const mc = page.locator('main sk-mc').last();
  await expectLang(mc.locator('.sk-stem'), 'de');
  for (const sel of ['.sk-mc-head', '.sk-mc-instr', '.sk-mc-conf legend', '.sk-mc-actions button']) {
    await expectLang(mc.locator(sel).first(), 'en');
  }

  await page.goto(`${C}/exercises/ex-rc-tp-grenzfrequenz/`);
  await expectLang(page.getByRole('button', { name: 'Show hint 1 of 2' }), 'en');
  await expectLang(page.locator('sk-answer-check .sk-check-title'), 'en');
  await expectLang(page.locator('sk-answer-check .sk-check-label').first(), 'de');
  await expectLang(page.getByRole('button', { name: 'Solved' }), 'en');

  await page.goto(`${C}/exams/probeklausur-1/`);
  await expectLang(page.getByRole('button', { name: 'Start exam' }), 'en');
  await expectLang(page.locator('.sk-exam-cover h2'), 'en');

  await page.goto(`${C}/progress/`);
  await expectLang(page.locator('sk-progress .sk-progress-note'), 'en');
  await expectLang(page.locator('sk-progress .sk-topic-name').first(), 'de');
});

test('the session goal is in the course language on the home page and the overview', async ({ page }) => {
  for (const path of ['/', `${C}/`]) {
    await page.goto(path);
    await elementsReady(page);
    const goal = page.locator('.session-card:not([hidden]) .session-goal').first();
    await expectLang(goal, 'de');
  }
});
