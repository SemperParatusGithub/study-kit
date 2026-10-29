// One course with everything its pages need, gathered from the content collections, plus
// the route table (docs/architecture.md §3.2; refs.lua writes the same URLs).
import { getCollection, type CollectionEntry } from 'astro:content';
import type { DocData, ExamFm } from './types';
import { renderLabel } from './katex';
import { pdfHref, readPdfs, readSources, sourceHref, type PdfDoc, type SourceDoc } from './pdf';
import type { CourseInfo } from './stats.ts';
import { coursesDir, joinPath, readJson } from './sys.mjs';

export type CourseData = CollectionEntry<'courses'>['data'];
export type Doc = CollectionEntry<'docs'> & { data: DocData };
export type PlanData = CollectionEntry<'plans'>['data'];
export type Session = PlanData['sessions'][number];

export const route = {
  home: () => '/',
  search: () => '/search/',
  course: (c: string) => `/c/${c}/`,
  plan: (c: string) => `/c/${c}/plan/`,
  summaries: (c: string) => `/c/${c}/summary/`,
  summary: (c: string, topic: string) => `/c/${c}/summary/${topic}/`,
  exercises: (c: string) => `/c/${c}/exercises/`,
  exercise: (c: string, id: string) => `/c/${c}/exercises/${id}/`,
  mc: (c: string) => `/c/${c}/mc/`,
  mcTopic: (c: string, topic: string) => `/c/${c}/mc/${topic}/`,
  mcPool: (c: string, topic: string) => `/c/${c}/mc/${topic}.json`,
  cheatsheet: (c: string) => `/c/${c}/cheatsheet/`,
  exams: (c: string) => `/c/${c}/exams/`,
  exam: (c: string, id: string) => `/c/${c}/exams/${id}/`,
  progress: (c: string) => `/c/${c}/progress/`,
  pdf: pdfHref,
  source: sourceHref,
};

export interface Topic {
  id: string;
  title: string;
  weight: number;
  prereq: string[];
  focus: boolean;
  skip: boolean;
}

export interface Exam {
  id: string;
  doc: Doc;
  fm: ExamFm;
  tasks: Doc[];
  mc: Doc | null;
  aids: string[];
  mcPoints: number;
}

export interface Course {
  id: string;
  data: CourseData;
  title: string;
  short: string;
  lang: 'de' | 'en';
  examDate: string | null;
  topics: Topic[];
  topicTitle: (id: string | null | undefined) => string;
  docs: Doc[];
  overview: Doc | null;
  cheatsheet: Doc | null;
  summaries: Doc[];
  exercises: Doc[];
  banks: Doc[];
  exams: Exam[];
  plan: PlanData | null;
  mastery: Record<string, unknown> | null;
  /** Built PDFs from _build/pdf/manifest.json (lib/pdf.ts); empty until they are built. */
  pdfs: PdfDoc[];
  /** Source documents (sources/raw) the site serves. */
  sources: SourceDoc[];
}

const cache = new Map<string, Promise<Course>>();

/** Every course, sorted by title. */
export async function listCourses(): Promise<Course[]> {
  const entries = await getCollection('courses');
  const out = await Promise.all(entries.map((e) => loadCourse(e.id)));
  return out.sort((a, b) => a.title.localeCompare(b.title));
}

/** One course (cached for the build; dev always reads the current collections). */
export function loadCourse(id: string): Promise<Course> {
  if (!import.meta.env.PROD) return build(id);
  let hit = cache.get(id);
  if (!hit) {
    hit = build(id);
    cache.set(id, hit);
  }
  return hit;
}

/** getStaticPaths for /c/[course]/… pages. */
export async function coursePaths() {
  const courses = await listCourses();
  return courses.map((course) => ({ params: { course: course.id }, props: { course } }));
}

async function build(id: string): Promise<Course> {
  const entry = (await getCollection('courses')).find((e) => e.id === id);
  if (!entry) throw new Error(`unknown course '${id}'`);
  const data = entry.data;
  const docs = (await getCollection('docs', (d) => d.data.course === id)) as Doc[];
  const plan = (await getCollection('plans')).find((p) => p.id === id)?.data ?? null;
  // Written by `studykit progress report` (Phase 5); a course without it has no build-time
  // mastery. Read directly: an empty collection would warn on every request.
  const raw = readJson(joinPath(coursesDir(), id, 'progress', 'mastery.json'));
  const mastery = raw && typeof raw === 'object' && !Array.isArray(raw) ? (raw as Record<string, unknown>) : null;

  const topics: Topic[] = data.topics.map((t) => ({
    ...t,
    focus: data.focus.includes(t.id),
    skip: data.skip.includes(t.id),
  }));
  const order = new Map(topics.map((t, i) => [t.id, i]));
  const byTopic = (a: Doc, b: Doc) =>
    (order.get(a.data.topic ?? '') ?? 99) - (order.get(b.data.topic ?? '') ?? 99);
  const kind = (k: DocData['kind']) => docs.filter((d) => d.data.kind === k);

  const summaries = kind('summary').sort((a, b) => (a.data.order ?? 0) - (b.data.order ?? 0) || byTopic(a, b));
  const exercises = kind('exercise').sort(
    (a, b) =>
      byTopic(a, b) ||
      Number(a.data.fm.difficulty ?? 0) - Number(b.data.fm.difficulty ?? 0) ||
      a.data.title.localeCompare(b.data.title),
  );
  const banks = kind('mc').sort(byTopic);
  const exams: Exam[] = kind('exam')
    .map((doc) => {
      const fm = doc.data.fm as unknown as ExamFm;
      const examId = doc.data.exam ?? doc.data.id ?? '';
      const own = docs.filter((d) => d.data.exam === examId);
      const files = Array.isArray(fm.tasks) ? fm.tasks : [];
      const tasks = own
        .filter((d) => d.data.kind === 'exam-task')
        .sort((a, b) => {
          const ia = files.indexOf(a.data.rel.split('/').pop() ?? '');
          const ib = files.indexOf(b.data.rel.split('/').pop() ?? '');
          return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib) || (a.data.order ?? 0) - (b.data.order ?? 0);
        });
      const mc = own.find((d) => d.data.kind === 'exam-mc') ?? null;
      const aids = Array.isArray(fm.aids) ? fm.aids : data.exam.aids;
      const mcPoints = mc && fm.mc ? mc.data.questions.length * fm.mc.points_each : 0;
      return { id: examId, doc, fm, tasks, mc, aids, mcPoints };
    })
    .sort((a, b) => a.id.localeCompare(b.id));

  const titles = new Map(topics.map((t) => [t.id, t.title]));
  // Dev keeps a page's props (this course) until content changes, and PDFs are built while
  // it runs: there the getters below read them again on every render.
  const live = !import.meta.env.PROD;
  const pdfs = live ? [] : readPdfs(id);
  const sources = live ? [] : readSources(id);
  return {
    id,
    data,
    title: data.title,
    short: data.short ?? data.title,
    lang: data.lang,
    examDate: data.exam.date ?? plan?.exam_date ?? null,
    topics,
    topicTitle: (t) => (t ? (titles.get(t) ?? t) : ''),
    docs,
    overview: kind('overview')[0] ?? null,
    cheatsheet: kind('cheatsheet')[0] ?? null,
    summaries,
    exercises,
    banks,
    exams,
    plan,
    mastery,
    get pdfs() {
      return live ? readPdfs(id) : pdfs;
    },
    get sources() {
      return live ? readSources(id) : sources;
    },
  };
}

export interface Ref {
  href: string;
  title: string;
}

/** A plan or content reference (`topic:x`, `ex:x`, `exam:x`, `mc:x`) as a link, if it exists. */
export function resolveRef(course: Course, ref: string | null | undefined): Ref | null {
  if (!ref) return null;
  const [scheme, id] = ref.split(':', 2) as [string, string | undefined];
  if (!id) return null;
  if (scheme === 'topic') {
    const has = course.summaries.some((s) => s.data.topic === id);
    return has ? { href: route.summary(course.id, id), title: course.topicTitle(id) } : null;
  }
  if (scheme === 'ex') {
    const ex = course.exercises.find((e) => e.data.id === id);
    return ex ? { href: route.exercise(course.id, id), title: ex.data.title } : null;
  }
  if (scheme === 'exam') {
    const exam = course.exams.find((e) => e.id === id);
    return exam ? { href: route.exam(course.id, id), title: exam.doc.data.title } : null;
  }
  if (scheme === 'mc') {
    const bank = course.banks.find((b) => b.data.questions.some((q) => q.id === id));
    return bank?.data.topic
      ? { href: `${route.mcTopic(course.id, bank.data.topic)}#${id}`, title: id }
      : null;
  }
  return null;
}

/** The next session on or after `today` (YYYY-MM-DD), or null. */
export function nextSession(plan: PlanData | null, today: string): Session | null {
  return plan?.sessions.find((s) => s.date >= today) ?? null;
}

function fraction(value: unknown): number | null {
  return typeof value === 'number' && value >= 0 && value <= 1 ? value : null;
}

/**
 * Overall mastery 0–1 from progress/mastery.json (`studykit progress report`, Phase 5):
 * an `overall` number, or the mean of `topics.<id>.mastery`; null when unknown.
 */
export function overallMastery(course: Course): number | null {
  const m = course.mastery;
  if (!m) return null;
  const direct = fraction(m.overall) ?? fraction(m.mastery);
  if (direct !== null) return direct;
  const topics = m.topics && typeof m.topics === 'object' ? Object.values(m.topics) : [];
  const values = topics
    .map((t) => fraction(typeof t === 'number' ? t : (t as { mastery?: unknown })?.mastery))
    .filter((v): v is number => v !== null);
  return values.length ? values.reduce((a, b) => a + b, 0) / values.length : null;
}

/**
 * A frontmatter label of `doc` as HTML. The loader renders every answer label, rubric
 * criterion and objective (and reports KaTeX errors with their line); other text is rendered
 * here as a fallback.
 */
export function labelHtml(doc: Doc, text: string): string {
  return doc.data.labels[text] ?? renderLabel(text);
}

/**
 * What the client needs to know about a course to show progress (lib/stats.ts): topics with
 * their questions and exercises, exams and plan sessions. CourseData.astro writes it into
 * the page.
 */
export function clientInfo(course: Course): CourseInfo {
  const c = course.id;
  return {
    id: c,
    examDate: course.examDate,
    topics: course.topics.map((t) => {
      const banks = course.banks.filter((b) => b.data.topic === t.id);
      const summary = course.summaries.some((s) => s.data.topic === t.id);
      return {
        id: t.id,
        title: t.title,
        weight: t.weight,
        skip: t.skip,
        href: summary ? route.summary(c, t.id) : banks.length ? route.mcTopic(c, t.id) : null,
        mc: banks.flatMap((b) => b.data.questions.map((q) => q.id)),
        ex: course.exercises.filter((e) => e.data.topic === t.id && e.data.id).map((e) => e.data.id as string),
      };
    }),
    exams: course.exams.map((e) => ({ id: e.id, title: e.doc.data.title, points: e.fm.points })),
    sessions: (course.plan?.sessions ?? []).map((s) => ({ id: s.id, date: s.date })),
  };
}

/** JSON for an inline <script type="application/json">: no "</script>" can end it early. */
export function scriptJson(value: unknown): string {
  return JSON.stringify(value).replace(/</g, '\\u003c');
}

/** Titles of source documents from the course index (_build/index.json). */
export function sourceTitle(courseId: string, doc: string): string {
  const index = readJson(joinPath(coursesDir(), courseId, '_build', 'index.json')) as {
    sources?: Record<string, { title?: string }>;
  } | null;
  return index?.sources?.[doc]?.title ?? doc;
}
