/**
 * Scanner behind the i18n hardcoded-string ratchet (TF-671, hardened in TF-772).
 *
 * Why this lives in `scripts/` and not next to the test that uses it: the
 * allowlist is generated, not hand-edited (see `regenerate-i18n-allowlist.ts`),
 * so the scan needs exactly one implementation shared by the Jest guard and the
 * regenerator. A module under `src/__tests__/` cannot serve that role — CRA's
 * `testMatch` treats every `.ts` file in a `__tests__` directory as a test suite
 * and fails it for containing no tests.
 *
 * Path anchoring: each scan root carries a fixed logical `prefix`
 * (`core/frontend/src`, …) rather than a `path.relative()` against a computed
 * repo root, because `core/` becomes the checkout root in the public mirror
 * (`git subtree split --prefix=core`). A shared anchor silently shifts by one
 * path segment there and every finding's key stops matching the allowlist.
 * Fixed prefixes describe what a path *means*, not where this file sits.
 */
import * as fs from 'fs';
import * as path from 'path';

// `core/frontend/src` in both layouts: the private monorepo (core/ nested under
// the repo root) and the public mirror (core/ IS the checkout root). This file
// sits in `core/frontend/scripts/`, so `../src` resolves correctly in both.
const CORE_SRC_DIR = path.resolve(__dirname, '../src');
// Only used to locate premium/enterprise, which live outside core/ and are
// therefore absent in the mirror by construction. Never used to compute a
// finding's `rel` path.
const MONOREPO_ROOT = path.resolve(CORE_SRC_DIR, '../../..');

export interface ScanRoot {
  dir: string;
  prefix: string;
}

export const SCAN_ROOTS: ScanRoot[] = [
  { dir: CORE_SRC_DIR, prefix: 'core/frontend/src' },
  { dir: path.resolve(MONOREPO_ROOT, 'premium/frontend/src'), prefix: 'premium/frontend/src' },
  { dir: path.resolve(MONOREPO_ROOT, 'enterprise/frontend/src'), prefix: 'enterprise/frontend/src' },
];

const SOURCE_EXT = /\.(ts|tsx)$/;
const SKIP_DIRS = new Set([
  'node_modules', '__tests__', '__mocks__', 'build', 'dist', 'coverage', 'locales', 'types',
]);
const SKIP_FILE = /\.(test|spec)\.(ts|tsx)$|\.d\.ts$/;

// Multi-line aware: the single-line scan in the TF-671 ticket missed
// UpgradePrompt entirely, because its copy sits in multi-line <Typography>.
//
// The lookbehind rules out `=>`: an arrow function's `>` was read as a closing
// tag, and everything up to the next TypeScript generic `<` as its text — which
// flagged two brace-free stretches of ordinary code (apiClient.ts,
// RAGExamCreator.tsx) as untranslated copy. A real JSX `>` is never preceded by
// `=`; it closes on an identifier, a quote, `/` or `}`.
const JSX_TEXT = /(?<==?[^=])>(\s*[A-Za-zÄÖÜäöüÉÈÀÇéèàç][^<>{}]*)</g;

// Second false-positive class, same root cause as the lookbehind above: a
// relational `>` (`r.width > window.innerWidth`) opens a match that a later
// relational `<` closes, and everything between reads as prose. The lookbehind
// cannot see this one — nothing distinguishes `a > b` from a multi-line JSX tag
// whose `>` sits alone on its own line, which is exactly the shape this guard
// was built to catch (UpgradePrompt).
//
// So the capture is filtered instead of the delimiter. A JSX text node is
// prose: it does not carry a semicolon or an assignment. Code does. This is a
// heuristic, not a proof — but the alternative is parking scanner artefacts in
// the allowlist, which corrupts the very number TF-772 tracks progress by.
//
// Its one blind spot: a JSX text node containing an HTML entity (`&nbsp;`)
// carries a semicolon and would be skipped. There is none in any of the three
// src trees today; if one appears, narrow the semicolon branch rather than
// dropping the filter.
const CODE_FRAGMENT = /[;=]|&&|\|\||\?\?/;

const VISIBLE_PROP =
  /\b(label|placeholder|title|aria-label|helperText|alt)\s*=\s*(['"])([^'"]{2,})\2/g;

// TF-772 C1. The predecessor was a single regex that required the literal to
// sit *directly* after `new Error(`, which saw 15 of 95 throw sites in the
// service directories. The dominant shape here is
// `throw new Error(error.detail || 'English fallback')` — the literal is the
// right-hand side of a `||`, not the sole argument — and a second shape passes
// it into a helper: `throw new Error(extractApiError(error.detail, 'Login
// failed'))`. Neither is expressible as a regex over the argument list, because
// the argument list nests. So the scan locates `new Error(`, reads the balanced
// argument, and reports *every* string literal inside it.
//
// Matching `new Error(` rather than `throw new Error(` additionally covers
// `reject(new Error('…'))`, the shape `WS_ERRORS` reaches the UI through
// (premium RAGService, TF-772 PR 5).
const NEW_ERROR = /\bnew Error\(/g;

/** Minimum literal length, matching the `{3,}` of the regex this replaced. */
const MIN_LITERAL_LENGTH = 3;

export interface Finding {
  file: string;
  line: number;
  kind: string;
  text: string;
}

export function walk(dir: string, out: string[] = []): string[] {
  if (!fs.existsSync(dir)) return out;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (SKIP_DIRS.has(entry.name)) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(full, out);
    else if (SOURCE_EXT.test(entry.name) && !SKIP_FILE.test(entry.name)) out.push(full);
  }
  return out;
}

export function stripComments(src: string): string {
  return src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
}

function lineOf(src: string, index: number): number {
  return src.slice(0, index).split('\n').length;
}

/**
 * Index just past the string literal starting at `start`.
 *
 * Escape-aware, so `'it\'s'` does not terminate early. An unterminated literal
 * returns the end of the source rather than looping — the scan must not hang on
 * a file that does not parse.
 */
function endOfString(src: string, start: number): number {
  const quote = src[start];
  let i = start + 1;
  while (i < src.length) {
    if (src[i] === '\\') {
      i += 2;
      continue;
    }
    if (src[i] === quote) return i + 1;
    i++;
  }
  return src.length;
}

const QUOTES = new Set(["'", '"', '`']);

/**
 * The text between the `(` at `open - 1` and its matching `)`.
 *
 * Parentheses inside string literals are skipped, so
 * `new Error('Fehler (intern)')` reads its whole argument instead of stopping
 * at the `)` in the prose.
 */
function balancedArgument(src: string, open: number): string {
  let depth = 1;
  let i = open;
  while (i < src.length && depth > 0) {
    const c = src[i];
    if (QUOTES.has(c)) {
      i = endOfString(src, i);
      continue;
    }
    if (c === '(') depth++;
    else if (c === ')') depth--;
    i++;
  }
  return src.slice(open, Math.max(open, i - 1));
}

/** Every string literal inside `arg`, unquoted, in source order. */
function stringLiteralsIn(arg: string): string[] {
  const out: string[] = [];
  let i = 0;
  while (i < arg.length) {
    if (QUOTES.has(arg[i])) {
      const end = endOfString(arg, i);
      // An unterminated literal yields arg.length; drop it rather than
      // reporting a truncated fragment as user-facing copy.
      if (end <= arg.length && arg[end - 1] === arg[i]) {
        out.push(arg.slice(i + 1, end - 1));
      }
      i = end;
      continue;
    }
    i++;
  }
  return out;
}

/**
 * Findings for one already-comment-stripped source text.
 *
 * Split out from the filesystem walk so the regression test in
 * `i18n-hardcoded-strings.regex.test.ts` can assert one example per form
 * without writing fixture files.
 */
export function scanSource(src: string, rel: string): Finding[] {
  const findings: Finding[] = [];
  const isService = /\/(services|api)\//.test(`/${rel}`);

  for (const m of src.matchAll(JSX_TEXT)) {
    const text = m[1].trim().replace(/\s+/g, ' ');
    if (text.length < 3 || !/[A-Za-zÄÖÜäöü]{3}/.test(text)) continue;
    if (CODE_FRAGMENT.test(text)) continue;
    findings.push({ file: rel, line: lineOf(src, m.index ?? 0), kind: 'jsx-text', text });
  }

  for (const m of src.matchAll(VISIBLE_PROP)) {
    findings.push({ file: rel, line: lineOf(src, m.index ?? 0), kind: m[1], text: m[3] });
  }

  // `literal-error` stays restricted to services/api — see the "deliberate
  // gap" note in i18n-hardcoded-strings.test.ts for why components are not
  // scanned for it.
  if (isService) {
    for (const m of src.matchAll(NEW_ERROR)) {
      const arg = balancedArgument(src, m.index + m[0].length);
      for (const text of stringLiteralsIn(arg)) {
        if (text.length < MIN_LITERAL_LENGTH) continue;
        findings.push({
          file: rel,
          line: lineOf(src, m.index),
          kind: 'literal-error',
          text,
        });
      }
    }
  }

  return findings;
}

export function collect(): Finding[] {
  const findings: Finding[] = [];
  for (const { dir, prefix } of SCAN_ROOTS) {
    for (const file of walk(dir)) {
      const rel = `${prefix}/${path.relative(dir, file).split(path.sep).join('/')}`;
      findings.push(...scanSource(stripComments(fs.readFileSync(file, 'utf8')), rel));
    }
  }
  return findings;
}

/** Line numbers shift constantly; the allowlist keys on file + kind + text. */
export const keyOf = (f: Finding): string => `${f.file}::${f.kind}::${f.text}`;

/** Allowlist content for the current tree: sorted, de-duplicated keys. */
export function allowlistFor(findings: Finding[]): string[] {
  return Array.from(new Set(findings.map(keyOf))).sort();
}

/**
 * Allowlist entries that are NOT remaining cleanup work and are meant to stay
 * indefinitely. TF-772 measures progress by allowlist size, so the target value
 * at the end of that ticket is exactly this list — not zero.
 *
 * The allowlist itself is a generated flat array of strings and has nowhere to
 * put a per-entry rationale, so the rationales live here, next to the data the
 * guard asserts against:
 *
 * - The three `CHF …` amounts are prices. They are identical in de/en/fr/it by
 *   design; routing them through `t()` would create four copies of one number
 *   that must never diverge.
 * - `Free`, `Starter`, `Professional`, `Enterprise` are subscription tier
 *   *names*, not descriptions. They are proper nouns that appear untranslated
 *   in invoices, in the RBAC tier column and in the backend's own enums.
 *
 * Nobody should try to "finish" these by translating "CHF 0" or "Starter";
 * `i18n-hardcoded-strings.test.ts` asserts they are still present so that a
 * well-meaning regeneration cannot quietly drop them.
 */
export const PERMANENT_EXCEPTIONS: string[] = [
  'core/frontend/src/pages/BillingPage.tsx::jsx-text::CHF 0',
  'core/frontend/src/pages/BillingPage.tsx::jsx-text::CHF 49',
  'core/frontend/src/pages/BillingPage.tsx::jsx-text::CHF 9',
  'core/frontend/src/pages/BillingPage.tsx::jsx-text::Enterprise',
  'core/frontend/src/pages/BillingPage.tsx::jsx-text::Free',
  'core/frontend/src/pages/BillingPage.tsx::jsx-text::Professional',
  'core/frontend/src/pages/BillingPage.tsx::jsx-text::Starter',
];
