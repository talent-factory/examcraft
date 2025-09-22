import { DocumentService } from '../DocumentService';
import { Document, DocumentStatus, DocumentUploadResponse, DocumentProcessingResponse } from '../../types/document';

// Mock fetch
global.fetch = jest.fn();
const mockFetch = fetch as jest.MockedFunction<typeof fetch>;

// Mock URL and Blob for download tests
global.URL.createObjectURL = jest.fn(() => 'mock-url');
global.URL.revokeObjectURL = jest.fn();

// Mock DOM methods for download
const mockLink = {
  href: '',
  download: '',
  click: jest.fn()
};

Object.defineProperty(document, 'createElement', {
  value: jest.fn(() => mockLink)
});

Object.defineProperty(document.body, 'appendChild', {
  value: jest.fn()
});

Object.defineProperty(document.body, 'removeChild', {
  value: jest.fn()
});

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
    it('downloads document successfully', async () => {
      const mockBlob = new Blob(['file content'], { type: 'application/pdf' });
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        blob: async () => mockBlob
      } as Response);

      await DocumentService.downloadDocument(1, 'test.pdf');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/documents/1/download',
        { method: 'GET' }
      );

      expect(global.URL.createObjectURL).toHaveBeenCalledWith(mockBlob);
      expect(mockLink.download).toBe('test.pdf');
      expect(mockLink.click).toHaveBeenCalled();
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

  describe('API URL Configuration', () => {
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
});
