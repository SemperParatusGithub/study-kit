// Content collections (docs/architecture.md §3.2). The pydantic models in
// src/studykit/model.py are the schema; these Zod schemas only cover what the site renders.
import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';
import { pandocLoader } from './loaders/pandoc';
import { env } from './lib/sys.mjs';

const base = env('STUDYKIT_COURSES_DIR') ?? '../courses';
const courseId = ({ entry }: { entry: string }) => entry.split('/')[0];

// Astro's YAML loader turns 2027-02-15 into a Date; the site works with ISO strings.
const isoDate = z
  .union([z.date(), z.string()])
  .transform((v) => (v instanceof Date ? v.toISOString().slice(0, 10) : v));

const topic = z.object({
  id: z.string(),
  title: z.string(),
  weight: z.number(),
  prereq: z.array(z.string()).default([]),
});

const courses = defineCollection({
  loader: glob({ pattern: '*/course.yaml', base, generateId: courseId }),
  schema: z.looseObject({
    id: z.string(),
    title: z.string(),
    short: z.string().nullish(),
    lang: z.enum(['de', 'en']),
    semester: z.string().nullish(),
    status: z.enum(['draft', 'ready']).default('draft'),
    exam: z.looseObject({
      date: isoDate.nullish(),
      duration_min: z.number().nullish(),
      points: z.number().nullish(),
      format: z.string(),
      aids: z.array(z.string()).default([]),
      mc: z
        .looseObject({
          present: z.boolean(),
          types: z.array(z.string()).default([]),
          scoring: z.enum(['all-or-nothing', 'partial', 'kprim']).default('all-or-nothing'),
          negative_marking: z.boolean().default(false),
        })
        .nullish(),
    }),
    cheatsheet: z
      .object({ allowed: z.boolean(), max_pages: z.number().default(2) })
      .default({ allowed: false, max_pages: 2 }),
    topics: z.array(topic).min(1),
    focus: z.array(z.string()).default([]),
    skip: z.array(z.string()).default([]),
  }),
});

const finding = z.object({
  path: z.string(),
  line: z.number(),
  col: z.number(),
  code: z.string(),
  message: z.string(),
  fix: z.string(),
  severity: z.enum(['error', 'warning', 'info']),
});

const docs = defineCollection({
  loader: pandocLoader({ base }),
  schema: z.object({
    course: z.string(),
    rel: z.string(),
    kind: z.enum(['overview', 'summary', 'exercise', 'mc', 'exam-mc', 'exam-task', 'cheatsheet', 'exam']),
    title: z.string(),
    id: z.string().nullable(),
    topic: z.string().nullable(),
    exam: z.string().nullable(),
    order: z.number().nullable(),
    fm: z.record(z.string(), z.unknown()),
    labels: z.record(z.string(), z.string()),
    h: z.string().nullable(),
    headings: z.array(z.object({ level: z.number(), id: z.string(), text: z.string() })),
    questions: z.array(
      z.object({
        id: z.string(),
        type: z.string(),
        difficulty: z.number().nullable(),
        topic: z.string().nullable(),
        h: z.string(),
        html: z.string(),
      }),
    ),
    findings: z.array(finding),
  }),
});

const session = z.looseObject({
  id: z.string(),
  date: isoDate,
  minutes: z.number(),
  kind: z.string(),
  topics: z.array(z.string()).default([]),
  goal: z.string().nullish(),
  note: z.string().nullish(),
  tasks: z
    .array(
      z.looseObject({
        do: z.string(),
        ref: z.string().nullish(),
        refs: z.array(z.string()).default([]),
        topic: z.string().nullish(),
        count: z.number().nullish(),
      }),
    )
    .default([]),
});

const plans = defineCollection({
  loader: glob({ pattern: '*/plan.yaml', base, generateId: courseId }),
  schema: z.looseObject({
    generated: isoDate,
    exam_date: isoDate.nullish(),
    sessions: z.array(session).default([]),
  }),
});

export const collections = { courses, docs, plans };
