// Layout of the sample course at the widths people use: nothing is cut off or pushed out of
// view, on screen and in print.
import { expect, test, type Page } from '@playwright/test';
import { C } from './helpers.ts';

/** Display formulas of the cheat sheet that are wider than their box (cut or scrolling). */
function overflowingMath(page: Page): Promise<string[]> {
  return page.locator('.cheatsheet .katex-display').evaluateAll((els) =>
    els.filter((el) => el.scrollWidth > el.clientWidth + 1).map((el) => (el.textContent ?? '').slice(0, 30)),
  );
}

test('the cheat sheet fills its columns and no formula is cut at a column edge', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`${C}/cheatsheet/`);
  const sheet = page.locator('.cheatsheet');
  const columns = await sheet.evaluate((el) => {
    const width = el.clientWidth - Number.parseFloat(getComputedStyle(el).paddingLeft) * 2;
    const gap = Number.parseFloat(getComputedStyle(el).columnGap);
    return Math.floor((width + gap) / (Number.parseFloat(getComputedStyle(el).columnWidth) + gap));
  });
  expect(columns).toBe(3);
  // every column holds content: the left edges of the sections' boxes fall in each one
  const lefts = await sheet.evaluate((el) => {
    const xs = new Set<number>();
    for (const child of el.querySelectorAll('.cs-section > *')) {
      for (const r of child.getClientRects()) xs.add(Math.round(r.left));
    }
    return [...xs];
  });
  expect(lefts.length).toBe(columns);
  expect(await overflowingMath(page)).toEqual([]);

  await page.setViewportSize({ width: 390, height: 844 });
  expect(await overflowingMath(page)).toEqual([]);

  // print: A4 in two columns (print.css), still nothing cut
  await page.emulateMedia({ media: 'print' });
  await page.setViewportSize({ width: 718, height: 1000 });
  expect(await overflowingMath(page)).toEqual([]);
});

test('on a phone the course tabs show the tab of the page', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  for (const tab of ['mc', 'cheatsheet', 'exams', 'progress']) {
    await page.goto(`${C}/${tab}/`);
    const inView = await page.locator('.course-nav ul').evaluate((list) => {
      const current = list.querySelector('a[aria-current="page"]')?.getBoundingClientRect();
      const box = list.getBoundingClientRect();
      return current !== undefined && current.left >= box.left - 0.5 && current.right <= box.right + 0.5;
    });
    expect(inView, tab).toBe(true);
  }
});

test('at 320 px no page scrolls sideways, also with long German titles in the pager', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 800 });
  for (const path of [`${C}/summary/spannungsteiler/`, `${C}/exercises/ex-st-belastet-allgemein/`]) {
    await page.goto(path);
    expect(await page.evaluate(() => document.documentElement.scrollWidth), path).toBeLessThanOrEqual(320);
  }
});
