// Progress store (docs/architecture.md §2.11). This module is the only code that touches
// localStorage; every access is wrapped in try/catch and falls back to memory, so a page
// works (without persistence) in private windows or when storage is blocked or full.
//
// Keys
//   studykit:v1:<course>          the progress document (schema studykit-progress/1)
//   studykit:v1:<course>:session  runtime state that is never exported (a running exam's
//                                 start time, its MC answers and rubric ticks)
//   studykit:theme                light | dark | system
//
// The document is exactly the export format that `studykit.model.Progress` validates:
//   {"schema":"studykit-progress/1","course":"…","exported_at":"…","items":{
//     "mc:<id>":   {h, box, due, attempts:[{t, chosen, score, conf, ms}]},
//     "ex:<id>":   {h, hints, answer_ok, rating, box, due},
//     "exam:<id>": {attempts:[{started, duration_s, points, total}]},
//     "plan:<id>": {done}}}
// Misconceptions are not stored: an MC item whose last attempt was sure and not fully
// right is one (scoring.isMisconception), and Leitner has put it in box 0.
//
// Migrations run on every read: a document without `schema` (written before the schema
// was versioned) is version 0; its attempts carried `sure: boolean` instead of `conf`.
// Entries that do not validate are dropped, so an export always validates. A document
// with a newer schema is read as far as possible but never written (read-only).

import { dayOf, isDay, review, type Conf, type Review } from './leitner.ts';

export const SCHEMA = 'studykit-progress/1';
export const THEME_KEY = 'studykit:theme';
export const UNKNOWN_HASH = '00000000';
export const MAX_ATTEMPTS = 100;
export const CHANGE_EVENT = 'studykit:progress';

export type Rating = 'solved' | 'partial' | 'not-yet';
export type Theme = 'light' | 'dark' | 'system';

export interface McAttempt {
  t: string;
  chosen: string[];
  score: number;
  conf: Conf;
  ms: number;
}
export interface McEntry {
  h: string;
  box: number | null;
  due: string | null;
  attempts: McAttempt[];
}
export interface ExEntry {
  h: string;
  hints: number;
  answer_ok: boolean | null;
  rating: Rating | null;
  box: number | null;
  due: string | null;
}
export interface ExamAttempt {
  started: string;
  duration_s: number;
  points: Record<string, number>;
  total: number;
}
export interface ExamEntry {
  attempts: ExamAttempt[];
}
export interface PlanEntry {
  done: boolean;
}
export type Entry = McEntry | ExEntry | ExamEntry | PlanEntry;

export interface ProgressDoc {
  schema: typeof SCHEMA;
  course: string;
  exported_at: string;
  items: Record<string, Entry>;
}

export interface Backend {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

// --- validation and migration ---------------------------------------------------------

const KEY_RE = /^(mc|ex|exam|plan):[a-z0-9][a-z0-9-]*$/;
const HASH_RE = /^[0-9a-f]{8,64}$/;
const CHOICE_RE = /^[A-F]$/;
const RATINGS: readonly Rating[] = ['solved', 'partial', 'not-yet'];

type Raw = Record<string, unknown>;
const isObj = (v: unknown): v is Raw => typeof v === 'object' && v !== null && !Array.isArray(v);
const isNum = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);
const isTime = (v: unknown): v is string => typeof v === 'string' && !Number.isNaN(Date.parse(v));

export function kindOf(key: string): 'mc' | 'ex' | 'exam' | 'plan' | null {
  const m = KEY_RE.exec(key);
  return m ? (m[1] as 'mc' | 'ex' | 'exam' | 'plan') : null;
}

function hash(v: unknown): string {
  return typeof v === 'string' && HASH_RE.test(v) ? v : UNKNOWN_HASH;
}

function box(v: unknown): number | null {
  return isNum(v) && Number.isInteger(v) && v >= 0 && v <= 5 ? v : null;
}

function day(v: unknown): string | null {
  return isDay(v) ? v : null;
}

function mcAttempt(v: unknown, version: number): McAttempt | null {
  if (!isObj(v) || !isTime(v.t) || !Array.isArray(v.chosen)) return null;
  const conf = version === 0 && typeof v.sure === 'boolean' ? (v.sure ? 'sure' : 'unsure') : v.conf;
  if (conf !== 'sure' && conf !== 'unsure') return null;
  if (!isNum(v.score) || v.score < 0 || v.score > 1) return null;
  const chosen = v.chosen.filter((c): c is string => typeof c === 'string' && CHOICE_RE.test(c));
  return {
    t: v.t,
    chosen,
    score: v.score,
    conf,
    ms: isNum(v.ms) && v.ms >= 0 ? Math.round(v.ms) : 0,
  };
}

function examAttempt(v: unknown): ExamAttempt | null {
  if (!isObj(v) || !isTime(v.started) || !isObj(v.points) || !isNum(v.total) || v.total < 0) {
    return null;
  }
  const points: Record<string, number> = {};
  for (const [k, p] of Object.entries(v.points)) if (isNum(p)) points[k] = p;
  return {
    started: v.started,
    duration_s: isNum(v.duration_s) && v.duration_s >= 0 ? Math.round(v.duration_s) : 0,
    points,
    total: v.total,
  };
}

/** One entry checked against the model its key names; null when it cannot be kept. */
export function sanitizeEntry(key: string, v: unknown, version = 1): Entry | null {
  if (!isObj(v)) return null;
  switch (kindOf(key)) {
    case 'mc': {
      const attempts = (Array.isArray(v.attempts) ? v.attempts : [])
        .map((a) => mcAttempt(a, version))
        .filter((a): a is McAttempt => a !== null)
        .slice(-MAX_ATTEMPTS);
      return { h: hash(v.h), box: box(v.box), due: day(v.due), attempts };
    }
    case 'ex':
      return {
        h: hash(v.h),
        hints: isNum(v.hints) && v.hints >= 0 ? Math.trunc(v.hints) : 0,
        answer_ok: typeof v.answer_ok === 'boolean' ? v.answer_ok : null,
        rating: RATINGS.includes(v.rating as Rating) ? (v.rating as Rating) : null,
        box: box(v.box),
        due: day(v.due),
      };
    case 'exam': {
      const attempts = (Array.isArray(v.attempts) ? v.attempts : [])
        .map(examAttempt)
        .filter((a): a is ExamAttempt => a !== null);
      return { attempts };
    }
    case 'plan':
      return typeof v.done === 'boolean' ? { done: v.done } : null;
    default:
      return null;
  }
}

export function emptyDoc(course: string): ProgressDoc {
  return { schema: SCHEMA, course, exported_at: new Date(0).toISOString(), items: {} };
}

export interface Migrated {
  doc: ProgressDoc;
  /** Schema version the input had (0 for an unversioned document). */
  from: number;
  /** The input has a newer schema than this site understands: read it, never write it. */
  newer: boolean;
}

function versionOf(schema: unknown): number | null {
  if (schema === undefined) return 0;
  const m = typeof schema === 'string' ? /^studykit-progress\/(\d+)$/.exec(schema) : null;
  return m ? Number(m[1]) : null;
}

/** Bring any stored or imported document to the current schema. */
export function migrate(raw: unknown, course: string): Migrated {
  if (!isObj(raw)) return { doc: emptyDoc(course), from: 1, newer: false };
  const version = versionOf(raw.schema);
  if (version === null) return { doc: emptyDoc(course), from: 1, newer: false };
  const doc = emptyDoc(course);
  if (isTime(raw.exported_at)) doc.exported_at = raw.exported_at;
  const items = isObj(raw.items) ? raw.items : {};
  for (const [key, value] of Object.entries(items)) {
    const entry = sanitizeEntry(key, value, version);
    if (entry) doc.items[key] = entry;
  }
  return { doc, from: version, newer: version > 1 };
}

// --- merge ------------------------------------------------------------------------------

function lastTime(entry: McEntry): string {
  return entry.attempts.reduce((t, a) => (a.t > t ? a.t : t), '');
}

function mergeMc(a: McEntry, b: McEntry): McEntry {
  const seen = new Map<string, McAttempt>();
  for (const at of [...a.attempts, ...b.attempts]) seen.set(`${at.t}|${at.chosen.join('')}`, at);
  const attempts = [...seen.values()].sort((x, y) => (x.t < y.t ? -1 : x.t > y.t ? 1 : 0));
  const newer = lastTime(b) > lastTime(a) ? b : a;
  return { h: newer.h, box: newer.box, due: newer.due, attempts: attempts.slice(-MAX_ATTEMPTS) };
}

function mergeEx(a: ExEntry, b: ExEntry): ExEntry {
  const later = (b.due ?? '') > (a.due ?? '') ? b : a;
  return {
    h: a.h !== UNKNOWN_HASH ? a.h : b.h,
    hints: Math.max(a.hints, b.hints),
    answer_ok: a.answer_ok === true || b.answer_ok === true ? true : (a.answer_ok ?? b.answer_ok),
    rating: a.rating ?? b.rating,
    box: later.box,
    due: later.due,
  };
}

function mergeExam(a: ExamEntry, b: ExamEntry): ExamEntry {
  const seen = new Map<string, ExamAttempt>();
  for (const at of [...a.attempts, ...b.attempts]) seen.set(at.started, at);
  return { attempts: [...seen.values()].sort((x, y) => (x.started < y.started ? -1 : 1)) };
}

export interface MergeResult {
  doc: ProgressDoc;
  added: number;
  merged: number;
}

/**
 * Union of two documents of the same course: attempts are combined (duplicates dropped),
 * schedules come from the side with the latest attempt, hint counts take the maximum, a
 * correct answer check or a done session stays done.
 */
export function merge(local: ProgressDoc, incoming: ProgressDoc): MergeResult {
  const doc: ProgressDoc = structuredClone(local);
  let added = 0;
  let merged = 0;
  for (const [key, entry] of Object.entries(incoming.items)) {
    const mine = doc.items[key];
    if (!mine) {
      doc.items[key] = structuredClone(entry);
      added++;
      continue;
    }
    merged++;
    switch (kindOf(key)) {
      case 'mc':
        doc.items[key] = mergeMc(mine as McEntry, entry as McEntry);
        break;
      case 'ex':
        doc.items[key] = mergeEx(mine as ExEntry, entry as ExEntry);
        break;
      case 'exam':
        doc.items[key] = mergeExam(mine as ExamEntry, entry as ExamEntry);
        break;
      case 'plan':
        doc.items[key] = { done: (mine as PlanEntry).done || (entry as PlanEntry).done };
        break;
      default:
        break;
    }
  }
  return { doc, added, merged };
}

// --- storage ----------------------------------------------------------------------------

const memory = new Map<string, string>();
const memoryBackend: Backend = {
  getItem: (k) => memory.get(k) ?? null,
  setItem: (k, v) => void memory.set(k, v),
  removeItem: (k) => void memory.delete(k),
};

function browserBackend(): Backend | null {
  try {
    const ls = globalThis.localStorage;
    if (!ls) return null;
    const probe = 'studykit:probe';
    ls.setItem(probe, '1');
    ls.removeItem(probe);
    return ls;
  } catch {
    return null;
  }
}

function safeGet(backend: Backend, key: string): string | null {
  try {
    return backend.getItem(key);
  } catch {
    return memory.get(key) ?? null;
  }
}

function safeSet(backend: Backend, key: string, value: string): boolean {
  try {
    backend.setItem(key, value);
    return true;
  } catch {
    memory.set(key, value); // quota exceeded or storage blocked: keep it for this page
    return false;
  }
}

function safeRemove(backend: Backend, key: string): void {
  try {
    backend.removeItem(key);
  } catch {
    memory.delete(key);
  }
}

function parse(text: string | null): unknown {
  if (text === null) return null;
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

export interface ImportResult {
  ok: boolean;
  added: number;
  merged: number;
  message: string;
}

export interface McRecord {
  h?: string | undefined;
  chosen: readonly string[];
  score: number;
  conf: Conf;
  ms: number;
  t?: string | undefined;
}

export interface When {
  today?: string | undefined;
  examDate?: string | null | undefined;
}

export class ProgressStore {
  readonly course: string;
  readonly key: string;
  readonly sessionKey: string;
  private backend: Backend;
  /** False when writes only reach memory (storage blocked or full). */
  persistent: boolean;

  constructor(course: string, backend?: Backend | null) {
    this.course = course;
    this.key = `studykit:v1:${course}`;
    this.sessionKey = `studykit:v1:${course}:session`;
    const real = backend === undefined ? browserBackend() : backend;
    this.backend = real ?? memoryBackend;
    this.persistent = real !== null;
  }

  private loadMigrated(): Migrated {
    return migrate(parse(safeGet(this.backend, this.key)), this.course);
  }

  read(): ProgressDoc {
    return this.loadMigrated().doc;
  }

  /** True when the stored document has a newer schema; then nothing is written. */
  get readOnly(): boolean {
    return this.loadMigrated().newer;
  }

  private write(doc: ProgressDoc, keys: string[]): boolean {
    if (this.readOnly) return false;
    const ok = safeSet(this.backend, this.key, JSON.stringify(doc));
    if (!ok) this.persistent = false;
    this.notify(keys);
    return ok;
  }

  /** Change one entry: `fn` gets the current entry (or undefined) and returns the new one. */
  update<E extends Entry>(key: string, fn: (prev: E | undefined) => E | null): E | null {
    if (!kindOf(key)) throw new RangeError(`invalid progress key: ${key}`);
    const doc = this.read();
    const next = fn(doc.items[key] as E | undefined);
    if (next === null) delete doc.items[key];
    else doc.items[key] = next;
    this.write(doc, [key]);
    return next;
  }

  get<E extends Entry>(key: string): E | undefined {
    return this.read().items[key] as E | undefined;
  }

  // --- typed helpers ---

  /** Record one MC answer and reschedule the item (Leitner, exam clamp). */
  recordMc(id: string, rec: McRecord, when: When = {}): { entry: McEntry; review: Review } {
    const key = `mc:${id}`;
    const t = rec.t ?? new Date().toISOString();
    const result = review(
      this.get<McEntry>(key)?.box,
      rec.score,
      rec.conf,
      when.today ?? dayOf(),
      when.examDate,
    );
    const entry = this.update<McEntry>(key, (prev) => {
      const attempt: McAttempt = {
        t,
        chosen: [...rec.chosen].filter((c) => CHOICE_RE.test(c)).sort(),
        score: Math.min(1, Math.max(0, rec.score)),
        conf: rec.conf,
        ms: Math.max(0, Math.round(rec.ms)),
      };
      return {
        h: rec.h && HASH_RE.test(rec.h) ? rec.h : (prev?.h ?? UNKNOWN_HASH),
        box: result.box,
        due: result.due,
        attempts: [...(prev?.attempts ?? []), attempt].slice(-MAX_ATTEMPTS),
      };
    }) as McEntry;
    return { entry, review: result };
  }

  /** Patch an exercise entry, creating it with hash `h` when it is new. */
  updateEx(id: string, h: string | undefined, patch: Partial<Omit<ExEntry, 'h'>>): ExEntry {
    return this.update<ExEntry>(`ex:${id}`, (prev) => ({
      h: h && HASH_RE.test(h) ? h : (prev?.h ?? UNKNOWN_HASH),
      hints: prev?.hints ?? 0,
      answer_ok: prev?.answer_ok ?? null,
      rating: prev?.rating ?? null,
      box: prev?.box ?? null,
      due: prev?.due ?? null,
      ...patch,
    })) as ExEntry;
  }

  /** Self-assessment of an exercise; it also schedules the exercise for review. */
  rateEx(id: string, h: string | undefined, rating: Rating, when: When = {}): ExEntry {
    const prev = this.get<ExEntry>(`ex:${id}`);
    const score = rating === 'solved' ? 1 : rating === 'partial' ? 0.5 : 0;
    const r = review(prev?.box, score, 'unsure', when.today ?? dayOf(), when.examDate);
    return this.updateEx(id, h, { rating, box: r.box, due: r.due });
  }

  addExamAttempt(id: string, attempt: ExamAttempt): ExamEntry {
    return this.update<ExamEntry>(`exam:${id}`, (prev) => ({
      attempts: [...(prev?.attempts ?? []), attempt],
    })) as ExamEntry;
  }

  setPlanDone(id: string, done: boolean): void {
    this.update<PlanEntry>(`plan:${id}`, () => ({ done }));
  }

  // --- export and import ---

  exportFile(now: Date = new Date()): { filename: string; text: string } {
    const doc = this.read();
    doc.exported_at = now.toISOString();
    return {
      filename: `studykit-progress-${this.course}-${dayOf(now)}.json`,
      text: `${JSON.stringify(doc, null, 2)}\n`,
    };
  }

  importText(text: string): ImportResult {
    const raw = parse(text);
    if (!isObj(raw) || versionOf(raw.schema) === null || !isObj(raw.items)) {
      return { ok: false, added: 0, merged: 0, message: 'This is not a study-kit progress file.' };
    }
    if (raw.course !== this.course) {
      return {
        ok: false,
        added: 0,
        merged: 0,
        message: `This file belongs to the course “${String(raw.course)}”, not “${this.course}”.`,
      };
    }
    const incoming = migrate(raw, this.course);
    if (this.readOnly) {
      return { ok: false, added: 0, merged: 0, message: 'Stored progress is newer than this site.' };
    }
    const { doc, added, merged } = merge(this.read(), incoming.doc);
    const saved = this.write(doc, Object.keys(incoming.doc.items));
    return {
      ok: true,
      added,
      merged,
      message: `Imported ${added + merged} items (${added} new, ${merged} merged)${saved ? '' : ', but this browser cannot store them'}.`,
    };
  }

  // --- runtime state (never exported) ---

  session<T>(name: string): T | undefined {
    const all = parse(safeGet(this.backend, this.sessionKey));
    return isObj(all) ? (all[name] as T | undefined) : undefined;
  }

  setSession(name: string, value: unknown): void {
    const all = parse(safeGet(this.backend, this.sessionKey));
    const next: Raw = isObj(all) ? all : {};
    if (value === undefined || value === null) delete next[name];
    else next[name] = value;
    if (Object.keys(next).length === 0) safeRemove(this.backend, this.sessionKey);
    else safeSet(this.backend, this.sessionKey, JSON.stringify(next));
  }

  // --- change notification ---

  private notify(keys: string[]): void {
    const target = globalThis as unknown as EventTarget;
    if (typeof target.dispatchEvent !== 'function' || typeof CustomEvent !== 'function') return;
    target.dispatchEvent(new CustomEvent(CHANGE_EVENT, { detail: { course: this.course, keys } }));
  }

  /** Call `fn` whenever this course's progress changes, here or in another tab. */
  subscribe(fn: (keys: string[] | null) => void): () => void {
    const target = globalThis as unknown as EventTarget;
    if (typeof target.addEventListener !== 'function') return () => {};
    const local = (e: Event) => {
      const detail = (e as CustomEvent<{ course: string; keys: string[] }>).detail;
      if (detail?.course === this.course) fn(detail.keys);
    };
    const remote = (e: Event) => {
      if ((e as StorageEvent).key === this.key || (e as StorageEvent).key === null) fn(null);
    };
    target.addEventListener(CHANGE_EVENT, local);
    target.addEventListener('storage', remote);
    return () => {
      target.removeEventListener(CHANGE_EVENT, local);
      target.removeEventListener('storage', remote);
    };
  }
}

const stores = new Map<string, ProgressStore>();

/** The shared store of a course for this page. */
export function storeFor(course: string): ProgressStore {
  let s = stores.get(course);
  if (!s) {
    s = new ProgressStore(course);
    stores.set(course, s);
  }
  return s;
}

let persistRequest: Promise<boolean | null> | null = null;

/** Ask the browser not to evict our storage (once per page). Null when unsupported. */
export function requestPersist(): Promise<boolean | null> {
  if (!persistRequest) {
    persistRequest = (async () => {
      try {
        const sm = globalThis.navigator?.storage;
        if (!sm?.persist) return null;
        if (sm.persisted && (await sm.persisted())) return true;
        return await sm.persist();
      } catch {
        return null;
      }
    })();
  }
  return persistRequest;
}

// --- theme ------------------------------------------------------------------------------

export function getTheme(): Theme {
  const b = browserBackend();
  const v = b ? safeGet(b, THEME_KEY) : memory.get(THEME_KEY);
  return v === 'light' || v === 'dark' ? v : 'system';
}

export function setTheme(theme: Theme): void {
  safeSet(browserBackend() ?? memoryBackend, THEME_KEY, theme);
}
