import type { Locator, Page } from '@playwright/test';

export const COURSE = 'mini';
export const KEY = `studykit:v1:${COURSE}`;
export const SESSION_KEY = `studykit:v1:${COURSE}:session`;

/** The stored progress document (or null). */
export async function progress(page: Page): Promise<any> {
  return page.evaluate((key) => JSON.parse(localStorage.getItem(key) ?? 'null'), KEY);
}

/** Put a progress document in place before every navigation of this page. */
export async function seed(page: Page, items: Record<string, unknown>): Promise<void> {
  const doc = { schema: 'studykit-progress/1', course: COURSE, exported_at: '2026-10-01T00:00:00Z', items };
  await page.addInitScript(
    ([key, text]) => {
      if (!sessionStorage.getItem('seeded')) {
        localStorage.setItem(key, text);
        sessionStorage.setItem('seeded', '1');
      }
    },
    [KEY, JSON.stringify(doc)] as const,
  );
}

/** Answer an <sk-mc>: fully right, or with every option inverted (wrong), then confidence. */
export async function answer(mc: Locator, right: boolean, conf: 'Sure' | 'Unsure' = 'Sure'): Promise<void> {
  const type = await mc.getAttribute('data-type');
  const opts = mc.locator('sk-opt');
  const n = await opts.count();
  for (let i = 0; i < n; i++) {
    const opt = opts.nth(i);
    const correct = (await opt.getAttribute('data-correct')) === 'true';
    if (type === 'kprim') {
      await opt.locator(`input[value="${correct === right}"]`).check();
    } else if (type === 'single') {
      if (correct === right) {
        await opt.locator('input').check();
        if (!right) break; // one wrong choice is enough
      }
    } else if (correct === right) {
      await opt.locator('input').check();
    }
  }
  if ((await mc.getAttribute('data-mode')) !== 'exam') await mc.getByLabel(conf, { exact: true }).check();
}

/** Today in the page's local time zone, YYYY-MM-DD. */
export async function pageDay(page: Page, offset = 0): Promise<string> {
  return page.evaluate((days) => {
    const d = new Date();
    d.setDate(d.getDate() + days);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  }, offset);
}
