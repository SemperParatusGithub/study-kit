// Browser harness for the custom elements:
//   pnpm -C site exec playwright test -c tests/elements
// The web server compiles src/lib + src/elements with the pinned TypeScript first.
// Screenshots (screenshots.spec.ts) go to SK_SHOTS_DIR, default node_modules/.cache/sk-elements/shots.
import { defineConfig, devices } from '@playwright/test';

const port = Number(process.env.SK_ELEMENTS_PORT ?? 4399);

export default defineConfig({
  testDir: '.',
  testMatch: '*.spec.ts',
  outputDir: '../../node_modules/.cache/sk-elements/results',
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  reporter: [['list']],
  timeout: 30_000,
  use: {
    ...devices['Desktop Chrome'],
    baseURL: `http://localhost:${port}`,
    locale: 'en-GB',
    timezoneId: 'Europe/Berlin',
    trace: 'retain-on-failure',
  },
  webServer: {
    command: 'node server.mjs',
    url: `http://localhost:${port}/health`,
    reuseExistingServer: false,
    timeout: 120_000,
    stdout: 'pipe',
    env: { SK_ELEMENTS_PORT: String(port) },
  },
});
