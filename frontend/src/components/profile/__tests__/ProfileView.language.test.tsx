import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import i18n from '../../../i18n'; // the real instance — the language is the subject here
import { ProfileView } from '../ProfileView';
import AuthService from '../../../services/AuthService';
import { getPendingLanguage } from '../../../utils/languagePreference';

// Same reason as ProfileView.test.tsx: this needs real i18next behaviour, not
// setupTests' key-lookup stub, because it asserts on the ACTIVE language.
jest.unmock('react-i18next');

jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: {
      id: 1,
      email: 'test@example.com',
      first_name: 'Test',
      last_name: 'User',
      status: 'active',
      created_at: '2024-01-01T00:00:00Z',
      is_superuser: false,
      roles: [],
    },
  }),
}));

jest.mock('../../../services/AuthService', () => ({
  __esModule: true,
  default: { updateProfile: jest.fn() },
}));

const updateProfile = AuthService.updateProfile as jest.Mock;

const selectLanguage = (code: string) =>
  fireEvent.change(screen.getByLabelText(/sprache|language|langue|lingua/i), {
    target: { value: code },
  });

beforeEach(async () => {
  localStorage.clear();
  updateProfile.mockReset();
  localStorage.setItem('examcraft_access_token', 'token');
  await i18n.changeLanguage('it');
});

/**
 * The bug: switching the language and saving it shared one try/catch, so a
 * failed PATCH /api/auth/me rolled the language back — the user was returned to
 * the language they had just left, with the error going only to the console.
 * Reproduced in the field by exhausting the IP rate limiter (429).
 */
describe('ProfileView language switching', () => {
  it('keeps the chosen language when saving it fails', async () => {
    updateProfile.mockRejectedValue(new Error('429 Too Many Requests'));
    render(<ProfileView />);

    selectLanguage('de');

    await waitFor(() => expect(updateProfile).toHaveBeenCalled());
    expect(i18n.language).toBe('de');
  });

  it('tells the user that only the sync failed', async () => {
    updateProfile.mockRejectedValue(new Error('429 Too Many Requests'));
    render(<ProfileView />);

    selectLanguage('de');

    // Previously this went to console.error only, so the user saw the language
    // snap back with no explanation at all.
    expect(await screen.findByRole('status')).toBeInTheDocument();
  });

  it('marks the choice as unsaved so a profile load cannot overwrite it', async () => {
    updateProfile.mockRejectedValue(new Error('offline'));
    render(<ProfileView />);

    selectLanguage('de');

    await waitFor(() => expect(getPendingLanguage()).toBe('de'));
  });

  it('drops the marker once the account has the language', async () => {
    updateProfile.mockResolvedValue({});
    render(<ProfileView />);

    selectLanguage('de');

    await waitFor(() =>
      expect(updateProfile).toHaveBeenCalledWith('token', { preferred_language: 'de' })
    );
    await waitFor(() => expect(getPendingLanguage()).toBeNull());
  });

  it('retries an unsaved choice when the page is opened again', async () => {
    localStorage.setItem('examcraft_language_pending', 'de');
    updateProfile.mockResolvedValue({});

    render(<ProfileView />);

    await waitFor(() =>
      expect(updateProfile).toHaveBeenCalledWith('token', { preferred_language: 'de' })
    );
    await waitFor(() => expect(getPendingLanguage()).toBeNull());
  });
});
