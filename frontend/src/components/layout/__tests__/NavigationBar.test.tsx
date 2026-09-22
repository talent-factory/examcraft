/**
 * NavigationBar accessible names.
 *
 * The user-menu trigger is an icon/avatar button with no visible text, so its
 * aria-label is the only name a screen reader announces. It used to be the
 * hardcoded English "User menu" regardless of the UI language.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { NavigationBar } from '../NavigationBar';

jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 1, first_name: 'Max', last_name: 'Muster', email: 'max@example.com' },
    logout: jest.fn(),
    isImpersonating: false,
  }),
}));

jest.mock('../PackageTierBadge', () => ({
  PackageTierBadge: () => null,
}));

describe('NavigationBar — accessible names (TF-775)', () => {
  it('names the user-menu button in the UI language', () => {
    render(
      <MemoryRouter>
        <NavigationBar />
      </MemoryRouter>,
    );

    expect(screen.getByRole('button', { name: 'Benutzermenü' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'User menu' })).not.toBeInTheDocument();
  });
});
