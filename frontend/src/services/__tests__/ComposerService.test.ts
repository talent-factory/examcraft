/**
 * ComposerService Tests
 *
 * We mock the shared apiClient to avoid real HTTP calls.
 */

jest.mock('../../api/apiClient', () => ({
  apiClient: {
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
  },
}));

// eslint-disable-next-line import/first
import { apiClient } from '../../api/apiClient';
// eslint-disable-next-line import/first
import { ComposerService } from '../ComposerService';
// eslint-disable-next-line import/first
import type {
  CreateExamRequest,
  UpdateExamRequest,
  AutoFillRequest,
  Exam,
  ExamDetail,
  ExamListResponse,
  ApprovedQuestionsResponse,
} from '../../types/composer';
// eslint-disable-next-line import/first
import { ExamStatus } from '../../types/composer';

const fakeClient = apiClient as jest.Mocked<{
  get: jest.Mock;
  post: jest.Mock;
  put: jest.Mock;
  delete: jest.Mock;
}>;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const makeExam = (overrides: Partial<Exam> = {}): Exam => ({
  id: 1,
  title: 'Test Exam',
  course: null,
  exam_date: null,
  time_limit_minutes: null,
  allowed_aids: null,
  instructions: null,
  passing_percentage: 50,
  total_points: 0,
  status: ExamStatus.DRAFT,
  language: 'de',
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
  question_count: 0,
  ...overrides,
});

const makeExamDetail = (overrides: Partial<ExamDetail> = {}): ExamDetail => ({
  ...makeExam(),
  questions: [],
  ...overrides,
});

// ---------------------------------------------------------------------------

describe('ComposerService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  // -------------------------------------------------------------------------
  // listExams
  // -------------------------------------------------------------------------

  describe('listExams', () => {
    it('calls GET /api/v1/exams/ without params', async () => {
      const response: ExamListResponse = { total: 0, exams: [] };
      fakeClient.get.mockResolvedValueOnce({ data: response });

      const result = await ComposerService.listExams();

      expect(fakeClient.get).toHaveBeenCalledWith('/api/v1/exams/', { params: undefined });
      expect(result).toEqual(response);
    });

    it('passes search and status params', async () => {
      const response: ExamListResponse = { total: 1, exams: [makeExam()] };
      fakeClient.get.mockResolvedValueOnce({ data: response });

      await ComposerService.listExams({ status: 'draft', search: 'test', limit: 10, offset: 0 });

      expect(fakeClient.get).toHaveBeenCalledWith('/api/v1/exams/', {
        params: { status: 'draft', search: 'test', limit: 10, offset: 0 },
      });
    });

    it('returns the full response', async () => {
      const response: ExamListResponse = { total: 1, exams: [makeExam({ id: 5, title: 'My Exam' })] };
      fakeClient.get.mockResolvedValueOnce({ data: response });

      const result = await ComposerService.listExams();

      expect(result.total).toBe(1);
      expect(result.exams[0].title).toBe('My Exam');
    });
  });

  // -------------------------------------------------------------------------
  // getExam
  // -------------------------------------------------------------------------

  describe('getExam', () => {
    it('calls GET /api/v1/exams/:id', async () => {
      const detail = makeExamDetail({ id: 42 });
      fakeClient.get.mockResolvedValueOnce({ data: detail });

      const result = await ComposerService.getExam(42);

      expect(fakeClient.get).toHaveBeenCalledWith('/api/v1/exams/42');
      expect(result.id).toBe(42);
    });
  });

  // -------------------------------------------------------------------------
  // createExam
  // -------------------------------------------------------------------------

  describe('createExam', () => {
    it('calls POST /api/v1/exams/', async () => {
      const payload: CreateExamRequest = { title: 'New Exam', language: 'de' };
      fakeClient.post.mockResolvedValueOnce({ data: makeExam({ title: 'New Exam' }) });

      const result = await ComposerService.createExam(payload);

      expect(fakeClient.post).toHaveBeenCalledWith('/api/v1/exams/', payload);
      expect(result.title).toBe('New Exam');
    });
  });

  // -------------------------------------------------------------------------
  // updateExam
  // -------------------------------------------------------------------------

  describe('updateExam', () => {
    it('calls PUT /api/v1/exams/:id', async () => {
      const payload: UpdateExamRequest = { title: 'Updated', updated_at: '2025-01-02T00:00:00Z' };
      fakeClient.put.mockResolvedValueOnce({ data: makeExam({ title: 'Updated' }) });

      const result = await ComposerService.updateExam(1, payload);

      expect(fakeClient.put).toHaveBeenCalledWith('/api/v1/exams/1', payload);
      expect(result.title).toBe('Updated');
    });
  });

  // -------------------------------------------------------------------------
  // deleteExam
  // -------------------------------------------------------------------------

  describe('deleteExam', () => {
    it('calls DELETE /api/v1/exams/:id', async () => {
      fakeClient.delete.mockResolvedValueOnce({ data: undefined });

      await ComposerService.deleteExam(5);

      expect(fakeClient.delete).toHaveBeenCalledWith('/api/v1/exams/5');
    });
  });

  // -------------------------------------------------------------------------
  // archiveExam / restoreExam (TF-398)
  // -------------------------------------------------------------------------

  describe('archiveExam', () => {
    it('posts to /archive with a reason', async () => {
      fakeClient.post.mockResolvedValueOnce({
        data: makeExam({ id: 5, archived_at: '2025-02-01T00:00:00Z' }),
      });

      const result = await ComposerService.archiveExam(5, 'veraltet');

      expect(fakeClient.post).toHaveBeenCalledWith('/api/v1/exams/5/archive', {
        reason: 'veraltet',
      });
      expect(result.archived_at).not.toBeNull();
    });

    it('sends reason=null when omitted', async () => {
      fakeClient.post.mockResolvedValueOnce({ data: makeExam({ id: 5 }) });

      await ComposerService.archiveExam(5);

      expect(fakeClient.post).toHaveBeenCalledWith('/api/v1/exams/5/archive', {
        reason: null,
      });
    });
  });

  describe('restoreExam', () => {
    it('posts to /restore', async () => {
      fakeClient.post.mockResolvedValueOnce({ data: makeExam({ id: 5 }) });

      await ComposerService.restoreExam(5);

      expect(fakeClient.post).toHaveBeenCalledWith('/api/v1/exams/5/restore');
    });
  });

  // -------------------------------------------------------------------------
  // addQuestions
  // -------------------------------------------------------------------------

  describe('addQuestions', () => {
    it('posts question_ids', async () => {
      fakeClient.post.mockResolvedValueOnce({ data: makeExamDetail() });

      await ComposerService.addQuestions(1, [10, 20]);

      expect(fakeClient.post).toHaveBeenCalledWith('/api/v1/exams/1/questions', {
        question_ids: [10, 20],
      });
    });
  });

  // -------------------------------------------------------------------------
  // updateExamQuestion
  // -------------------------------------------------------------------------

  describe('updateExamQuestion', () => {
    it('calls PUT /api/v1/exams/:id/questions/:eqId', async () => {
      fakeClient.put.mockResolvedValueOnce({ data: makeExamDetail() });

      await ComposerService.updateExamQuestion(1, 99, { points: 5, section: 'A' });

      expect(fakeClient.put).toHaveBeenCalledWith('/api/v1/exams/1/questions/99', {
        points: 5,
        section: 'A',
      });
    });
  });

  // -------------------------------------------------------------------------
  // removeExamQuestion
  // -------------------------------------------------------------------------

  describe('removeExamQuestion', () => {
    it('calls DELETE /api/v1/exams/:id/questions/:eqId', async () => {
      fakeClient.delete.mockResolvedValueOnce({ data: makeExamDetail() });

      await ComposerService.removeExamQuestion(1, 99);

      expect(fakeClient.delete).toHaveBeenCalledWith('/api/v1/exams/1/questions/99');
    });
  });

  // -------------------------------------------------------------------------
  // reorderQuestions
  // -------------------------------------------------------------------------

  describe('reorderQuestions', () => {
    it('posts order array', async () => {
      fakeClient.post.mockResolvedValueOnce({ data: makeExamDetail() });

      await ComposerService.reorderQuestions(1, [{ id: 2, position: 0 }, { id: 1, position: 1 }]);

      expect(fakeClient.post).toHaveBeenCalledWith('/api/v1/exams/1/reorder', {
        order: [{ id: 2, position: 0 }, { id: 1, position: 1 }],
      });
    });
  });

  // -------------------------------------------------------------------------
  // autoFill
  // -------------------------------------------------------------------------

  describe('autoFill', () => {
    it('posts auto-fill request', async () => {
      fakeClient.post.mockResolvedValueOnce({ data: makeExamDetail() });

      const request: AutoFillRequest = { count: 5, difficulty: ['easy', 'medium'] };
      await ComposerService.autoFill(1, request);

      expect(fakeClient.post).toHaveBeenCalledWith('/api/v1/exams/1/auto-fill', request);
    });
  });

  // -------------------------------------------------------------------------
  // finalizeExam
  // -------------------------------------------------------------------------

  describe('finalizeExam', () => {
    it('posts to /finalize', async () => {
      fakeClient.post.mockResolvedValueOnce({ data: makeExam({ status: ExamStatus.FINALIZED }) });

      const result = await ComposerService.finalizeExam(1);

      expect(fakeClient.post).toHaveBeenCalledWith('/api/v1/exams/1/finalize');
      expect(result.status).toBe(ExamStatus.FINALIZED);
    });
  });

  // -------------------------------------------------------------------------
  // unfinalizeExam
  // -------------------------------------------------------------------------

  describe('unfinalizeExam', () => {
    it('posts to /unfinalize', async () => {
      fakeClient.post.mockResolvedValueOnce({ data: makeExam() });

      await ComposerService.unfinalizeExam(1);

      expect(fakeClient.post).toHaveBeenCalledWith('/api/v1/exams/1/unfinalize');
    });
  });

  // -------------------------------------------------------------------------
  // listApprovedQuestions
  // -------------------------------------------------------------------------

  describe('listApprovedQuestions', () => {
    it('calls GET without params', async () => {
      const response: ApprovedQuestionsResponse = { total: 0, questions: [] };
      fakeClient.get.mockResolvedValueOnce({ data: response });

      await ComposerService.listApprovedQuestions();

      // The service destructures `document_ids` and spreads the rest into a
      // new params object, so callers without arguments get `params: {}`
      // (TF-321 introduced this when adding the document_ids array→csv
      // serialization). axios drops empty params from the URL anyway, so
      // there's no behavioral difference vs. `undefined`.
      expect(fakeClient.get).toHaveBeenCalledWith('/api/v1/exams/approved-questions', {
        params: {},
      });
    });

    it('passes filter params', async () => {
      fakeClient.get.mockResolvedValueOnce({ data: { total: 0, questions: [] } });

      await ComposerService.listApprovedQuestions({ topic: 'Math', limit: 20 });

      expect(fakeClient.get).toHaveBeenCalledWith('/api/v1/exams/approved-questions', {
        params: { topic: 'Math', limit: 20 },
      });
    });

    // TF-406: Fachfilter-Facetten + Sortierung
    it('passes the new facet params (ln_level, competency_id, quality_tier, bloom_level)', async () => {
      fakeClient.get.mockResolvedValueOnce({ data: { total: 0, questions: [] } });

      await ComposerService.listApprovedQuestions({
        ln_level: 3,
        competency_id: 7,
        quality_tier: 'A',
        bloom_level: 4,
      });

      expect(fakeClient.get).toHaveBeenCalledWith('/api/v1/exams/approved-questions', {
        params: { ln_level: 3, competency_id: 7, quality_tier: 'A', bloom_level: 4 },
      });
    });

    it('includes sort only when it differs from "newest"', async () => {
      fakeClient.get.mockResolvedValueOnce({ data: { total: 0, questions: [] } });
      await ComposerService.listApprovedQuestions({ sort: 'most_used' });
      expect(fakeClient.get).toHaveBeenCalledWith('/api/v1/exams/approved-questions', {
        params: { sort: 'most_used' },
      });

      fakeClient.get.mockResolvedValueOnce({ data: { total: 0, questions: [] } });
      await ComposerService.listApprovedQuestions({ sort: 'newest' });
      expect(fakeClient.get).toHaveBeenLastCalledWith('/api/v1/exams/approved-questions', {
        params: {},
      });
    });

    it('includes unused only when true', async () => {
      fakeClient.get.mockResolvedValueOnce({ data: { total: 0, questions: [] } });
      await ComposerService.listApprovedQuestions({ unused: true });
      expect(fakeClient.get).toHaveBeenCalledWith('/api/v1/exams/approved-questions', {
        params: { unused: true },
      });

      fakeClient.get.mockResolvedValueOnce({ data: { total: 0, questions: [] } });
      await ComposerService.listApprovedQuestions({ unused: false });
      expect(fakeClient.get).toHaveBeenLastCalledWith('/api/v1/exams/approved-questions', {
        params: {},
      });
    });
  });

  // -------------------------------------------------------------------------
  // downloadExport
  // -------------------------------------------------------------------------

  describe('downloadExport', () => {
    let mockCreateObjectURL: jest.Mock;
    let mockRevokeObjectURL: jest.Mock;
    let mockClick: jest.Mock;

    beforeEach(() => {
      mockCreateObjectURL = jest.fn().mockReturnValue('blob:http://localhost/fake');
      mockRevokeObjectURL = jest.fn();
      mockClick = jest.fn();

      window.URL.createObjectURL = mockCreateObjectURL;
      window.URL.revokeObjectURL = mockRevokeObjectURL;

      jest.spyOn(document.body, 'appendChild').mockImplementation(jest.fn() as any);
      jest.spyOn(document.body, 'removeChild').mockImplementation(jest.fn() as any);
    });

    afterEach(() => {
      jest.restoreAllMocks();
    });

    it('fetches blob and triggers click for download', async () => {
      fakeClient.get.mockResolvedValueOnce({
        data: new Blob(['content']),
        headers: { 'content-disposition': 'attachment; filename="exam_1.md"' },
      });
      jest.spyOn(document, 'createElement').mockImplementation((tag: string) => {
        if (tag === 'a') {
          return { href: '', download: '', click: mockClick, remove: jest.fn() } as unknown as HTMLAnchorElement;
        }
        return document.createElement.bind(document)(tag);
      });

      await ComposerService.downloadExport(1, 'markdown', false);

      expect(fakeClient.get).toHaveBeenCalledWith(
        '/api/v1/exams/1/export/markdown',
        expect.objectContaining({ responseType: 'blob' })
      );
      expect(mockCreateObjectURL).toHaveBeenCalled();
      expect(mockClick).toHaveBeenCalled();
      expect(mockRevokeObjectURL).toHaveBeenCalled();
    });

    it('sets include_solutions=true when format is markdown and flag is true', async () => {
      fakeClient.get.mockResolvedValueOnce({ data: new Blob(['content']), headers: {} });
      jest.spyOn(document, 'createElement').mockReturnValue(
        { href: '', download: '', click: mockClick, remove: jest.fn() } as unknown as HTMLAnchorElement
      );

      await ComposerService.downloadExport(1, 'markdown', true);

      const params: URLSearchParams = fakeClient.get.mock.calls[0][1].params;
      expect(params.get('include_solutions')).toBe('true');
    });

    it('does NOT set include_solutions for json format when flag is false', async () => {
      fakeClient.get.mockResolvedValueOnce({ data: new Blob(['content']), headers: {} });
      jest.spyOn(document, 'createElement').mockReturnValue(
        { href: '', download: '', click: mockClick, remove: jest.fn() } as unknown as HTMLAnchorElement
      );

      // The service passes includeSolutions=false for json (handled by ExportDialog)
      await ComposerService.downloadExport(1, 'json', false);

      const params: URLSearchParams = fakeClient.get.mock.calls[0][1].params;
      expect(params.get('include_solutions')).toBeNull();
    });

    it('uses fallback filename when content-disposition missing', async () => {
      fakeClient.get.mockResolvedValueOnce({ data: new Blob(['content']), headers: {} });

      let mockCapturedLink: any = null;
      jest.spyOn(document, 'createElement').mockImplementation((tag: string) => {
        if (tag === 'a') {
          mockCapturedLink = { href: '', download: '', click: mockClick, remove: jest.fn() };
          return mockCapturedLink;
        }
        return document.createElement.bind(document)(tag);
      });

      await ComposerService.downloadExport(3, 'json', false);

      expect(mockCapturedLink?.download).toBe('exam_export.json');
    });
  });


});
