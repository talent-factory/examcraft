import {
  getPendingLanguage,
  setPendingLanguage,
  clearPendingLanguage,
  resolveLanguageOnProfileLoad,
} from '../languagePreference';

beforeEach(() => localStorage.clear());

describe('pending language marker', () => {
  it('round-trips a supported language', () => {
    setPendingLanguage('fr');
    expect(getPendingLanguage()).toBe('fr');
  });

  it('ignores a value that is not a supported language', () => {
    localStorage.setItem('examcraft_language_pending', 'klingon');
    expect(getPendingLanguage()).toBeNull();
  });

  it('is gone after clearing', () => {
    setPendingLanguage('it');
    clearPendingLanguage();
    expect(getPendingLanguage()).toBeNull();
  });

  it('survives an unreadable store by reporting no pending choice', () => {
    const getItem = jest
      .spyOn(Storage.prototype, 'getItem')
      .mockImplementation(() => {
        throw new Error('private mode');
      });
    // Falling back to "nothing pending" hands control to the account value,
    // which is the safe direction: it can never strand a user in a language.
    expect(getPendingLanguage()).toBeNull();
    getItem.mockRestore();
  });
});

/**
 * The rule this whole change exists for: the account value is a cross-device
 * default, an unsaved local choice outranks it. Before, the account always won
 * on profile load, so a failed save was undone again at the next reload.
 */
describe('resolveLanguageOnProfileLoad', () => {
  it('prefers an unsaved local choice over the account value', () => {
    setPendingLanguage('de');
    expect(resolveLanguageOnProfileLoad('it')).toBe('de');
  });

  it('uses the account value when nothing is pending', () => {
    expect(resolveLanguageOnProfileLoad('it')).toBe('it');
  });

  it('lets a language from another device through once the choice is saved', () => {
    setPendingLanguage('de');
    clearPendingLanguage(); // what a successful save does
    expect(resolveLanguageOnProfileLoad('fr')).toBe('fr');
  });

  it('returns null when neither side has a language', () => {
    expect(resolveLanguageOnProfileLoad(undefined)).toBeNull();
    expect(resolveLanguageOnProfileLoad(null)).toBeNull();
    expect(resolveLanguageOnProfileLoad('')).toBeNull();
  });
});
