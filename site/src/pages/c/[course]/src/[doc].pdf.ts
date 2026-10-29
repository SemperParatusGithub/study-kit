// Source documents (docs/architecture.md §2.1): /c/<c>/src/<doc>.pdf serves the file of
// <doc> in sources/raw/ as sources/manifest.yaml lists it, byte for byte. refs.lua links
// `src:<doc>#p=<n>` here with #page=<n>, which the browser's PDF viewer opens at that page.
// The build emits every listed document whose file exists; dev reads it on request.
import type { APIRoute } from 'astro';
import { listCourses } from '../../../../lib/courses';
import { pdfResponse, sourceFile } from '../../../../lib/pdf';

export async function getStaticPaths() {
  const courses = await listCourses();
  return courses.flatMap((course) =>
    course.sources.map((doc) => ({ params: { course: course.id, doc: doc.id } })),
  );
}

export const GET: APIRoute = ({ params }) => {
  const course = params.course ?? '';
  const doc = params.doc ?? '';
  return pdfResponse(sourceFile(course, doc), `${course}/sources: ${doc}.pdf`, import.meta.env.DEV);
};
