import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import { GuestRoute } from '../GuestRoute';

let mockAuth = { isAuthenticated: false, isLoading: false };

jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => mockAuth,
}));

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

function renderAt(url: string) {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <Routes>
        <Route path="/login" element={<GuestRoute><div>login-page</div></GuestRoute>} />
        <Route path="/dashboard" element={<div>dashboard</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('GuestRoute', () => {
  it('zeigt die Login-Seite ohne Session', () => {
    mockAuth = { isAuthenticated: false, isLoading: false };
    renderAt('/login');
    expect(screen.getByText('login-page')).toBeInTheDocument();
  });

  it('leitet angemeldete Benutzer aufs Dashboard', () => {
    mockAuth = { isAuthenticated: true, isLoading: false };
    renderAt('/login');
    expect(screen.getByText('dashboard')).toBeInTheDocument();
  });

  it('zeigt bei ?error= die Login-Seite, auch mit gültiger Session (z. B. reauth_failed)', () => {
    mockAuth = { isAuthenticated: true, isLoading: false };
    renderAt('/login?error=reauth_failed');
    expect(screen.getByText('login-page')).toBeInTheDocument();
  });
});
