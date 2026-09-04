import * as fs from 'fs';
import * as path from 'path';

/**
 * Enforces the boundary documented in apiDetail.ts's doc comment: it exists
 * for the Tags API's German prose specifically, not as a general-purpose
 * "show whatever the backend said" helper. Without this test, that boundary
 * lived in a comment only — nothing stopped a future call site from
 * importing `apiDetail` for an endpoint that answers in English, silently
 * reintroducing exactly the raw-text leak TF-671 removed.
 *
 * If this test fails because you added a legitimate new call site, that's
 * the point: update ALLOWED_IMPORTERS deliberately, with the same
 * "does this endpoint actually answer in the user's language?" justification
 * apiDetail.ts's doc comment gives for the existing three.
 */

// Same fixed-prefix pattern as i18n-hardcoded-strings.test.ts, and for the
// same reason: `core/` is mirrored standalone to the public repo, where
// `premium/` and `enterprise/` don't exist — a path anchored to a computed
// repo root would break there. See that file's docblock for the full story.
const CORE_SRC_DIR = path.resolve(__dirname, '../..');
const MONOREPO_ROOT = path.resolve(CORE_SRC_DIR, '../../..');
const SOURCE_EXT = /\.(ts|tsx)$/;
const SKIP_DIRS = new Set(['node_modules', 'build', 'dist', 'coverage']);

const SCAN_ROOTS: Array<{ dir: string; prefix: string }> = [
  { dir: CORE_SRC_DIR, prefix: 'core/frontend/src' },
  { dir: path.resolve(MONOREPO_ROOT, 'premium/frontend/src'), prefix: 'premium/frontend/src' },
  { dir: path.resolve(MONOREPO_ROOT, 'enterprise/frontend/src'), prefix: 'enterprise/frontend/src' },
];

const ALLOWED_IMPORTERS = new Set([
  'core/frontend/src/components/tags/TagCreateForm.tsx',
  'core/frontend/src/pages/TagSettingsPage.tsx',
  // The apiDetail.ts module itself and its own tests import/re-export it.
  'core/frontend/src/errors/apiDetail.ts',
  'core/frontend/src/errors/index.ts',
  'core/frontend/src/errors/__tests__/apiDetail.test.ts',
  'core/frontend/src/errors/__tests__/apiDetail.boundary.test.ts',
]);

function walk(dir: string, out: string[] = []): string[] {
  if (!fs.existsSync(dir)) return out;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (SKIP_DIRS.has(entry.name)) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(full, out);
    else if (SOURCE_EXT.test(entry.name)) out.push(full);
  }
  return out;
}

it('apiDetail wird nur an den dokumentierten Stellen importiert', () => {
  // Matches an actual `import { apiDetail, ... } from '...'` (or the
  // equivalent `export { apiDetail } from './apiDetail'` re-export) —
  // deliberately NOT a bare `/apiDetail/` substring match, which would also
  // trip on this file's own doc comments and on the cross-reference notes
  // in AppError.ts / AppErrorCode.i18n.test.ts that merely mention the name.
  const IMPORT_APIDETAIL = /\b(?:import|export)\s*\{[^}]*\bapiDetail\b[^}]*\}\s*from/;
  const offenders: string[] = [];

  for (const { dir, prefix } of SCAN_ROOTS) {
    for (const file of walk(dir)) {
      const rel = `${prefix}/${path.relative(dir, file).split(path.sep).join('/')}`;
      if (ALLOWED_IMPORTERS.has(rel)) continue;
      const src = fs.readFileSync(file, 'utf8');
      if (IMPORT_APIDETAIL.test(src)) {
        offenders.push(rel);
      }
    }
  }

  if (offenders.length > 0) {
    throw new Error(
      `apiDetail() wird an unerwarteten Stellen referenziert: ${offenders.join(', ')}. ` +
      'apiDetail ist nur für Endpunkte gedacht, die bereits in der Sprache der ' +
      'Nutzenden antworten (aktuell: Tags-API). Für alles andere translateError() ' +
      'verwenden — siehe errors/apiDetail.ts. Wenn diese neue Stelle wirklich ' +
      'gehört, ALLOWED_IMPORTERS bewusst erweitern.',
    );
  }
});
