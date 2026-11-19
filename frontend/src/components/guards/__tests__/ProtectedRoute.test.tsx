import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';

import { ProtectedRoute } from '../ProtectedRoute';

let mockAuth = { isAuthenticated: false, isLoading: false };

jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => mockAuth,
}));

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

const LoginProbe = () => {
  const location = useLocation();
  const from = (location.state as { from?: { pathname: string; search: string } } | null)?.from;
  return <div>login-page from={from ? `${from.pathname}${from.search}` : 'none'}</div>;
};

function renderAt(url: string, redirectTo?: string) {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <Routes>
        <Route
          path="/exams"
          element={
            <ProtectedRoute redirectTo={redirectTo}>
              <div>geschuetzt</div>
            </ProtectedRoute>
          }
        />
        <Route path="/login" element={<LoginProbe />} />
        <Route path="/anmeldung" element={<div>eigene-anmeldung</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ProtectedRoute', () => {
  it('zeigt den Inhalt mit Session', () => {
    mockAuth = { isAuthenticated: true, isLoading: false };
    renderAt('/exams');
    expect(screen.getByText('geschuetzt')).toBeInTheDocument();
  });

  it('zeigt während des Ladens nur den Spinner und leitet nicht um', () => {
    mockAuth = { isAuthenticated: false, isLoading: true };
    renderAt('/exams');
    expect(screen.getByText('guards.loading')).toBeInTheDocument();
    expect(screen.queryByText('geschuetzt')).not.toBeInTheDocument();
    expect(screen.queryByText(/login-page/)).not.toBeInTheDocument();
  });

  it('leitet ohne Session auf /login und merkt sich das Ziel', () => {
    mockAuth = { isAuthenticated: false, isLoading: false };
    renderAt('/exams?tab=2');
    expect(screen.getByText('login-page from=/exams?tab=2')).toBeInTheDocument();
    expect(screen.queryByText('geschuetzt')).not.toBeInTheDocument();
  });

  it('leitet auf das konfigurierte Ziel um', () => {
    mockAuth = { isAuthenticated: false, isLoading: false };
    renderAt('/exams', '/anmeldung');
    expect(screen.getByText('eigene-anmeldung')).toBeInTheDocument();
  });
});
