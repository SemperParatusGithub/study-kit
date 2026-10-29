// Node built-ins behind a small typed surface (build time only; never shipped to the browser).
// The site has no @types/node, so TypeScript reads the JSDoc below instead of node's types;
// keep every node: import in this file.
import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { availableParallelism } from 'node:os';
import { isAbsolute, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

// Pages are bundled into chunks at build time, so import.meta.url says nothing about where
// the site lives; astro.config.mjs records the site directory in STUDYKIT_SITE_ROOT.

/** Absolute path of the site directory. */
export const siteRoot = resolve(process.env.STUDYKIT_SITE_ROOT ?? process.cwd());

/** Absolute path of the repository (the parent of site/). */
export const repoRoot = resolve(siteRoot, '..');

/**
 * An environment variable.
 * @param {string} name
 * @returns {string | undefined}
 */
export function env(name) {
  return process.env[name];
}

/** True when STUDYKIT_STRICT=1: every content problem fails the build. */
export function strict() {
  return process.env.STUDYKIT_STRICT === '1';
}

/**
 * The courses directory (STUDYKIT_COURSES_DIR, default ../courses), absolute.
 * @returns {string}
 */
export function coursesDir() {
  return resolve(siteRoot, process.env.STUDYKIT_COURSES_DIR ?? '../courses');
}

/**
 * A directory path relative to the site (or absolute), resolved.
 * @param {string} path
 * @returns {string}
 */
export function sitePath(path) {
  return resolve(siteRoot, path);
}

/**
 * @param {URL | string} url
 * @returns {string}
 */
export function fromFileUrl(url) {
  return fileURLToPath(url);
}

/**
 * @param {...string} parts
 * @returns {string}
 */
export function joinPath(...parts) {
  return join(...parts);
}

/**
 * @param {string} from
 * @param {string} to
 * @returns {string}
 */
export function relativePath(from, to) {
  return relative(from, to).split(sep).join('/');
}

/**
 * @param {string} path
 * @returns {boolean}
 */
export function isAbsolutePath(path) {
  return isAbsolute(path);
}

/**
 * A path as the repository shows it (repo-relative when inside, else absolute).
 * @param {string} path
 * @returns {string}
 */
export function displayPath(path) {
  const rel = relative(repoRoot, path);
  return rel.startsWith('..') || isAbsolute(rel) ? path : rel.split(sep).join('/');
}

/**
 * @param {string} path
 * @returns {boolean}
 */
export function isFile(path) {
  try {
    return statSync(path).isFile();
  } catch {
    return false;
  }
}

/**
 * @param {string} path
 * @returns {boolean}
 */
export function isDir(path) {
  try {
    return statSync(path).isDirectory();
  } catch {
    return false;
  }
}

/**
 * @param {string} path
 * @returns {boolean}
 */
export function exists(path) {
  return existsSync(path);
}

/**
 * File contents as UTF-8, or null when the file cannot be read.
 * @param {string} path
 * @returns {string | null}
 */
export function readText(path) {
  try {
    return readFileSync(path, 'utf8');
  } catch {
    return null;
  }
}

/**
 * Parsed JSON file, or null when it is missing or invalid.
 * @param {string} path
 * @returns {unknown}
 */
export function readJson(path) {
  const text = readText(path);
  if (text === null) return null;
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

/**
 * Sorted entry names of a directory ([] when it does not exist).
 * @param {string} path
 * @returns {string[]}
 */
export function listDir(path) {
  try {
    return readdirSync(path).sort();
  } catch {
    return [];
  }
}

/**
 * Hex sha256 of the UTF-8 strings given, joined with NUL (one string: its plain hash).
 * @param {...string} parts
 * @returns {string}
 */
export function sha256(...parts) {
  return createHash('sha256').update(parts.join('\0')).digest('hex');
}

/** @returns {number} */
export function cpuCount() {
  return availableParallelism();
}

/**
 * Run a command and collect its output. Never rejects for a non-zero exit; rejects only
 * when the command cannot be started (code 'ENOENT' etc.).
 * @param {string} command
 * @param {string[]} args
 * @param {{cwd?: string, input?: string, env?: Record<string, string | undefined>}} [options]
 * @returns {Promise<{code: number, stdout: string, stderr: string}>}
 */
export function run(command, args, options = {}) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(command, args, {
      cwd: options.cwd ?? repoRoot,
      env: { ...process.env, ...(options.env ?? {}) },
      stdio: ['pipe', 'pipe', 'pipe'],
    });
    /** @type {Buffer[]} */
    const out = [];
    /** @type {Buffer[]} */
    const err = [];
    child.stdout.on('data', (chunk) => out.push(chunk));
    child.stderr.on('data', (chunk) => err.push(chunk));
    child.on('error', reject);
    child.on('close', (code) =>
      resolvePromise({
        code: code ?? 1,
        stdout: Buffer.concat(out).toString('utf8'),
        stderr: Buffer.concat(err).toString('utf8'),
      }),
    );
    child.stdin.end(options.input ?? '');
  });
}
