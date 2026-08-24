import fs from 'fs';
import path from 'path';

/**
 * TF-626-Review: `types/index.ts` re-exports several modules via
 * `export * from './x'`. TypeScript does NOT resolve a name conflict
 * between two `export *` sources with an error — the colliding name
 * simply vanishes silently from the barrel (no compiler diagnostic at
 * the point of conflict, only a later "no exported member" if and when
 * someone tries to import it). Exactly that happened with
 * `SupportedLanguage` (collided between auth.ts and document.ts, see
 * PR #191 / TF-626) and was only discovered through an unrelated
 * compile error.
 *
 * `rbac.ts` already sidesteps this deliberately via a selective
 * `export type { ... }` (see the comment there: "Selective export to
 * avoid conflicts with auth.ts") — this test makes the same guarantee
 * machine-checkable for the remaining wildcard-re-exported modules
 * instead of only documenting it. It doesn't replace a real typecheck
 * (which needs the actual barrel resolution), but is pure text
 * analysis — fast, no `ts-morph`/compiler-API dependency, and fails for
 * any new name collision across these files.
 */

const TYPES_DIR = path.join(__dirname, '..');

// Must match the `export * from './x'` lines in `types/index.ts`.
const WILDCARD_EXPORTED_MODULES = [
  'auth',
  'document',
  'exam',
  'review',
  'prompt',
  'competencyFramework',
];

// Top-level `export interface X`, `export type X`, `export enum X`,
// `export const X`, `export class X`, `export function X` — deliberately
// top-level only (not `export default`, which doesn't collide by name).
const EXPORT_NAME_PATTERN =
  /^export\s+(?:interface|type|enum|class|function|const|abstract class)\s+([A-Za-z_$][A-Za-z0-9_$]*)/gm;

function extractExportedNames(moduleName: string): string[] {
  const filePath = path.join(TYPES_DIR, `${moduleName}.ts`);
  const content = fs.readFileSync(filePath, 'utf-8');
  const names: string[] = [];
  let match: RegExpExecArray | null;
  // Regex has global state — reset before each file, no shared call
  // pattern across iterations.
  EXPORT_NAME_PATTERN.lastIndex = 0;
  while ((match = EXPORT_NAME_PATTERN.exec(content)) !== null) {
    names.push(match[1]);
  }
  return names;
}

describe('types/index.ts barrel — keine stillen export*-Kollisionen (TF-626-Review)', () => {
  it('exportiert jeder wildcard-re-exportierte Name aus genau einem Modul', () => {
    const owners = new Map<string, string[]>();

    for (const moduleName of WILDCARD_EXPORTED_MODULES) {
      for (const name of extractExportedNames(moduleName)) {
        const existing = owners.get(name) ?? [];
        existing.push(moduleName);
        owners.set(name, existing);
      }
    }

    const collisions = Array.from(owners.entries()).filter(
      ([, modules]) => modules.length > 1
    );

    if (collisions.length > 0) {
      const details = collisions
        .map(([name, modules]) => `  - "${name}" in: ${modules.join(', ')}`)
        .join('\n');
      throw new Error(
        `Namenskollision(en) zwischen wildcard-re-exportierten Type-Modulen ` +
          `gefunden — TypeScripts "export *" wuerde den betroffenen Namen ` +
          `lautlos aus dem Barrel entfernen (siehe SupportedLanguage-Bug, ` +
          `TF-626):\n${details}\n\n` +
          `Fix: einen der beiden Namen umbenennen (bevorzugt, siehe ` +
          `SupportedLanguageOption-Praezedenzfall in document.ts), oder das ` +
          `betroffene Modul auf selektive \`export type { ... }\` umstellen ` +
          `(siehe rbac.ts in types/index.ts).`
      );
    }
  });

  it('deckt genau die in types/index.ts per export* re-exportierten Module ab', () => {
    // Fail-safe: if someone extends types/index.ts with another
    // `export * from` without updating this list, the test should flag
    // it instead of staying silent (it would otherwise not check the
    // new file at all).
    const indexContent = fs.readFileSync(
      path.join(TYPES_DIR, 'index.ts'),
      'utf-8'
    );
    const wildcardModulesInIndex = Array.from(
      indexContent.matchAll(/export\s+\*\s+from\s+'\.\/([^']+)'/g)
    ).map((m) => m[1]);

    expect(new Set(WILDCARD_EXPORTED_MODULES)).toEqual(
      new Set(wildcardModulesInIndex)
    );
  });
});
