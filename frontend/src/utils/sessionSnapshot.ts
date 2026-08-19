/**
 * Versionierte sessionStorage-Snapshots (TF-608).
 *
 * Gedacht für flüchtigen UI-Zustand, der einen Seitenwechsel überleben soll,
 * aber nicht dauerhaft gehört: der Konfigurationsstand eines Wizards, die Liste
 * weggeklickter Hinweise. sessionStorage (nicht localStorage) ist bewusst
 * gewählt — der Zustand gehört zum Tab, nicht zum Gerät, und verschwindet
 * spätestens beim Schliessen.
 *
 * Alle Zugriffe sind fehlertolerant: sessionStorage kann in Safari im privaten
 * Modus, unter strengen Cookie-Policies oder bei vollem Kontingent werfen. Ein
 * kaputter Snapshot darf nie die Seite mitreissen — im Zweifel gilt "kein
 * Snapshot vorhanden".
 */

const KEY_PREFIX = 'examcraft.snapshot.';

interface SnapshotEnvelope<T> {
  version: number;
  savedAt: string;
  data: T;
}

const storageKey = (key: string): string => `${KEY_PREFIX}${key}`;

const getStorage = (): Storage | null => {
  try {
    return window.sessionStorage;
  } catch {
    // Zugriff auf sessionStorage kann selbst schon werfen (Cookie-Policy).
    return null;
  }
};

/**
 * Liest einen Snapshot. Gibt `null` zurück, wenn keiner existiert, die Version
 * nicht passt oder der Eintrag beschädigt ist — in den letzten beiden Fällen
 * wird der Eintrag gleich entfernt, damit er nicht bei jedem Mount erneut
 * geparst wird.
 */
export function readSessionSnapshot<T>(key: string, version: number): T | null {
  const storage = getStorage();
  if (!storage) return null;

  let raw: string | null;
  try {
    raw = storage.getItem(storageKey(key));
  } catch (err) {
    console.warn(`[sessionSnapshot] Snapshot "${key}" konnte nicht gelesen werden:`, err);
    return null;
  }
  if (!raw) return null;

  try {
    const envelope = JSON.parse(raw) as SnapshotEnvelope<T>;
    if (!envelope || typeof envelope !== 'object' || envelope.version !== version) {
      clearSessionSnapshot(key);
      return null;
    }
    return envelope.data;
  } catch (err) {
    // Beschädigter/inkompatibler Eintrag (kaputtes JSON, o.ä.) — wie beim
    // Write-Pfad geloggt, damit ein solcher Fund eine Debugging-Spur
    // hinterlässt statt komplett spurlos zu verschwinden.
    console.warn(`[sessionSnapshot] Snapshot "${key}" ist beschädigt und wird verworfen:`, err);
    clearSessionSnapshot(key);
    return null;
  }
}

/**
 * Schreibt einen Snapshot. Schlägt das fehl (Kontingent, privater Modus), geht
 * nur die Wiederherstellbarkeit verloren — nie der laufende Arbeitsschritt.
 */
export function writeSessionSnapshot<T>(key: string, version: number, data: T): void {
  const storage = getStorage();
  if (!storage) return;

  const envelope: SnapshotEnvelope<T> = {
    version,
    savedAt: new Date().toISOString(),
    data,
  };

  try {
    storage.setItem(storageKey(key), JSON.stringify(envelope));
  } catch (err) {
    console.warn(`[sessionSnapshot] Snapshot "${key}" konnte nicht gespeichert werden:`, err);
  }
}

/**
 * Entfernt ALLE Snapshots dieser Anwendung.
 *
 * Beim Logout aufzurufen: sessionStorage überlebt einen Benutzerwechsel im
 * selben Tab, und die Snapshots enthalten getippten Inhalt (z. B. das
 * Prüfungsthema). Auf einem geteilten Rechner — Schulungsraum, Klassenzimmer —
 * bekäme der nächste Nutzer sonst den Stand seines Vorgängers zu sehen.
 *
 * Bewusst über das Präfix statt über eine Liste bekannter Schlüssel: ein später
 * hinzugefügter Snapshot ist damit automatisch mit abgedeckt und kann nicht
 * vergessen werden.
 */
export function clearAllSessionSnapshots(): void {
  const storage = getStorage();
  if (!storage) return;

  let keys: string[];
  try {
    keys = [];
    for (let index = 0; index < storage.length; index++) {
      const key = storage.key(index);
      if (key && key.startsWith(KEY_PREFIX)) keys.push(key);
    }
    // Erst sammeln, dann löschen — Entfernen während der Iteration verschiebt
    // die Indizes und überspringt Einträge.
  } catch (err) {
    console.warn('[sessionSnapshot] Snapshots konnten nicht aufgelistet werden:', err);
    return;
  }

  // TF-608 Fix: jeder removeItem einzeln behandelt statt in einem
  // gemeinsamen try/catch um die ganze Schleife — sonst bricht EIN
  // fehlschlagender Key (z. B. SecurityError im Private-Modus) die
  // Schleife komplett ab und lässt alle nachfolgenden Snapshots ungelöscht
  // liegen. Das untergräbt genau den Privacy-Zweck dieser Funktion (siehe
  // Docstring oben): der nächste Nutzer auf dem geteilten Rechner sähe
  // trotz "Logout" weiterhin den Stand seines Vorgängers.
  let failures = 0;
  for (const key of keys) {
    try {
      storage.removeItem(key);
    } catch (err) {
      failures += 1;
      console.warn(`[sessionSnapshot] Snapshot "${key}" konnte nicht geleert werden:`, err);
    }
  }
  if (failures > 0) {
    console.warn(
      `[sessionSnapshot] ${failures}/${keys.length} Snapshot(s) konnten beim Logout nicht entfernt werden.`
    );
  }
}

/** Entfernt einen Snapshot. Fehler werden geschluckt. */
export function clearSessionSnapshot(key: string): void {
  const storage = getStorage();
  if (!storage) return;
  try {
    storage.removeItem(storageKey(key));
  } catch {
    // Nichts zu tun — der Snapshot bleibt eben liegen.
  }
}
