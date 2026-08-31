/**
 * Persisted configuration state of the RAG question generation wizard (TF-608).
 *
 * The wizard itself is a Premium component; the snapshot's shape and
 * validation live here because core already holds the RAG types and the
 * GenerationTasksContext — and because that keeps the validation logic
 * covered by the CI suite.
 */

import type { PromptSelection, RAGExamRequest } from '../types';
// TagValue lives with the tags API, not in ../types (it is re-exported from
// lib.ts for tier packages).
import type { TagValue } from '../api/tagsApi';

/** Key of the snapshot in sessionStorage (see `sessionSnapshot.ts`). */
export const RAG_WIZARD_SNAPSHOT_KEY = 'ragExamWizard';
/** Bump on every form change — older snapshots are then discarded instead
 *  of being read in half-restored.
 *
 *  2 (TF-719): `activeStep` is no longer the sole source for the entry step —
 *  a `?step=` in the URL beats the snapshot, and the restored step is
 *  additionally checked against its reachability (no step 1 without a
 *  document selection). A version 1 snapshot may carry a step that the new
 *  check resolves differently; discarding it is more honest than restoring
 *  it half-way. */
export const RAG_WIZARD_SNAPSHOT_VERSION = 2;
/**
 * Last `activeStep` index (0-based) a snapshot is allowed to restore. The
 * final wizard step (`activeStep === 3`, UI label `step4Label` /
 * "Prüfungsfragen generiert") is the results view — it depends on a
 * generated exam object that isn't in sessionStorage (too large, and the
 * questions already live in the review queue anyway).
 *
 * (Not to be confused with the 1-based "step 3" in `RAGExamCreator.tsx`
 * — that refers to the same `activeStep === 2`, the context analysis, there.)
 */
export const MAX_RESTORABLE_WIZARD_STEP = 2;

/**
 * `contextPreview` is deliberately absent: the preview can go stale and is
 * freshly loaded again when returning to step 3. The competency framework
 * only travels as an ID and is resolved once the framework list is loaded.
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
   * The state stems from a generation that has already been started, not
   * from an interrupted configuration. The wizard deliberately keeps the
   * settings afterwards — "quick repeat" depends on that — so a
   * pre-populated wizard here is expected and the restoration hint is
   * superfluous.
   */
  generationStarted: boolean;
}

/**
 * Hardens a read snapshot against shape drift. sessionStorage may hold an
 * entry from an earlier session whose structure no longer fits; an
 * incomplete snapshot must not put the wizard into a state it can crash
 * from. Only what has the expected shape is adopted — everything else
 * falls back to the component's default.
 *
 * Returns `null` when nothing usable is left; the component uses that to
 * distinguish "nothing restored" from "state restored".
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
    // Container shape alone isn't enough here: `RAGExamCreator.tsx`
    // consumes `restored?.ragRequest?.topic?.trim()` directly — a `topic`
    // from an incompatible older version that isn't a string would crash
    // there with a TypeError instead of (like the rest of this function)
    // staying defensively empty. Only this one consumed field is
    // therefore hardened; the remaining fields of `ragRequest` are passed
    // through unchecked (see the module docstring: "shape drift" is
    // deliberately not fully covered here).
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
  // `frameworkId` is deliberately `number | null` in the full type
  // (explicitly "no framework selected" vs. "field missing"). A stored
  // `null` is passed through here rather than treated as "field missing",
  // so the type contract and the sanitizer don't drift apart.
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
