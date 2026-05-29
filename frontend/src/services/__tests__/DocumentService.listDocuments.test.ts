import { DocumentService } from '../DocumentService';

function mockFetchOnce(body: any, ok = true, status = 200) {
  (global as any).fetch = jest.fn().mockResolvedValue({
    ok, status, statusText: 'OK', json: async () => body,
  });
}
afterEach(() => jest.resetAllMocks());

test('listDocuments serializes array filters as repeated params', async () => {
  mockFetchOnce({ documents: [], total: 0, page: 2, page_size: 12, total_pages: 0,
    stats: { total: 0, processed: 0, with_vectors: 0, in_progress: 0 } });
  const res = await DocumentService.listDocuments({
    q: 'foo', visibility: 'own', status: ['processing', 'processed'],
    mime_family: ['pdf'], tag_ids: [1, 3], sort: 'title_asc', page: 2, page_size: 12,
  });
  expect(res.page).toBe(2);
  const url = (global.fetch as jest.Mock).mock.calls[0][0] as string;
  expect(url).toContain('/api/v1/documents/?');
  expect(url).toContain('q=foo');
  expect(url).toContain('visibility=own');
  expect(url).toContain('status=processing');
  expect(url).toContain('status=processed');
  expect(url).toContain('tag_ids=1');
  expect(url).toContain('tag_ids=3');
  expect(url).toContain('sort=title_asc');
  expect(url).toContain('page=2');
  expect(url).toContain('page_size=12');
});

test('listDocuments omits empty params', async () => {
  mockFetchOnce({ documents: [], total: 0, page: 1, page_size: 24, total_pages: 0,
    stats: { total: 0, processed: 0, with_vectors: 0, in_progress: 0 } });
  await DocumentService.listDocuments({ page: 1, page_size: 24 });
  const url = (global.fetch as jest.Mock).mock.calls[0][0] as string;
  expect(url).not.toContain('q=');
  expect(url).not.toContain('status=');
});
