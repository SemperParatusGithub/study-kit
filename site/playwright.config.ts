// End-to-end tests of the built site (docs/architecture.md §4.4):
//   pnpm -C site exec playwright test        (or: just e2e)
// The suite runs against the sample course, built beforehand by
//   STUDYKIT_COURSES_DIR=examples just build sample-course
// The web server only serves that build (astro preview on localhost:4321, strictPort); it
// never builds. Results and the HTML report go to node_modules/.cache/sk-e2e (gitignored):
//   pnpm -C site exec playwright show-report node_modules/.cache/sk-e2e/report
// The browser harness of the custom elements has its own config in tests/elements.
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { defineConfig, devices } from '@playwright/test';

// 4321 is the site's port; SK_E2E_PORT moves the suite when a dev server holds it.
const PORT = Number(process.env.SK_E2E_PORT ?? 4321);
const CI = Boolean(process.env.CI);
const OUT = 'node_modules/.cache/sk-e2e';
const sample = fileURLToPath(new URL('./dist/c/sample-course/index.html', import.meta.url));

if (!existsSync(sample)) {
  throw new Error(
    'site/dist has no sample course. Build it first: STUDYKIT_COURSES_DIR=examples just build sample-course',
  );
}

export default defineConfig({
  testDir: 'tests/e2e',
  testMatch: '*.spec.ts',
  outputDir: `${OUT}/results`,
  fullyParallel: true,
  forbidOnly: CI,
  retries: CI ? 1 : 0,
  timeout: 30_000,
  expect: { timeout: 5_000 },
  reporter: CI
    ? [['list'], ['github'], ['html', { open: 'never', outputFolder: `${OUT}/report` }]]
    : [['list'], ['html', { open: 'never', outputFolder: `${OUT}/report` }]],
  use: {
    baseURL: `http://localhost:${PORT}`,
    locale: 'en-GB',
    timezoneId: 'Europe/Berlin',
    colorScheme: 'light',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    actionTimeout: 10_000,
    navigationTimeout: 15_000,
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    // astro.config.mjs pins localhost and vite.preview.strictPort: a busy port fails
    // instead of moving, since progress in localStorage is tied to the origin.
    // --ignore-lock keeps the server in the foreground: Astro moves `astro preview` to a
    // background daemon when it detects a coding agent, which would outlive the run. Node
    // starts Astro without a package-manager wrapper, so ending the run stops it.
    command: `node node_modules/astro/bin/astro.mjs preview --ignore-lock --port ${PORT}`,
    url: `http://localhost:${PORT}/`,
    reuseExistingServer: false,
    timeout: 60_000,
    stdout: 'ignore',
    stderr: 'pipe',
    env: { ASTRO_TELEMETRY_DISABLED: '1' },
  },
});
