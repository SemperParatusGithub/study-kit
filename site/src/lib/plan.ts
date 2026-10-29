// Study plan sessions (plan.yaml, docs/architecture.md §2.9) as UI data: what each task
// says and where it links.
import { resolveRef, route, type Course, type Ref, type Session } from './courses';
import { weekStart } from './format';

export interface TaskView {
  label: string;
  links: Ref[];
  detail?: string;
}

const VERB: Record<string, string> = {
  read: 'Read',
  exercises: 'Exercises',
  mc: 'MC practice',
  exam: 'Mock exam',
  review: 'Review',
  cheatsheet: 'Cheat sheet',
};

export function taskView(course: Course, task: Session['tasks'][number]): TaskView {
  const refs = [task.ref, ...task.refs].filter((r): r is string => Boolean(r));
  const links = refs.map((r) => resolveRef(course, r)).filter((r): r is Ref => r !== null);
  const label = VERB[task.do] ?? task.do;
  if (task.do === 'mc' && task.topic) {
    const hasBank = course.banks.some((b) => b.data.topic === task.topic);
    if (hasBank) links.push({ href: route.mcTopic(course.id, task.topic), title: course.topicTitle(task.topic) });
    return { label, links, detail: task.count ? `${task.count} questions` : undefined };
  }
  if (task.do === 'review' && task.topic && !links.length) {
    const ref = resolveRef(course, `topic:${task.topic}`);
    if (ref) links.push(ref);
  }
  if (task.do === 'cheatsheet' && course.cheatsheet) {
    links.push({ href: route.cheatsheet(course.id), title: course.cheatsheet.data.title });
  }
  return { label, links };
}

/** The first link of a session: where "Start" goes. */
export function sessionStart(course: Course, session: Session): string {
  for (const task of session.tasks) {
    const view = taskView(course, task);
    if (view.links.length) return view.links[0].href;
  }
  return route.plan(course.id);
}

export interface Week {
  start: string;
  sessions: Session[];
}

export function weeks(sessions: Session[]): Week[] {
  const out: Week[] = [];
  for (const s of [...sessions].sort((a, b) => a.date.localeCompare(b.date))) {
    const start = weekStart(s.date);
    const last = out.at(-1);
    if (last && last.start === start) last.sessions.push(s);
    else out.push({ start, sessions: [s] });
  }
  return out;
}
