// The quiz modes of <sk-quiz> (docs/architecture.md §3.2): Practice, Test (?n=, ?minutes=),
// Mistakes, Due and Mixed, each ending on the result screen with the score per topic. The
// question order is random, so every step reads the question on screen and answers it from
// its data-correct attributes.
import { expect, test, type Locator, type Page } from '@playwright/test';
import { answer, C, current, elementsReady, expectResult, freezeDay, NOW, pageDay, Tally, type How } from './helpers.ts';

test.beforeEach(async ({ page }) => {
  await freezeDay(page);
});

/** Open a mode of the MC hub (an exclusive <details> accordion) and return its quiz. */
async function mode(page: Page, id: 'practice' | 'test' | 'mistakes' | 'due' | 'mixed'): Promise<Locator> {
  const details = page.locator(`details#${id}`);
  if ((await details.getAttribute('open')) === null) await details.locator('summary').click();
  const quiz = details.locator('sk-quiz');
  await expect(quiz.locator('.sk-quiz-count')).not.toBeEmpty();
  return quiz;
}

/** A mode with nothing to offer shows only its message, without the start form. */
async function expectNoForm(quiz: Locator): Promise<void> {
  await expect(quiz.locator('.sk-quiz-actions')).toHaveCount(1);
  await expect(quiz.locator('.sk-quiz-actions')).toBeHidden();
  await expect(quiz.locator('.sk-quiz-fields')).toBeHidden();
}

/** Answer the question on screen; in instant-feedback modes check it and see the verdict. */
async function step(quiz: Locator, tally: Tally, how: How, conf: 'Sure' | 'Unsure' = 'Unsure', instant = true): Promise<string> {
  const mc = current(quiz);
  const id = (await mc.getAttribute('data-id')) ?? '';
  const topic = (await mc.getAttribute('data-topic')) ?? '';
  const next = quiz.locator('.sk-quiz-nav .sk-btn-primary');
  await expect(next).toHaveAttribute('aria-disabled', 'true');
  const score = await answer(mc, how, conf);
  if (instant) {
    await mc.getByRole('button', { name: 'Check' }).click();
    await expect(mc.locator('.sk-mc-feedback')).toContainText(score === 1 ? 'Correct.' : 'Not correct.');
    await expect(mc.locator('.sk-explanation')).toBeVisible();
  } else {
    // Test mode: no Check, no feedback until the end
    await expect(mc.getByRole('button', { name: 'Check' })).toHaveCount(0);
    await expect(mc.locator('.sk-mc-feedback')).toBeEmpty();
    await expect(mc.locator('.sk-explanation')).toBeHidden();
  }
  await expect(next).toHaveAttribute('aria-disabled', 'false');
  tally.add(topic, score);
  return id;
}

/** Answer one question on a topic page (outside any quiz) and return its id. */
async function answerOnTopicPage(page: Page, topic: string, how: How, conf: 'Sure' | 'Unsure'): Promise<string> {
  await page.goto(`${C}/mc/${topic}/`);
  await elementsReady(page);
  const mc = page.locator('ol.questions sk-mc').first();
  await answer(mc, how, conf);
  await mc.getByRole('button', { name: 'Check' }).click();
  await expect(mc.locator('.sk-mc-feedback')).not.toBeEmpty();
  return (await mc.getAttribute('data-id')) ?? '';
}

test('Practice: instant feedback per question, ?n= sets the length, result per topic', async ({ page }) => {
  await page.goto(`${C}/mc/wechselstrom/?n=4`);
  const quiz = page.locator('section.practice sk-quiz');
  await expect(quiz).toHaveAttribute('data-mode', 'practice');
  await expect(quiz.locator('.sk-quiz-count')).toHaveText('10 questions available.');
  await expect(quiz.getByLabel('Questions')).toHaveValue('4');
  await quiz.getByRole('button', { name: 'Start' }).click();

  const tally = new Tally();
  let misconception = '';
  for (let i = 0; i < 4; i++) {
    await expect(quiz.locator('.sk-quiz-pos')).toHaveText(`Question ${i + 1} of 4`);
    const how: How = i === 1 ? 'wrong' : 'right';
    const id = await step(quiz, tally, how, how === 'wrong' ? 'Sure' : 'Unsure');
    if (how === 'wrong') misconception = id;
    await quiz.getByRole('button', { name: i === 3 ? 'See result' : 'Next' }).click();
  }
  await expectResult(quiz, tally);
  const result = quiz.locator('.sk-quiz-result');
  await expect(result.locator('.sk-quiz-meta')).toContainText('Practice · 4 of 4 answered');
  await expect(result.locator('.sk-quiz-misconceptions a').first()).toHaveAttribute('href', `#review-${misconception}`);
  await expect(result.getByRole('button', { name: 'Retry mistakes (1)' })).toBeVisible();

  // "New quiz" replaces the result screen: focus goes to the start form, not to the page
  await result.getByRole('button', { name: 'New quiz' }).focus();
  await page.keyboard.press('Enter');
  await expect(quiz.getByLabel('Questions')).toBeFocused();
});

test('Test: ?n= and ?minutes= pre-fill the form, feedback waits for the end, time-up ends the quiz', async ({ page }) => {
  await page.goto(`${C}/mc/?n=3&minutes=5`);
  const quiz = await mode(page, 'test');
  await expect(quiz).toHaveAttribute('data-mode', 'test');
  await expect(quiz.locator('.sk-quiz-count')).toHaveText('30 questions available.');
  await expect(quiz.getByLabel('Questions')).toHaveValue('3');
  await expect(quiz.getByLabel('Time limit (minutes)')).toHaveValue('5');
  await quiz.getByRole('button', { name: 'Start' }).click();
  await expect(quiz.locator('.sk-quiz-time')).toHaveText(/^Time left [45]:\d\d$/);

  const tally = new Tally();
  await step(quiz, tally, 'right', 'Sure', false);
  await quiz.getByRole('button', { name: 'Next' }).click();
  await expect(quiz.locator('.sk-quiz-pos')).toHaveText('Question 2 of 3');
  await step(quiz, tally, 'wrong', 'Unsure', false);
  await quiz.getByRole('button', { name: 'Next' }).click();
  await expect(quiz.locator('.sk-quiz-pos')).toHaveText('Question 3 of 3');
  tally.add((await current(quiz).getAttribute('data-topic')) ?? '', 0); // left open

  await page.clock.fastForward('05:00');
  await expectResult(quiz, tally);
  const result = quiz.locator('.sk-quiz-result');
  await expect(result.locator('.sk-quiz-meta')).toContainText('Test · 2 of 3 answered');
  await expect(result.locator('.sk-quiz-meta')).toContainText('time is up');
  // now every answer is revealed, the wrong and the open one unfolded
  const items = result.locator('.sk-quiz-review details');
  await expect(items).toHaveCount(3);
  await expect(items.nth(0)).not.toHaveAttribute('open');
  for (const i of [1, 2]) {
    await expect(items.nth(i)).toHaveAttribute('open');
    await expect(items.nth(i).locator('.sk-mc-feedback')).toContainText('Not correct.');
  }
});

test('Mistakes: a wrong answer comes back, a right one clears it', async ({ page }) => {
  const wrong = await answerOnTopicPage(page, 'spannungsteiler', 'wrong', 'Unsure');
  await page.goto(`${C}/mc/`);
  let quiz = await mode(page, 'mistakes');
  await expect(quiz.locator('.sk-quiz-count')).toHaveText('1 question available.');
  await quiz.getByRole('button', { name: 'Start' }).click();
  await expect(current(quiz)).toHaveAttribute('data-id', wrong);
  const tally = new Tally();
  await step(quiz, tally, 'right');
  await quiz.getByRole('button', { name: 'See result' }).click();
  await expectResult(quiz, tally);

  await page.reload();
  quiz = await mode(page, 'mistakes');
  await expect(quiz.locator('.sk-quiz-count')).toHaveText(
    'No mistakes to review: every question you answered was right last time.',
  );
  await expectNoForm(quiz);
});

test('Due: a right answer is due again after three days', async ({ page }) => {
  const id = await answerOnTopicPage(page, 'wechselstrom', 'right', 'Sure');
  await page.goto(`${C}/mc/`);
  let quiz = await mode(page, 'due');
  const due = await pageDay(page, 3);
  await expect(quiz.locator('.sk-quiz-count')).toHaveText(`Nothing is due today. The next review is in 3 days (${due}).`);
  await expectNoForm(quiz);

  await page.clock.setSystemTime(new Date(NOW.getTime() + 3 * 86_400_000));
  await page.reload();
  quiz = await mode(page, 'due');
  await expect(quiz.locator('.sk-quiz-count')).toHaveText('1 question available.');
  await quiz.getByRole('button', { name: 'Start' }).click();
  await expect(current(quiz)).toHaveAttribute('data-id', id);
  const tally = new Tally();
  await step(quiz, tally, 'right', 'Sure');
  await expect(current(quiz).locator('.sk-mc-feedback')).toContainText('Next review in 7 days.'); // box 2 → 3
  await quiz.getByRole('button', { name: 'See result' }).click();
  await expectResult(quiz, tally);
  await expect(quiz.locator('.sk-quiz-meta')).toContainText('Due for review · 1 of 1 answered');
});

test('Mixed: all banks together, filtered by topic, result per topic', async ({ page }) => {
  await page.goto(`${C}/mc/?n=5`);
  const quiz = await mode(page, 'mixed');
  await expect(quiz.locator('.sk-quiz-count')).toHaveText('30 questions available.');
  const topics = quiz.locator('.sk-quiz-filter').filter({ hasText: 'Topics' }).getByRole('checkbox');
  await expect(topics).toHaveCount(3);
  const skipped = quiz.getByRole('checkbox', { name: 'Spannungsteiler und Ersatzquellen' });
  await skipped.uncheck();
  await expect(quiz.locator('.sk-quiz-count')).toHaveText('20 questions available.');
  await expect(quiz.getByLabel('Questions')).toHaveValue('5');
  await quiz.getByRole('button', { name: 'Start' }).click();

  const tally = new Tally();
  for (let i = 0; i < 5; i++) {
    await expect(quiz.locator('.sk-quiz-pos')).toHaveText(`Question ${i + 1} of 5`);
    await expect(current(quiz)).not.toHaveAttribute('data-topic', 'spannungsteiler');
    await step(quiz, tally, i % 2 === 0 ? 'right' : 'wrong');
    await quiz.getByRole('button', { name: i === 4 ? 'See result' : 'Next' }).click();
  }
  await expectResult(quiz, tally);
  await expect(quiz.locator('.sk-quiz-meta')).toContainText('Mixed · 5 of 5 answered');
});
