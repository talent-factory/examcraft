/**
 * Regenerates `src/__tests__/i18n-hardcoded-strings.allowlist.json` (TF-772).
 *
 *     bun run scripts/regenerate-i18n-allowlist.ts
 *     bun run scripts/regenerate-i18n-allowlist.ts --check
 *
 * The allowlist is generated, never hand-edited and never hand-merged. When two
 * branches both touch it, the resolution is:
 *
 *     git checkout --ours src/__tests__/i18n-hardcoded-strings.allowlist.json
 *     bun run scripts/regenerate-i18n-allowlist.ts
 *     git add src/__tests__/i18n-hardcoded-strings.allowlist.json
 *
 * That recipe is why this script exists: TF-772 splits the cleanup across four
 * branches that all shrink this file, and a three-way text merge of a sorted
 * array produces plausible-looking garbage.
 *
 * Regenerating is not the way to silence a guard failure. A NEW hardcoded
 * string must be translated; running this script would simply freeze it in.
 * Run it after removing strings, and after a merge.
 */
import * as fs from 'fs';
import * as path from 'path';

import { SCAN_ROOTS, allowlistFor, collect } from './i18n-hardcoded-strings-scan';

const ALLOWLIST_PATH = path.resolve(
  __dirname,
  '../src/__tests__/i18n-hardcoded-strings.allowlist.json',
);

/**
 * A Core-only checkout (the public mirror ships `core/` alone) cannot see
 * premium/ or enterprise/. Regenerating there would silently delete every
 * premium and enterprise entry and present it as progress, so refuse instead.
 */
function assertAllTiersPresent(): void {
  const missing = SCAN_ROOTS.filter((r) => !fs.existsSync(r.dir)).map((r) => r.prefix);
  if (missing.length > 0) {
    console.error(
      `Refusing to regenerate: ${missing.join(', ')} not present in this checkout.\n` +
        'Their allowlist entries would be dropped as if they had been cleaned up.\n' +
        'Run this from a full monorepo checkout.',
    );
    process.exit(2);
  }
}

function main(): void {
  assertAllTiersPresent();

  const next = allowlistFor(collect());
  const serialised = `${JSON.stringify(next, null, 2)}\n`;

  const previous: string[] = fs.existsSync(ALLOWLIST_PATH)
    ? (JSON.parse(fs.readFileSync(ALLOWLIST_PATH, 'utf8')) as string[])
    : [];

  if (process.argv.includes('--check')) {
    const current = fs.existsSync(ALLOWLIST_PATH)
      ? fs.readFileSync(ALLOWLIST_PATH, 'utf8')
      : '';
    if (current !== serialised) {
      console.error(
        'Allowlist is out of date. Run: bun run scripts/regenerate-i18n-allowlist.ts',
      );
      process.exit(1);
    }
    console.log(`Allowlist up to date (${next.length} entries).`);
    return;
  }

  fs.writeFileSync(ALLOWLIST_PATH, serialised);

  const before = new Set(previous);
  const after = new Set(next);
  const added = next.filter((k) => !before.has(k));
  const removed = previous.filter((k) => !after.has(k));

  console.log(`Allowlist: ${previous.length} → ${next.length} entries`);
  console.log(`  added:   ${added.length}`);
  console.log(`  removed: ${removed.length}`);
  for (const key of removed) console.log(`    - ${key}`);
}

main();
