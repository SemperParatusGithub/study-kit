// Static MC pool for <sk-quiz> (docs/architecture.md §3.2): the topic's practice questions
// with their rendered <sk-mc> (KaTeX and figures applied) and content hash.
//   {topic, title, questions: [{id, type, difficulty, topic, h, html}]}
import type { APIRoute } from 'astro';
import { listCourses, type Course, type Doc } from '../../../../lib/courses';
import { inlineFigures } from '../../../../lib/figures';

export async function getStaticPaths() {
  const courses = await listCourses();
  return courses.flatMap((course) =>
    course.banks
      .filter((b) => b.data.topic)
      .map((bank) => ({ params: { course: course.id, topic: bank.data.topic as string }, props: { course, bank } })),
  );
}

export const GET: APIRoute = ({ props }) => {
  const { course, bank } = props as { course: Course; bank: Doc };
  const body = {
    topic: bank.data.topic,
    title: course.topicTitle(bank.data.topic),
    questions: bank.data.questions.map((q) => ({
      id: q.id,
      type: q.type,
      difficulty: q.difficulty,
      topic: q.topic ?? bank.data.topic,
      h: q.h,
      html: inlineFigures(q.html, course.id),
    })),
  };
  return new Response(JSON.stringify(body), { headers: { 'Content-Type': 'application/json; charset=utf-8' } });
};
