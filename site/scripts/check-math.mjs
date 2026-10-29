// Render math with KaTeX in strict mode, exactly as the site does at build time.
// stdin:  JSON array of {"tex": string, "display": boolean}
// stdout: JSON array of {"ok": boolean, "error"?: string}, same order as the input
import katex from "katex";

export const KATEX_OPTIONS = {
  throwOnError: true,
  strict: "error",
  trust: false,
  output: "html",
};

export function checkMath(items) {
  return items.map(({ tex, display }) => {
    try {
      katex.renderToString(tex, { ...KATEX_OPTIONS, displayMode: Boolean(display) });
      return { ok: true };
    } catch (err) {
      return { ok: false, error: String(err.message ?? err) };
    }
  });
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  const items = JSON.parse(Buffer.concat(chunks).toString("utf8"));
  process.stdout.write(JSON.stringify(checkMath(items)));
}
