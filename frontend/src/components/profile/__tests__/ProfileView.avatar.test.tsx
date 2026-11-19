import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ProfileView } from '../ProfileView';

const mockUploadAvatar = jest.fn();
const mockDeleteAvatar = jest.fn();
let mockSource: 'idp' | 'upload' | null = 'idp';

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
      avatar_source: mockSource,
      avatar_updated_at: '2026-11-19T10:00:00Z',
    },
    uploadAvatar: mockUploadAvatar,
    deleteAvatar: mockDeleteAvatar,
  }),
}));

jest.mock('../../../services/AuthService', () => ({
  __esModule: true,
  default: { updateProfile: jest.fn() },
}));

describe('ProfileView avatar', () => {
  beforeEach(() => {
    mockUploadAvatar.mockReset();
    mockDeleteAvatar.mockReset();
    mockSource = 'idp';
  });

  it('uploads the chosen file', async () => {
    mockUploadAvatar.mockResolvedValue(undefined);
    render(<ProfileView />);
    const file = new File(['x'], 'a.png', { type: 'image/png' });
    fireEvent.change(screen.getByTestId('avatar-file-input'), { target: { files: [file] } });
    await waitFor(() => expect(mockUploadAvatar).toHaveBeenCalledWith(file));
  });

  it('shows an error when the upload fails', async () => {
    mockUploadAvatar.mockRejectedValue(new Error('boom'));
    render(<ProfileView />);
    const file = new File(['x'], 'a.png', { type: 'image/png' });
    fireEvent.change(screen.getByTestId('avatar-file-input'), { target: { files: [file] } });
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });

  it('offers removal only for an uploaded picture', async () => {
    const { unmount } = render(<ProfileView />);
    expect(screen.queryByText('Bild entfernen')).not.toBeInTheDocument();
    unmount();

    mockSource = 'upload';
    mockDeleteAvatar.mockResolvedValue(undefined);
    render(<ProfileView />);
    fireEvent.click(screen.getByText('Bild entfernen'));
    await waitFor(() => expect(mockDeleteAvatar).toHaveBeenCalled());
  });
});
