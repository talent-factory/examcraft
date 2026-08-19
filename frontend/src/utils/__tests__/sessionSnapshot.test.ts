import {
  readSessionSnapshot,
  writeSessionSnapshot,
  clearSessionSnapshot,
  clearAllSessionSnapshots,
} from '../sessionSnapshot';

const KEY = 'testWizard';
const STORAGE_KEY = 'examcraft.snapshot.testWizard';

describe('sessionSnapshot', () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    jest.restoreAllMocks();
  });

  it('round-trips a value', () => {
    writeSessionSnapshot(KEY, 1, { topic: 'Heapsort', step: 2 });
    expect(readSessionSnapshot(KEY, 1)).toEqual({ topic: 'Heapsort', step: 2 });
  });

  it('returns null when nothing was stored', () => {
    expect(readSessionSnapshot(KEY, 1)).toBeNull();
  });

  it('stores the payload under a namespaced key with version metadata', () => {
    writeSessionSnapshot(KEY, 3, { a: 1 });
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    expect(raw).not.toBeNull();
    const envelope = JSON.parse(raw as string);
    expect(envelope.version).toBe(3);
    expect(envelope.data).toEqual({ a: 1 });
    expect(typeof envelope.savedAt).toBe('string');
  });

  it('discards a snapshot written by an older version', () => {
    writeSessionSnapshot(KEY, 1, { topic: 'alt' });

    expect(readSessionSnapshot(KEY, 2)).toBeNull();
    // Der veraltete Eintrag wird gleich entsorgt, damit er nicht bei jedem
    // Mount erneut geparst wird.
    expect(window.sessionStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it('discards a corrupt entry instead of throwing', () => {
    window.sessionStorage.setItem(STORAGE_KEY, '{not json');

    expect(readSessionSnapshot(KEY, 1)).toBeNull();
    expect(window.sessionStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it('discards an entry that is not an envelope', () => {
    window.sessionStorage.setItem(STORAGE_KEY, '"just a string"');
    expect(readSessionSnapshot(KEY, 1)).toBeNull();
  });

  it('clears a stored snapshot', () => {
    writeSessionSnapshot(KEY, 1, { a: 1 });
    clearSessionSnapshot(KEY);
    expect(readSessionSnapshot(KEY, 1)).toBeNull();
  });

  describe('clearAllSessionSnapshots', () => {
    it('removes every snapshot of this application', () => {
      writeSessionSnapshot('wizardA', 1, { a: 1 });
      writeSessionSnapshot('wizardB', 1, { b: 2 });
      writeSessionSnapshot('dismissedTasks', 1, ['t1']);

      clearAllSessionSnapshots();

      expect(readSessionSnapshot('wizardA', 1)).toBeNull();
      expect(readSessionSnapshot('wizardB', 1)).toBeNull();
      expect(readSessionSnapshot('dismissedTasks', 1)).toBeNull();
    });

    it('leaves foreign sessionStorage entries untouched', () => {
      window.sessionStorage.setItem('someOtherApp.state', 'keep me');
      writeSessionSnapshot('wizardA', 1, { a: 1 });

      clearAllSessionSnapshots();

      expect(window.sessionStorage.getItem('someOtherApp.state')).toBe('keep me');
    });

    it('removes all entries even though removal shifts indices', () => {
      // Beim Löschen während der Iteration würde jeder zweite Eintrag
      // übersprungen — genau das darf nicht passieren, sonst überlebt der
      // Stand des Vorgängers den Logout.
      for (let i = 0; i < 6; i++) {
        writeSessionSnapshot(`wizard${i}`, 1, { i });
      }

      clearAllSessionSnapshots();

      const remaining = Object.keys(window.sessionStorage).filter((key) =>
        key.startsWith('examcraft.snapshot.')
      );
      expect(remaining).toEqual([]);
    });

    it('survives a storage failure', () => {
      const warn = jest.spyOn(console, 'warn').mockImplementation(() => {});
      jest.spyOn(window.sessionStorage, 'removeItem').mockImplementation(() => {
        throw new DOMException('SecurityError');
      });
      writeSessionSnapshot('wizardA', 1, { a: 1 });

      expect(() => clearAllSessionSnapshots()).not.toThrow();
      expect(warn).toHaveBeenCalled();
    });
  });

  it('survives a write failure (quota exceeded / private mode)', () => {
    const warn = jest.spyOn(console, 'warn').mockImplementation(() => {});
    jest.spyOn(window.sessionStorage, 'setItem').mockImplementation(() => {
      throw new DOMException('QuotaExceededError');
    });

    expect(() => writeSessionSnapshot(KEY, 1, { a: 1 })).not.toThrow();
    expect(warn).toHaveBeenCalled();
  });

  it('survives a read failure', () => {
    jest.spyOn(window.sessionStorage, 'getItem').mockImplementation(() => {
      throw new DOMException('SecurityError');
    });

    expect(readSessionSnapshot(KEY, 1)).toBeNull();
  });
});
