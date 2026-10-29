// Entry point for `node --test site/tests/unit/` (Node 24 runs a directory argument as a
// module, which resolves to this file). It loads every *.test.ts next to it, so the
// directory form and the glob form (`node --test 'tests/unit/**/*.test.ts'` from site/)
// run the same tests.

import { readdirSync } from 'node:fs';

const here = new URL('./', import.meta.url);
for (const name of readdirSync(here).filter((n) => n.endsWith('.test.ts')).sort()) {
  await import(new URL(name, here).href);
}
