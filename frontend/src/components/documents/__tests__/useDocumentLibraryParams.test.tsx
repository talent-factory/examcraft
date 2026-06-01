import React from 'react';
import { renderHook, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { useDocumentLibraryParams } from '../useDocumentLibraryParams';

const wrapper = (initial: string) =>
  ({ children }: { children: React.ReactNode }) => (
    <MemoryRouter initialEntries={[initial]}>{children}</MemoryRouter>
  );

beforeEach(() => localStorage.clear());

test('parses filters from the URL', () => {
  const { result } = renderHook(() => useDocumentLibraryParams(), {
    wrapper: wrapper('/documents?q=foo&status=processing&status=processed&tag_ids=1&tag_ids=3&page=2&size=12&view=list&sort=title_asc&visibility=own&mime_family=pdf'),
  });
  expect(result.current.params.q).toBe('foo');
  expect(result.current.params.status).toEqual(['processing', 'processed']);
  expect(result.current.params.tag_ids).toEqual([1, 3]);
  expect(result.current.params.page).toBe(2);
  expect(result.current.params.page_size).toBe(12);
  expect(result.current.params.sort).toBe('title_asc');
  expect(result.current.params.visibility).toBe('own');
  expect(result.current.params.mime_family).toEqual(['pdf']);
  expect(result.current.view).toBe('list');
});

test('defaults: page 1, size 24, view cards, empty filters', () => {
  const { result } = renderHook(() => useDocumentLibraryParams(), { wrapper: wrapper('/documents') });
  expect(result.current.params.page).toBe(1);
  expect(result.current.params.page_size).toBe(24);
  expect(result.current.view).toBe('cards');
  expect(result.current.params.status).toEqual([]);
  expect(result.current.params.q).toBeUndefined();
});

test('setParam updates a value and resets page to 1 for filter changes', () => {
  const { result } = renderHook(() => useDocumentLibraryParams(), { wrapper: wrapper('/documents?page=3') });
  act(() => result.current.setParam('q', 'abc'));
  expect(result.current.params.q).toBe('abc');
  expect(result.current.params.page).toBe(1);
});

test('setParam(page) does NOT reset page', () => {
  const { result } = renderHook(() => useDocumentLibraryParams(), { wrapper: wrapper('/documents') });
  act(() => result.current.setParam('page', 4));
  expect(result.current.params.page).toBe(4);
});

test('setParam(view) persists to localStorage and URL', () => {
  const { result } = renderHook(() => useDocumentLibraryParams(), { wrapper: wrapper('/documents') });
  act(() => result.current.setParam('view', 'list'));
  expect(result.current.view).toBe('list');
  expect(localStorage.getItem('examcraft_docs_view')).toBe('list');
});

test('setParam(page_size) persists + resets page', () => {
  const { result } = renderHook(() => useDocumentLibraryParams(), { wrapper: wrapper('/documents?page=5') });
  act(() => result.current.setParam('page_size', 48));
  expect(result.current.params.page_size).toBe(48);
  expect(result.current.params.page).toBe(1);
  expect(localStorage.getItem('examcraft_docs_page_size')).toBe('48');
});

test('multi-select param (status) round-trips', () => {
  const { result } = renderHook(() => useDocumentLibraryParams(), { wrapper: wrapper('/documents') });
  act(() => result.current.setParam('status', ['processing', 'error']));
  expect(result.current.params.status).toEqual(['processing', 'error']);
});

test('resetFilters clears filters but keeps page_size + view', () => {
  const { result } = renderHook(() => useDocumentLibraryParams(), {
    wrapper: wrapper('/documents?q=foo&status=processed&size=48&view=list'),
  });
  act(() => result.current.resetFilters());
  expect(result.current.params.q).toBeUndefined();
  expect(result.current.params.status).toEqual([]);
  expect(result.current.params.page_size).toBe(48);
  expect(result.current.view).toBe('list');
});
