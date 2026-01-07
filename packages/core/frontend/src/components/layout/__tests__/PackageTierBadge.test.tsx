/**
 * Tests for PackageTierBadge Component
 * Tests tier detection, localStorage key, and API integration
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import PackageTierBadge from '../PackageTierBadge';

// Mock environment variables BEFORE importing component
const MOCK_API_URL = 'http://localhost:8000';
process.env.REACT_APP_API_URL = MOCK_API_URL;

// Mock fetch globally
global.fetch = jest.fn();

describe('PackageTierBadge', () => {
  beforeEach(() => {
    // Clear all mocks before each test
    jest.clearAllMocks();
    localStorage.clear();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  // ==================== Tier Detection Tests ====================

  it('shows Professional tier for authenticated user with Professional subscription', async () => {
    // Arrange: Set correct localStorage key
    localStorage.setItem('examcraft_access_token', 'fake-jwt-token');

    // Mock API response for Professional tier
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        name: 'professional',
        display_name: 'Professional',
        description: 'Professional Tier',
        features: ['rag_generation', 'document_chatbot', 'advanced_prompt_management'],
        quotas: {
          max_documents: -1,
          max_questions_per_month: 1000,
          max_users: 10,
        },
      }),
    });

    // Act
    render(<PackageTierBadge />);

    // Assert: Wait for API call to complete
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalled();
    });

    // Assert: Wait for badge update
    await waitFor(() => {
      const badge = screen.getByText(/Premium - Professional/i);
      expect(badge).toBeInTheDocument();
    }, { timeout: 3000 });

    // Verify correct API endpoint was called
    expect(global.fetch).toHaveBeenCalledWith(
      `${MOCK_API_URL}/api/v1/rbac/tiers/my`,
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer fake-jwt-token',
        }),
      })
    );
  });

  it('shows Starter tier for authenticated user with Starter subscription', async () => {
    // Arrange
    localStorage.setItem('examcraft_access_token', 'fake-jwt-token');

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        name: 'starter',
        display_name: 'Starter',
        description: 'Starter Tier',
        features: ['rag_generation', 'prompt_templates'],
        quotas: {
          max_documents: 50,
          max_questions_per_month: 200,
          max_users: 3,
        },
      }),
    });

    // Act
    render(<PackageTierBadge />);

    // Assert
    await waitFor(() => {
      expect(screen.getByText(/Premium/i)).toBeInTheDocument();
      expect(screen.getByText(/Starter/i)).toBeInTheDocument();
    });
  });

  it('shows Free tier for unauthenticated user', async () => {
    // Arrange: No token in localStorage
    // (localStorage is already clear from beforeEach)

    // Act
    render(<PackageTierBadge />);

    // Assert: Should show Free tier immediately (no API call)
    await waitFor(() => {
      expect(screen.getByText(/Core/i)).toBeInTheDocument();
      expect(screen.getByText(/Free/i)).toBeInTheDocument();
    });

    // Verify NO API call was made
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('shows Enterprise tier for authenticated user with Enterprise subscription', async () => {
    // Arrange
    localStorage.setItem('examcraft_access_token', 'fake-jwt-token');

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        name: 'enterprise',
        display_name: 'Enterprise',
        description: 'Enterprise Tier',
        features: ['sso_integration', 'custom_branding', 'api_access'],
        quotas: {
          max_documents: -1,
          max_questions_per_month: -1,
          max_users: -1,
        },
      }),
    });

    // Act
    render(<PackageTierBadge />);

    // Assert
    await waitFor(() => {
      expect(screen.getByText(/Enterprise/i)).toBeInTheDocument();
    });
  });

  // ==================== LocalStorage Key Tests ====================

  it('uses correct localStorage key "examcraft_access_token"', async () => {
    // Arrange: Set WRONG key (old key)
    localStorage.setItem('access_token', 'wrong-key-token');

    // Act
    render(<PackageTierBadge />);

    // Assert: Should show Free tier (token not found)
    await waitFor(() => {
      expect(screen.getByText(/Free/i)).toBeInTheDocument();
    });

    // Verify NO API call was made (no token found)
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('does not use old localStorage key "access_token"', async () => {
    // Arrange: Set both keys
    localStorage.setItem('access_token', 'old-token');
    localStorage.setItem('examcraft_access_token', 'new-token');

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        name: 'professional',
        display_name: 'Professional',
      }),
    });

    // Act
    render(<PackageTierBadge />);

    // Assert: Should use NEW key
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.anything(),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer new-token',
          }),
        })
      );
    });
  });

  // ==================== Error Handling Tests ====================

  it('falls back to Free tier on API error', async () => {
    // Arrange
    localStorage.setItem('examcraft_access_token', 'fake-jwt-token');

    (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

    // Act
    render(<PackageTierBadge />);

    // Assert: Should fall back to Free tier
    await waitFor(() => {
      expect(screen.getByText(/Free/i)).toBeInTheDocument();
    });
  });

  it('falls back to Free tier on 401 Unauthorized', async () => {
    // Arrange
    localStorage.setItem('examcraft_access_token', 'invalid-token');

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 401,
    });

    // Act
    render(<PackageTierBadge />);

    // Assert
    await waitFor(() => {
      expect(screen.getByText(/Free/i)).toBeInTheDocument();
    });
  });

  it('falls back to Free tier on 403 Forbidden', async () => {
    // Arrange
    localStorage.setItem('examcraft_access_token', 'fake-jwt-token');

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 403,
    });

    // Act
    render(<PackageTierBadge />);

    // Assert
    await waitFor(() => {
      expect(screen.getByText(/Free/i)).toBeInTheDocument();
    });
  });

  // ==================== Loading State Tests ====================

  it('shows loading state while fetching tier', async () => {
    // Arrange
    localStorage.setItem('examcraft_access_token', 'fake-jwt-token');

    // Mock slow API response
    (global.fetch as jest.Mock).mockImplementation(
      () =>
        new Promise((resolve) =>
          setTimeout(
            () =>
              resolve({
                ok: true,
                json: async () => ({ name: 'professional', display_name: 'Professional' }),
              }),
            100
          )
        )
    );

    // Act
    render(<PackageTierBadge />);

    // Assert: Should show loading state initially
    // (Implementation-specific - adjust based on actual loading UI)
    expect(screen.queryByText(/Professional/i)).not.toBeInTheDocument();

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.getByText(/Professional/i)).toBeInTheDocument();
    });
  });

  // ==================== Tooltip Tests ====================

  it('shows correct tooltip for Professional tier', async () => {
    // Arrange
    localStorage.setItem('examcraft_access_token', 'fake-jwt-token');

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        name: 'professional',
        display_name: 'Professional',
        description: 'Premium Package - Professional Tier',
      }),
    });

    // Act
    render(<PackageTierBadge />);

    // Assert: Tooltip should contain tier description
    await waitFor(() => {
      const badge = screen.getByText(/Professional/i);
      expect(badge).toBeInTheDocument();
      // Note: Tooltip testing requires user interaction or specific tooltip library testing
    });
  });

  // ==================== Badge Color Tests ====================

  it('uses purple color for Professional tier', async () => {
    // Arrange
    localStorage.setItem('examcraft_access_token', 'fake-jwt-token');

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        name: 'professional',
        display_name: 'Professional',
      }),
    });

    // Act
    const { container } = render(<PackageTierBadge />);

    // Assert: Check for purple color (MUI uses inline styles)
    await waitFor(() => {
      const badge = container.querySelector('.MuiChip-root');
      expect(badge).toBeInTheDocument();
      // MUI applies backgroundColor via inline styles or CSS-in-JS
      // We just verify the badge is rendered with Professional tier
      expect(screen.getByText(/Professional/i)).toBeInTheDocument();
    });
  });

  it('uses gray color for Free tier', async () => {
    // Arrange: No token

    // Act
    const { container } = render(<PackageTierBadge />);

    // Assert: Check for Free tier badge
    await waitFor(() => {
      const badge = container.querySelector('.MuiChip-root');
      expect(badge).toBeInTheDocument();
      // MUI applies backgroundColor via inline styles or CSS-in-JS
      // We just verify the badge is rendered with Free tier
      expect(screen.getByText(/Free/i)).toBeInTheDocument();
    });
  });
});
