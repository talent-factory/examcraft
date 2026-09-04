/**
 * Ratchet guard against hardcoded user-facing strings (TF-671).
 *
 * Why a ratchet and not a clean gate: TF-671 fixed the foundation and the most
 * visible components, but ~45 call sites remain. A test that only fails on NEW
 * violations can land now instead of waiting for the whole cleanup — and the
 * allowlist doubles as the machine-readable remainder list. Entries are only
 * ever removed, never added: that is the whole point.
 *
 * When this test fails on your change, translate the string. Do not add it to
 * the allowlist.
 *
 * Permanent exception: seven allowlist entries from BillingPage.tsx (the CHF
 * amounts and the Free/Starter/Professional/Enterprise plan names) are not
 * remaining cleanup work. They are identical across all four locales on
 * purpose and are meant to stay in the allowlist indefinitely — do not try to
 * "finish" them by translating "CHF 0" or "Starter".
 *
 * First blind spot: the scan reads JSX text nodes and a fixed whitelist of
 * visible props (label, placeholder, title, aria-label, helperText, alt). It
 * does not see props outside that whitelist, nor string arguments passed to
 * function calls. `core/frontend/src/utils/componentLoader.tsx` used to be a
 * real example — it passed English prose straight into `withFeatureGate(...)`,
 * which `UpgradePrompt.tsx` then rendered verbatim; that specific case was
 * fixed by routing i18n keys through instead (`UpgradePrompt` now resolves
 * `featureNameKey`/`featureDescriptionKey` via `t()` itself). The blind spot
 * itself is not fixed, though — the scan still cannot see any other string
 * argument passed to any other function call. A proper fix needs an
 * AST-based scan, which is out of scope here; this comment exists so nobody
 * mistakes the ratchet's current reach for full coverage.
 *
 * Second blind spot, specific to `literal-error`: LITERAL_ERROR only matches
 * a string literal that sits directly inside `throw new Error(...)`. The
 * dominant form in this codebase's services is
 * `throw new Error(error.detail || 'English fallback text')` — the literal is
 * the right-hand side of a `||`, not the sole argument — and the regex does
 * not see it at all. Of the 94 `throw new Error(` call sites across the
 * service directories (measured against the current tree — recompute rather
 * than trust this number, it drifts with every service edit), this pattern
 * accounts for the majority; the regex catches only 14. Do not read the
 * absence of `literal-error` findings in services as evidence that class B
 * is covered there — it mostly is not.
 *
 * Third blind spot: the UI-facing sibling of the same class. Dozens of
 * components still do `setError(err instanceof Error ? err.message : ...)`
 * or a bare `setError(err.message)` / `alert(err.message)` — exactly the
 * pattern `translateError()` exists to replace — outside the `services`/`api`
 * directories this scan's `literal-error` kind is restricted to, and with no
 * string literal for JSX_TEXT/VISIBLE_PROP to catch (the message is a runtime
 * value, not a literal). This scan does not see it at all, in either
 * direction. Do not read a clean `i18n hardcoded-string ratchet` run as
 * evidence that no raw error text reaches the UI — see TF-772 for the actual
 * remaining scope.
 *
 * Tier absence tolerance: `core/` is mirrored standalone to the public repo
 * via `git subtree split --prefix=core` (see `.github/workflows/mirror.yml`),
 * where `premium/` and `enterprise/` do not exist and `core/.github/workflows/ci.yml`
 * runs this suite without `continue-on-error`. A missing tier root is
 * therefore an expected Core-only checkout, not a broken scan — the sanity
 * checks below skip absent roots instead of failing, and the stale-allowlist
 * check only considers entries whose root is present in the current checkout.
 *
 * Path anchoring: each scan root carries its own fixed logical `prefix`
 * (`core/frontend/src`, `premium/frontend/src`, `enterprise/frontend/src`)
 * instead of a `path.relative()` against a computed repo root. That
 * distinction matters because `core/` becomes the checkout root in the
 * public mirror — a single shared root anchor silently shifts by one path
 * segment there, and every finding's `rel` key stops matching the allowlist
 * (all fresh, none stale), breaking the mirror's `test-frontend` CI job on
 * every push to `develop`/`main`. Fixed prefixes are immune to that: they
 * describe what a path *means*, not where this file happens to sit.
 */
import * as fs from 'fs';
import * as path from 'path';

import allowlist from './i18n-hardcoded-strings.allowlist.json';

// `core/frontend/src` in both layouts: the private monorepo (core/ nested
// under the repo root) and the public mirror (core/ IS the checkout root).
const CORE_SRC_DIR = path.resolve(__dirname, '..');
// Only used to locate premium/enterprise, which live outside core/ and are
// therefore absent in the mirror by construction — see "Tier absence
// tolerance" above. Never used to compute a finding's `rel` path.
const MONOREPO_ROOT = path.resolve(CORE_SRC_DIR, '../../..');

interface ScanRoot { dir: string; prefix: string; }

const SCAN_ROOTS: ScanRoot[] = [
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
// The lookbehind rules out `=>`: an arrow function's `>` was read as a
// closing tag, and everything up to the next TypeScript generic `<` as its
// text — which flagged two brace-free stretches of ordinary code
// (apiClient.ts, RAGExamCreator.tsx) as untranslated copy. A real JSX `>`
// is never preceded by `=`; it closes on an identifier, a quote, `/` or `}`.
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
const LITERAL_ERROR = /throw new Error\(\s*(['"`])([^'"`]{3,})\1/g;

interface Finding { file: string; line: number; kind: string; text: string; }

function walk(dir: string, out: string[] = []): string[] {
  if (!fs.existsSync(dir)) return out;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (SKIP_DIRS.has(entry.name)) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(full, out);
    else if (SOURCE_EXT.test(entry.name) && !SKIP_FILE.test(entry.name)) out.push(full);
  }
  return out;
}

function stripComments(src: string): string {
  return src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
}

function lineOf(src: string, index: number): number {
  return src.slice(0, index).split('\n').length;
}

function collect(): Finding[] {
  const findings: Finding[] = [];
  for (const { dir, prefix } of SCAN_ROOTS) {
    for (const file of walk(dir)) {
      const rel = `${prefix}/${path.relative(dir, file).split(path.sep).join('/')}`;
      const src = stripComments(fs.readFileSync(file, 'utf8'));
      const isService = /\/(services|api)\//.test(rel);

      for (const m of src.matchAll(JSX_TEXT)) {
        const text = m[1].trim().replace(/\s+/g, ' ');
        if (text.length < 3 || !/[A-Za-zÄÖÜäöü]{3}/.test(text)) continue;
        if (CODE_FRAGMENT.test(text)) continue;
        findings.push({ file: rel, line: lineOf(src, m.index ?? 0), kind: 'jsx-text', text });
      }
      for (const m of src.matchAll(VISIBLE_PROP)) {
        findings.push({ file: rel, line: lineOf(src, m.index ?? 0), kind: m[1], text: m[3] });
      }
      if (isService) {
        for (const m of src.matchAll(LITERAL_ERROR)) {
          findings.push({ file: rel, line: lineOf(src, m.index ?? 0), kind: 'literal-error', text: m[2] });
        }
      }
    }
  }
  return findings;
}

// Line numbers shift constantly; the allowlist keys on file + kind + text.
const keyOf = (f: Finding): string => `${f.file}::${f.kind}::${f.text}`;

describe('i18n hardcoded-string ratchet', () => {
  const findings = collect();
  const allowed = new Set<string>(allowlist as string[]);

  // Without this, a broken walk() over any one of the three roots would silently
  // make the guard vacuously green for that tier — and the failure would surface
  // misleadingly via the "erledigte Einträge" test below instead of pointing at
  // the real cause: a broken scan, not a finished cleanup. Thresholds are well
  // below the actual file counts (core ~205, premium ~27) so normal churn
  // doesn't make this flaky. enterprise/frontend/src dropped from ~4 files to
  // just index.ts (an intentionally empty barrel) once its three dead-code
  // placeholders were removed in TF-671, so its threshold only guards against
  // a totally broken scan (0 files), not against churn.
  const SANITY_ROOTS: Array<{ label: string; root: string; min: number }> = [
    { label: 'core/frontend/src', root: SCAN_ROOTS[0].dir, min: 50 },
    { label: 'premium/frontend/src', root: SCAN_ROOTS[1].dir, min: 15 },
    { label: 'enterprise/frontend/src', root: SCAN_ROOTS[2].dir, min: 0 },
  ];

  for (const { label, root, min } of SANITY_ROOTS) {
    // Skip (not fail) when the tier root is absent: the public mirror ships
    // core/ only (git subtree split --prefix=core), so a missing premium/ or
    // enterprise/ root is a Core-only checkout, not a broken scan.
    (fs.existsSync(root) ? it : it.skip)(`scannt überhaupt Dateien (sanity check): ${label}`, () => {
      const count = walk(root).length;
      if (count <= min) {
        throw new Error(
          `walk() fand nur ${count} Datei(en) unter ${label} (erwartet: > ${min}). ` +
          `Diese Wurzel liefert keine oder zu wenige Treffer — das deutet auf einen ` +
          `falschen/fehlenden Pfad oder einen kaputten Scan hin, nicht auf erledigte ` +
          `Allowlist-Einträge.`,
        );
      }
    });
  }

  it('keine NEUEN hart codierten Strings', () => {
    const fresh = findings.filter((f) => !allowed.has(keyOf(f)));
    if (fresh.length > 0) {
      const head = fresh.slice(0, 40)
        .map((f) => `  ${f.file}:${f.line} [${f.kind}] ${f.text.slice(0, 80)}`).join('\n');
      const tail = fresh.length > 40 ? `\n  ... (+${fresh.length - 40} weitere)` : '';
      throw new Error(
        `${fresh.length} neue(r) hart codierte(r) String(s). Bitte übersetzen — ` +
        `NICHT der Allowlist hinzufügen:\n${head}${tail}`,
      );
    }
  });

  // The ratchet: entries leave the allowlist, they never come back.
  it('die Allowlist enthält keine erledigten Einträge mehr', () => {
    const live = new Set(findings.map(keyOf));
    // Only judge allowlist entries whose root tier is present in this checkout.
    // In a Core-only mirror checkout, premium/enterprise entries are neither
    // "live" nor "done" — their root simply was not scanned — so they must not
    // be flagged as stale.
    const presentRoots = SCAN_ROOTS
      .filter((r) => fs.existsSync(r.dir))
      .map((r) => r.prefix);
    const stale = Array.from(allowed).filter(
      (k) => !live.has(k) && presentRoots.some((p) => k.startsWith(p)),
    );
    if (stale.length > 0) {
      throw new Error(
        `${stale.length} Allowlist-Eintrag/Einträge sind erledigt und müssen ` +
        `aus i18n-hardcoded-strings.allowlist.json entfernt werden:\n  ${stale.join('\n  ')}`,
      );
    }
  });
});
