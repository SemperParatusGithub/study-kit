// Fills the shell's progress placeholders from browser progress (docs/architecture.md
// §2.11, §3.2). The pages render them empty (CSS shows "—"); this module computes the
// figures with lib/stats.ts from the progress store and the course info the shell writes
// into the page (<script type="application/json" data-sk-course-data="<course>">), and
// refreshes them whenever progress changes on this page, in another tab, or the page comes
// back from the back/forward cache.
//
//   [data-sk-due-count][data-course] [data-topic]   MC questions due today (of one topic)
//   [data-sk-accuracy][data-course][data-topic]     accuracy over the last 10 answers
//   ol[data-sk-weakest][data-course]                the 3 weakest topics; the next
//                                                   [data-sk-weakest-empty] hides itself
//   [data-sk-mastery][data-course]                  mastery ring (MasteryRing.astro)
//   [data-sk-exam-best][data-course][data-exam]     best mock-exam result
//   [data-sk-exam-locked][data-course][data-exam]   hidden while that mock exam runs
//     [data-duration-min]                           (started, not submitted, time left):
//                                                   the solutions PDF on the exam list
//   [data-sk-status][data-item]                     exercise status; the row [data-item]
//                                                   gets data-status (new, started,
//                                                   not-yet, partial, solved) for the
//                                                   list filter
//   [data-next-session][data-course]                shows the first session card
//                                                   ([data-session-date][data-session])
//                                                   today or later that is not done
// A placeholder's course is its own data-course, else the nearest one, else <body>'s.
// <sk-plan> fills its own "behind schedule" banner.

import { isDay } from '../lib/leitner.ts';
import { storeFor } from '../lib/store.ts';
import {
  dueCount,
  examSummary,
  exerciseStatus,
  mastery,
  nextSession,
  RECENT,
  topicStats,
  weakestTopics,
  type CourseInfo,
  type ExerciseStatus,
  type Items,
  type TopicInfo,
} from '../lib/stats.ts';
import { h, percent, pts, today } from './util.ts';

const PLACEHOLDERS = [
  '[data-sk-due-count]',
  '[data-sk-accuracy]',
  '[data-sk-weakest]',
  '[data-sk-mastery]',
  '[data-sk-exam-best]',
  '[data-sk-exam-locked]',
  '[data-sk-status]',
  '[data-next-session]',
].join(',');

const STATUS_TEXT: Record<ExerciseStatus, string> = {
  new: '',
  started: 'Started',
  'not-yet': 'Not yet',
  partial: 'Partly',
  solved: 'Solved',
};

/** The course a placeholder belongs to. */
function courseOfPlaceholder(el: Element): string {
  return (
    el.getAttribute('data-course') ||
    el.closest('[data-course]')?.getAttribute('data-course') ||
    document.body?.dataset.course ||
    ''
  );
}

/** The course info the shell wrote into the page, or a minimal stand-in. */
export function courseInfo(course: string, root: ParentNode = document): CourseInfo {
  const script = [...root.querySelectorAll<HTMLScriptElement>('script[data-sk-course-data]')].find(
    (s) => s.dataset.skCourseData === course,
  );
  let raw: Partial<CourseInfo> = {};
  try {
    raw = script?.textContent ? (JSON.parse(script.textContent) as Partial<CourseInfo>) : {};
  } catch {
    raw = {};
  }
  const bodyDate = document.body?.dataset.course === course ? document.body.dataset.examDate : null;
  const examDate = isDay(raw.examDate) ? raw.examDate : isDay(bodyDate) ? bodyDate : null;
  return {
    id: course,
    examDate,
    topics: Array.isArray(raw.topics) ? raw.topics.filter((t): t is TopicInfo => typeof t?.id === 'string') : [],
    exams: Array.isArray(raw.exams) ? raw.exams : [],
    sessions: Array.isArray(raw.sessions) ? raw.sessions.filter((s) => isDay(s?.date)) : [],
  };
}

function setText(el: Element, text: string): void {
  if (el.textContent !== text) el.textContent = text;
}

function fillDue(el: HTMLElement, items: Items, info: CourseInfo, day: string): void {
  const topic = el.dataset.topic || undefined;
  const n = dueCount(items, info.topics, day, info.examDate, topic);
  setText(el, String(n));
  el.dataset.value = String(n);
}

function fillAccuracy(el: HTMLElement, acc: number | null, n: number): void {
  setText(el, acc === null ? '' : percent(acc));
  if (acc === null) el.removeAttribute('title');
  else el.title = `Right in the last ${n} ${n === 1 ? 'answer' : 'answers'} (at most ${RECENT})`;
}

function fillWeakest(list: HTMLElement, items: Items, info: CourseInfo, day: string): void {
  const stats = topicStats(items, info.topics, day, info.examDate);
  const weak = weakestTopics(stats, info.topics, 3);
  const href = new Map(info.topics.map((t) => [t.id, t.href ?? null]));
  list.replaceChildren(
    ...weak.map((s) => {
      const link = href.get(s.id);
      return h('li', { 'data-topic': s.id },
        link ? h('a', { href: link }, s.title) : h('span', {}, s.title),
        ' ',
        h('span', { class: 'sk-weak-value' }, percent(s.accuracy ?? 0)));
    }),
  );
  const empty =
    list.parentElement?.querySelector<HTMLElement>('[data-sk-weakest-empty]') ??
    document.querySelector<HTMLElement>(`[data-sk-weakest-empty][data-course="${CSS.escape(info.id)}"]`);
  if (empty) empty.hidden = weak.length > 0;
}

const RING_R = 22;

/** Redraw a MasteryRing (56×56 viewBox, radius 22) for `pct` (0–100) or null. */
function fillRing(el: HTMLElement, pct: number | null, fromBrowser: boolean): void {
  const svg = el.querySelector('svg');
  const value = el.querySelector('.mastery-value');
  if (!svg || !value) return;
  let fill = svg.querySelector<SVGCircleElement>('circle[data-sk-ring-fill]') ?? svg.querySelectorAll('circle')[1] ?? null;
  if (pct === null || pct <= 0) {
    fill?.remove();
  } else {
    if (!fill) {
      fill = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      for (const [k, v] of Object.entries({
        cx: '28', cy: '28', r: String(RING_R), fill: 'none', stroke: 'var(--accent)', 'stroke-width': '6',
        'stroke-linecap': 'round', transform: 'rotate(-90 28 28)',
      })) fill.setAttribute(k, v);
      svg.append(fill);
    }
    fill.setAttribute('data-sk-ring-fill', '');
    const c = 2 * Math.PI * RING_R;
    fill.setAttribute('stroke-dasharray', `${((c * pct) / 100).toFixed(2)} ${c.toFixed(2)}`);
  }
  setText(value, pct === null ? '—' : `${pct}%`);
  el.dataset.value = pct === null ? '' : String(pct);
  el.setAttribute('role', 'img');
  el.setAttribute(
    'aria-label',
    pct === null ? 'Mastery: no answers yet' : `Mastery ${pct}%${fromBrowser ? ', from your answers in this browser' : ''}`,
  );
}

function fillMastery(el: HTMLElement, items: Items, info: CourseInfo, day: string): void {
  // The build-time value (progress/mastery.json) stays until this browser has answers.
  el.dataset.buildValue ??= el.dataset.value ?? '';
  const m = mastery(topicStats(items, info.topics, day, info.examDate), info.topics);
  if (m !== null) {
    fillRing(el, Math.round(m * 100), true);
    return;
  }
  const build = el.dataset.buildValue;
  fillRing(el, build ? Number(build) : null, false);
}

function fillExam(el: HTMLElement, items: Items, info: CourseInfo): void {
  const id = el.dataset.exam ?? '';
  const { count, best, last } = examSummary(items[`exam:${id}`]);
  if (!best || !last) {
    setText(el, 'not taken yet');
    el.dataset.value = '';
    return;
  }
  const max = info.exams.find((e) => e.id === id)?.points;
  const of = (total: number) => (max ? `${pts(total)} / ${pts(max)}` : pts(total));
  const when = new Date(last.started).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
  const text =
    count === 1
      ? `${of(best.total)} points (${when})`
      : `${of(best.total)} points · ${count} attempts, last ${of(last.total)} (${when})`;
  setText(el, text);
  el.dataset.value = String(best.total);
}

/** Hide `el` while its mock exam runs, as <sk-exam> keeps the exam's solutions locked. */
function fillExamLock(el: HTMLElement, course: string): void {
  const s = storeFor(course).session<{ started?: unknown; submitted?: unknown }>(`exam:${el.dataset.exam ?? ''}`);
  const started = typeof s?.started === 'string' ? Date.parse(s.started) : Number.NaN;
  // a missing or broken duration counts as time left: locked until submitted
  const end = started + Number(el.dataset.durationMin) * 60_000;
  const running = Boolean(s?.started) && !s?.submitted && !(Date.now() >= end);
  if (el.hidden !== running) el.hidden = running;
}

function fillStatus(el: HTMLElement, items: Items): void {
  const item = el.dataset.item ?? '';
  const status = exerciseStatus(items[item]);
  setText(el, STATUS_TEXT[status]);
  el.dataset.status = status;
  // The list row: site.ts filters on data-status and re-applies when it changes.
  const row = el.closest<HTMLElement>('[data-filter-row], li[data-item]');
  if (row && row.dataset.status !== status) row.dataset.status = status;
}

function fillNextSession(box: HTMLElement, items: Items, day: string): void {
  const cards = [...box.querySelectorAll<HTMLElement>('[data-session-date]')];
  const sessions = cards.map((el) => ({ id: el.dataset.session ?? '', date: el.dataset.sessionDate ?? '', el }));
  const next = nextSession(sessions, items, day);
  for (const s of sessions) s.el.hidden = s !== next;
  const none = box.querySelector<HTMLElement>('[data-no-session]');
  if (none) none.hidden = Boolean(next);
}

/** Fill every placeholder of `course` below `root`. */
export function fillCourse(course: string, root: ParentNode = document): void {
  const items = storeFor(course).read().items;
  const info = courseInfo(course);
  const day = today();
  const mine = [...root.querySelectorAll<HTMLElement>(PLACEHOLDERS)].filter((el) => courseOfPlaceholder(el) === course);
  let stats: ReturnType<typeof topicStats> | null = null;
  const statOf = (topic: string) => {
    stats ??= topicStats(items, info.topics, day, info.examDate);
    return stats.find((s) => s.id === topic);
  };
  for (const el of mine) {
    if (el.matches('[data-sk-due-count]')) fillDue(el, items, info, day);
    else if (el.matches('[data-sk-accuracy]')) {
      const st = statOf(el.dataset.topic ?? '');
      fillAccuracy(el, st?.accuracy ?? null, st?.recent.length ?? 0);
    } else if (el.matches('[data-sk-weakest]')) fillWeakest(el, items, info, day);
    else if (el.matches('[data-sk-mastery]')) fillMastery(el, items, info, day);
    else if (el.matches('[data-sk-exam-best]')) fillExam(el, items, info);
    else if (el.matches('[data-sk-exam-locked]')) fillExamLock(el, course);
    else if (el.matches('[data-sk-status]')) fillStatus(el, items);
    else if (el.matches('[data-next-session]')) fillNextSession(el, items, day);
  }
}

/** Every course that has a placeholder below `root`. */
export function placeholderCourses(root: ParentNode = document): string[] {
  const set = new Set<string>();
  for (const el of root.querySelectorAll(PLACEHOLDERS)) {
    const c = courseOfPlaceholder(el);
    if (c) set.add(c);
  }
  return [...set];
}

const watched = new Set<string>();

/** Fill all placeholders now and keep them current. */
export function startDashboard(root: ParentNode = document): void {
  const courses = placeholderCourses(root);
  for (const c of courses) {
    fillCourse(c, root);
    if (watched.has(c)) continue;
    watched.add(c);
    storeFor(c).subscribe(() => fillCourse(c, root));
  }
  if (!watched.has('#pageshow')) {
    watched.add('#pageshow');
    // A page restored from the back/forward cache missed what other pages recorded.
    window.addEventListener('pageshow', (e) => {
      if (e.persisted) for (const c of placeholderCourses(root)) fillCourse(c, root);
    });
    // A mock exam started, submitted or retaken in another tab changes only session state.
    window.addEventListener('storage', (e) => {
      if (e.key?.endsWith(':session')) for (const c of placeholderCourses(root)) fillCourse(c, root);
    });
  }
}
