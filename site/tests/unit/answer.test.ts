import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  check,
  checkExpr,
  checkNumeric,
  decomposeUnit,
  evaluate,
  formatExpr,
  parseAnswers,
  parseExpr,
  parseNumber,
  sameValues,
  toleranceHint,
} from '../../src/lib/answer.ts';

// Reference values computed with Python: 1/(2*pi*1e3*100e-9) = 1591.549…,
// 20*log10(1/sqrt(2)) = -3.0103 (the §2.5 example answers).
const FG = { key: 'fg', label: '$f_\\mathrm{g}$', value: 1591.55, unit: 'Hz', rtol: 1e-3 };
const HDB = { key: 'Hdb', label: '$|H|$', value: -3.0103, unit: 'dB', atol: 0.01 };
const H = { key: 'H', label: '$H(s)$', expr: '1/(1+s*R*C)', symbols: ['s', 'R', 'C'] };

const num = (text: string) => parseNumber(text)?.value;

test('German and English decimal separators', () => {
  assert.equal(num('1,59'), 1.59);
  assert.equal(num('1.59'), 1.59);
  assert.equal(num('1591,55'), 1591.55);
  assert.equal(num(',5'), 0.5);
  assert.equal(num('.5'), 0.5);
  assert.equal(num('0'), 0);
});

test('thousands separators: dots, commas, spaces and apostrophes', () => {
  assert.equal(num('1.591,55'), 1591.55);
  assert.equal(num('1,591.55'), 1591.55);
  assert.equal(num('1.000.000'), 1e6);
  assert.equal(num('1,000,000'), 1e6);
  assert.equal(num('1 591,55'), 1591.55);
  assert.equal(num('1 591,55'), 1591.55);
  assert.equal(num("1'591.55"), 1591.55);
  assert.equal(num('100 200'), 100200);
  // malformed groups are rejected rather than guessed
  assert.equal(parseNumber('1.5.3'), null);
  assert.equal(parseNumber('12,34,5'), null);
  assert.equal(parseNumber('1.591.5,2,3'), null);
});

test('signs and exponents', () => {
  assert.equal(num('-3,01'), -3.01);
  assert.equal(num('−3,01'), -3.01);
  assert.equal(num('+2'), 2);
  assert.equal(num('- 2'), -2);
  assert.equal(num('1.59e3'), 1590);
  assert.equal(num('1,59E3'), 1590);
  assert.equal(num('2e-3'), 0.002);
  assert.equal(num('1,59·10^3'), 1590);
  assert.equal(num('1,59 x 10^3'), 1590);
  assert.equal(num('1,59×10³'), 1590);
  assert.equal(num('1,59 * 10^(-3)'), 0.00159);
  assert.equal(num('1,59·10⁻³'), 0.00159);
  assert.equal(num('10^-3'), 0.001);
  assert.equal(num('10⁶'), 1e6);
  assert.equal(parseNumber('abc'), null);
  assert.equal(parseNumber('kHz'), null);
  assert.equal(parseNumber(''), null);
});

test('units and SI prefixes are split off', () => {
  assert.deepEqual(parseNumber('1,59 kHz'), { value: 1.59, unit: 'kHz', decimalComma: true });
  assert.deepEqual(parseNumber('6 V'), { value: 6, unit: 'V', decimalComma: false });
  assert.equal(parseNumber('4,7µF')?.unit, 'μF');
  assert.equal(parseNumber('-45°')?.unit, '°');
  assert.equal(parseNumber('2,2 k Ω')?.unit, 'kΩ');
  assert.equal(parseNumber('5eV')?.unit, 'eV');
  assert.deepEqual(decomposeUnit('kHz'), { factor: 1e3, base: 'Hz', prefixOnly: false });
  assert.deepEqual(decomposeUnit('kOhm'), { factor: 1e3, base: 'Ω', prefixOnly: false });
  assert.deepEqual(decomposeUnit('µF'), { factor: 1e-6, base: 'F', prefixOnly: false });
  assert.deepEqual(decomposeUnit('uF'), { factor: 1e-6, base: 'F', prefixOnly: false });
  assert.deepEqual(decomposeUnit('dB'), { factor: 1, base: 'dB', prefixOnly: false });
  assert.deepEqual(decomposeUnit('min'), { factor: 1, base: 'min', prefixOnly: false });
  assert.deepEqual(decomposeUnit('mm'), { factor: 1e-3, base: 'm', prefixOnly: false });
  assert.deepEqual(decomposeUnit('m'), { factor: 1, base: 'm', prefixOnly: false });
  assert.deepEqual(decomposeUnit('k'), { factor: 1e3, base: '', prefixOnly: true });
  assert.deepEqual(decomposeUnit('V/A'), { factor: 1, base: 'V/A', prefixOnly: false });
});

test('numeric answers: tolerance relative to the reference (rtol)', () => {
  for (const ok of ['1591,55', '1,59 kHz', '1.59 kHz', '1590 Hz', '1,5915e3', '1,59k', '1.591,5 Hz', '0,00159 MHz', '1,59 khz', '1,59 KHz']) {
    assert.equal(checkNumeric(ok, FG).ok, true, ok);
  }
  for (const bad of ['1,6 kHz', '1500', '159 Hz']) {
    const v = checkNumeric(bad, FG);
    assert.equal(v.ok, false, bad);
    assert.equal(v.ok ? '' : v.reason, 'tolerance');
  }
});

test('numeric answers: absolute tolerance (atol) and units without prefixes', () => {
  assert.equal(checkNumeric('-3,01 dB', HDB).ok, true);
  assert.equal(checkNumeric('−3,01', HDB).ok, true);
  assert.equal(checkNumeric('-3,02 db', HDB).ok, true);
  assert.equal(checkNumeric('-3 dB', HDB).ok, false); // 0.0103 > 0.01
  assert.equal(checkNumeric('-3,03 dB', HDB).ok, false);
});

test('numeric answers: the answer unit may carry a prefix itself', () => {
  const spec = { key: 'R', label: 'R', value: 2.2, unit: 'kΩ', rtol: 1e-3 };
  assert.equal(checkNumeric('2,2', spec).ok, true);
  assert.equal(checkNumeric('2200 Ω', spec).ok, true);
  assert.equal(checkNumeric('2200 Ohm', spec).ok, true);
  assert.equal(checkNumeric('2,2 kOhm', spec).ok, true);
  assert.equal(checkNumeric('0,0022 MΩ', spec).ok, true);
  assert.equal(checkNumeric('2,2 Ω', spec).ok, false);
  const deg = { key: 'phi', label: 'φ', value: -45, unit: '°', atol: 0.5 };
  assert.equal(checkNumeric('-45°', deg).ok, true);
  assert.equal(checkNumeric('-45 deg', deg).ok, true);
  assert.equal(checkNumeric('-0,7854 rad', deg).ok, true);
});

test('numeric answers: unit mismatch, unreadable and empty input', () => {
  const unit = checkNumeric('1,59 kV', FG);
  assert.equal(unit.ok, false);
  assert.equal(unit.ok ? '' : unit.reason, 'unit');
  assert.match(unit.message, /asked in Hz/);
  const unreadable = checkNumeric('etwa eins', FG);
  assert.equal(unreadable.ok ? '' : unreadable.reason, 'unreadable');
  const empty = checkNumeric('  ', FG);
  assert.equal(empty.ok ? '' : empty.reason, 'empty');
  const dimless = { key: 'v', label: 'v', value: 0.5, rtol: 1e-3 };
  assert.equal(checkNumeric('50 %', dimless).ok, true);
  assert.equal(checkNumeric('0,5', dimless).ok, true);
  assert.equal(checkNumeric('0,5 V', dimless).ok, false);
});

test('numeric answers: read-back and typical-mistake hints', () => {
  const v = checkNumeric('1,59 kHz', FG);
  assert.equal(v.read, '1,59 kHz = 1590 Hz');
  const twoPi = checkNumeric('10 kHz', FG);
  assert.match(twoPi.ok ? '' : (twoPi.hint ?? ''), /2π/);
  const decade = checkNumeric('159,155 Hz', FG);
  assert.match(decade.ok ? '' : (decade.hint ?? ''), /power of ten/);
  const rms = checkNumeric('2250,79 Hz', FG);
  assert.match(rms.ok ? '' : (rms.hint ?? ''), /√2/);
  const lin = checkNumeric('0,7071', HDB);
  assert.match(lin.ok ? '' : (lin.hint ?? ''), /linear/);
  const sign = checkNumeric('3,0103 dB', HDB);
  assert.match(sign.ok ? '' : (sign.hint ?? ''), /sign/);
  assert.equal(toleranceHint(FG), '±0.1 %');
  assert.equal(toleranceHint(HDB), '±0.01 dB');
});

test('expression parser: precedence, implicit multiplication and read-back', () => {
  const sym = ['s', 'R', 'C'];
  assert.equal(formatExpr(parseExpr('1/(1+s*R*C)', sym)), '1/(1 + s·R·C)');
  assert.equal(formatExpr(parseExpr('1/(1+sRC)', sym)), '1/(1 + s·R·C)');
  assert.equal(formatExpr(parseExpr('1 / (1 + s R C)', sym)), '1/(1 + s·R·C)');
  assert.equal(formatExpr(parseExpr('2^-1', [])), '2^(−1)');
  assert.equal(formatExpr(parseExpr('-s^2', sym)), '−s^2');
  assert.equal(formatExpr(parseExpr('a-(b-c)', ['a', 'b', 'c'])), 'a − (b − c)');
  assert.equal(formatExpr(parseExpr('2(s+1)', sym)), '2·(s + 1)');
  const env = { s: 2, R: 3, C: 5 };
  assert.equal(evaluate(parseExpr('2^3^2', []), env).re, 512); // right-associative
  assert.equal(evaluate(parseExpr('-2^2', []), env).re, -4);
  assert.equal(evaluate(parseExpr('s**2 R', sym), env).re, 12);
  assert.equal(evaluate(parseExpr('6/2s', sym), env).re, 6); // (6/2)·s
  assert.ok(Math.abs(evaluate(parseExpr('e^(j*pi)', []), env).re + 1) < 1e-12);
  assert.ok(Math.abs(evaluate(parseExpr('sqrt(-4)', []), env).im - 2) < 1e-12);
  assert.ok(Math.abs(evaluate(parseExpr('2π', []), env).re - 2 * Math.PI) < 1e-12);
  assert.ok(Math.abs(evaluate(parseExpr('0,5·s', sym), env).re - 1) < 1e-12);
});

test('expression parser: errors are reported, never evaluated', () => {
  assert.throws(() => parseExpr('1/(1+s*R*C', ['s', 'R', 'C']), /closing parenthesis/);
  assert.throws(() => parseExpr('x + 1', ['s']), /Unknown name “x”/);
  assert.throws(() => parseExpr('alert(1)', ['s']), /Unknown name/);
  assert.throws(() => parseExpr('constructor', ['s']), /Unknown name/);
  assert.throws(() => parseExpr('toString(1)', ['s']), /Unknown name/);
  assert.equal(decomposeUnit('constructor').base, 'constructor');
  assert.throws(() => parseExpr('sin s', ['s']), /parentheses/);
  assert.throws(() => parseExpr('1 + ', []), /ends too early/);
  assert.throws(() => parseExpr('1 $ 2', []), /Unexpected/);
});

test('expression answers: equivalent forms pass, different ones fail', () => {
  for (const ok of ['1/(1+s*R*C)', '1/(1+sRC)', '1/(s C R + 1)', '(1+s*R*C)^-1', '1/(1+RCs)', '(1 + R·C·s)⁻¹']) {
    assert.equal(checkExpr(ok, H).ok, true, ok);
  }
  for (const bad of ['1/(1+s*R)', 's*R*C/(1+s*R*C)', '1/(1+s*R*C)^2', '1/(1-s*R*C)']) {
    const v = checkExpr(bad, H);
    assert.equal(v.ok, false, bad);
    assert.equal(v.ok ? '' : v.reason, 'different');
  }
  const name = checkExpr('1/(1+s*L)', H);
  assert.equal(name.ok ? '' : name.reason, 'name');
  assert.match(name.message, /Use the symbols s, R, C/);
  // complex-valued references (SymPy syntax with I)
  const Z = { key: 'Z', label: 'Z', expr: 'R + 1/(I*w*C)', symbols: ['R', 'w', 'C'] };
  assert.equal(checkExpr('R - j/(ωC)', Z).ok, true);
  assert.equal(checkExpr('R + j/(w C)', Z).ok, false);
  const decay = { key: 'u', label: 'u', expr: 'U*exp(-t/(R*C))', symbols: ['U', 't', 'R', 'C'] };
  assert.equal(checkExpr('U e^(-t/(RC))', decay).ok, true);
  assert.equal(checkExpr('U (1 - e^(-t/(RC)))', decay).ok, false);
  assert.equal(sameValues(parseExpr('s', ['s']), parseExpr('s', ['s']), ['s']), true);
});

test('check dispatches on expr and parseAnswers reads data-answers', () => {
  assert.equal(check('1,59 kHz', FG).ok, true);
  assert.equal(check('1/(1+sRC)', H).ok, true);
  const answers = parseAnswers(JSON.stringify([FG, H, { key: 'x' }, 'junk']));
  assert.deepEqual(answers.map((a) => a.key), ['fg', 'H']);
  assert.deepEqual(parseAnswers('not json'), []);
  assert.deepEqual(parseAnswers(undefined), []);
});
