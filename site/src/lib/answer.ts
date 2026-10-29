// Answer checking for exercises (docs/architecture.md §2.5).
//
// Numeric answers `{key, label, value, unit, rtol, atol}`: the input is read as a number in
// German or English notation with an optional SI prefix and unit ("1,59 kHz", "1.59e3 Hz",
// "1.591,5", "−3,01 dB", "4,7 µF", "2,2 kOhm") and accepted when
//     |x − value| ≤ atol + rtol·|value|      (both in the answer's unit; a missing one is 0).
// A number without a unit is read in the answer's unit.
// Separators: with both "." and "," the last one is the decimal separator; a single "." or
// "," is always decimal; repeated ones (and spaces or ' between groups of three digits) are
// thousands separators. Also read: a leading "f =" or "≈", a trailing "." or ";", resistor
// codes ("2k2" = 2,2 k, "4R7" = 4,7) and plain arithmetic without symbols ("1/√2", "2π·50").
//
// Symbolic answers `{key, label, expr, symbols}`: the input and the reference (SymPy syntax:
// ** or ^, I for the imaginary unit, E, pi, sqrt, exp, log …) are parsed by a small
// recursive-descent parser (no eval) and evaluated with complex arithmetic at random
// positive values of the symbols; they must agree at every sample point. "√x" and "√(…)"
// are sqrt.

import { fnv1a, mulberry32 } from './shuffle.ts';

export interface AnswerSpec {
  key: string;
  label: string;
  value?: number | null | undefined;
  unit?: string | null | undefined;
  rtol?: number | null | undefined;
  atol?: number | null | undefined;
  expr?: string | null | undefined;
  symbols?: readonly string[] | null | undefined;
}

export type Reason = 'empty' | 'unreadable' | 'unit' | 'tolerance' | 'syntax' | 'name' | 'different';

export type Verdict =
  | { ok: true; message: string; read: string }
  | { ok: false; reason: Reason; message: string; read?: string; hint?: string };

// --- text normalisation ---------------------------------------------------------------

const SUPERSCRIPTS: Record<string, string> = {
  '⁰': '0', '¹': '1', '²': '2', '³': '3', '⁴': '4',
  '⁵': '5', '⁶': '6', '⁷': '7', '⁸': '8', '⁹': '9', '⁻': '-', '⁺': '+',
};

export function normalize(text: string): string {
  return text
    .normalize('NFC')
    .replace(/[−‐-–]/g, '-')
    .replace(/[  -   ]/g, ' ')
    .replace(/µ/g, 'μ') // micro sign → Greek mu
    .replace(/Ω/g, 'Ω') // ohm sign → Greek capital omega
    .replace(/[⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺]+/g, (m) => '^' + [...m].map((c) => SUPERSCRIPTS[c] ?? '').join(''))
    .replace(/\s+/g, ' ')
    .trim();
}

// --- numbers ----------------------------------------------------------------------------

export interface ParsedNumber {
  value: number;
  unit: string;
  decimalComma: boolean;
  /** How arithmetic input was read ("1/sqrt(2)"); absent for plain numbers. */
  read?: string;
}

function count(text: string, ch: string): number {
  let n = 0;
  for (const c of text) if (c === ch) n++;
  return n;
}

function joinGroups(intPart: string, sep: string): string | null {
  const groups = intPart.split(sep);
  const [first, ...rest] = groups;
  if (first === undefined || !/^\d{1,3}$/.test(first)) return null;
  if (!rest.every((g) => /^\d{3}$/.test(g))) return null;
  return groups.join('');
}

/** The value of a mantissa such as "1.591,55", "1,59", "1 591.5" or ".5"; null if malformed. */
function mantissa(raw: string): { value: number; decimalComma: boolean } | null {
  const text = raw.replace(/['\s]/g, '');
  if (!/^[\d.,]+$/.test(text) || !/\d/.test(text)) return null;
  const dots = count(text, '.');
  const commas = count(text, ',');
  let decimal: '.' | ',' | null = null;
  let thousands: '.' | ',' | null = null;
  if (dots > 0 && commas > 0) {
    decimal = text.lastIndexOf('.') > text.lastIndexOf(',') ? '.' : ',';
    thousands = decimal === '.' ? ',' : '.';
    if (count(text, decimal) !== 1) return null;
  } else if (dots + commas === 1) {
    decimal = dots ? '.' : ',';
  } else if (dots > 1) {
    thousands = '.';
  } else if (commas > 1) {
    thousands = ',';
  }
  let intPart = text;
  let frac = '';
  if (decimal) {
    const at = text.indexOf(decimal);
    intPart = text.slice(0, at);
    frac = text.slice(at + 1);
  }
  if (thousands) {
    const joined = joinGroups(intPart, thousands);
    if (joined === null) return null;
    intPart = joined;
  }
  // Spaces and ' only between groups of three digits (checked by the scanner) end up here.
  if (!/^\d*$/.test(intPart) || !/^\d*$/.test(frac) || (intPart === '' && frac === '')) return null;
  const value = Number(`${intPart || '0'}.${frac || '0'}`);
  return Number.isFinite(value) ? { value, decimalComma: decimal === ',' } : null;
}

/** "f =", "U_2 =", "≈", "~" before the value. */
const LEAD = /^(?:[A-Za-z\u0370-\u03ff][\w\u0370-\u03ff]*\s?)?(?:=|≈|~)\s?/;
/**
 * Resistor and capacitor codes (IEC 60062): a multiplier letter in place of the decimal
 * point ("2k2" = 2,2 k, "4R7" = 4,7, "4u7" = 4,7 μ). Not "m": "1m5" would read as metres.
 */
const R_CODE = /^(\d+)([RkMGTpnuμ])(\d+)(?![\d.,'])/;

/** The input without a leading "name =" / "≈" and trailing sentence punctuation. */
function trimmed(text: string): string {
  return normalize(text).replace(LEAD, '').replace(/\s?[.;,]+$/, '');
}

const EXPONENT_E = /^[eE]([+-]?\d+)/;
const EXPONENT_TEN = /^\s?[*·⋅×xX]\s?10\s?\^\s?[({]?\s?([+-]?\d+)\s?[)}]?/;
const POWER_OF_TEN = /^\s?\^\s?[({]?\s?([+-]?\d+)\s?[)}]?/;

/** Read "<sign><number><exponent> <unit>"; null when the text does not start with a number. */
export function parseNumber(text: string): ParsedNumber | null {
  const s = trimmed(text);
  let i = 0;
  let sign = 1;
  if (s[i] === '+' || s[i] === '-') {
    sign = s[i] === '-' ? -1 : 1;
    i++;
    if (s[i] === ' ') i++;
  }
  const code = R_CODE.exec(s.slice(i));
  if (code) {
    const [whole, int, letter, frac] = code as unknown as [string, string, string, string];
    const rest = s.slice(i + whole.length).trim().replace(/\s/g, '');
    return {
      value: sign * Number(`${int}.${frac}`),
      unit: `${letter === 'R' ? '' : letter}${rest}`,
      decimalComma: false,
    };
  }
  let raw = '';
  while (i < s.length) {
    const c = s[i] as string;
    if (/[\d.,']/.test(c)) {
      raw += c;
      i++;
    } else if (c === ' ' && /\d$/.test(raw) && /^\d{3}(?!\d)/.test(s.slice(i + 1))) {
      raw += c;
      i++;
    } else {
      break;
    }
  }
  const m = mantissa(raw);
  if (!m) return null;
  let value = m.value;
  const rest = s.slice(i);
  const exponent = EXPONENT_E.exec(rest) ?? EXPONENT_TEN.exec(rest);
  const power = exponent ? null : raw === '10' ? POWER_OF_TEN.exec(rest) : null;
  if (exponent) {
    value *= 10 ** Number(exponent[1]); // 1,59e3 · 1,59·10^3
    i += exponent[0].length;
  } else if (power) {
    value = 10 ** Number(power[1]); // 10^-3
    i += power[0].length;
  }
  const unit = s.slice(i).trim().replace(/^\[(.*)\]$/, '$1').replace(/\s/g, '');
  return { value: sign * value, unit, decimalComma: m.decimalComma };
}

// --- units ------------------------------------------------------------------------------

const PREFIXES: ReadonlyArray<readonly [string, number]> = [
  ['da', 1e1], ['Y', 1e24], ['Z', 1e21], ['E', 1e18], ['P', 1e15], ['T', 1e12], ['G', 1e9],
  ['M', 1e6], ['k', 1e3], ['h', 1e2], ['d', 1e-1], ['c', 1e-2], ['m', 1e-3], ['μ', 1e-6],
  ['u', 1e-6], ['n', 1e-9], ['p', 1e-12], ['f', 1e-15], ['a', 1e-18],
];
const PREFIX = new Map(PREFIXES);

const UNITS = new Set([
  'Hz', 'V', 'A', 'W', 'Ω', 'F', 'H', 's', 'm', 'g', 'K', 'J', 'N', 'Pa', 'C', 'S', 'T', 'Wb',
  'VA', 'var', 'Wh', 'Ah', 'eV', 'lm', 'lx', 'cd', 'mol', 'bar', 'l', 'L', 'B', 'bit', 'Np',
  'dB', 'dBm', 'dBV', 'dBu', 'dBW', '%', '‰', 'ppm', '°', '°C', 'rad', 'sr', 'min', 'h', 'd',
]);

// Lookup tables are Maps: a plain object would also "contain" names such as constructor.
const ALIASES = new Map(Object.entries({
  Ohm: 'Ω', ohm: 'Ω', Ohms: 'Ω', ohms: 'Ω', deg: '°', Grad: '°', sec: 's', hz: 'Hz', HZ: 'Hz',
  db: 'dB', DB: 'dB', '1/s': 's^-1',
}));

function canon(unit: string): string {
  return ALIASES.get(unit) ?? unit;
}

export interface UnitParts {
  factor: number;
  base: string;
  prefixOnly: boolean;
}

/** Split a unit into SI prefix factor and base unit ("kΩ" → 1e3, "Ω"; "min" → 1, "min"). */
export function decomposeUnit(unit: string): UnitParts {
  const u = canon(normalize(unit).replace(/\s/g, ''));
  if (u === '' || UNITS.has(u)) return { factor: 1, base: u, prefixOnly: false };
  for (const [p, f] of PREFIXES) {
    if (u.length > p.length && u.startsWith(p)) {
      const rest = canon(u.slice(p.length));
      if (UNITS.has(rest)) return { factor: f, base: rest, prefixOnly: false };
    }
  }
  const only = PREFIX.get(u);
  if (only !== undefined) return { factor: only, base: '', prefixOnly: true };
  return { factor: 1, base: u, prefixOnly: false }; // compound units are compared verbatim
}

/** Factor that turns a value in `given` into base units of `expected`, or null. */
function unitFactor(given: string, expected: UnitParts): number | null {
  if (given === '') return expected.factor;
  const g = decomposeUnit(given);
  if (g.base === expected.base && !g.prefixOnly) return g.factor;
  if (g.prefixOnly) return g.factor; // "1,59 k" with the answer in Hz
  if (g.base === '°' && expected.base === 'rad') return (g.factor * Math.PI) / 180;
  if (g.base === 'rad' && expected.base === '°') return (g.factor * 180) / Math.PI;
  if (expected.base === '' && g.base === '%') return 0.01;
  // Lenient about the case of the base unit ("khz", "KHz"), never about the prefix.
  const want = expected.base.toLowerCase();
  if (want === '') return null;
  const lower = given.toLowerCase();
  if (lower === want) return 1;
  for (const [p, f] of [...PREFIXES, ['K', 1e3] as const]) {
    if (given.startsWith(p) && given.slice(p.length).toLowerCase() === want) return f;
  }
  return null;
}

// --- formatting -------------------------------------------------------------------------

export function formatNumber(value: number, decimalComma = false): string {
  if (!Number.isFinite(value)) return String(value);
  const abs = Math.abs(value);
  let text: string;
  if (abs !== 0 && (abs >= 1e7 || abs < 1e-4)) {
    const [m, e] = value.toExponential(5).split('e');
    text = `${String(Number(m))}·10^${Number(e)}`;
  } else {
    text = String(Number(value.toPrecision(6)));
  }
  return decimalComma ? text.replace('.', ',') : text;
}

function tolText(spec: AnswerSpec): string {
  const parts: string[] = [];
  if (spec.rtol) parts.push(`${formatNumber(spec.rtol * 100)} %`);
  if (spec.atol) parts.push(`${formatNumber(spec.atol)}${spec.unit ? ` ${spec.unit}` : ''}`);
  return parts.join(' + ');
}

/** "±0.1 %" or "±0.01 dB": the tolerance in words for the input hint. */
export function toleranceHint(spec: AnswerSpec): string {
  const t = tolText(spec);
  return t ? `±${t}` : '';
}

// --- numeric check ----------------------------------------------------------------------

function near(a: number, b: number, rel: number): boolean {
  return Math.abs(a - b) <= rel * Math.max(Math.abs(a), Math.abs(b));
}

/** A hint naming a typical mistake when the value is off by a telltale factor. */
export function mistakeHint(got: number, want: number, unit: UnitParts): string | undefined {
  if (got === 0 || want === 0 || !Number.isFinite(got)) return undefined;
  const rel = 3e-3;
  if (unit.base === 'dB' && near(20 * Math.log10(Math.abs(got)), want, rel)) {
    return 'That looks like the linear value; the answer is asked in dB.';
  }
  if (unit.base === '°' && near((got * 180) / Math.PI, want, rel)) {
    return 'That looks like radians; the answer is asked in degrees.';
  }
  if (unit.base === 'rad' && near((got * Math.PI) / 180, want, rel)) {
    return 'That looks like degrees; the answer is asked in radians.';
  }
  const r = got / want;
  if (near(r, -1, rel)) return 'Check the sign.';
  if (near(Math.abs(r), 2 * Math.PI, rel) || near(Math.abs(r), 1 / (2 * Math.PI), rel)) {
    return 'Off by a factor of 2π: angular frequency ω versus frequency f?';
  }
  if (near(Math.abs(r), Math.SQRT2, rel) || near(Math.abs(r), Math.SQRT1_2, rel)) {
    return 'Off by a factor of √2: amplitude versus RMS value?';
  }
  const k = Math.log10(Math.abs(r));
  if (r > 0 && Math.round(k) !== 0 && Math.abs(k - Math.round(k)) < 1.5e-3) {
    return 'Off by a power of ten: check the unit prefixes.';
  }
  return undefined;
}

/** Arithmetic in the input: an operator, a root, a power, π or parentheses. */
const ARITHMETIC = /[/*·×÷√^()π]|\bpi\b|\bsqrt\b/;

/** The value of a constant expression such as "1/√2" or "2π·50", or null. */
export function constantValue(text: string): { value: number; read: string } | null {
  const s = trimmed(text);
  // "1.591,5/2": the expression reader knows no thousands separators, so do not guess.
  if (/\d[.,]\d+[.,]\d/.test(s)) return null;
  if (!ARITHMETIC.test(s.replace(/^[+-]?[\d.,' ]+\s?[*·×xX]\s?10\s?\^/, ''))) return null;
  try {
    const e = parseExpr(s, []);
    const v = evaluate(e, {});
    if (!Number.isFinite(v.re) || Math.abs(v.im) > 1e-12 * Math.max(1, Math.abs(v.re))) return null;
    return { value: v.re, read: formatExpr(e) };
  } catch {
    return null;
  }
}

export function checkNumeric(input: string, spec: AnswerSpec): Verdict {
  if (normalize(input) === '') return { ok: false, reason: 'empty', message: 'Enter a value.' };
  const parsed = numberOrArithmetic(input, spec);
  if (!parsed) {
    return {
      ok: false,
      reason: 'unreadable',
      message: 'This is not a number I can read. Examples: 1,59 kHz · 1.59e3 Hz · −3,01 dB',
    };
  }
  const expected = decomposeUnit(spec.unit ?? '');
  const factor = unitFactor(parsed.unit, expected);
  const read = parsed.read !== undefined
    ? `${parsed.read} = ${formatNumber(parsed.value, parsed.decimalComma)}`
    : `${formatNumber(parsed.value, parsed.decimalComma)}${parsed.unit ? ` ${parsed.unit}` : ''}`;
  if (factor === null) {
    return {
      ok: false,
      reason: 'unit',
      read,
      message: spec.unit
        ? `The unit “${parsed.unit}” does not fit; the answer is asked in ${spec.unit}.`
        : `The answer has no unit; remove “${parsed.unit}”.`,
    };
  }
  const want = (spec.value ?? Number.NaN) * expected.factor;
  const got = parsed.value * factor;
  const tol = (spec.atol ?? 0) * expected.factor + (spec.rtol ?? 0) * Math.abs(want);
  const shown =
    factor !== expected.factor && expected.base
      ? `${read} = ${formatNumber(got / expected.factor, parsed.decimalComma)} ${spec.unit ?? ''}`.trim()
      : read;
  if (Math.abs(got - want) <= tol) return { ok: true, read: shown, message: 'Correct.' };
  const hint = mistakeHint(got, want, expected);
  const tolerance = toleranceHint(spec);
  return {
    ok: false,
    reason: 'tolerance',
    read: shown,
    message: `Not correct${tolerance ? ` within ${tolerance}` : ''}.`,
    ...(hint ? { hint } : {}),
  };
}

/**
 * The input as a number with unit; when that fails or leaves a unit that does not fit,
 * the input as plain arithmetic without symbols, in the answer's unit ("1/√2").
 */
function numberOrArithmetic(input: string, spec: AnswerSpec): ParsedNumber | null {
  const parsed = parseNumber(input);
  if (parsed && unitFactor(parsed.unit, decomposeUnit(spec.unit ?? '')) !== null) return parsed;
  const c = constantValue(input);
  if (c) return { value: c.value, unit: '', decimalComma: /\d,\d/.test(input), read: c.read };
  return parsed;
}

// --- expressions ------------------------------------------------------------------------

export type Expr =
  | { k: 'num'; v: number }
  | { k: 'sym'; name: string }
  | { k: 'const'; name: 'pi' | 'e' | 'i' }
  | { k: 'neg'; a: Expr }
  | { k: 'bin'; op: '+' | '-' | '*' | '/' | '^'; a: Expr; b: Expr }
  | { k: 'call'; fn: string; a: Expr };

export class ExprError extends Error {
  reason: 'syntax' | 'name';
  constructor(reason: 'syntax' | 'name', message: string) {
    super(message);
    this.reason = reason;
  }
}

interface Cx {
  re: number;
  im: number;
}

const cx = (re: number, im = 0): Cx => ({ re, im });
const add = (a: Cx, b: Cx): Cx => cx(a.re + b.re, a.im + b.im);
const sub = (a: Cx, b: Cx): Cx => cx(a.re - b.re, a.im - b.im);
const mul = (a: Cx, b: Cx): Cx => cx(a.re * b.re - a.im * b.im, a.re * b.im + a.im * b.re);
function div(a: Cx, b: Cx): Cx {
  const d = b.re * b.re + b.im * b.im;
  return cx((a.re * b.re + a.im * b.im) / d, (a.im * b.re - a.re * b.im) / d);
}
const abs = (a: Cx): number => Math.hypot(a.re, a.im);
const exp = (a: Cx): Cx => cx(Math.exp(a.re) * Math.cos(a.im), Math.exp(a.re) * Math.sin(a.im));
// `+ 0` turns −0 into +0: the principal branch must give log(−4) = ln 4 + iπ.
const log = (a: Cx): Cx => cx(Math.log(abs(a)), Math.atan2(a.im + 0, a.re));
const I = cx(0, 1);
const ONE = cx(1);
function pow(a: Cx, b: Cx): Cx {
  if (b.im === 0 && Number.isInteger(b.re) && Math.abs(b.re) <= 64) {
    let result = ONE;
    let base = a;
    let n = Math.abs(b.re);
    while (n > 0) {
      if (n & 1) result = mul(result, base);
      base = mul(base, base);
      n >>= 1;
    }
    return b.re < 0 ? div(ONE, result) : result;
  }
  if (a.re === 0 && a.im === 0) return b.re > 0 ? cx(0) : cx(Number.NaN);
  return exp(mul(b, log(a)));
}
const sqrt = (a: Cx): Cx => pow(a, cx(0.5));
const sin = (a: Cx): Cx => cx(Math.sin(a.re) * Math.cosh(a.im), Math.cos(a.re) * Math.sinh(a.im));
const cos = (a: Cx): Cx => cx(Math.cos(a.re) * Math.cosh(a.im), -Math.sin(a.re) * Math.sinh(a.im));
const sinh = (a: Cx): Cx => div(sub(exp(a), exp(cx(-a.re, -a.im))), cx(2));
const cosh = (a: Cx): Cx => div(add(exp(a), exp(cx(-a.re, -a.im))), cx(2));
// asin z = −i·log(iz + √(1 − z²)), atan z = (i/2)·(log(1 − iz) − log(1 + iz))
const asin = (a: Cx): Cx => mul(cx(0, -1), log(add(mul(I, a), sqrt(sub(ONE, mul(a, a))))));
const atan = (a: Cx): Cx =>
  mul(cx(0, 0.5), sub(log(sub(ONE, mul(I, a))), log(add(ONE, mul(I, a)))));

const FUNCTIONS = new Map<string, (a: Cx) => Cx>(Object.entries({
  sqrt,
  exp,
  ln: log,
  log,
  lg: (a: Cx) => div(log(a), cx(Math.LN10)),
  log10: (a: Cx) => div(log(a), cx(Math.LN10)),
  sin,
  cos,
  tan: (a: Cx) => div(sin(a), cos(a)),
  asin,
  arcsin: asin,
  acos: (a: Cx) => sub(cx(Math.PI / 2), asin(a)),
  arccos: (a: Cx) => sub(cx(Math.PI / 2), asin(a)),
  atan,
  arctan: atan,
  sinh,
  cosh,
  tanh: (a: Cx) => div(sinh(a), cosh(a)),
  abs: (a: Cx) => cx(abs(a)),
  Abs: (a: Cx) => cx(abs(a)),
  arg: (a: Cx) => cx(Math.atan2(a.im, a.re)),
  re: (a: Cx) => cx(a.re),
  im: (a: Cx) => cx(a.im),
}));

const CONSTANTS = new Map<string, 'pi' | 'e' | 'i'>([
  ['pi', 'pi'], ['Pi', 'pi'], ['e', 'e'], ['E', 'e'], ['i', 'i'], ['j', 'i'], ['I', 'i'],
]);

const GREEK = new Map(Object.entries({
  α: 'alpha', β: 'beta', γ: 'gamma', δ: 'delta', ε: 'epsilon', ζ: 'zeta', η: 'eta',
  θ: 'theta', κ: 'kappa', λ: 'lambda', μ: 'mu', ν: 'nu', ξ: 'xi', π: 'pi', ρ: 'rho',
  σ: 'sigma', τ: 'tau', φ: 'phi', ϕ: 'phi', χ: 'chi', ψ: 'psi', ω: 'omega', Ω: 'Omega',
  Δ: 'Delta', Φ: 'Phi',
}));

type Tok = { t: 'num'; v: number } | { t: 'id'; s: string } | { t: 'op'; s: string };

function tokenize(source: string): Tok[] {
  const s = normalize(source)
    .replace(/\*\*/g, '^')
    .replace(/[·⋅×]/g, '*')
    .replace(/√/g, ' √ ')
    .replace(/÷/g, '/')
    .replace(/[[{]/g, '(')
    .replace(/[\]}]/g, ')')
    .replace(/[α-ωΑ-Ωϕ]/g, (c) => {
      const name = GREEK.get(c);
      return name ? ` ${name} ` : c;
    });
  const out: Tok[] = [];
  const re = /\s*(?:(\d+(?:[.,]\d+)?(?:[eE][+-]?\d+)?|[.,]\d+)|([A-Za-z_][A-Za-z0-9_]*)|([-+*/^()√]))/y;
  let i = 0;
  while (i < s.length) {
    if (/^\s*$/.test(s.slice(i))) break;
    re.lastIndex = i;
    const m = re.exec(s);
    if (!m) throw new ExprError('syntax', `Unexpected “${s.slice(i).trim().slice(0, 12)}”.`);
    if (m[1] !== undefined) out.push({ t: 'num', v: Number(m[1].replace(',', '.')) });
    else if (m[2] !== undefined) out.push({ t: 'id', s: m[2] });
    else if (m[3] !== undefined) out.push({ t: 'op', s: m[3] });
    i = re.lastIndex;
  }
  return out;
}

const NAME_ALIASES = new Map([['omega', 'w'], ['w', 'omega']]);

/** Split an identifier run such as "sRC" into known names (greedy, longest first). */
function splitName(run: string, symbols: ReadonlySet<string>): string[] {
  const known = (name: string) => symbols.has(name) || FUNCTIONS.has(name) || CONSTANTS.has(name);
  if (known(run)) return [run];
  const alias = NAME_ALIASES.get(run);
  if (alias && symbols.has(alias)) return [alias];
  const names = [...symbols, ...FUNCTIONS.keys(), ...CONSTANTS.keys()].sort(
    (a, b) => b.length - a.length,
  );
  const parts: string[] = [];
  let i = 0;
  while (i < run.length) {
    const hit = names.find((n) => run.startsWith(n, i));
    if (!hit) {
      const list = [...symbols].join(', ');
      throw new ExprError('name', `Unknown name “${run}”.${list ? ` Use the symbols ${list}.` : ''}`);
    }
    parts.push(hit);
    i += hit.length;
  }
  return parts;
}

class Parser {
  private toks: Tok[];
  private pos = 0;
  private symbols: ReadonlySet<string>;

  constructor(toks: Tok[], symbols: ReadonlySet<string>) {
    this.symbols = symbols;
    // Expand identifier runs into single names first.
    this.toks = toks.flatMap((t) =>
      t.t === 'id' ? splitName(t.s, symbols).map((s): Tok => ({ t: 'id', s })) : [t],
    );
  }

  private peek(): Tok | undefined {
    return this.toks[this.pos];
  }

  private isOp(s: string): boolean {
    const t = this.peek();
    return t !== undefined && t.t === 'op' && t.s === s;
  }

  parse(): Expr {
    if (this.toks.length === 0) throw new ExprError('syntax', 'Enter an expression.');
    const e = this.sum();
    if (this.pos < this.toks.length) throw new ExprError('syntax', 'Unbalanced or unexpected input.');
    return e;
  }

  private sum(): Expr {
    let a = this.term();
    while (this.isOp('+') || this.isOp('-')) {
      const op = (this.toks[this.pos++] as { s: '+' | '-' }).s;
      a = { k: 'bin', op, a, b: this.term() };
    }
    return a;
  }

  private startsFactor(): boolean {
    const t = this.peek();
    return t !== undefined && (t.t === 'num' || t.t === 'id' || (t.t === 'op' && (t.s === '(' || t.s === '√')));
  }

  private term(): Expr {
    let a = this.unary();
    for (;;) {
      if (this.isOp('*') || this.isOp('/')) {
        const op = (this.toks[this.pos++] as { s: '*' | '/' }).s;
        a = { k: 'bin', op, a, b: this.unary() };
      } else if (this.startsFactor()) {
        a = { k: 'bin', op: '*', a, b: this.unary() }; // implicit multiplication
      } else {
        return a;
      }
    }
  }

  private unary(): Expr {
    if (this.isOp('-')) {
      this.pos++;
      return { k: 'neg', a: this.unary() };
    }
    if (this.isOp('+')) {
      this.pos++;
      return this.unary();
    }
    return this.power();
  }

  private power(): Expr {
    const base = this.atom();
    if (this.isOp('^')) {
      this.pos++;
      return { k: 'bin', op: '^', a: base, b: this.unary() };
    }
    return base;
  }

  private atom(): Expr {
    const t = this.toks[this.pos++];
    if (!t) throw new ExprError('syntax', 'The expression ends too early.');
    if (t.t === 'num') return { k: 'num', v: t.v };
    if (t.t === 'op' && t.s === '√') return { k: 'call', fn: 'sqrt', a: this.atom() }; // √2, √(…)
    if (t.t === 'op') {
      if (t.s !== '(') throw new ExprError('syntax', `Unexpected “${t.s}”.`);
      const e = this.sum();
      if (!this.isOp(')')) throw new ExprError('syntax', 'A closing parenthesis is missing.');
      this.pos++;
      return e;
    }
    const name = t.s;
    if (this.symbols.has(name)) return { k: 'sym', name };
    if (FUNCTIONS.has(name)) {
      if (!this.isOp('(')) throw new ExprError('syntax', `Write ${name}(…) with parentheses.`);
      this.pos++;
      const a = this.sum();
      if (!this.isOp(')')) throw new ExprError('syntax', 'A closing parenthesis is missing.');
      this.pos++;
      return { k: 'call', fn: name, a };
    }
    const c = CONSTANTS.get(name);
    if (c) return { k: 'const', name: c };
    throw new ExprError('name', `Unknown name “${name}”.`);
  }
}

export function parseExpr(source: string, symbols: readonly string[]): Expr {
  return new Parser(tokenize(source), new Set(symbols)).parse();
}

export function evaluate(e: Expr, env: Readonly<Record<string, number>>): Cx {
  switch (e.k) {
    case 'num':
      return cx(e.v);
    case 'sym':
      return cx(env[e.name] ?? Number.NaN);
    case 'const':
      return e.name === 'pi' ? cx(Math.PI) : e.name === 'e' ? cx(Math.E) : I;
    case 'neg': {
      const a = evaluate(e.a, env);
      return cx(-a.re, -a.im);
    }
    case 'call':
      return (FUNCTIONS.get(e.fn) ?? (() => cx(Number.NaN)))(evaluate(e.a, env));
    case 'bin': {
      const a = evaluate(e.a, env);
      const b = evaluate(e.b, env);
      if (e.op === '+') return add(a, b);
      if (e.op === '-') return sub(a, b);
      if (e.op === '*') return mul(a, b);
      if (e.op === '/') return div(a, b);
      return pow(a, b);
    }
  }
}

const PREC = { '+': 1, '-': 1, '*': 2, '/': 2, neg: 3, '^': 4 } as const;

/** The expression as read, with only the parentheses it needs: "1/(1 + s·R·C)". */
export function formatExpr(e: Expr): string {
  const wrap = (x: Expr, min: number, strict = false): string => {
    const p = x.k === 'bin' ? PREC[x.op] : x.k === 'neg' ? PREC.neg : 9;
    const text = formatExpr(x);
    return p < min || (strict && p === min) ? `(${text})` : text;
  };
  switch (e.k) {
    case 'num':
      return String(e.v);
    case 'sym':
      return e.name;
    case 'const':
      return e.name === 'pi' ? 'π' : e.name === 'e' ? 'e' : 'j';
    case 'neg':
      return `−${wrap(e.a, PREC.neg)}`;
    case 'call':
      return `${e.fn}(${formatExpr(e.a)})`;
    case 'bin': {
      const p = PREC[e.op];
      if (e.op === '^') return `${wrap(e.a, p, true)}^${wrap(e.b, p)}`;
      const sep = e.op === '*' ? '·' : e.op === '/' ? '/' : ` ${e.op === '-' ? '−' : '+'} `;
      return `${wrap(e.a, p)}${sep}${wrap(e.b, p, e.op === '-' || e.op === '/')}`;
    }
  }
}

/**
 * Compare two expressions at random positive symbol values (log-uniform in [0.25, 4]).
 * Returns true when they agree at every usable sample point, false at the first
 * disagreement, and null when the reference is undefined almost everywhere.
 */
export function sameValues(
  user: Expr,
  reference: Expr,
  symbols: readonly string[],
  seed = 'studykit',
): boolean | null {
  const rand = mulberry32(fnv1a(seed));
  let usable = 0;
  for (let attempt = 0; attempt < 48 && usable < 10; attempt++) {
    const env: Record<string, number> = {};
    for (const s of symbols) env[s] = 10 ** (rand() * 1.2 - 0.6);
    const r = evaluate(reference, env);
    if (!Number.isFinite(r.re) || !Number.isFinite(r.im) || abs(r) > 1e12) continue;
    const u = evaluate(user, env);
    if (!Number.isFinite(u.re) || !Number.isFinite(u.im)) return false;
    if (abs(sub(u, r)) > 1e-9 + 1e-7 * Math.max(abs(u), abs(r))) return false;
    usable++;
  }
  return usable >= 4 ? true : null;
}

export function checkExpr(input: string, spec: AnswerSpec): Verdict {
  if (normalize(input) === '') return { ok: false, reason: 'empty', message: 'Enter an expression.' };
  const symbols = [...(spec.symbols ?? [])];
  let user: Expr;
  try {
    user = parseExpr(input, symbols);
  } catch (err) {
    const e = err instanceof ExprError ? err : new ExprError('syntax', String(err));
    return { ok: false, reason: e.reason, message: e.message };
  }
  const read = formatExpr(user);
  let reference: Expr;
  try {
    reference = parseExpr(spec.expr ?? '', symbols);
  } catch {
    return { ok: false, reason: 'syntax', read, message: 'The reference answer cannot be read.' };
  }
  const same = sameValues(user, reference, symbols, `${spec.key}:${spec.expr ?? ''}`);
  if (same === true) return { ok: true, read, message: 'Correct.' };
  return {
    ok: false,
    reason: 'different',
    read,
    message: same === null ? 'This cannot be compared.' : 'Not equivalent to the expected expression.',
  };
}

export function check(input: string, spec: AnswerSpec): Verdict {
  return spec.expr ? checkExpr(input, spec) : checkNumeric(input, spec);
}

/** Read `data-answers`; entries without a key or a value/expr are dropped. */
export function parseAnswers(json: string | undefined | null): AnswerSpec[] {
  if (!json) return [];
  let data: unknown;
  try {
    data = JSON.parse(json);
  } catch {
    return [];
  }
  if (!Array.isArray(data)) return [];
  return data.filter(
    (a): a is AnswerSpec =>
      typeof a === 'object' && a !== null && typeof (a as AnswerSpec).key === 'string' &&
      (typeof (a as AnswerSpec).value === 'number' || typeof (a as AnswerSpec).expr === 'string'),
  );
}
