// Static study site (docs/architecture.md §3.2). Course data comes from
// STUDYKIT_COURSES_DIR (default ../courses) through src/content.config.ts.
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'astro/config';

const siteRoot = fileURLToPath(new URL('.', import.meta.url));
const repoRoot = fileURLToPath(new URL('..', import.meta.url));

// Build-time modules are bundled into chunks, so they cannot locate the site from their own
// URL; src/lib/sys.mjs reads this instead.
process.env.STUDYKIT_SITE_ROOT ??= siteRoot;

export default defineConfig({
  output: 'static',
  // Progress lives in localStorage, which is tied to the origin: always localhost:4321.
  server: { host: 'localhost', port: 4321 },
  devToolbar: { enabled: false },
  vite: {
    server: { strictPort: true, fs: { allow: [repoRoot] } },
    preview: { strictPort: true },
  },
});
