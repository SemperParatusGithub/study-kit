// Shapes of the content collections (src/content.config.ts) and of course frontmatter as
// the render bridge returns it (pydantic models in src/studykit/model.py, dumped as JSON).
import type { Finding } from './findings';
import type { McElement, MetaHeading } from './html';

export type DocKind =
  | 'overview'
  | 'summary'
  | 'exercise'
  | 'mc'
  | 'exam-mc'
  | 'exam-task'
  | 'cheatsheet'
  | 'exam';

/** What the pandoc loader stores per course file. */
export interface DocData {
  course: string;
  rel: string;
  kind: DocKind;
  title: string;
  /** exercise / exam-task / exam id */
  id: string | null;
  topic: string | null;
  /** exam id for exam.yaml, exam tasks and the exam MC part */
  exam: string | null;
  /** NN prefix of summary chapters and exam tasks */
  order: number | null;
  /** validated frontmatter (or exam.yaml) as plain JSON */
  fm: Record<string, unknown>;
  /** frontmatter labels with inline math (answers, rubric, objectives): text -> HTML */
  labels: Record<string, string>;
  /** content hash of an exercise or exam task (§2.11) */
  h: string | null;
  headings: MetaHeading[];
  questions: McElement[];
  findings: Finding[];
}

export interface AnswerFm {
  key: string;
  label: string;
  value?: number | null;
  unit?: string | null;
  rtol?: number | null;
  atol?: number | null;
  expr?: string | null;
  symbols?: string[];
}

export interface ExerciseFm {
  id: string;
  title: string;
  topic: string;
  difficulty: number;
  kind: string;
  minutes: number;
  source?: { doc: string; page?: number | null; relation: string } | null;
  answers?: AnswerFm[];
}

export interface ExamTaskFm extends Omit<ExerciseFm, 'difficulty' | 'minutes'> {
  points: number;
  archetype: string;
  rubric: { points: number; criterion: string }[];
  difficulty?: number | null;
  minutes?: number | null;
}

export interface SummaryFm {
  topic: string;
  title: string;
  objectives?: string[];
  sources?: { doc: string; pages?: string | number | null }[];
}

export interface CheatsheetFm {
  title: string;
  max_pages: number;
  priority?: string[];
}

export interface ExamFm {
  id: string;
  title: string;
  duration_min: number;
  points: number;
  pass_points: number;
  aids: 'inherit' | string[];
  tasks: string[];
  mc?: { file: string; points_each: number } | null;
}
