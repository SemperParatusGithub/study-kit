// Colour pairs of styles/tokens.css used for text: at least 4.5:1 (WCAG 1.4.3) in the light
// and the dark theme, as the file's header promises.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const css = readFileSync(new URL('../../src/styles/tokens.css', import.meta.url), 'utf8');

/** --name: light-dark(#light, #dark) → [light, dark] */
function token(name: string): [string, string] {
  const m = new RegExp(`--${name}:\\s*light-dark\\((#[0-9a-f]{6}),\\s*(#[0-9a-f]{6})\\)`, 'i').exec(css);
  assert.ok(m, `token --${name}`);
  return [m[1] ?? '', m[2] ?? ''];
}

function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const c = Number.parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * (r ?? 0) + 0.7152 * (g ?? 0) + 0.0722 * (b ?? 0);
}

function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return ((hi ?? 0) + 0.05) / ((lo ?? 0) + 0.05);
}

// [text, background]: feedback text on its tint, box titles on their box, text on surfaces
const PAIRS: Array<[string, string]> = [
  ['ok', 'ok-soft'],
  ['warn', 'warn-soft'],
  ['bad', 'bad-soft'],
  ['accent', 'accent-soft'],
  ...['definition', 'theorem', 'example', 'note', 'warning', 'takeaways'].map(
    (k): [string, string] => [`box-${k}`, `box-${k}-bg`],
  ),
  ...['text', 'text-muted', 'accent', 'ok', 'warn', 'bad'].flatMap((t): Array<[string, string]> => [
    [t, 'bg'],
    [t, 'surface'],
  ]),
];

for (const [fg, bg] of PAIRS) {
  test(`--${fg} on --${bg} has 4.5:1 or more in both themes`, () => {
    const [fl, fd] = token(fg);
    const [bl, bd] = token(bg);
    assert.ok(contrast(fl, bl) >= 4.5, `light ${fl} on ${bl}: ${contrast(fl, bl).toFixed(2)}`);
    assert.ok(contrast(fd, bd) >= 4.5, `dark ${fd} on ${bd}: ${contrast(fd, bd).toFixed(2)}`);
  });
}
