// Built PDFs (docs/architecture.md §3.3): /c/<c>/pdf/<file> serves <course>/_build/pdf/<file>
// for every document in _build/pdf/manifest.json, byte for byte. The build emits exactly the
// listed files; dev reads them on request.
import type { APIRoute } from 'astro';
import { listCourses } from '../../../../lib/courses';
import { expectedPdfFiles, pdfFile, pdfResponse } from '../../../../lib/pdf';

export async function getStaticPaths() {
  const courses = await listCourses();
  return courses.flatMap((course) => {
    const files = new Set(course.pdfs.map((d) => d.file));
    // Dev caches these paths until content changes; listing every file the pipeline may
    // write lets a PDF built while the server runs be served at once (GET checks it).
    if (import.meta.env.DEV) for (const f of expectedPdfFiles(course.exams.map((e) => e.id))) files.add(f);
    return [...files].map((file) => ({ params: { course: course.id, name: file.replace(/\.pdf$/, '') } }));
  });
}

export const GET: APIRoute = ({ params }) => {
  const course = params.course ?? '';
  const file = `${params.name ?? ''}.pdf`;
  return pdfResponse(pdfFile(course, file), `${course}/_build/pdf/${file}`, import.meta.env.DEV);
};
