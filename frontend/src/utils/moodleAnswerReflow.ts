/**
 * Reconstructs readable line structure in Moodle free-text answers (TF-430).
 *
 * Moodle already flattens line breaks on export — none of the source files
 * (JSON or CSV) still have them. What remains is residual structure at the
 * old break points: NBSP (U+00A0), runs of 3+ spaces, and tabs. This
 * function turns those signals into Markdown-friendly paragraph breaks at
 * render time, WITHOUT changing the original text stored in the DB.
 *
 * Deliberately conservative (guard against over-segmentation):
 * - A tab or a run of 3+ whitespace (spaces and/or NBSP) breaks.
 * - A single NBSP (or a 1–2-character run) becomes a normal space — so
 *   mid-sentence `word<NBSP>word` cases (occurring repeatedly in the demo
 *   corpus) don't tear the sentence apart.
 *
 * The MarkdownRenderer only uses `remark-gfm` (no `remark-breaks`); single
 * `\n` collapse to a space there. Breaks are therefore emitted as blank
 * lines (`\n\n`) so they stay visible in the render.
 *
 * Returns `''` for null/undefined/empty/whitespace-only, so callers can
 * keep their `|| '—'` fallback.
 */

// Internal break marker: U+0000 never occurs in Moodle answers and only
// serves as a sentinel before split(). Deliberately written as an escape
// (not as an invisible byte) — do NOT replace with a space.
const BREAK = '\u0000';

export function reflowMoodleAnswer(text: string | null | undefined): string {
  if (!text) return '';

  const withBreaks = text
    // existing line breaks (CR/LF) are real breaks — never pass through as
    // a bare single \n (would collapse invisibly in the render)
    .replace(/[\r\n]+/g, BREAK)
    // tab = indentation/break residue → break
    .replace(/\t/g, BREAK)
    // run of 3+ whitespace (space and/or NBSP) → break
    .replace(/[ \u00a0]{3,}/g, BREAK)
    // remaining NBSP (solo / 1–2-char run) → normal space
    .replace(/\u00a0/g, ' ');

  return withBreaks
    .split(BREAK)
    .map((segment) => segment.replace(/ {2,}/g, ' ').trim())
    .filter((segment) => segment.length > 0)
    .join('\n\n');
}

export default reflowMoodleAnswer;
