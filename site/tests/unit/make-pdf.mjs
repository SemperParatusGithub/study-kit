// A minimal PDF writer for the unit tests of the PDF routes (unit/pdf.test.ts). The site's
// real PDFs come from `studykit pdf` (docs/architecture.md §3.3) and are checked end to end
// in e2e/pdf.spec.ts; these small ones only stand in for a course's files in a temporary
// directory. Generated at test time, never committed.

export const PRODUCER = 'studykit site tests: test PDF';

/** Text of a PDF string literal, encoded WinAnsi (latin1) with ( ) \ escaped. */
function pdfString(text) {
  return `(${text.replace(/[\\()]/g, (c) => `\\${c}`)})`;
}

/**
 * A valid PDF 1.7 with one page per entry of `pages` (each a list of text lines), set in
 * the standard Helvetica font, so every reader (pypdfium2, browsers) opens it.
 * @param {string[][]} pages
 * @param {string} title
 * @returns {Buffer}
 */
export function makePdf(pages, title) {
  const objects = [];
  const add = (body) => objects.push(body); // the new length: the object's number
  const catalog = add(null);
  const tree = add(null);
  const font = add('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>');
  const kids = [];
  for (const lines of pages) {
    const ops = ['BT', '/F1 22 Tf', '72 760 Td', '26 TL'];
    lines.forEach((line, i) => {
      if (i === 1) ops.push('/F1 12 Tf', '16 TL');
      ops.push(`${pdfString(line)} Tj`, 'T*');
    });
    ops.push('ET');
    const stream = Buffer.from(ops.join('\n'), 'latin1');
    const content = add(Buffer.concat([
      Buffer.from(`<< /Length ${stream.length} >>\nstream\n`, 'latin1'),
      stream,
      Buffer.from('\nendstream', 'latin1'),
    ]));
    kids.push(add(`<< /Type /Page /Parent ${tree} 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 ${font} 0 R >> >> /Contents ${content} 0 R >>`));
  }
  objects[catalog - 1] = `<< /Type /Catalog /Pages ${tree} 0 R >>`;
  objects[tree - 1] = `<< /Type /Pages /Kids [${kids.map((k) => `${k} 0 R`).join(' ')}] /Count ${kids.length} >>`;
  const info = add(`<< /Title ${pdfString(title)} /Producer ${pdfString(PRODUCER)} >>`);

  const chunks = [Buffer.from('%PDF-1.7\n%\xe2\xe3\xcf\xd3\n', 'latin1')];
  let offset = chunks[0].length;
  const offsets = [];
  objects.forEach((body, i) => {
    const chunk = Buffer.concat([
      Buffer.from(`${i + 1} 0 obj\n`, 'latin1'),
      Buffer.isBuffer(body) ? body : Buffer.from(body, 'latin1'),
      Buffer.from('\nendobj\n', 'latin1'),
    ]);
    offsets.push(offset);
    offset += chunk.length;
    chunks.push(chunk);
  });
  const xref = [
    'xref',
    `0 ${objects.length + 1}`,
    '0000000000 65535 f ',
    ...offsets.map((o) => `${String(o).padStart(10, '0')} 00000 n `),
    'trailer',
    `<< /Size ${objects.length + 1} /Root ${catalog} 0 R /Info ${info} 0 R >>`,
    'startxref',
    String(offset),
    '%%EOF',
    '',
  ].join('\n');
  chunks.push(Buffer.from(xref, 'latin1'));
  return Buffer.concat(chunks);
}
