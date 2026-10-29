// MC questions on a topic page (docs/architecture.md §4.4, flows 1 and 2): one question of
// each type is answered, scored and recorded, and the progress survives a reload.
import { expect, test } from '@playwright/test';
import { answer, C, elementsReady, freezeDay, pageDay, progress, type How } from './helpers.ts';

const TOPIC = 'rc-filter';

test.beforeEach(async ({ page }) => {
  await freezeDay(page);
});

test('one question of each type is scored, recorded and shown again after a reload', async ({ page }) => {
  await page.goto(`${C}/mc/${TOPIC}/`);
  await elementsReady(page);
  const plan: Array<{ type: string; how: How; conf: 'Sure' | 'Unsure'; verdict: string; box: number; days: number }> = [
    // a new item starts in box 1: right → box 2 (3 days), wrong → box 1 (1 day)
    { type: 'single', how: 'right', conf: 'Sure', verdict: 'Correct. Next review in 3 days.', box: 2, days: 3 },
    // one correct option left out: nothing under the course's all-or-nothing rule (partial
    // or Kprim scoring would give part of the point here)
    { type: 'multi', how: 'one-off', conf: 'Unsure', verdict: 'Not correct. Next review tomorrow.', box: 1, days: 1 },
    { type: 'kprim', how: 'one-off', conf: 'Unsure', verdict: 'Partly correct: 0.5 of 1 point. Next review tomorrow.', box: 1, days: 1 },
  ];
  const done: Array<{ id: string; score: number }> = [];
  for (const step of plan) {
    const mc = page.locator(`ol.questions sk-mc[data-type="${step.type}"]`).first();
    const id = (await mc.getAttribute('data-id')) ?? '';
    const check = mc.getByRole('button', { name: 'Check' });
    await expect(check).toHaveAttribute('aria-disabled', 'true');
    const score = await answer(mc, step.how, step.conf);
    await expect(check).toHaveAttribute('aria-disabled', 'false');
    await check.click();
    await expect(mc.locator('.sk-mc-feedback')).toContainText(step.verdict);
    if (step.how === 'one-off' && step.type === 'multi') {
      // the left-out correct option is marked as missed
      await expect(mc.locator('sk-opt.is-missed')).toHaveCount(1);
    }
    // every option's why and the explanation are shown after checking
    const whys = mc.locator('.sk-why');
    for (let i = 0; i < (await whys.count()); i++) await expect(whys.nth(i)).toBeVisible();
    await expect(mc.locator('.sk-explanation')).toBeVisible();

    const entry = (await progress(page)).items[`mc:${id}`];
    expect(entry.attempts).toHaveLength(1);
    expect(entry.attempts[0]).toMatchObject({ score, conf: step.conf.toLowerCase() });
    expect(entry.box).toBe(step.box);
    expect(entry.due).toBe(await pageDay(page, step.days));
    done.push({ id, score });
  }

  await page.reload();
  await elementsReady(page);
  const notes = [
    'Last time: correct (sure), today · next review in 3 days.',
    'Last time: wrong (unsure), today · next review tomorrow.',
    'Last time: partly correct (unsure), today · next review tomorrow.',
  ];
  for (const [i, { id }] of done.entries()) {
    await expect(page.locator(`ol.questions sk-mc[data-id="${id}"] .sk-mc-note`)).toHaveText(notes[i] ?? '');
  }

  // the progress page counts the three answers for the topic
  await page.goto(`${C}/progress/`);
  const stats = page.locator('sk-progress .sk-stats');
  await expect(stats).toContainText('3 answers');
  await expect(stats).toContainText('0 due today');
  const mean = done.reduce((s, d) => s + d.score, 0) / done.length;
  const topic = page.locator('sk-progress .sk-topic').filter({ hasText: 'RC-Filter' });
  await expect(topic.locator('.sk-topic-value')).toHaveText(`${Math.round(mean * 100)} %`);
});

test('keyboard: digits choose, S and U set the confidence, Enter checks, N moves on', async ({ page }) => {
  await page.goto(`${C}/mc/${TOPIC}/`);
  await elementsReady(page);
  const all = page.locator('ol.questions sk-mc');

  // single choice: the digit of the right option (options are in display order)
  const single = page.locator('ol.questions sk-mc[data-type="single"]').first();
  const correct = await single.locator('sk-opt').evaluateAll((os) => os.map((o) => o.getAttribute('data-correct') === 'true'));
  await single.focus();
  await page.keyboard.press(String(correct.indexOf(true) + 1));
  await page.keyboard.press('s');
  await page.keyboard.press('Enter');
  await expect(single.locator('.sk-mc-feedback')).toContainText('Correct.');
  const index = await all.evaluateAll((els, id) => els.findIndex((e) => e.getAttribute('data-id') === id), await single.getAttribute('data-id'));
  await page.keyboard.press('n');
  await expect(all.nth(index + 1)).toBeFocused();

  // Kprim: a digit cycles a statement through true and false
  const kprim = page.locator('ol.questions sk-mc[data-type="kprim"]').first();
  const truth = await kprim.locator('sk-opt').evaluateAll((os) => os.map((o) => o.getAttribute('data-correct') === 'true'));
  await kprim.focus();
  for (const [i, t] of truth.entries()) {
    await page.keyboard.press(String(i + 1)); // true
    if (!t) await page.keyboard.press(String(i + 1)); // false
  }
  await page.keyboard.press('u');
  await page.keyboard.press('Enter');
  await expect(kprim.locator('.sk-mc-feedback')).toContainText('Correct.');
  const id = await kprim.getAttribute('data-id');
  expect((await progress(page)).items[`mc:${id}`].attempts[0]).toMatchObject({ score: 1, conf: 'unsure' });
});
