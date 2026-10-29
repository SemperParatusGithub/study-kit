// Static server for the element harness (site/tests/elements).
//
//   node tests/elements/server.mjs [--no-build]     (from site/; port SK_ELEMENTS_PORT or 4399)
//
// 1. Compiles site/src/lib and site/src/elements with the pinned TypeScript into
//    node_modules/.cache/sk-elements/build (gitignored).
// 2. Serves pages/*.html with <!--#include fixtures/…--> resolved, the fixtures' <sk-math>
//    rendered by KaTeX exactly as the site loader does (docs/architecture.md §3.2, step 5),
//    the pool JSON files likewise, the compiled modules under /build/, elements.css under
//    /styles/ and KaTeX's dist under /katex/.

import { spawnSync } from 'node:child_process';
import { readFile, stat } from 'node:fs/promises';
import { createServer } from 'node:http';
import { createRequire } from 'node:module';
import { dirname, extname, join, normalize, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import katex from 'katex';

const HERE = dirname(fileURLToPath(import.meta.url));
const SITE = resolve(HERE, '../..');
const BUILD = join(SITE, 'node_modules/.cache/sk-elements/build');
const KATEX_DIST = join(SITE, 'node_modules/katex/dist');
const PORT = Number(process.env.SK_ELEMENTS_PORT ?? 4399);

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.woff2': 'font/woff2',
  '.woff': 'font/woff',
  '.ttf': 'font/ttf',
  '.map': 'application/json',
};

export function build() {
  const require = createRequire(import.meta.url);
  const tsc = require.resolve('typescript/bin/tsc');
  const r = spawnSync(process.execPath, [tsc, '-p', join(HERE, 'tsconfig.json')], { stdio: 'inherit' });
  if (r.status !== 0) throw new Error('tsc failed');
}

const MATH_RE = /<sk-math data-tex="([^"]*)" data-display="([01])"><\/sk-math>/g;

/** Replace each <sk-math> with KaTeX HTML (the loader's options). */
export function renderMath(html) {
  return html.replace(MATH_RE, (_, b64, display) =>
    katex.renderToString(Buffer.from(b64, 'base64').toString('utf8'), {
      displayMode: display === '1',
      throwOnError: true,
      strict: 'error',
      trust: false,
    }),
  );
}

async function page(file) {
  let html = await readFile(file, 'utf8');
  const includes = [...html.matchAll(/<!--#include ([\w./-]+)-->/g)];
  for (const [marker, rel] of includes) {
    const text = await readFile(join(HERE, rel), 'utf8');
    html = html.replace(marker, () => text); // a function: no $& patterns in fixtures
  }
  return renderMath(html);
}

function within(root, path) {
  const full = normalize(join(root, path));
  return full.startsWith(root) ? full : null;
}

async function respond(req, res) {
  const url = new URL(req.url ?? '/', 'http://localhost');
  let path = decodeURIComponent(url.pathname);
  if (path === '/health') return send(res, 200, 'text/plain', 'ok');
  if (path === '/') path = '/index.html';
  let file = null;
  let transform = null;
  if (path.startsWith('/build/')) file = within(BUILD, path.slice(7));
  else if (path.startsWith('/katex/')) file = within(KATEX_DIST, path.slice(7));
  else if (path === '/styles/elements.css') file = join(SITE, 'src/styles/elements.css');
  else if (path.startsWith('/fixtures/pools/')) {
    file = within(join(HERE, 'fixtures/pools'), path.slice(16));
    transform = (text) => {
      const pool = JSON.parse(text);
      for (const q of pool.questions) q.html = renderMath(q.html);
      return JSON.stringify(pool);
    };
  } else if (/^\/[\w-]+\.(html|css)$/.test(path)) {
    file = path.endsWith('.html') ? join(HERE, 'pages', path) : join(HERE, path);
  }
  if (!file) return send(res, 404, 'text/plain', 'not found');
  try {
    await stat(file);
  } catch {
    return send(res, 404, 'text/plain', 'not found');
  }
  const type = TYPES[extname(file)] ?? 'application/octet-stream';
  if (extname(file) === '.html' && file.includes('/pages/')) return send(res, 200, type, await page(file));
  const body = await readFile(file);
  return send(res, 200, type, transform ? transform(body.toString('utf8')) : body);
}

function send(res, status, type, body) {
  res.writeHead(status, { 'content-type': type, 'cache-control': 'no-store' });
  res.end(body);
}

if (import.meta.url === `file://${process.argv[1]}`) {
  if (!process.argv.includes('--no-build')) build();
  createServer((req, res) => {
    respond(req, res).catch((err) => send(res, 500, 'text/plain', String(err?.stack ?? err)));
  }).listen(PORT, 'localhost', () => {
    console.log(`element harness on http://localhost:${PORT}/`);
  });
}
