/**
 * Guard (EXAMCRAFT-137): Allowlist für `localStorage`-Schlüssel.
 *
 * Seit der Cookie-Session-Umstellung (EXAMCRAFT-126) hält der Browser keine
 * Tokens und kein Profil mehr. Dieser Test liest den Produktivcode und prüft,
 * dass jeder Schlüssel, der per `localStorage.setItem` geschrieben wird
 * (literal oder über eine `const`-Konstante aufgelöst; dynamische Schlüssel
 * schlagen als `<unaufgelöst: …>` fehl), bewusst freigegeben ist, und dass
 * keiner nach Anmeldedaten aussieht. Ein neuer
 * Schlüssel zwingt so zu einer Entscheidung im Review.
 */
import * as fs from 'fs';
import * as path from 'path';

const SRC = path.resolve(__dirname, '..');

// Schlüssel mit Begründung. Neue Einträge brauchen eine Zeile, die erklärt,
// warum der Wert unkritisch ist (keine Anmeldedaten, keine Profildaten).
const ALLOWED_KEYS: Record<string, string> = {
  examcraft_logout_broadcast: 'Cross-Tab-Logout-Signal, nur ein Zeitstempel',
  examcraft_impersonation_expires_at: 'UI-Hinweis für das Impersonation-Banner, nur ein Zeitstempel',
  examcraft_language_pending: 'Sprachwahl vor dem Login',
  examcraft_tf354_privacy_banner_dismissed: 'Banner weggeklickt',
  'examcraft.sidebar.isOpen': 'UI-Zustand der Seitenleiste',
  'examcraft.sidebar.expandedGroups': 'UI-Zustand der Seitenleiste',
  examcraft_docs_page_size: 'Seitengrösse der Dokumentenliste',
  examcraft_docs_view: 'Ansicht der Dokumentenliste',
  'examcraft.help.tab': 'Zuletzt gewählter Hilfe-Tab',
  'examcraft.help.seenTracks': 'Gesehene Hilfe-Touren',
  ec_onboarding_modal_dismissed: 'Onboarding-Dialog weggeklickt',
  examcraft_user_features: 'Feature-Cache (Tarif-Features plus numerische userId zur Cache-Zuordnung, keine Anmeldedaten)',
  'competencyFrameworks.filter': 'Filterauswahl',
  'tagSettings.filter': 'Filterauswahl',
};

const FORBIDDEN_NAME = /token|jwt|bearer|password|passwort|secret|credential|cookie|session_id|refresh/i;

const listSourceFiles = (dir: string): string[] =>
  fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      return entry.name === '__tests__' || entry.name === 'node_modules' ? [] : listSourceFiles(full);
    }
    return /\.(ts|tsx)$/.test(entry.name) && !/\.(test|spec)\.(ts|tsx)$/.test(entry.name) ? [full] : [];
  });

/** Schlüssel aller `localStorage.setItem(<Literal|Konstante>, …)`-Aufrufe. */
const collectWrittenKeys = (): Array<{ file: string; key: string }> => {
  const found: Array<{ file: string; key: string }> = [];
  for (const file of listSourceFiles(SRC)) {
    const source = fs.readFileSync(file, 'utf8');
    const constants = new Map(
      [...source.matchAll(/const\s+([A-Z_][A-Z0-9_]*)\s*=\s*['"]([^'"]+)['"]/g)].map((m) => [m[1], m[2]]),
    );
    for (const call of source.matchAll(/localStorage\.setItem\(\s*([^,)]+?)\s*,/g)) {
      const arg = call[1];
      const literal = /^['"]([^'"]+)['"]$/.exec(arg);
      const key = literal ? literal[1] : constants.get(arg) ?? `<unaufgelöst: ${arg}>`;
      found.push({ file: path.relative(SRC, file), key });
    }
  }
  return found;
};

describe('localStorage-Schlüssel', () => {
  const written = collectWrittenKeys();

  it('findet die bekannten Schreibzugriffe (Schutz gegen einen leeren Scan)', () => {
    const keys = written.map((w) => w.key);
    expect(keys).toEqual(
      expect.arrayContaining(['examcraft_logout_broadcast', 'examcraft_impersonation_expires_at']),
    );
  });

  it('schreibt nur freigegebene Schlüssel', () => {
    const unknown = written.filter((w) => !(w.key in ALLOWED_KEYS));
    expect(unknown).toEqual([]);
  });

  it('hat keinen Schlüssel, der nach Anmeldedaten aussieht', () => {
    const suspicious = [...new Set([...written.map((w) => w.key), ...Object.keys(ALLOWED_KEYS)])].filter(
      (key) => FORBIDDEN_NAME.test(key),
    );
    expect(suspicious).toEqual([]);
  });

  it('führt keine verwaisten Einträge in der Allowlist', () => {
    const used = new Set(written.map((w) => w.key));
    const orphaned = Object.keys(ALLOWED_KEYS).filter((key) => !used.has(key));
    expect(orphaned).toEqual([]);
  });

  it('schreibt keine alten Token-Schlüssel mehr', () => {
    const all = fs
      .readdirSync(SRC, { recursive: true } as never)
      .map(String)
      .filter((f) => /\.(ts|tsx)$/.test(f) && !/(__tests__|\.test\.|\.spec\.)/.test(f))
      .map((f) => fs.readFileSync(path.join(SRC, f), 'utf8'))
      .join('\n');
    expect(all).not.toMatch(/examcraft_(access|refresh)_token|examcraft_user['"]/);
  });
});
