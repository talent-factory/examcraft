/**
 * RegisterForm Component Tests
 * Simple smoke tests to verify component structure
 */

import React from 'react';
import { render } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { RegisterForm } from '../RegisterForm';
import { AuthProvider } from '../../../contexts/AuthContext';

// Mock AuthService
jest.mock('../../../services/AuthService', () => ({
  __esModule: true,
  default: {
    login: jest.fn(),
    register: jest.fn(),
    logout: jest.fn(),
    getProfile: jest.fn(),
    initiateOAuth: jest.fn(),
  },
}));

describe('RegisterForm', () => {
  it('should render without crashing', () => {
    const { container } = render(
      <BrowserRouter>
        <AuthProvider>
          <RegisterForm />
        </AuthProvider>
      </BrowserRouter>
    );
    
    expect(container).toBeTruthy();
  });
});
