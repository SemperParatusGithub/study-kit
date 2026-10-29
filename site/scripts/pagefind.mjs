// After `astro build`: index dist/ with `pagefind --site dist` (docs/architecture.md §3.5),
// forcing one language so every course shares one index, then copy the index to
// public/pagefind/ so `astro dev` serves the last built search index.
import { spawnSync } from 'node:child_process';
import { cpSync, existsSync, readdirSync, readFileSync, rmSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const site = fileURLToPath(new URL('..', import.meta.url));
const dist = join(site, 'dist');

/** The most common <html lang> of the course pages (Pagefind wants one language). */
function courseLanguage() {
  const counts = new Map();
  const courses = join(dist, 'c');
  for (const name of existsSync(courses) ? readdirSync(courses) : []) {
    const page = join(courses, name, 'index.html');
    if (!existsSync(page)) continue;
    const lang = /<html[^>]*\slang="([a-z]{2})/i.exec(readFileSync(page, 'utf8'))?.[1];
    if (lang) counts.set(lang, (counts.get(lang) ?? 0) + 1);
  }
  return [...counts].sort((a, b) => b[1] - a[1])[0]?.[0] ?? 'en';
}

const lang = courseLanguage();
const bin = join(site, 'node_modules', '.bin', process.platform === 'win32' ? 'pagefind.cmd' : 'pagefind');
const run = spawnSync(bin, ['--site', 'dist', '--force-language', lang], { cwd: site, stdio: 'inherit' });
if (run.status !== 0) {
  console.error(`pagefind failed (exit ${run.status ?? run.signal})`);
  process.exit(run.status ?? 1);
}

const target = join(site, 'public', 'pagefind');
rmSync(target, { recursive: true, force: true });
cpSync(join(dist, 'pagefind'), target, { recursive: true });
console.log(`pagefind: index (${lang}) copied to public/pagefind/ for astro dev`);
