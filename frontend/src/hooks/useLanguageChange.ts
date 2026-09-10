import { useTranslation } from 'react-i18next';
import { useAuth } from '../contexts/AuthContext';
import AuthService from '../services/AuthService';
import { ACCESS_TOKEN_KEY } from '../api/tokenRefreshLock';
import { setPendingLanguage, clearPendingLanguage } from '../utils/languagePreference';
import { SupportedLanguage } from '../types/auth';

export type LanguageChangeOutcome = 'saved' | 'failed' | 'skipped';

/**
 * Shared "switch the UI language, then try to persist it to the account"
 * flow. Review fix (TF-802): `ReleaseNotesDialog`'s language pills used to
 * call `i18n.changeLanguage()` directly, bypassing this entirely — see
 * `src/utils/languagePreference.ts` for why that silently reverts on the very
 * next profile load or token refresh (`AuthContext`'s
 * `resolveLanguageOnProfileLoad()` falls back to the account's
 * `preferred_language` whenever no pending marker is set).
 *
 * The switch itself is a client-side operation and cannot fail; only the
 * account save can, and a failed save does not revert the switch — the
 * pending marker keeps applying it in this browser (and gets retried, e.g.
 * from `ProfileView`) until a save succeeds.
 */
export function useLanguageChange() {
  const { i18n } = useTranslation();
  const { user } = useAuth();

  const changeLanguage = async (language: SupportedLanguage): Promise<LanguageChangeOutcome> => {
    setPendingLanguage(language);
    await i18n
      .changeLanguage(language)
      .catch((e: unknown) => console.error('[useLanguageChange] Language change failed:', e));

    const token = window.localStorage.getItem(ACCESS_TOKEN_KEY);
    if (!user || !token) return 'skipped';

    try {
      await AuthService.updateProfile(token, { preferred_language: language });
      // Account and browser agree again — drop the marker so a language set
      // on another device is not ignored here forever.
      clearPendingLanguage();
      return 'saved';
    } catch (error) {
      console.error('[useLanguageChange] Saving the language preference failed:', error);
      return 'failed';
    }
  };

  return { changeLanguage };
}

export default useLanguageChange;
