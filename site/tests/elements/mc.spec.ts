import { expect, test } from '@playwright/test';
import { optionOrder } from '../../src/lib/shuffle.ts';
import { answer, pageDay, progress } from './helpers.ts';

test.beforeEach(async ({ page, javaScriptEnabled }) => {
  await page.goto('/mc.html');
  if (javaScriptEnabled) await expect(page.locator('sk-mc.sk-mc-ready')).toHaveCount(6);
});

test('options are shown in the mc.pdf order, pin-last stays last', async ({ page }) => {
  const questions = page.locator('sk-mc');
  for (let q = 0; q < 6; q++) {
    const mc = questions.nth(q);
    const id = (await mc.getAttribute('data-id')) ?? '';
    const pin = (await mc.getAttribute('data-pin-last')) === 'true';
    const shown = await mc.locator('sk-opt').evaluateAll((els) => els.map((e) => e.getAttribute('data-key')));
    const expected = optionOrder(id, shown.length, pin).map((i) => 'ABCDEF'[i]);
    expect(shown, id).toEqual(expected);
    const letters = await mc.locator('.sk-opt-letter').allTextContents();
    expect(letters).toEqual(['A', 'B', 'C', 'D', 'E', 'F'].slice(0, shown.length));
  }
  // mc-rc-tiefpass-002 has pin-last: "Keine der Aussagen ist richtig." stays last
  await expect(page.locator('sk-mc[data-id="mc-rc-tiefpass-002"] sk-opt').last()).toContainText('Keine der Aussagen');
});

test('single: Check needs an answer and a confidence, then shows every why', async ({ page }) => {
  const mc = page.locator('sk-mc[data-id="mc-rc-tiefpass-001"]');
  const check = mc.getByRole('button', { name: 'Check' });
  await expect(mc.locator('.sk-why').first()).toBeHidden();
  await expect(check).toHaveAttribute('aria-disabled', 'true');
  await check.click({ force: true });
  await expect(mc.locator('.sk-mc-status')).toHaveText('Choose an answer first.');
  await mc.locator('sk-opt[data-key="A"] input').check();
  await check.click({ force: true });
  await expect(mc.locator('.sk-mc-status')).toHaveText('Say whether you are sure before checking.');
  await expect(mc.locator('.sk-why').first()).toBeHidden();

  await page.evaluate(() => {
    document.addEventListener('sk:answer', (e) => ((window as any).lastAnswer = (e as CustomEvent).detail));
  });
  await mc.getByLabel('Sure', { exact: true }).check();
  await expect(check).toHaveAttribute('aria-disabled', 'false');
  await check.click();
  await expect(mc.locator('.sk-mc-feedback')).toContainText('Correct. Next review in 3 days.');
  await expect(mc.locator('.sk-why')).toHaveCount(4);
  for (const why of await mc.locator('.sk-why').all()) await expect(why).toBeVisible();
  await expect(mc.locator('.sk-explanation')).toBeVisible();
  await expect(mc.locator('sk-opt[data-key="A"] .sk-opt-mark')).toHaveText('✓ Correct, your choice');
  await expect(mc.locator('sk-opt input').first()).toBeDisabled();

  const detail = await page.evaluate(() => (window as any).lastAnswer);
  expect(detail).toMatchObject({
    id: 'mc-rc-tiefpass-001', item: 'mc:mc-rc-tiefpass-001', topic: 'rc-tiefpass', type: 'single',
    chosen: ['A'], score: 1, conf: 'sure', correct: true, misconception: false, box: 2,
  });

  const doc = await progress(page);
  const entry = doc.items['mc:mc-rc-tiefpass-001'];
  expect(entry.h).toBe(await mc.getAttribute('data-h'));
  expect(entry.box).toBe(2);
  expect(entry.due).toBe(await pageDay(page, 3));
  expect(entry.attempts).toHaveLength(1);
  expect(entry.attempts[0]).toMatchObject({ chosen: ['A'], score: 1, conf: 'sure' });
});

test('multi: all-or-nothing, and a sure wrong answer is a misconception', async ({ page }) => {
  const mc = page.locator('sk-mc[data-id="mc-rc-tiefpass-002"]');
  await mc.locator('sk-opt[data-key="A"] input').check(); // one of two correct options
  await mc.getByLabel('Sure', { exact: true }).check();
  await mc.getByRole('button', { name: 'Check' }).click();
  await expect(mc.locator('.sk-mc-feedback')).toContainText('Not correct.');
  await expect(mc.locator('.sk-mc-feedback')).toContainText('misconception');
  await expect(mc.locator('sk-opt[data-key="B"] .sk-opt-mark')).toHaveText('✗ Missed: this answer is correct');
  const entry = (await progress(page)).items['mc:mc-rc-tiefpass-002'];
  expect(entry).toMatchObject({ box: 0, due: await pageDay(page) });
  expect(entry.attempts[0]).toMatchObject({ chosen: ['A'], score: 0, conf: 'sure' });

  // Try again: the next attempt is recorded on top
  await mc.getByRole('button', { name: 'Try again' }).click();
  await answer(mc, true, 'Unsure');
  await mc.getByRole('button', { name: 'Check' }).click();
  await expect(mc.locator('.sk-mc-feedback')).toContainText('Correct.');
  const again = (await progress(page)).items['mc:mc-rc-tiefpass-002'];
  expect(again.attempts.map((a: { score: number }) => a.score)).toEqual([0, 1]);
  expect(again.box).toBe(1);
});

test('kprim: three of four statements right scores 0.5', async ({ page }) => {
  const mc = page.locator('sk-mc[data-id="mc-rc-tiefpass-003"]');
  await mc.locator('sk-opt[data-key="A"] input[value="true"]').check();
  await mc.locator('sk-opt[data-key="B"] input[value="true"]').check();
  await mc.locator('sk-opt[data-key="C"] input[value="true"]').check(); // wrong
  await expect(mc.getByRole('button', { name: 'Check' })).toHaveAttribute('aria-disabled', 'true');
  await mc.getByRole('button', { name: 'Check' }).click({ force: true });
  await expect(mc.locator('.sk-mc-status')).toHaveText('Judge all four statements first.');
  await mc.locator('sk-opt[data-key="D"] input[value="false"]').check();
  await mc.getByLabel('Unsure').check();
  await mc.getByRole('button', { name: 'Check' }).click();
  await expect(mc.locator('.sk-mc-feedback')).toContainText('Partly correct: 0.5 of 1 point.');
  await expect(mc.locator('sk-opt[data-key="C"] .sk-opt-mark')).toHaveText('✗ False, you said true');
  await expect(mc.locator('sk-opt[data-key="D"] .sk-opt-mark')).toHaveText('✓ False, you said false');
  const entry = (await progress(page)).items['mc:mc-rc-tiefpass-003'];
  expect(entry.attempts[0]).toMatchObject({ chosen: ['A', 'B', 'C'], score: 0.5, conf: 'unsure' });
  expect(entry.box).toBe(1);
});

test('keyboard: digits choose, S and U set confidence, Enter checks, N moves on', async ({ page }) => {
  const first = page.locator('sk-mc').first();
  await first.focus();
  await page.keyboard.press('2'); // display B = source A, the correct answer
  await expect(first.locator('sk-opt[data-key="A"] input')).toBeChecked();
  await page.keyboard.press('Enter');
  await expect(first.locator('.sk-mc-status')).toHaveText('Say whether you are sure before checking.');
  await page.keyboard.press('u');
  await page.keyboard.press('s');
  await expect(first.getByLabel('Sure', { exact: true })).toBeChecked();
  await page.keyboard.press('Enter');
  await expect(first.locator('.sk-mc-feedback')).toContainText('Correct.');
  await page.keyboard.press('n');
  const focused = await page.evaluate(() => document.activeElement?.closest('sk-mc')?.getAttribute('data-id'));
  expect(focused).toBe('mc-rc-tiefpass-002');

  // Kprim: a digit cycles the statement through true and false
  const kprim = page.locator('sk-mc[data-id="mc-rc-tiefpass-003"]');
  await kprim.focus();
  const firstKey = await kprim.locator('sk-opt').first().getAttribute('data-key');
  await page.keyboard.press('1');
  await expect(kprim.locator(`sk-opt[data-key="${firstKey}"] input[value="true"]`)).toBeChecked();
  await page.keyboard.press('1');
  await expect(kprim.locator(`sk-opt[data-key="${firstKey}"] input[value="false"]`)).toBeChecked();
});

test('the last attempt shows after a reload; changed content is flagged', async ({ page }) => {
  const mc = page.locator('sk-mc[data-id="mc-rc-tiefpass-001"]');
  await answer(mc, false, 'Unsure');
  await mc.getByRole('button', { name: 'Check' }).click();
  await page.reload();
  await expect(mc.locator('.sk-mc-note')).toHaveText('Last time: wrong (unsure), today · next review tomorrow.');
  await page.evaluate(() => {
    const doc = JSON.parse(localStorage.getItem('studykit:v1:mini') ?? '{}');
    doc.items['mc:mc-rc-tiefpass-001'].h = 'ffffffff';
    localStorage.setItem('studykit:v1:mini', JSON.stringify(doc));
  });
  await page.reload();
  await expect(mc.locator('.sk-mc-note')).toHaveText('Content changed since your attempt.');
});

test('clicking the option row selects it; links inside options still work', async ({ page }) => {
  const mc = page.locator('sk-mc[data-id="mc-rc-tiefpass-002"]');
  await mc.locator('sk-opt[data-key="B"] .sk-opt-text').click();
  await expect(mc.locator('sk-opt[data-key="B"] input')).toBeChecked();
  await mc.locator('sk-opt[data-key="B"] .sk-opt-text').click();
  await expect(mc.locator('sk-opt[data-key="B"] input')).not.toBeChecked();
  await expect(mc.locator('sk-opt[data-key="B"] input')).toHaveAccessibleName(/^[A-D] Bei/);
});

test('reduced motion turns transitions off', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  const d = await page.locator('sk-opt').first().evaluate((e) => getComputedStyle(e).transitionDuration);
  expect(d).toBe('0s');
});

test.describe('without JavaScript', () => {
  test.use({ javaScriptEnabled: false });
  test('questions stay readable and the key stays hidden', async ({ page }) => {
    const mc = page.locator('sk-mc[data-id="mc-rc-tiefpass-001"]');
    await expect(mc.locator('.sk-stem')).toBeVisible();
    await expect(mc.locator('.sk-opt-text')).toHaveCount(4);
    for (const t of await mc.locator('.sk-opt-text').all()) await expect(t).toBeVisible();
    await expect(mc.locator('.sk-why').first()).toBeHidden();
    await expect(mc.locator('.sk-explanation')).toBeHidden();
    await expect(page.locator('.katex').first()).toBeVisible();
  });
});
