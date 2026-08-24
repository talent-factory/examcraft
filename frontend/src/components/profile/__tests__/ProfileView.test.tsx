import React from 'react';
import { render, screen } from '@testing-library/react';
import i18n from '../../../i18n'; // load the real i18n instance
import { ProfileView } from '../ProfileView';

// setupTests.ts installs a global mock for 'react-i18next' that resolves keys
// via a simplified lookup (no support for i18next's `defaultValue` option).
// This test needs the *real* react-i18next + i18next behaviour to genuinely
// verify both the readable-label mapping and the raw-key fallback, so we
// unmock it here. jest.mock/jest.unmock calls are hoisted above all imports
// by babel-plugin-jest-hoist, so this takes effect before the imports above
// (which transitively require 'react-i18next') are resolved.
jest.unmock('react-i18next');

// Mock AuthContext so useAuth() returns a user with roles
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
      roles: [
        {
          id: 1,
          display_name: 'Dozent',
          permissions: ['documents:read', 'create_questions', 'some:unknown_permission'],
        },
      ],
    },
  }),
}));

// AuthService is imported by ProfileView (language switching) — mock it
jest.mock('../../../services/AuthService', () => ({
  __esModule: true,
  default: { updateProfile: jest.fn() },
}));

describe('ProfileView permissions', () => {
  // jsdom's navigator.language ('en-US') would otherwise make i18next-browser-languagedetector
  // pick 'en' instead of 'de', so force the language explicitly for deterministic assertions.
  beforeAll(async () => {
    await i18n.changeLanguage('de');
  });

  it('renders known permissions as readable labels', () => {
    render(<ProfileView />);
    expect(screen.getByText('Dokumente ansehen')).toBeInTheDocument();
    expect(screen.getByText('Fragen erstellen')).toBeInTheDocument();
  });

  it('falls back to the raw key for unknown permissions', () => {
    render(<ProfileView />);
    expect(screen.getByText('some:unknown_permission')).toBeInTheDocument();
  });
});
