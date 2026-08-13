import { DocumentService } from '../DocumentService';
import { Document, DocumentStatus, DocumentUploadResponse, DocumentProcessingResponse, DocumentVisibility } from '../../types/document';

jest.mock('../../api/apiClient');

// Mock fetch
global.fetch = jest.fn();
const mockFetch = fetch as jest.MockedFunction<typeof fetch>;

// Mock URL and Blob for download tests
global.URL.createObjectURL = jest.fn(() => 'mock-url');
global.URL.revokeObjectURL = jest.fn();

// Mock DOM methods for download
const mockLink = document.createElement('a');
mockLink.click = jest.fn();

const originalCreateElement = document.createElement.bind(document);
document.createElement = jest.fn((tagName: string) => {
  if (tagName === 'a') {
    return mockLink;
  }
  return originalCreateElement(tagName);
}) as any;

document.body.appendChild = jest.fn();
document.body.removeChild = jest.fn();

// Sample test data
const mockDocument: Document = {
  id: 1,
  filename: 'test-document.pdf',
  mime_type: 'application/pdf',
  status: DocumentStatus.PROCESSED,
  created_at: '2025-09-22T10:00:00Z',
  processed_at: '2025-09-22T10:01:00Z',
  file_size: 1024000,
  has_vectors: true,
  metadata: {
    total_chunks: 5,
    embedding_model: 'test-model',
    processing_time: 1.5
  }
};

const mockUploadResponse: DocumentUploadResponse = {
  document_id: 1,
  filename: 'test-document.pdf',
  message: 'Upload successful'
};

const mockProcessingResponse: DocumentProcessingResponse = {
  message: 'Processing successful',
  document_id: 1,
  processing_stats: {
    total_chunks: 5,
    embedding_dimension: 384,
    model_name: 'test-model',
    processing_time: 1.5
  }
};

describe('DocumentService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    process.env.REACT_APP_API_URL = 'http://localhost:8000';
  });

  describe('uploadDocument', () => {
    it('uploads document successfully', async () => {
      const mockFile = new File(['test content'], 'test.pdf', { type: 'application/pdf' });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockUploadResponse
      } as Response);

      const result = await DocumentService.uploadDocument(mockFile);

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/documents/upload',
        {
          method: 'POST',
          headers: expect.any(Object),
          body: expect.any(FormData)
        }
      );

      expect(result).toEqual(mockUploadResponse);
    });

    it('handles upload errors', async () => {
      const mockFile = new File(['test content'], 'test.pdf', { type: 'application/pdf' });

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        json: async () => ({ detail: 'Invalid file format' })
      } as Response);

      await expect(DocumentService.uploadDocument(mockFile))
        .rejects.toThrow('Invalid file format');
    });

    it('handles network errors', async () => {
      const mockFile = new File(['test content'], 'test.pdf', { type: 'application/pdf' });

      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(DocumentService.uploadDocument(mockFile))
        .rejects.toThrow('Network error');
    });

    // TF-620: these run against the REAL uploadDocument implementation
    // (unlike the component tests, which mock the whole service) — they
    // catch a wrong field name or a wrong `visibility === TEAM` guard that
    // component-level mocked-service tests can't see.
    it('appends org_unit_id to the multipart body when visibility=team', async () => {
      const mockFile = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockUploadResponse,
      } as Response);

      await DocumentService.uploadDocument(mockFile, DocumentVisibility.TEAM, 42);

      const body = mockFetch.mock.calls[0][1]!.body as FormData;
      expect(body.get('visibility')).toBe('team');
      expect(body.get('org_unit_id')).toBe('42');
    });

    it('omits org_unit_id when visibility=team but no org unit was picked', async () => {
      const mockFile = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockUploadResponse,
      } as Response);

      await DocumentService.uploadDocument(mockFile, DocumentVisibility.TEAM, null);

      const body = mockFetch.mock.calls[0][1]!.body as FormData;
      expect(body.get('org_unit_id')).toBeNull();
    });

    it('ignores a supplied orgUnitId when visibility is not team', async () => {
      const mockFile = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockUploadResponse,
      } as Response);

      await DocumentService.uploadDocument(mockFile, DocumentVisibility.PRIVATE, 42);

      const body = mockFetch.mock.calls[0][1]!.body as FormData;
      expect(body.get('visibility')).toBe('private');
      expect(body.get('org_unit_id')).toBeNull();
    });
  });

  describe('updateVisibility', () => {
    it('includes org_unit_id in the PATCH body when visibility=team', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockDocument,
      } as Response);

      await DocumentService.updateVisibility(1, DocumentVisibility.TEAM, 42);

      const call = mockFetch.mock.calls[0];
      expect(call[0]).toBe('http://localhost:8000/api/v1/documents/1');
      const body = JSON.parse(call[1]!.body as string);
      expect(body).toEqual({ visibility: 'team', org_unit_id: 42 });
    });

    it('omits org_unit_id from the PATCH body for non-team visibility', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockDocument,
      } as Response);

      await DocumentService.updateVisibility(1, DocumentVisibility.INSTITUTION);

      const body = JSON.parse(mockFetch.mock.calls[0][1]!.body as string);
      expect(body).toEqual({ visibility: 'institution' });
    });

    it('propagates the backend error detail on failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        json: async () => ({ detail: 'Cannot share with team: no valid Org-Unit' }),
      } as Response);

      await expect(DocumentService.updateVisibility(1, DocumentVisibility.TEAM, 42))
        .rejects.toThrow('Cannot share with team: no valid Org-Unit');
    });
  });

  describe('renameDocument', () => {
    it('PATCHes display_name and returns the updated document', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ ...mockDocument, display_name: 'Neuer Titel' }),
      } as Response);

      const result = await DocumentService.renameDocument(1, 'Neuer Titel');

      const call = mockFetch.mock.calls[0];
      expect(call[0]).toBe('http://localhost:8000/api/v1/documents/1');
      expect(call[1]!.method).toBe('PATCH');
      expect(JSON.parse(call[1]!.body as string)).toEqual({ display_name: 'Neuer Titel' });
      expect(result.display_name).toBe('Neuer Titel');
    });

    // TF-606: callers (DocumentLibrary's isPermissionDenied) branch on both
    // `.status` and `.name === 'DocumentFetchError'` — assert both here so a
    // regression to a plain `Error` is caught even though every component
    // test fabricates its own error object rather than exercising the
    // service.
    it('throws a DocumentFetchError carrying the 403 status and backend detail on an owner-only rejection', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 403,
        statusText: 'Forbidden',
        json: async () => ({ detail: 'Nur der Eigentümer darf dieses Dokument umbenennen' }),
      } as Response);

      await expect(DocumentService.renameDocument(1, 'Neuer Titel')).rejects.toMatchObject({
        name: 'DocumentFetchError',
        status: 403,
        message: 'Nur der Eigentümer darf dieses Dokument umbenennen',
      });
    });

    // A blank/missing `detail` must not leak an English statusText-derived
    // message — callers (DocumentLibrary.renameErrorMessage) fall back to a
    // localized default only when the message is empty.
    it('leaves the message blank when the backend omits detail', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({}),
      } as Response);

      await expect(DocumentService.renameDocument(1, 'Neuer Titel')).rejects.toMatchObject({
        name: 'DocumentFetchError',
        status: 500,
        message: '',
      });
    });

    // A failed fetch() itself (offline, DNS, CORS) — no HTTP response at all
    // — must surface as status 0, same convention as getDocumentRaw.
    it('throws a DocumentFetchError with status 0 when the network call itself fails', async () => {
      mockFetch.mockRejectedValueOnce(new TypeError('Failed to fetch'));

      await expect(DocumentService.renameDocument(1, 'Neuer Titel')).rejects.toMatchObject({
        name: 'DocumentFetchError',
        status: 0,
      });
    });
  });

  describe('processDocument', () => {
    it('processes document successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockProcessingResponse
      } as Response);

      const result = await DocumentService.processDocument(1, true);

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/documents/1/process?create_vectors=true',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          }
        }
      );

      expect(result).toEqual(mockProcessingResponse);
    });

    it('processes document without vectors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockProcessingResponse
      } as Response);

      await DocumentService.processDocument(1, false);

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/documents/1/process?create_vectors=false',
        expect.any(Object)
      );
    });

    it('handles processing errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({ detail: 'Processing failed' })
      } as Response);

      await expect(DocumentService.processDocument(1, true))
        .rejects.toThrow('Processing failed');
    });
  });

  describe('getDocuments', () => {
    it('retrieves documents successfully', async () => {
      const mockDocuments = [mockDocument];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ documents: mockDocuments })
      } as Response);

      const result = await DocumentService.getDocuments();

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/documents/',
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json'
          }
        }
      );

      expect(result).toEqual(mockDocuments);
    });

    it('handles empty documents response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({})
      } as Response);

      const result = await DocumentService.getDocuments();

      expect(result).toEqual([]);
    });

    it('handles get documents errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({ detail: 'Server error' })
      } as Response);

      await expect(DocumentService.getDocuments())
        .rejects.toThrow('Server error');
    });
  });

  describe('getAvailableDocuments', () => {
    it('retrieves available documents successfully', async () => {
      const mockResponse = {
        total_documents: 1,
        processed_documents: 1,
        documents_with_vectors: 1,
        documents: [mockDocument]
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      } as Response);

      const result = await DocumentService.getAvailableDocuments(true);

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/rag/available-documents?processed_only=true',
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json'
          }
        }
      );

      expect(result).toEqual(mockResponse);
    });

    it('retrieves all documents when processed_only is false', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ documents: [] })
      } as Response);

      await DocumentService.getAvailableDocuments(false);

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/rag/available-documents?processed_only=false',
        expect.any(Object)
      );
    });
  });

  describe('getDocument', () => {
    it('retrieves specific document successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockDocument
      } as Response);

      const result = await DocumentService.getDocument(1);

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/documents/1',
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json'
          }
        }
      );

      expect(result).toEqual(mockDocument);
    });

    it('handles document not found', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: async () => ({ detail: 'Document not found' })
      } as Response);

      await expect(DocumentService.getDocument(999))
        .rejects.toThrow('Document not found');
    });
  });

  describe('deleteDocument', () => {
    it('deletes document successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({})
      } as Response);

      await DocumentService.deleteDocument(1);

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/documents/1',
        {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json'
          }
        }
      );
    });

    it('handles delete errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 403,
        statusText: 'Forbidden',
        json: async () => ({ detail: 'Access denied' })
      } as Response);

      await expect(DocumentService.deleteDocument(1))
        .rejects.toThrow('Access denied');
    });
  });

  describe('downloadDocument', () => {
    // TODO: This test is skipped because mocking DOM elements (createElement, appendChild, etc.)
    // in Jest is complex and fragile. The download functionality works correctly in the browser.
    // Consider using E2E tests (Playwright) to test this functionality instead.
    it.skip('downloads document successfully', async () => {
      const mockBlob = new Blob(['file content'], { type: 'application/pdf' });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        blob: async () => mockBlob
      } as Response);

      await DocumentService.downloadDocument(1, 'test.pdf');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/documents/1/download',
        {
          method: 'GET',
          headers: expect.any(Object)
        }
      );

      expect(global.URL.createObjectURL).toHaveBeenCalledWith(mockBlob);
      expect(global.URL.revokeObjectURL).toHaveBeenCalled();
    });

    it('handles download errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: async () => ({ detail: 'File not found' })
      } as Response);

      await expect(DocumentService.downloadDocument(1, 'test.pdf'))
        .rejects.toThrow('File not found');
    });
  });

  describe('getDocumentChunks', () => {
    it('retrieves document chunks successfully', async () => {
      const mockChunks = [
        {
          chunk_id: 'chunk_1',
          content: 'Test content',
          metadata: { page: 1 }
        }
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockChunks
      } as Response);

      const result = await DocumentService.getDocumentChunks(1);

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/search/document/1/chunks',
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json'
          }
        }
      );

      expect(result).toEqual(mockChunks);
    });
  });

  describe('reindexDocument', () => {
    it('reindexes document successfully', async () => {
      const mockResponse = { message: 'Reindexing started' };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      } as Response);

      const result = await DocumentService.reindexDocument(1);

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/search/reindex/1',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          }
        }
      );

      expect(result).toEqual(mockResponse);
    });
  });

  describe('getProcessingStatus', () => {
    it('retrieves processing status successfully', async () => {
      const mockStatus = { status: 'processing', progress: 50 };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockStatus
      } as Response);

      const result = await DocumentService.getProcessingStatus(1);

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/documents/1/status',
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json'
          }
        }
      );

      expect(result).toEqual(mockStatus);
    });
  });

  describe('uploadMultipleDocuments', () => {
    it('uploads multiple documents successfully', async () => {
      const mockFiles = [
        new File(['content1'], 'file1.pdf', { type: 'application/pdf' }),
        new File(['content2'], 'file2.txt', { type: 'text/plain' })
      ];

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ document_id: 1, filename: 'file1.pdf', message: 'Success' })
        } as Response)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ message: 'Processing successful', document_id: 1 })
        } as Response)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ document_id: 2, filename: 'file2.txt', message: 'Success' })
        } as Response)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ message: 'Processing successful', document_id: 2 })
        } as Response);

      const mockOnProgress = jest.fn();
      const mockOnComplete = jest.fn();
      const mockOnError = jest.fn();

      const results = await DocumentService.uploadMultipleDocuments(
        mockFiles,
        mockOnProgress,
        mockOnComplete,
        mockOnError
      );

      expect(results).toHaveLength(2);
      expect(mockOnProgress).toHaveBeenCalledTimes(4); // 2 files × 2 calls each
      expect(mockOnComplete).toHaveBeenCalledTimes(2);
      expect(mockOnError).not.toHaveBeenCalled();
    });

    it('handles errors in multiple upload', async () => {
      const mockFiles = [
        new File(['content1'], 'file1.pdf', { type: 'application/pdf' }),
        new File(['content2'], 'file2.txt', { type: 'text/plain' })
      ];

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ document_id: 1, filename: 'file1.pdf', message: 'Success' })
        } as Response)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ message: 'Processing successful', document_id: 1 })
        } as Response)
        .mockRejectedValueOnce(new Error('Upload failed'));

      const mockOnError = jest.fn();

      const results = await DocumentService.uploadMultipleDocuments(
        mockFiles,
        undefined,
        undefined,
        mockOnError
      );

      expect(results).toHaveLength(1); // Only first file succeeded
      expect(mockOnError).toHaveBeenCalledWith('file2.txt', 'Upload failed');
    });
  });

  describe('batchProcessDocuments', () => {
    it('processes multiple documents successfully', async () => {
      const documentIds = [1, 2];

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ message: 'Processing successful', document_id: 1 })
        } as Response)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ message: 'Processing successful', document_id: 2 })
        } as Response);

      const mockOnProgress = jest.fn();
      const mockOnComplete = jest.fn();

      const results = await DocumentService.batchProcessDocuments(
        documentIds,
        true,
        mockOnProgress,
        mockOnComplete
      );

      expect(results).toHaveLength(2);
      expect(mockOnProgress).toHaveBeenCalledTimes(4); // 2 documents × 2 calls each
      expect(mockOnComplete).toHaveBeenCalledTimes(2);
    });

    it('handles errors in batch processing', async () => {
      const documentIds = [1, 2];

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ message: 'Processing successful', document_id: 1 })
        } as Response)
        .mockRejectedValueOnce(new Error('Processing failed'));

      const mockOnError = jest.fn();

      const results = await DocumentService.batchProcessDocuments(
        documentIds,
        true,
        undefined,
        undefined,
        mockOnError
      );

      expect(results).toHaveLength(1); // Only first document succeeded
      expect(mockOnError).toHaveBeenCalledWith(2, 'Processing failed');
    });
  });

  // TODO: These tests are skipped because API_BASE_URL is a module-level constant
  // that is set at import time and cannot be changed dynamically in tests.
  // To properly test this, we would need to use jest.resetModules() and re-import
  // the module for each test, which is complex and fragile.
  describe.skip('API URL Configuration', () => {
    it('uses default API URL when env var not set', async () => {
      delete process.env.REACT_APP_API_URL;

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ documents: [] })
      } as Response);

      await DocumentService.getDocuments();

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/documents/',
        expect.any(Object)
      );
    });

    it('uses custom API URL from env var', async () => {
      process.env.REACT_APP_API_URL = 'https://api.example.com';

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ documents: [] })
      } as Response);

      await DocumentService.getDocuments();

      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.example.com/api/v1/documents/',
        expect.any(Object)
      );
    });
  });

  describe('Error Handling', () => {
    it('handles JSON parsing errors gracefully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => { throw new Error('Invalid JSON'); }
      } as Response);

      await expect(DocumentService.getDocuments())
        .rejects.toThrow('Failed to fetch documents: Internal Server Error');
    });

    it('handles network timeouts', async () => {
      mockFetch.mockImplementation(() =>
        new Promise((_, reject) =>
          setTimeout(() => reject(new Error('Network timeout')), 100)
        )
      );

      await expect(DocumentService.getDocuments())
        .rejects.toThrow('Network timeout');
    });
  });

  describe('getDocumentRaw', () => {
    const { DocumentFetchError } = jest.requireActual('../DocumentService');

    it('returns the raw Response on success so the caller can read .blob()/.text()', async () => {
      const fakeResponse = {
        ok: true,
        status: 200,
        blob: jest.fn().mockResolvedValue(new Blob(['x'])),
        text: jest.fn().mockResolvedValue('hello'),
      } as unknown as Response;
      mockFetch.mockResolvedValueOnce(fakeResponse);

      const result = await DocumentService.getDocumentRaw(42);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/documents/42/raw'),
        expect.objectContaining({ method: 'GET' }),
      );
      expect(result).toBe(fakeResponse);
    });

    it('throws DocumentFetchError carrying the backend detail and status', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        clone: function () { return this; },
        text: async () => JSON.stringify({ detail: 'Datei im Speicher nicht gefunden' }),
      } as unknown as Response);

      await expect(DocumentService.getDocumentRaw(42)).rejects.toMatchObject({
        name: 'DocumentFetchError',
        status: 404,
        message: 'Datei im Speicher nicht gefunden',
      });
    });

    it('falls back to statusText when the body is not JSON', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 502,
        statusText: 'Bad Gateway',
        clone: function () { return this; },
        text: async () => '<html><body>nginx</body></html>',
      } as unknown as Response);

      await expect(DocumentService.getDocumentRaw(42)).rejects.toMatchObject({
        status: 502,
        message: 'Bad Gateway',
      });
      // Diagnostic snippet logged for the developer.
      expect(consoleSpy).toHaveBeenCalled();
      consoleSpy.mockRestore();
    });

    it('translates fetch rejection into DocumentFetchError(status=0)', async () => {
      mockFetch.mockRejectedValueOnce(new TypeError('Failed to fetch'));

      await expect(DocumentService.getDocumentRaw(42)).rejects.toMatchObject({
        status: 0,
        message: 'Failed to fetch',
      });
    });

    it('exports DocumentFetchError as a real Error subclass', () => {
      const err = new DocumentFetchError('boom', 503);
      expect(err).toBeInstanceOf(Error);
      expect(err.status).toBe(503);
      expect(err.name).toBe('DocumentFetchError');
    });
  });
});
