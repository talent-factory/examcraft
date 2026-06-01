import { DocumentSort, DocumentListResponse, DocumentTag } from '../document';

test('DocumentListResponse shape is usable', () => {
  const tag: DocumentTag = { id: 1, name: 'Mathe', scope: 'user', is_own: true };
  const res: DocumentListResponse = {
    documents: [], total: 0, page: 1, page_size: 24, total_pages: 0,
    stats: { total: 0, processed: 0, with_vectors: 0, in_progress: 0 },
  };
  const sort: DocumentSort = 'created_at_desc';
  expect(res.page_size).toBe(24);
  expect(tag.scope).toBe('user');
  expect(sort).toBe('created_at_desc');
});
