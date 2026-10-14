import React from 'react';
import { render, screen } from '@testing-library/react';
import i18n from '../../../i18n';
import { ProfileView } from '../ProfileView';
import { getDateLocale } from '../../../utils/dateLocale';
import { User } from '../../../types/auth';
// A real /auth/me response body. test_login_tracking.py validates the same
// file against UserProfileResponse, so a renamed or dropped backend field
// breaks one of the two suites instead of silently hiding the block (TF-1060).
import authMeResponse from '../../../__fixtures__/authMe.response.json';

jest.unmock('react-i18next');

let mockUser: User;
jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({ user: mockUser }),
}));

jest.mock('../../../services/AuthService', () => ({
  __esModule: true,
  default: { updateProfile: jest.fn() },
}));

describe('ProfileView last login', () => {
  beforeAll(async () => {
    await i18n.changeLanguage('de');
  });

  it('shows the previous login from the /auth/me response', () => {
    mockUser = authMeResponse as unknown as User;
    render(<ProfileView />);

    expect(screen.getByText('Letzte Anmeldung')).toBeInTheDocument();
    const expected = new Date(authMeResponse.previous_login_at).toLocaleString(
      getDateLocale('de')
    );
    expect(screen.getByText(expected)).toBeInTheDocument();
  });

  it('hides the block on the first login', () => {
    mockUser = { ...authMeResponse, previous_login_at: null } as unknown as User;
    render(<ProfileView />);

    expect(screen.queryByText('Letzte Anmeldung')).not.toBeInTheDocument();
  });
});
