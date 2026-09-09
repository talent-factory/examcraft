/**
 * Ratchet guard against hardcoded user-facing strings (TF-671, TF-772).
 *
 * Why a ratchet and not a clean gate: TF-671 fixed the foundation and the most
 * visible components, but the bulk of the service layer remains. A test that
 * only fails on NEW violations can land now instead of waiting for the whole
 * cleanup — and the allowlist doubles as the machine-readable remainder list.
 * Entries are only ever removed, never added: that is the whole point.
 *
 * When this test fails on your change, translate the string. Do not add it to
 * the allowlist, and do not regenerate the allowlist to make it go away.
 *
 * The allowlist is GENERATED. Never edit it by hand, never merge it by hand:
 *
 *     git checkout --ours src/__tests__/i18n-hardcoded-strings.allowlist.json
 *     bun run scripts/regenerate-i18n-allowlist.ts
 *     git add src/__tests__/i18n-hardcoded-strings.allowlist.json
 *
 * The scan lives in `scripts/i18n-hardcoded-strings-scan.ts` so this guard and
 * the regenerator cannot drift apart; the "tier absence tolerance" and "path
 * anchoring" notes that used to sit here are documented there, next to the
 * code they constrain.
 *
 * Permanent exceptions: seven allowlist entries from BillingPage.tsx (the CHF
 * amounts and the Free/Starter/Professional/Enterprise tier names) are not
 * remaining cleanup work and stay indefinitely. They are listed with their
 * rationale as `PERMANENT_EXCEPTIONS` in the scan module, and asserted below so
 * a regeneration cannot quietly drop them.
 *
 * ---------------------------------------------------------------------------
 * Error-key convention (TF-772/TF-773) — read this before adding an error key
 * ---------------------------------------------------------------------------
 *
 * The backend answers with a machine-readable code alongside the human text
 * (ADR 0005, `core/backend/errors.py`):
 *
 *     { "detail": "Ein Tag mit diesem Namen existiert bereits.",
 *       "error_code": "documents_tag_exists",
 *       "error_params": { "name": "Mathematik" } }
 *
 * `error_code` is verbatim the key in `core/backend/locales/t.{de,en,fr,it}
 * .json` — flat snake_case with a domain prefix. The frontend adopts that
 * identity rather than inventing a parallel space:
 *
 *     frontend key = "errors." + error_code      e.g. errors.documents_tag_exists
 *
 * No mapping table, no rewrite into dot notation. Rules that follow from it:
 *
 * 1. Sort new keys alphabetically into the `errors` block of all four locales.
 *    Because the backend prefixes (`auth_`, `documents_`, `rbac_`, …) cluster
 *    alphabetically, work split across branches lands in disjoint line ranges
 *    and merges without conflicts.
 * 2. Every key exists in de, en, fr AND it. Not optional.
 * 3. Interpolation differs between the two systems: the backend writes
 *    `%{name}`, i18next writes `{{name}}`. Rewrite when copying a text over.
 * 4. Existing NESTED keys (`errors.help.*`, `errors.rag.*`, …) are NOT migrated
 *    to the flat form here. Their fate belongs to TF-775.
 *
 * ---------------------------------------------------------------------------
 * Reach of this scan — what it does not see, and why
 * ---------------------------------------------------------------------------
 *
 * FIXED in TF-772: `literal-error` used to match only a literal sitting
 * directly inside `new Error(...)`, which saw 15 of 95 throw sites in the
 * service directories. It now reads the balanced argument and reports every
 * string literal inside it, covering the two dominant shapes
 * (`new Error(detail || 'text')` and `new Error(helper(detail, 'text'))`) plus
 * `reject(new Error('text'))`. `i18n-hardcoded-strings.regex.test.ts` pins one
 * example per form.
 *
 * DELIBERATE GAP 1 — string arguments to arbitrary function calls. The scan
 * reads JSX text nodes and a fixed whitelist of visible props (label,
 * placeholder, title, aria-label, helperText, alt). Prose passed as an argument
 * to some other function is invisible unless that function is `Error`.
 * `componentLoader.tsx` used to be the live example — it passed English prose
 * into `withFeatureGate(...)`, which `UpgradePrompt.tsx` rendered verbatim;
 * that case was fixed by routing i18n keys through instead. Closing the gap
 * itself needs an AST-based scan, which is out of proportion to what it would
 * catch today. Left open knowingly.
 *
 * DELIBERATE GAP 2 — `setError(err.message)`. Components still do
 * `setError(err instanceof Error ? err.message : …)` or `alert(err.message)`,
 * which is exactly what `translateError()` exists to replace. There is no
 * string literal involved: the message is a runtime value. A literal scanner
 * structurally cannot see this class, so no regex change will help. It is
 * tracked as TF-772 Teil A instead. Do not read a green run here as evidence
 * that no raw error text reaches the UI.
 *
 * DELIBERATE GAP 3 — `literal-error` is restricted to `services/` and `api/`.
 * Throws elsewhere are overwhelmingly developer errors that stay English by the
 * TF-295 boundary (`useAuth must be used within an AuthProvider`,
 * `Not authenticated`). Scanning components would park ~15 of those in the
 * allowlist permanently and destroy the number TF-772 measures progress by.
 * The cost is one user-facing literal the scan cannot see:
 * `ResendVerificationButton.tsx` (`Failed to resend verification email`). It
 * is real TF-772 work; it is just tracked by the ticket rather than by this
 * guard. (This PR's own `DocumentUpload.tsx`/`DocumentLibrary.tsx` changes
 * removed the two other literals that used to be listed here — `Upload
 * cancelled` became the `UploadCancelled` sentinel, and the
 * `Document processing failed…`/`…timeout after…` strings went with the
 * deleted dead `waitForDocumentProcessing` function.)
 */
import {
  PERMANENT_EXCEPTIONS,
  SCAN_ROOTS,
  collect,
  keyOf,
  walk,
} from '../../scripts/i18n-hardcoded-strings-scan';

import * as fs from 'fs';

import allowlist from './i18n-hardcoded-strings.allowlist.json';

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

  // TF-772 measures progress by allowlist size, and its target value is these
  // seven entries — not zero. Without this assertion, "shrink the allowlist"
  // reads as an invitation to translate "CHF 0" into four identical strings.
  it('die sieben Dauerausnahmen stehen noch in der Allowlist', () => {
    const missing = PERMANENT_EXCEPTIONS.filter((k) => !allowed.has(k));
    if (missing.length > 0) {
      throw new Error(
        `${missing.length} Dauerausnahme(n) fehlen in der Allowlist. Sie sind ` +
        `bewusste Ausnahmen (Preise und Tarifnamen, siehe PERMANENT_EXCEPTIONS ` +
        `in scripts/i18n-hardcoded-strings-scan.ts) und dürfen nicht übersetzt ` +
        `werden:\n  ${missing.join('\n  ')}`,
      );
    }
  });
});
