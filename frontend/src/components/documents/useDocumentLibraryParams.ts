import { useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  DocumentListParams, DocumentSort, MimeFamily, StatusGroup, ViewMode, VisibilityFilter,
} from '../../types/document';

const LS_SIZE = 'examcraft_docs_page_size';
const LS_VIEW = 'examcraft_docs_view';
const DEFAULT_SIZE = 24;
const PAGE_RESETTING_KEYS = new Set([
  'q', 'visibility', 'status', 'mime_family', 'tag_ids', 'sort',
]);

function readLsNumber(key: string, fallback: number): number {
  const v = Number(localStorage.getItem(key));
  return Number.isFinite(v) && v > 0 ? v : fallback;
}

export interface ResolvedParams extends DocumentListParams {
  status: StatusGroup[];
  mime_family: MimeFamily[];
  tag_ids: number[];
  page: number;
  page_size: number;
}

export interface UseDocumentLibraryParams {
  params: ResolvedParams;
  view: ViewMode;
  setParam: (key: keyof DocumentListParams | 'view', value: unknown) => void;
  resetFilters: () => void;
}

export function useDocumentLibraryParams(): UseDocumentLibraryParams {
  const [searchParams, setSearchParams] = useSearchParams();

  const params: ResolvedParams = useMemo(() => {
    const sizeFromUrl = searchParams.get('size');
    const page_size = sizeFromUrl ? Number(sizeFromUrl) : readLsNumber(LS_SIZE, DEFAULT_SIZE);
    return {
      q: searchParams.get('q') || undefined,
      visibility: (searchParams.get('visibility') as VisibilityFilter) || undefined,
      status: searchParams.getAll('status') as StatusGroup[],
      mime_family: searchParams.getAll('mime_family') as MimeFamily[],
      tag_ids: searchParams.getAll('tag_ids').map(Number).filter((n) => Number.isFinite(n)),
      sort: (searchParams.get('sort') as DocumentSort) || undefined,
      page: Number(searchParams.get('page')) || 1,
      page_size: Number.isFinite(page_size) && page_size > 0 ? page_size : DEFAULT_SIZE,
    };
  }, [searchParams]);

  const view: ViewMode = useMemo(
    () =>
      (searchParams.get('view') as ViewMode) ||
      (localStorage.getItem(LS_VIEW) as ViewMode) ||
      'cards',
    [searchParams],
  );

  const setParam = useCallback(
    (key: keyof DocumentListParams | 'view', value: unknown) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (key === 'view') {
            if (value) {
              next.set('view', String(value));
              localStorage.setItem(LS_VIEW, String(value));
            }
            return next;
          }
          if (key === 'page_size') {
            next.set('size', String(value));
            localStorage.setItem(LS_SIZE, String(value));
            next.set('page', '1');
            return next;
          }
          if (key === 'status' || key === 'mime_family' || key === 'tag_ids') {
            next.delete(key);
            (Array.isArray(value) ? value : []).forEach((v) => next.append(key, String(v)));
          } else if (value === undefined || value === null || value === '') {
            next.delete(key);
          } else {
            next.set(key, String(value));
          }
          if (PAGE_RESETTING_KEYS.has(key as string)) next.set('page', '1');
          return next;
        },
        { replace: key === 'q' },
      );
    },
    [setSearchParams],
  );

  const resetFilters = useCallback(() => {
    setSearchParams((prev) => {
      const next = new URLSearchParams();
      const size = prev.get('size');
      const v = prev.get('view');
      if (size) next.set('size', size);
      if (v) next.set('view', v);
      return next;
    });
  }, [setSearchParams]);

  return { params, view, setParam, resetFilters };
}
