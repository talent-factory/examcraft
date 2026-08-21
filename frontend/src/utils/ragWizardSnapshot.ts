/**
 * Persistierter Konfigurationsstand des RAG-Fragengenerierungs-Wizards (TF-608).
 *
 * Der Wizard selbst ist eine Premium-Komponente; Form und Absicherung des
 * Snapshots liegen hier, weil der Core ohnehin die RAG-Typen und den
 * GenerationTasksContext hält — und weil die Prüflogik so von der CI-Suite
 * abgedeckt wird.
 */

import type { PromptSelection, RAGExamRequest } from '../types';
// TagValue lives with the tags API, not in ../types (it is re-exported from
// lib.ts for tier packages).
import type { TagValue } from '../api/tagsApi';

/** Schlüssel des Snapshots im sessionStorage (siehe `sessionSnapshot.ts`). */
export const RAG_WIZARD_SNAPSHOT_KEY = 'ragExamWizard';
/** Bei jeder Formänderung erhöhen — alte Snapshots werden dann verworfen
 *  statt halb eingelesen. */
export const RAG_WIZARD_SNAPSHOT_VERSION = 1;
/**
 * Letzter `activeStep`-Index (0-basiert), den ein Snapshot wiederherstellen
 * darf. Der letzte Wizard-Schritt (`activeStep === 3`, UI-Label `step4Label`
 * / "Prüfungsfragen generiert") ist die Ergebnisansicht — die hängt an einem
 * generierten Prüfungsobjekt, das nicht im sessionStorage liegt (zu gross,
 * und die Fragen stehen ohnehin in der Prüf-Queue).
 *
 * (Nicht mit dem 1-basierten "Schritt 3" in `RAGExamCreator.tsx` verwechseln
 * — das bezeichnet dort denselben `activeStep === 2`, die Kontext-Vorschau.)
 */
export const MAX_RESTORABLE_WIZARD_STEP = 2;

/**
 * `contextPreview` fehlt bewusst: Die Vorschau kann veralten und wird bei
 * Rückkehr auf Schritt 3 frisch geladen. Der Kompetenzrahmen reist nur als ID
 * mit und wird aufgelöst, sobald die Rahmenliste geladen ist.
 */
export interface RAGWizardSnapshot {
  activeStep: number;
  selectedDocs: number[];
  ragRequest: RAGExamRequest;
  promptSelection: PromptSelection;
  templateVariables: Record<string, Record<string, any>>;
  selectedTags: TagValue[];
  frameworkId: number | null;
  competenciesOverride: string;
  /**
   * Der Stand stammt aus einer bereits gestarteten Generierung, nicht aus einer
   * unterbrochenen Konfiguration. Der Wizard behält die Einstellungen danach
   * absichtlich — daran hängt "Schnelle Wiederholung" —, also ist ein
   * vorbelegter Wizard hier erwartbar und der Wiederherstellungs-Hinweis
   * überflüssig.
   */
  generationStarted: boolean;
}

/**
 * Härtet einen gelesenen Snapshot gegen Formdrift ab. Der sessionStorage kann
 * einen Eintrag aus einer früheren Sitzung enthalten, dessen Struktur nicht mehr
 * passt; ein unvollständiger Snapshot darf den Wizard nicht in einen Zustand
 * bringen, aus dem heraus er abstürzt. Übernommen wird nur, was die erwartete
 * Form hat — für alles andere gilt der Default der Komponente.
 *
 * Gibt `null` zurück, wenn nichts Verwertbares übrig bleibt; die Komponente
 * unterscheidet daran "nichts wiederhergestellt" von "Stand wiederhergestellt".
 */
export function sanitizeWizardSnapshot(
  raw: unknown
): Partial<RAGWizardSnapshot> | null {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
  const snapshot = raw as Partial<RAGWizardSnapshot>;
  const result: Partial<RAGWizardSnapshot> = {};

  if (typeof snapshot.activeStep === 'number' && Number.isFinite(snapshot.activeStep)) {
    result.activeStep = Math.min(
      Math.max(Math.trunc(snapshot.activeStep), 0),
      MAX_RESTORABLE_WIZARD_STEP
    );
  }
  if (Array.isArray(snapshot.selectedDocs)) {
    result.selectedDocs = snapshot.selectedDocs.filter(
      (id): id is number => typeof id === 'number'
    );
  }
  if (snapshot.ragRequest && typeof snapshot.ragRequest === 'object') {
    // Container-Form allein reicht hier nicht: `RAGExamCreator.tsx` konsumiert
    // `restored?.ragRequest?.topic?.trim()` direkt — ein `topic` aus einer
    // inkompatiblen Vorversion, das kein String ist, würde dort mit einer
    // TypeError crashen statt (wie der Rest dieser Funktion) defensiv leer
    // zu bleiben. Nur dieses eine konsumierte Feld wird deshalb gehärtet;
    // die übrigen Felder von `ragRequest` bleiben ungeprüft durchgereicht
    // (siehe Modul-Docstring: "Formdrift" ist hier bewusst nicht vollständig
    // abgedeckt).
    const candidate = { ...snapshot.ragRequest } as Partial<RAGExamRequest>;
    if ('topic' in candidate && typeof candidate.topic !== 'string') {
      delete candidate.topic;
    }
    result.ragRequest = candidate as RAGExamRequest;
  }
  if (snapshot.promptSelection && typeof snapshot.promptSelection === 'object') {
    result.promptSelection = snapshot.promptSelection;
  }
  if (snapshot.templateVariables && typeof snapshot.templateVariables === 'object') {
    result.templateVariables = snapshot.templateVariables;
  }
  if (Array.isArray(snapshot.selectedTags)) {
    result.selectedTags = snapshot.selectedTags;
  }
  // `frameworkId` ist im vollen Typ bewusst `number | null` (explizit "kein
  // Framework gewählt" vs. "Feld fehlt"). Ein gespeichertes `null` hier mit
  // durchreichen, statt es wie "Feld fehlt" zu behandeln, damit Typ-Kontrakt
  // und Sanitizer nicht auseinanderlaufen.
  if (typeof snapshot.frameworkId === 'number' || snapshot.frameworkId === null) {
    result.frameworkId = snapshot.frameworkId;
  }
  if (typeof snapshot.competenciesOverride === 'string') {
    result.competenciesOverride = snapshot.competenciesOverride;
  }
  if (typeof snapshot.generationStarted === 'boolean') {
    result.generationStarted = snapshot.generationStarted;
  }

  return Object.keys(result).length > 0 ? result : null;
}
