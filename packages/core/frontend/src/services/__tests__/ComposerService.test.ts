/**
 * ComposerService Tests
 *
 * We mock axios entirely to avoid ESM parsing issues.
 * The mock is self-contained: we capture the fake instance via a closure
 * that is evaluated lazily (when the interceptor is invoked at module load
 * time), so we avoid TDZ errors from jest.mock hoisting.
 */

jest.mock('axios', () => {
  const makeInstance = () => ({
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() },
    },
  });
  const instance = makeInstance();
  return {
    __esModule: true,
    default: {
      create: jest.fn(() => instance),
      // Expose instance for tests via a non-standard property
      __instance: instance,
    },
  };
});

import axios from 'axios';
import { ComposerService } from '../ComposerService';
import type {
  CreateExamRequest,
  UpdateExamRequest,
  AutoFillRequest,
  Exam,
  ExamDetail,
  ExamListResponse,
  ApprovedQuestionsResponse,
} from '../../types/composer';
import { ExamStatus } from '../../types/composer';

// Retrieve the fake instance that was created when ComposerService was loaded.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const fakeInstance = (axios as any).__instance as {
  get: jest.Mock;
  post: jest.Mock;
  put: jest.Mock;
  delete: jest.Mock;
  interceptors: { request: { use: jest.Mock }; response: { use: jest.Mock } };
};

// Capture the interceptor callback BEFORE any clearAllMocks() can wipe it.
// ComposerService registers it at module load time (during the import above).
const requestInterceptorFn: (config: { headers: Record<string, string> }) => any =
  fakeInstance.interceptors.request.use.mock.calls[0][0];

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
      fakeInstance.get.mockResolvedValueOnce({ data: response });

      const result = await ComposerService.listExams();

      expect(fakeInstance.get).toHaveBeenCalledWith('/api/v1/exams/', { params: undefined });
      expect(result).toEqual(response);
    });

    it('passes search and status params', async () => {
      const response: ExamListResponse = { total: 1, exams: [makeExam()] };
      fakeInstance.get.mockResolvedValueOnce({ data: response });

      await ComposerService.listExams({ status: 'draft', search: 'test', limit: 10, offset: 0 });

      expect(fakeInstance.get).toHaveBeenCalledWith('/api/v1/exams/', {
        params: { status: 'draft', search: 'test', limit: 10, offset: 0 },
      });
    });

    it('returns the full response', async () => {
      const response: ExamListResponse = { total: 1, exams: [makeExam({ id: 5, title: 'My Exam' })] };
      fakeInstance.get.mockResolvedValueOnce({ data: response });

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
      fakeInstance.get.mockResolvedValueOnce({ data: detail });

      const result = await ComposerService.getExam(42);

      expect(fakeInstance.get).toHaveBeenCalledWith('/api/v1/exams/42');
      expect(result.id).toBe(42);
    });
  });

  // -------------------------------------------------------------------------
  // createExam
  // -------------------------------------------------------------------------

  describe('createExam', () => {
    it('calls POST /api/v1/exams/', async () => {
      const payload: CreateExamRequest = { title: 'New Exam', language: 'de' };
      fakeInstance.post.mockResolvedValueOnce({ data: makeExam({ title: 'New Exam' }) });

      const result = await ComposerService.createExam(payload);

      expect(fakeInstance.post).toHaveBeenCalledWith('/api/v1/exams/', payload);
      expect(result.title).toBe('New Exam');
    });
  });

  // -------------------------------------------------------------------------
  // updateExam
  // -------------------------------------------------------------------------

  describe('updateExam', () => {
    it('calls PUT /api/v1/exams/:id', async () => {
      const payload: UpdateExamRequest = { title: 'Updated', updated_at: '2025-01-02T00:00:00Z' };
      fakeInstance.put.mockResolvedValueOnce({ data: makeExam({ title: 'Updated' }) });

      const result = await ComposerService.updateExam(1, payload);

      expect(fakeInstance.put).toHaveBeenCalledWith('/api/v1/exams/1', payload);
      expect(result.title).toBe('Updated');
    });
  });

  // -------------------------------------------------------------------------
  // deleteExam
  // -------------------------------------------------------------------------

  describe('deleteExam', () => {
    it('calls DELETE /api/v1/exams/:id', async () => {
      fakeInstance.delete.mockResolvedValueOnce({ data: undefined });

      await ComposerService.deleteExam(5);

      expect(fakeInstance.delete).toHaveBeenCalledWith('/api/v1/exams/5');
    });
  });

  // -------------------------------------------------------------------------
  // addQuestions
  // -------------------------------------------------------------------------

  describe('addQuestions', () => {
    it('posts question_ids', async () => {
      fakeInstance.post.mockResolvedValueOnce({ data: makeExamDetail() });

      await ComposerService.addQuestions(1, [10, 20]);

      expect(fakeInstance.post).toHaveBeenCalledWith('/api/v1/exams/1/questions', {
        question_ids: [10, 20],
      });
    });
  });

  // -------------------------------------------------------------------------
  // updateExamQuestion
  // -------------------------------------------------------------------------

  describe('updateExamQuestion', () => {
    it('calls PUT /api/v1/exams/:id/questions/:eqId', async () => {
      fakeInstance.put.mockResolvedValueOnce({ data: makeExamDetail() });

      await ComposerService.updateExamQuestion(1, 99, { points: 5, section: 'A' });

      expect(fakeInstance.put).toHaveBeenCalledWith('/api/v1/exams/1/questions/99', {
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
      fakeInstance.delete.mockResolvedValueOnce({ data: makeExamDetail() });

      await ComposerService.removeExamQuestion(1, 99);

      expect(fakeInstance.delete).toHaveBeenCalledWith('/api/v1/exams/1/questions/99');
    });
  });

  // -------------------------------------------------------------------------
  // reorderQuestions
  // -------------------------------------------------------------------------

  describe('reorderQuestions', () => {
    it('posts order array', async () => {
      fakeInstance.post.mockResolvedValueOnce({ data: makeExamDetail() });

      await ComposerService.reorderQuestions(1, [{ id: 2, position: 0 }, { id: 1, position: 1 }]);

      expect(fakeInstance.post).toHaveBeenCalledWith('/api/v1/exams/1/reorder', {
        order: [{ id: 2, position: 0 }, { id: 1, position: 1 }],
      });
    });
  });

  // -------------------------------------------------------------------------
  // autoFill
  // -------------------------------------------------------------------------

  describe('autoFill', () => {
    it('posts auto-fill request', async () => {
      fakeInstance.post.mockResolvedValueOnce({ data: makeExamDetail() });

      const request: AutoFillRequest = { count: 5, difficulty: ['easy', 'medium'] };
      await ComposerService.autoFill(1, request);

      expect(fakeInstance.post).toHaveBeenCalledWith('/api/v1/exams/1/auto-fill', request);
    });
  });

  // -------------------------------------------------------------------------
  // finalizeExam
  // -------------------------------------------------------------------------

  describe('finalizeExam', () => {
    it('posts to /finalize', async () => {
      fakeInstance.post.mockResolvedValueOnce({ data: makeExam({ status: ExamStatus.FINALIZED }) });

      const result = await ComposerService.finalizeExam(1);

      expect(fakeInstance.post).toHaveBeenCalledWith('/api/v1/exams/1/finalize');
      expect(result.status).toBe(ExamStatus.FINALIZED);
    });
  });

  // -------------------------------------------------------------------------
  // unfinalizeExam
  // -------------------------------------------------------------------------

  describe('unfinalizeExam', () => {
    it('posts to /unfinalize', async () => {
      fakeInstance.post.mockResolvedValueOnce({ data: makeExam() });

      await ComposerService.unfinalizeExam(1);

      expect(fakeInstance.post).toHaveBeenCalledWith('/api/v1/exams/1/unfinalize');
    });
  });

  // -------------------------------------------------------------------------
  // listApprovedQuestions
  // -------------------------------------------------------------------------

  describe('listApprovedQuestions', () => {
    it('calls GET without params', async () => {
      const response: ApprovedQuestionsResponse = { total: 0, questions: [] };
      fakeInstance.get.mockResolvedValueOnce({ data: response });

      await ComposerService.listApprovedQuestions();

      expect(fakeInstance.get).toHaveBeenCalledWith('/api/v1/exams/approved-questions', {
        params: undefined,
      });
    });

    it('passes filter params', async () => {
      fakeInstance.get.mockResolvedValueOnce({ data: { total: 0, questions: [] } });

      await ComposerService.listApprovedQuestions({ topic: 'Math', limit: 20 });

      expect(fakeInstance.get).toHaveBeenCalledWith('/api/v1/exams/approved-questions', {
        params: { topic: 'Math', limit: 20 },
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
      fakeInstance.get.mockResolvedValueOnce({
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

      expect(fakeInstance.get).toHaveBeenCalledWith(
        '/api/v1/exams/1/export/markdown',
        expect.objectContaining({ responseType: 'blob' })
      );
      expect(mockCreateObjectURL).toHaveBeenCalled();
      expect(mockClick).toHaveBeenCalled();
      expect(mockRevokeObjectURL).toHaveBeenCalled();
    });

    it('sets include_solutions=true when format is markdown and flag is true', async () => {
      fakeInstance.get.mockResolvedValueOnce({ data: new Blob(['content']), headers: {} });
      jest.spyOn(document, 'createElement').mockReturnValue(
        { href: '', download: '', click: mockClick, remove: jest.fn() } as unknown as HTMLAnchorElement
      );

      await ComposerService.downloadExport(1, 'markdown', true);

      const params: URLSearchParams = fakeInstance.get.mock.calls[0][1].params;
      expect(params.get('include_solutions')).toBe('true');
    });

    it('does NOT set include_solutions for json format when flag is false', async () => {
      fakeInstance.get.mockResolvedValueOnce({ data: new Blob(['content']), headers: {} });
      jest.spyOn(document, 'createElement').mockReturnValue(
        { href: '', download: '', click: mockClick, remove: jest.fn() } as unknown as HTMLAnchorElement
      );

      // The service passes includeSolutions=false for json (handled by ExportDialog)
      await ComposerService.downloadExport(1, 'json', false);

      const params: URLSearchParams = fakeInstance.get.mock.calls[0][1].params;
      expect(params.get('include_solutions')).toBeNull();
    });

    it('uses fallback filename when content-disposition missing', async () => {
      fakeInstance.get.mockResolvedValueOnce({ data: new Blob(['content']), headers: {} });

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

  // -------------------------------------------------------------------------
  // Auth token interceptor
  // -------------------------------------------------------------------------

  describe('auth token interceptor', () => {
    // requestInterceptorFn is captured at module scope before any clearAllMocks() runs

    it('is registered as a function', () => {
      expect(requestInterceptorFn).toBeDefined();
      expect(typeof requestInterceptorFn).toBe('function');
    });

    it('adds Bearer token from localStorage', () => {
      localStorage.setItem('examcraft_access_token', 'my-test-token');

      const config = { headers: {} as Record<string, string> };
      const result = requestInterceptorFn(config);

      expect(result.headers.Authorization).toBe('Bearer my-test-token');
    });

    it('skips Authorization when no token stored', () => {
      localStorage.removeItem('examcraft_access_token');

      const config = { headers: {} as Record<string, string> };
      const result = requestInterceptorFn(config);

      expect(result.headers.Authorization).toBeUndefined();
    });
  });
});
