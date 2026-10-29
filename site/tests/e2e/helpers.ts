// Shared helpers of the end-to-end suite. Everything about the content (ids, types, the
// right answers, topic titles) is read from the built pages at run time: options carry
// data-correct, and the quiz order and option order are never assumed.
import { expect, type Locator, type Page } from '@playwright/test';

export const COURSE = 'sample-course';
export const KEY = `studykit:v1:${COURSE}`;
export const SESSION_KEY = `studykit:v1:${COURSE}:session`;
export const C = `/c/${COURSE}`;

/**
 * A fixed moment inside the sample course's study period, far from its exam (2027-02-15),
 * so Leitner due days and the exam clamp are the same whenever the suite runs. The pages
 * run in Europe/Berlin (playwright.config.ts), where this is 10:00 on 2026-11-16.
 */
export const NOW = new Date('2026-11-16T10:00:00+01:00');

/** Run the page clock from NOW (time flows; fastForward and setSystemTime move it). */
export async function freezeDay(page: Page, at: Date = NOW): Promise<void> {
  await page.clock.install({ time: at });
}

/** The stored progress document of the sample course (or null). */
export async function progress(page: Page): Promise<any> {
  return page.evaluate((key) => JSON.parse(localStorage.getItem(key) ?? 'null'), KEY);
}

/** The local calendar day of the page clock, `offset` days on. */
export async function pageDay(page: Page, offset = 0): Promise<string> {
  return page.evaluate((days) => {
    const d = new Date();
    d.setDate(d.getDate() + days);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  }, offset);
}

export type How = 'right' | 'wrong' | 'one-off';

/**
 * Answer an <sk-mc> from its data-correct attributes:
 *   right    every option decided correctly (score 1)
 *   wrong    a wrong choice (single), only the wrong options (multi), every statement
 *            judged the opposite way (Kprim): score 0
 *   one-off  Kprim with exactly one statement judged wrongly (score 0.5)
 * Outside exams the confidence is set too. Returns the score the answer must get.
 */
export async function answer(mc: Locator, how: How, conf: 'Sure' | 'Unsure' = 'Sure'): Promise<number> {
  const type = await mc.getAttribute('data-type');
  if (how === 'one-off' && type !== 'kprim') throw new Error('one-off answers are for Kprim questions');
  const opts = mc.locator('sk-opt');
  const n = await opts.count();
  const correct: boolean[] = [];
  for (let i = 0; i < n; i++) correct.push((await opts.nth(i).getAttribute('data-correct')) === 'true');
  let expected = how === 'right' ? 1 : 0;
  if (type === 'kprim') {
    for (let i = 0; i < n; i++) {
      const flip = how === 'wrong' || (how === 'one-off' && i === 0);
      await opts.nth(i).locator(`input[value="${correct[i] !== flip}"]`).check();
    }
    if (how === 'one-off') expected = 0.5;
  } else if (type === 'single') {
    const pick = correct.findIndex((c) => c === (how === 'right'));
    await opts.nth(pick).locator('input').check();
  } else {
    for (let i = 0; i < n; i++) {
      if (correct[i] === (how === 'right')) await opts.nth(i).locator('input').check();
    }
  }
  if ((await mc.getAttribute('data-mode')) !== 'exam') {
    await mc.locator('.sk-mc-conf').getByLabel(conf, { exact: true }).check();
  }
  return expected;
}

/** The custom elements have upgraded the page (the module script ran). */
export async function elementsReady(page: Page): Promise<void> {
  await expect(page.locator('sk-theme fieldset')).toBeAttached();
}

/** id → title of the course topics, as the quiz result screen names them. */
export async function topicTitles(quiz: Locator): Promise<Record<string, string>> {
  return JSON.parse((await quiz.getAttribute('data-topic-titles')) ?? '{}');
}

/** Score and question count per topic, as the test answered them. */
export class Tally {
  readonly topics = new Map<string, { score: number; n: number }>();

  add(topic: string, score: number): void {
    const t = this.topics.get(topic) ?? { score: 0, n: 0 };
    t.score += score;
    t.n += 1;
    this.topics.set(topic, t);
  }

  get total(): number {
    return [...this.topics.values()].reduce((s, t) => s + t.score, 0);
  }

  get n(): number {
    return [...this.topics.values()].reduce((s, t) => s + t.n, 0);
  }
}

/** The quiz result: total, and one "By topic" row per topic with its score. */
export async function expectResult(quiz: Locator, tally: Tally): Promise<void> {
  const titles = await topicTitles(quiz);
  const result = quiz.locator('.sk-quiz-result');
  await expect(result.getByRole('heading', { name: 'Result' })).toBeVisible();
  await expect(result.locator('.sk-quiz-score strong')).toHaveText(`${tally.total} / ${tally.n}`);
  const rows = result.locator('.sk-quiz-topics tbody tr');
  await expect(rows).toHaveCount(tally.topics.size);
  for (const [topic, t] of tally.topics) {
    const row = rows.filter({ has: quiz.page().getByRole('rowheader', { name: titles[topic] ?? topic, exact: true }) });
    await expect(row.locator('td').first()).toHaveText(`${t.score} / ${t.n}`);
    await expect(row.getByRole('link')).toHaveAttribute('href', `${C}/summary/${topic}/`);
  }
}

/** The question a running quiz shows now. */
export function current(quiz: Locator): Locator {
  return quiz.locator('.sk-quiz-stage sk-mc');
}
