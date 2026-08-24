/**
 * Versioned sessionStorage snapshots (TF-608).
 *
 * Meant for transient UI state that should survive a page change but
 * doesn't belong long-term: a wizard's configuration state, the list of
 * dismissed hints. sessionStorage (not localStorage) is deliberately
 * chosen — the state belongs to the tab, not the device, and disappears
 * at the latest when it's closed.
 *
 * All access is fault-tolerant: sessionStorage can throw in Safari private
 * mode, under strict cookie policies, or when the quota is full. A broken
 * snapshot must never take the page down with it — when in doubt, "no
 * snapshot present" applies.
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
    // Accessing sessionStorage itself can already throw (cookie policy).
    return null;
  }
};

/**
 * Reads a snapshot. Returns `null` when none exists, the version doesn't
 * match, or the entry is corrupt — in the latter two cases the entry is
 * removed right away, so it isn't re-parsed on every mount.
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
    // Corrupt/incompatible entry (broken JSON, etc.) — logged like the
    // write path, so a find like this leaves a debugging trail instead of
    // disappearing completely without a trace.
    console.warn(`[sessionSnapshot] Snapshot "${key}" ist beschädigt und wird verworfen:`, err);
    clearSessionSnapshot(key);
    return null;
  }
}

/**
 * Writes a snapshot. If this fails (quota, private mode), only the
 * restorability is lost — never the current work step.
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
 * Removes ALL snapshots of this application.
 *
 * Call this on logout: sessionStorage survives a user switch in the same
 * tab, and the snapshots contain typed content (e.g. the exam topic). On
 * a shared machine — training room, classroom — the next user would
 * otherwise see their predecessor's state.
 *
 * Deliberately keyed off the prefix rather than a list of known keys: a
 * snapshot added later is thus automatically covered and can't be
 * forgotten.
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
    // Collect first, then delete — removing during iteration shifts the
    // indices and skips entries.
  } catch (err) {
    console.warn('[sessionSnapshot] Snapshots konnten nicht aufgelistet werden:', err);
    return;
  }

  // TF-608 fix: each removeItem handled individually instead of in one
  // shared try/catch around the whole loop — otherwise ONE failing key
  // (e.g. SecurityError in private mode) would abort the loop entirely and
  // leave all subsequent snapshots undeleted. That would undermine exactly
  // the privacy purpose of this function (see the docstring above): the
  // next user on the shared machine would still see their predecessor's
  // state despite "logging out".
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

/** Removes a snapshot. Errors are swallowed. */
export function clearSessionSnapshot(key: string): void {
  const storage = getStorage();
  if (!storage) return;
  try {
    storage.removeItem(storageKey(key));
  } catch {
    // Nothing to do — the snapshot just stays behind.
  }
}
