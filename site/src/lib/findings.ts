// Findings in the study-kit format (`path:line:col SK-CODE message (fix: …)`, §4.3) and the
// red error card the site shows for them in dev; with STUDYKIT_STRICT=1 they fail the build.
import { escapeHtml } from './html';

export interface Finding {
  path: string;
  line: number;
  col: number;
  code: string;
  message: string;
  fix: string;
  severity: 'error' | 'warning' | 'info';
}

export function formatFinding(f: Finding): string {
  const prefix = f.severity === 'error' ? '' : `${f.severity}: `;
  const fix = f.fix ? ` (fix: ${f.fix})` : '';
  return `${f.path}:${f.line}:${f.col} ${f.code} ${prefix}${f.message}${fix}`;
}

export function errorCard(findings: Finding[], title?: string): string {
  const items = findings
    .map(
      (f) =>
        `<li><code class="sk-error-where">${escapeHtml(`${f.path}:${f.line}:${f.col}`)}</code> ` +
        `<strong>${escapeHtml(f.code)}</strong> ${escapeHtml(f.message)}` +
        (f.fix ? `<span class="sk-error-fix">Fix: ${escapeHtml(f.fix)}</span>` : '') +
        '</li>',
    )
    .join('');
  const n = findings.length;
  const heading = title ?? `${n} content ${n === 1 ? 'error' : 'errors'} in this file`;
  return (
    `<div class="sk-error-card" role="alert" lang="en"><p class="sk-error-title">` +
    `${escapeHtml(heading)}</p><ul>${items}</ul></div>\n`
  );
}

/** What a strict build (STUDYKIT_STRICT=1) throws instead of showing error cards. */
export class StrictError extends Error {
  constructor(findings: Finding[]) {
    super(
      `${findings.length} content error(s) (STUDYKIT_STRICT=1):\n` +
        findings.map((f) => `  ${formatFinding(f)}`).join('\n'),
    );
    this.name = 'StrictError';
  }
}
