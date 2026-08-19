import fs from 'fs';
import path from 'path';

/**
 * TF-626-Review: `types/index.ts` re-exportiert mehrere Module per
 * `export * from './x'`. TypeScript loest einen Namenskonflikt zwischen zwei
 * `export *`-Quellen NICHT mit einem Fehler auf — der kollidierende Name
 * verschwindet einfach lautlos aus dem Barrel (kein Compiler-Diagnostic am
 * Ort des Konflikts, nur ein spaeteres "no exported member", falls und wenn
 * jemand versucht, ihn zu importieren). Genau das ist bei `SupportedLanguage`
 * passiert (kollidierte zwischen auth.ts und document.ts, siehe PR #191 /
 * TF-626) und wurde erst durch einen zufaelligen Compile-Fehler entdeckt.
 *
 * `rbac.ts` umgeht das bereits bewusst per selektivem `export type { ... }`
 * (siehe Kommentar dort: "Selective export to avoid conflicts with
 * auth.ts") — dieser Test macht dieselbe Garantie fuer die verbleibenden,
 * per Wildcard re-exportierten Module maschinell pruefbar, statt sie nur zu
 * dokumentieren. Er ersetzt keinen echten Typecheck (der die tatsaechliche
 * Barrel-Aufloesung braucht), ist aber eine reine Textanalyse — schnell,
 * ohne `ts-morph`/Compiler-API-Abhaengigkeit, und faellt fuer jede neue
 * Namenskollision unter denselben Dateien rot.
 */

const TYPES_DIR = path.join(__dirname, '..');

// Muss mit den `export * from './x'`-Zeilen in `types/index.ts` uebereinstimmen.
const WILDCARD_EXPORTED_MODULES = [
  'auth',
  'document',
  'exam',
  'review',
  'prompt',
  'competencyFramework',
];

// Top-level `export interface X`, `export type X`, `export enum X`,
// `export const X`, `export class X`, `export function X` — bewusst nur
// Top-level (kein `export default`, das kollidiert nicht namentlich).
const EXPORT_NAME_PATTERN =
  /^export\s+(?:interface|type|enum|class|function|const|abstract class)\s+([A-Za-z_$][A-Za-z0-9_$]*)/gm;

function extractExportedNames(moduleName: string): string[] {
  const filePath = path.join(TYPES_DIR, `${moduleName}.ts`);
  const content = fs.readFileSync(filePath, 'utf-8');
  const names: string[] = [];
  let match: RegExpExecArray | null;
  // Regex hat globalen State — pro Datei einen frischen Aufruf, kein
  // gemeinsames Aufrufmuster ueber Iterationen hinweg.
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
    // Fail-safe: wenn jemand types/index.ts um ein weiteres `export * from` erweitert,
    // ohne diese Liste nachzuziehen, soll der Test das melden statt still zu
    // schweigen (er wuerde die neue Datei sonst nicht mitpruefen).
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
