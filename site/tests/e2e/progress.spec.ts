// Progress export and import (docs/architecture.md §2.11): the exported file holds the
// whole progress document and merges back into a fresh browser as a union.
import { readFile } from 'node:fs/promises';
import { expect, test } from '@playwright/test';
import { answer, C, COURSE, elementsReady, freezeDay, NOW, pageDay, progress } from './helpers.ts';

test('an export round-trips through import into a fresh browser', async ({ page, browser }, info) => {
  await freezeDay(page);
  // some progress: one MC answer, one exercise hint and rating
  await page.goto(`${C}/mc/rc-filter/`);
  await elementsReady(page);
  const mc = page.locator('ol.questions sk-mc').first();
  const mcId = await mc.getAttribute('data-id');
  await answer(mc, 'right', 'Sure');
  await mc.getByRole('button', { name: 'Check' }).click();
  await page.goto(`${C}/exercises/ex-st-unbelastet/`);
  await elementsReady(page);
  await page.locator('sk-hints').getByRole('button', { name: /^Show hint 1/ }).click();
  await page.locator('sk-self-assess').getByRole('button', { name: 'Partly' }).click();
  const stored = await progress(page);

  // export
  await page.goto(`${C}/progress/`);
  await expect(page.locator('sk-progress .sk-stats')).toContainText('1 answer');
  const exporter = page.locator('sk-export');
  const download = page.waitForEvent('download');
  await exporter.getByRole('button', { name: 'Export progress' }).click();
  const file = await download;
  expect(file.suggestedFilename()).toBe(`studykit-progress-${COURSE}-${await pageDay(page)}.json`);
  await expect(exporter.locator('.sk-export-status')).toHaveText(`Saved ${file.suggestedFilename()}.`);
  const path = info.outputPath(file.suggestedFilename());
  await file.saveAs(path);
  const exported = JSON.parse(await readFile(path, 'utf8'));
  expect(exported).toMatchObject({ schema: 'studykit-progress/1', course: COURSE });
  expect(Date.parse(exported.exported_at)).toBeGreaterThanOrEqual(NOW.getTime());
  expect(Object.keys(exported.items).sort()).toEqual([`ex:ex-st-unbelastet`, `mc:${mcId}`]);
  expect(exported.items).toEqual(stored.items);

  // import into another browser profile that has no progress yet
  const { baseURL, locale, timezoneId } = info.project.use;
  const other = await browser.newContext({ baseURL, locale, timezoneId });
  try {
    const fresh = await other.newPage();
    await freezeDay(fresh);
    await fresh.goto(`${C}/progress/`);
    await expect(fresh.locator('sk-progress .sk-stats')).toContainText('0 answers');
    const importer = fresh.locator('sk-export');
    await importer.locator('input[type=file]').setInputFiles(path);
    await expect(importer.locator('.sk-export-status')).toHaveText('Imported 2 items (2 new, 0 merged).');
    expect((await progress(fresh)).items).toEqual(exported.items);
    await expect(fresh.locator('sk-progress .sk-stats')).toContainText('1 answer'); // live update

    // importing the same file again is a union: nothing changes
    await importer.locator('input[type=file]').setInputFiles(path);
    await expect(importer.locator('.sk-export-status')).toHaveText('Imported 2 items (0 new, 2 merged).');
    expect((await progress(fresh)).items).toEqual(exported.items);

    // the imported progress shows on the pages
    await fresh.goto(`${C}/mc/rc-filter/`);
    await expect(fresh.locator(`ol.questions sk-mc[data-id="${mcId}"] .sk-mc-note`)).toContainText(
      'Last time: correct (sure)',
    );
  } finally {
    await other.close();
  }
});
