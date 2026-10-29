// Progress store (docs/architecture.md §2.11). This module is the only code that touches
// localStorage; every access is wrapped in try/catch. Reading and writing fail separately:
// when storage is full, stored progress stays readable and a write that fails is kept in a
// memory overlay that reads see first, so the page (and an export) still has everything.
// Without any storage (blocked, private windows) the page works from memory alone.
//
// Keys
//   studykit:v1:<course>          the progress document (schema studykit-progress/1)
//   studykit:v1:<course>:session  runtime state that is never exported (a running exam's
//                                 start time, its MC answers and rubric ticks; the hints
//                                 of an exercise review that is not rated yet)
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
// Exercise attempts: `hints` counts the hints of one attempt, the one the rating belongs to
// (or, before the first rating, the one under way), and more than HINT_CAP of them cap that
// rating at "partial". Once a rated exercise has come up for review (its due day has come),
// working on it again is a new attempt that starts without hints: until it is rated, its
// hints are kept in the session state (exHints), and rating it stores them with the rating.
//
// Migrations run on every read: a document without `schema` (written before the schema
// was versioned) is version 0; its attempts carried `sure: boolean` instead of `conf`.
// Entries that do not validate are dropped, so an export always validates: timestamps are
// ISO 8601 (as datetime.fromisoformat reads them, not whatever Date.parse takes), counts
// are safe integers. A document with a newer schema is read as far as possible but never
// written (read-only).

import { dayOf, ENTRY_BOX, isDay, isDue, review, reviewDayOf, type Conf, type Review } from './leitner.ts';

export const SCHEMA = 'studykit-progress/1';
export const THEME_KEY = 'studykit:theme';
export const UNKNOWN_HASH = '00000000';
export const MAX_ATTEMPTS = 100;
export const CHANGE_EVENT = 'studykit:progress';
/** Using more hints than this caps an exercise's rating at "partial" (§3.2). */
export const HINT_CAP = 1;

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
const ISO_TIME_RE = /^\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})?)?$/;

/** `v` when it is an ISO 8601 date or date-time that both JS and Python read, else null. */
function time(v: unknown): string | null {
  if (typeof v !== 'string' || !ISO_TIME_RE.test(v) || !isDay(v.slice(0, 10))) return null;
  return Number.isNaN(Date.parse(v.replace(' ', 'T'))) ? null : v;
}

/** A count or duration: a non-negative number rounded to a safe integer, or null. */
function count(v: unknown, round: (x: number) => number = Math.round): number | null {
  if (!isNum(v) || v < 0) return null;
  const n = round(v);
  return Number.isSafeInteger(n) ? n : null;
}

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
  const t = isObj(v) ? time(v.t) : null;
  if (!isObj(v) || !t || !Array.isArray(v.chosen)) return null;
  const conf = version === 0 && typeof v.sure === 'boolean' ? (v.sure ? 'sure' : 'unsure') : v.conf;
  if (conf !== 'sure' && conf !== 'unsure') return null;
  if (!isNum(v.score) || v.score < 0 || v.score > 1) return null;
  const chosen = v.chosen.filter((c): c is string => typeof c === 'string' && CHOICE_RE.test(c));
  return {
    t,
    chosen,
    score: v.score,
    conf,
    ms: count(v.ms) ?? 0,
  };
}

function examAttempt(v: unknown): ExamAttempt | null {
  const started = isObj(v) ? time(v.started) : null;
  if (!isObj(v) || !started || !isObj(v.points) || !isNum(v.total) || v.total < 0) {
    return null;
  }
  const points: Record<string, number> = {};
  for (const [k, p] of Object.entries(v.points)) if (isNum(p)) points[k] = p;
  return {
    started,
    duration_s: count(v.duration_s) ?? 0,
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
        hints: count(v.hints, Math.trunc) ?? 0,
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
  doc.exported_at = time(raw.exported_at) ?? doc.exported_at;
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

/** The rating an exercise may keep after `hints` hints: "solved" becomes "partial". */
export function cappedRating(rating: Rating, hints: number): Rating {
  return rating === 'solved' && hints > HINT_CAP ? 'partial' : rating;
}

const RATING_SCORE: Record<Rating, number> = { solved: 1, partial: 0.5, 'not-yet': 0 };

/**
 * A rated exercise has come up for review: its due day has come (also during the rest days
 * before the exam, when nothing counts as due), or the exam clamp has made it due. Working on
 * it now is a new attempt.
 */
export function reviewStarted(entry: ExEntry | undefined, today: string, examDate?: string | null): boolean {
  if (!entry?.rating || !entry.due) return false;
  return entry.due <= today || isDue(entry.due, reviewDayOf(entry.due, entry.box), today, examDate);
}

/** Session state of an exercise review that is not rated yet: the due day it answers. */
interface ExReview {
  due: string;
  hints: number;
}

// Exercise entries have no time stamp, so the side whose review is due later stands for the
// later self-assessment; its rating, box and due day are taken together (only rateEx sets
// them, so a side without a rating has no due day either). The hint counts are combined, so
// a "solved" from one side can meet the other side's hints: it is capped like rateEx caps
// it, back in the entry box and due no later than either side planned.
function mergeEx(a: ExEntry, b: ExEntry): ExEntry {
  const later = (b.due ?? '') > (a.due ?? '') ? b : a;
  const hints = Math.max(a.hints, b.hints);
  const merged: ExEntry = {
    h: a.h !== UNKNOWN_HASH ? a.h : b.h,
    hints,
    answer_ok: a.answer_ok === true || b.answer_ok === true ? true : (a.answer_ok ?? b.answer_ok),
    rating: later.rating,
    box: later.box,
    due: later.due,
  };
  if (merged.rating && cappedRating(merged.rating, hints) !== merged.rating) {
    const dues = [a.due, b.due].filter((d): d is string => d !== null).sort();
    merged.rating = cappedRating(merged.rating, hints);
    merged.box = ENTRY_BOX;
    merged.due = dues[0] ?? null;
  }
  return merged;
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

/**
 * A storage backend behind try/catch with a memory overlay. Reads see the overlay first,
 * then the backend; a write that fails (quota exceeded, storage blocked) goes to the
 * overlay, so this page keeps seeing it, and a later successful write clears it again.
 */
export class SafeStorage {
  private readonly backend: Backend | null;
  /** Values whose write or removal failed; null marks a removal. */
  private readonly overlay = new Map<string, string | null>();

  constructor(backend: Backend | null) {
    this.backend = backend;
  }

  /** There is a backend to read stored progress from. */
  get readable(): boolean {
    return this.backend !== null;
  }

  /** True when a write reaches the backend now (it is not full or blocked). */
  probe(): boolean {
    if (!this.backend) return false;
    try {
      this.backend.setItem('studykit:probe', '1');
      this.backend.removeItem('studykit:probe');
      return true;
    } catch {
      return false;
    }
  }

  get(key: string): string | null {
    if (this.overlay.has(key)) return this.overlay.get(key) ?? null;
    if (!this.backend) return null;
    try {
      return this.backend.getItem(key);
    } catch {
      return null;
    }
  }

  /** Store a value; false when it only reached memory. */
  set(key: string, value: string): boolean {
    if (this.backend) {
      try {
        this.backend.setItem(key, value);
        this.overlay.delete(key);
        return true;
      } catch {
        // full or blocked: keep it for this page below
      }
    }
    this.overlay.set(key, value);
    return false;
  }

  remove(key: string): void {
    if (this.backend) {
      try {
        this.backend.removeItem(key);
        this.overlay.delete(key);
        return;
      } catch {
        // blocked: hide it for this page below
      }
    }
    this.overlay.set(key, null);
  }
}

/** localStorage when it can be read (it may still refuse writes), else null. */
function localStorageBackend(): Backend | null {
  try {
    const ls = globalThis.localStorage;
    if (!ls) return null;
    ls.getItem('studykit:probe');
    return ls;
  } catch {
    return null;
  }
}

let browser: SafeStorage | null = null;

/** The page's one view of localStorage, shared by every course store and the theme. */
function browserStorage(): SafeStorage {
  browser ??= new SafeStorage(localStorageBackend());
  return browser;
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
  private readonly storage: SafeStorage;
  /** False when writes only reach memory (storage blocked or full). */
  persistent: boolean;

  /** `backend`: localStorage when omitted; null for memory only. */
  constructor(course: string, backend?: Backend | null) {
    this.course = course;
    this.key = `studykit:v1:${course}`;
    this.sessionKey = `studykit:v1:${course}:session`;
    this.storage = backend === undefined ? browserStorage() : new SafeStorage(backend);
    this.persistent = this.storage.probe();
  }

  /** Stored progress can be read (false: no storage at all, everything is in memory). */
  get readable(): boolean {
    return this.storage.readable;
  }

  private loadMigrated(): Migrated {
    return migrate(parse(this.storage.get(this.key)), this.course);
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
    const ok = this.storage.set(this.key, JSON.stringify(doc));
    this.persistent = ok;
    if (ok) void requestPersist();
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

  /** The open review of a rated exercise that has come up for review, else null. */
  private openReview(id: string, entry: ExEntry | undefined, when: When): ExReview | null {
    if (!entry?.due || !reviewStarted(entry, when.today ?? dayOf(), when.examDate)) return null;
    const rec = this.session<Partial<ExReview>>(`ex:${id}`);
    const hints = rec?.due === entry.due && isNum(rec.hints) && rec.hints >= 0 ? Math.trunc(rec.hints) : 0;
    return { due: entry.due, hints };
  }

  /**
   * Hints used in the exercise's current attempt: those of its rating, or of the review under
   * way once a rated exercise has come up for review (none until one is opened).
   */
  exHints(id: string, when: When = {}): number {
    const entry = this.get<ExEntry>(`ex:${id}`);
    return this.openReview(id, entry, when)?.hints ?? entry?.hints ?? 0;
  }

  /**
   * Self-assessment of an exercise; it also schedules the exercise for review. With more
   * than HINT_CAP hints used in this attempt, "solved" is stored as "partial".
   */
  rateEx(id: string, h: string | undefined, rating: Rating, when: When = {}): ExEntry {
    const prev = this.get<ExEntry>(`ex:${id}`);
    const open = this.openReview(id, prev, when);
    const hints = open?.hints ?? prev?.hints ?? 0;
    const capped = cappedRating(rating, hints);
    const r = review(prev?.box, RATING_SCORE[capped], 'unsure', when.today ?? dayOf(), when.examDate);
    if (open) this.setSession(`ex:${id}`, null);
    return this.updateEx(id, h, { hints, rating: capped, box: r.box, due: r.due });
  }

  /**
   * `used` hints of an exercise are open in this attempt; the count never goes down within
   * it. In a review under way the count is kept in the session state until the rating.
   * Otherwise, when it passes HINT_CAP after the exercise was rated "solved", the rating
   * becomes "partial" and the exercise is rescheduled as if it had been rated so.
   */
  useHints(id: string, h: string | undefined, used: number, when: When = {}): ExEntry {
    const prev = this.get<ExEntry>(`ex:${id}`);
    const open = this.openReview(id, prev, when);
    if (prev && open) {
      this.setSession(`ex:${id}`, { due: open.due, hints: Math.max(open.hints, used) } satisfies ExReview);
      return prev;
    }
    const hints = Math.max(prev?.hints ?? 0, used);
    const rating = prev?.rating ?? null;
    if (rating && cappedRating(rating, hints) !== rating) {
      const capped = cappedRating(rating, hints);
      const r = review(prev?.box, RATING_SCORE[capped], 'unsure', when.today ?? dayOf(), when.examDate);
      return this.updateEx(id, h, { hints, rating: capped, box: r.box, due: r.due });
    }
    return this.updateEx(id, h, { hints });
  }

  addExamAttempt(id: string, attempt: ExamAttempt): ExamEntry {
    return this.update<ExamEntry>(`exam:${id}`, (prev) => ({
      attempts: [...(prev?.attempts ?? []), attempt],
    })) as ExamEntry;
  }

  /** Add an exam attempt, or replace the one with the same start time (regrading). */
  saveExamAttempt(id: string, attempt: ExamAttempt): ExamEntry {
    return this.update<ExamEntry>(`exam:${id}`, (prev) => ({
      attempts: [...(prev?.attempts ?? []).filter((a) => a.started !== attempt.started), attempt].sort(
        (a, b) => (a.started < b.started ? -1 : 1),
      ),
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
      message: `Imported ${added + merged} ${added + merged === 1 ? 'item' : 'items'} (${added} new, ${merged} merged)${
        saved ? '' : `, but this browser cannot store ${added + merged === 1 ? 'it' : 'them'}`
      }.`,
    };
  }

  // --- runtime state (never exported) ---

  session<T>(name: string): T | undefined {
    const all = parse(this.storage.get(this.sessionKey));
    return isObj(all) ? (all[name] as T | undefined) : undefined;
  }

  setSession(name: string, value: unknown): void {
    const all = parse(this.storage.get(this.sessionKey));
    const next: Raw = isObj(all) ? all : {};
    if (value === undefined || value === null) delete next[name];
    else next[name] = value;
    if (Object.keys(next).length === 0) this.storage.remove(this.sessionKey);
    else this.storage.set(this.sessionKey, JSON.stringify(next));
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
  const v = browserStorage().get(THEME_KEY);
  return v === 'light' || v === 'dark' ? v : 'system';
}

export function setTheme(theme: Theme): void {
  browserStorage().set(THEME_KEY, theme);
}
