import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import TagAutocomplete from '../TagAutocomplete';
import { isPendingTag } from '../../../api/tagsApi';

jest.mock('../../../api/tagsApi', () => {
  const actual = jest.requireActual('../../../api/tagsApi');
  return {
    ...actual,
    tagsApi: {
      listTags: jest.fn().mockResolvedValue([
        { id: 1, name: 'Bestand', scope: 'institution', institution_id: 1, usage_count: 2, is_archived: false, is_own: true },
      ]),
      createTag: jest.fn(),
    },
  };
});

import { tagsApi } from '../../../api/tagsApi';

const renderDeferred = (value: any[] = [], onChange = jest.fn()) => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <TagAutocomplete value={value} onChange={onChange} deferCreation />
    </QueryClientProvider>
  );
  return { onChange };
};

describe('deferCreation=true', () => {
  it('ruft createTag NICHT auf — fügt stattdessen PendingTag zu onChange hinzu', async () => {
    const { onChange } = renderDeferred();
    const input = screen.getByRole('combobox');

    await userEvent.type(input, 'NeuerTag');
    await userEvent.keyboard('{Enter}');

    await waitFor(() => expect(onChange).toHaveBeenCalled());
    expect(tagsApi.createTag).not.toHaveBeenCalled();

    const [calledWith] = onChange.mock.calls[0];
    const lastTag = calledWith[calledWith.length - 1];
    expect(isPendingTag(lastTag)).toBe(true);
    expect(lastTag.name).toBe('NeuerTag');
  });

  it('zeigt Pending-Chip wenn PendingTag im value', async () => {
    const pendingTag = { __pending: true as const, name: 'PendingTest' };
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <TagAutocomplete value={[pendingTag]} onChange={jest.fn()} deferCreation />
      </QueryClientProvider>
    );
    expect(screen.getByText('PendingTest')).toBeInTheDocument();
  });
});

describe('deferCreation=false (Standard)', () => {
  it('ruft createTag auf wenn kein deferCreation', async () => {
    (tagsApi.createTag as jest.Mock).mockResolvedValueOnce({
      id: 99, name: 'EchterTag', scope: 'institution', institution_id: 1,
      usage_count: 0, is_archived: false, is_own: true,
    });

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const onChange = jest.fn();
    render(
      <QueryClientProvider client={qc}>
        <TagAutocomplete value={[]} onChange={onChange} />
      </QueryClientProvider>
    );

    const input = screen.getByRole('combobox');
    await userEvent.type(input, 'EchterTag');
    await userEvent.keyboard('{Enter}');

    // TF-397: createTag now receives scope + kind ('content' by default).
    await waitFor(() =>
      expect(tagsApi.createTag).toHaveBeenCalledWith('EchterTag', 'institution', 'content')
    );
  });
});
