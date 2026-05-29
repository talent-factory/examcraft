import {
  Document,
  DocumentUploadResponse,
  DocumentProcessingResponse,
  AvailableDocumentsResponse,
  DocumentVisibility,
  DocumentListParams,
  DocumentListResponse,
  DocumentTag,
} from '../types/document';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

/**
 * Error thrown by document fetches that need to react to HTTP status
 * (per-status messaging, auth-redirect, retry decisions). Carries the
 * raw `status` so callers can map to a localized message instead of
 * showing a stack-trace string. `status === 0` means the network call
 * itself failed (offline, DNS, CORS) — no HTTP response was received.
 */
export class DocumentFetchError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'DocumentFetchError';
    this.status = status;
  }
}

export class DocumentService {
  // 401 handling is delegated to the global fetch interceptor installed by
  // AuthContext (see apiClient.setupFetchInterceptor). It transparently
  // refreshes the token and retries through the shared mutex, then triggers
  // logout if refresh fails. This service must not duplicate that logic —
  // doing so causes double-refresh races and forces a hard page reload.

  /**
   * Get auth headers with token
   */
  private static getAuthHeaders(additionalHeaders: HeadersInit = {}): HeadersInit {
    const token = localStorage.getItem('examcraft_access_token');
    return {
      'Content-Type': 'application/json',
      ...additionalHeaders,
      ...(token && { Authorization: `Bearer ${token}` }),
    };
  }

  /**
   * Upload a document file.
   *
   * @param visibility Sharing scope (TF-354). Defaults to `private` so an
   *   upload is owner-only unless the user explicitly shares it.
   */
  static async uploadDocument(
    file: File,
    visibility: DocumentVisibility = DocumentVisibility.PRIVATE,
  ): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('visibility', visibility);

    // For FormData, we must NOT set Content-Type header
    // The browser will set it automatically with the correct multipart/form-data boundary
    const token = localStorage.getItem('examcraft_access_token');
    const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};

    const response = await fetch(`${API_BASE_URL}/api/v1/documents/upload`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Upload failed: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Process a document (extract text and create vectors)
   */
  static async processDocument(
    documentId: number,
    createVectors: boolean = true
  ): Promise<DocumentProcessingResponse> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/documents/${documentId}/process?create_vectors=${createVectors}`,
      {
        method: 'POST',
        headers: this.getAuthHeaders(),
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Processing failed: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Get all documents for the current user
   */
  static async getDocuments(): Promise<Document[]> {
    const response = await fetch(`${API_BASE_URL}/api/v1/documents/`, {
      method: 'GET',
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to fetch documents: ${response.statusText}`);
    }

    const data = await response.json();
    return data.documents || [];
  }

  /**
   * Get available documents for RAG (processed documents only)
   */
  static async getAvailableDocuments(processedOnly: boolean = true): Promise<AvailableDocumentsResponse> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/rag/available-documents?processed_only=${processedOnly}`,
      {
        method: 'GET',
        headers: this.getAuthHeaders(),
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to fetch available documents: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Get a specific document by ID
   */
  static async getDocument(documentId: number): Promise<Document> {
    const response = await fetch(`${API_BASE_URL}/api/v1/documents/${documentId}`, {
      method: 'GET',
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to fetch document: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Set or clear the user-editable display name for a document.
   * Pass null to clear the override and fall back to the resolver chain
   * (filtered metadata title → original filename).
   */
  static async renameDocument(
    documentId: number,
    displayName: string | null,
  ): Promise<Document> {
    const response = await fetch(`${API_BASE_URL}/api/v1/documents/${documentId}`, {
      method: 'PATCH',
      headers: this.getAuthHeaders(),
      body: JSON.stringify({ display_name: displayName }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to rename document: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Update a document's visibility (TF-354). Owner-only on the backend.
   */
  static async updateVisibility(
    documentId: number,
    visibility: DocumentVisibility,
  ): Promise<Document> {
    const response = await fetch(`${API_BASE_URL}/api/v1/documents/${documentId}`, {
      method: 'PATCH',
      headers: this.getAuthHeaders(),
      body: JSON.stringify({ visibility }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to update visibility: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Delete a document
   */
  static async deleteDocument(documentId: number): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/v1/documents/${documentId}`, {
      method: 'DELETE',
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to delete document: ${response.statusText}`);
    }
  }

  /**
   * Download a document
   */
  static async downloadDocument(documentId: number, filename: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/v1/documents/${documentId}/download`, {
      method: 'GET',
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to download document: ${response.statusText}`);
    }

    // Create blob and download
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  }

  /**
   * Fetch raw document bytes with Content-Disposition: inline
   * (vs. downloadDocument which forces attachment). Caller chooses how
   * to consume the Response — .blob() for PDF in an iframe, .text() for
   * Markdown / plain text. Throws `DocumentFetchError` on failure so
   * callers can branch on `.status` for per-status UI messaging.
   */
  static async getDocumentRaw(documentId: number): Promise<Response> {
    let response: Response;
    try {
      response = await fetch(`${API_BASE_URL}/api/v1/documents/${documentId}/raw`, {
        method: 'GET',
        headers: this.getAuthHeaders(),
      });
    } catch (e) {
      throw new DocumentFetchError(
        e && typeof e === 'object' && 'message' in e ? (e as Error).message : 'Network error',
        0,
      );
    }

    if (!response.ok) {
      let detail: string | undefined;
      try {
        const body = await response.clone().text();
        try {
          const parsed = JSON.parse(body);
          if (parsed && typeof parsed.detail === 'string') {
            detail = parsed.detail;
          }
        } catch {
          // Backend returned non-JSON (HTML error page from a proxy, etc.).
          // Surface a snippet to console so a developer reproducing the bug
          // can recover the body — the user-facing message stays generic.
          if (body) {
            // eslint-disable-next-line no-console
            console.error(
              `getDocumentRaw: non-JSON ${response.status} body`,
              body.slice(0, 200),
            );
          }
        }
      } catch {
        // Body unavailable — fall through to statusText.
      }
      throw new DocumentFetchError(
        detail || response.statusText || 'Request failed',
        response.status,
      );
    }

    return response;
  }

  /**
   * Get full document content (for preview)
   */
  static async getDocumentContent(documentId: number): Promise<{
    document_id: number;
    title: string;
    content: string;
    content_length: number;
    metadata?: any;
  }> {
    const response = await fetch(`${API_BASE_URL}/api/v1/documents/${documentId}/content`, {
      method: 'GET',
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to fetch document content: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Get document chunks (for preview)
   */
  static async getDocumentChunks(documentId: number): Promise<any[]> {
    const response = await fetch(`${API_BASE_URL}/api/v1/search/document/${documentId}/chunks`, {
      method: 'GET',
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to fetch document chunks: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Get document chunks with pagination (for large documents)
   */
  static async getDocumentChunksPaginated(
    documentId: number,
    page: number = 1,
    pageSize: number = 10
  ): Promise<{
    document_id: number;
    total_chunks: number;
    total_pages: number;
    current_page: number;
    page_size: number;
    chunks: any[];
  }> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/documents/${documentId}/chunks-paginated?page=${page}&page_size=${pageSize}`,
      {
        method: 'GET',
        headers: this.getAuthHeaders(),
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to fetch document chunks: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Reindex document vectors
   */
  static async reindexDocument(documentId: number): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/api/v1/search/reindex/${documentId}`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to reindex document: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Get processing status of a document
   */
  static async getProcessingStatus(documentId: number): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/api/v1/documents/${documentId}/status`, {
      method: 'GET',
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to get processing status: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Upload multiple documents
   */
  static async uploadMultipleDocuments(
    files: File[],
    onProgress?: (filename: string, progress: number) => void,
    onComplete?: (filename: string, result: DocumentUploadResponse) => void,
    onError?: (filename: string, error: string) => void
  ): Promise<DocumentUploadResponse[]> {
    const results: DocumentUploadResponse[] = [];

    for (const file of files) {
      try {
        onProgress?.(file.name, 0);

        const result = await this.uploadDocument(file);
        results.push(result);

        onProgress?.(file.name, 100);
        onComplete?.(file.name, result);

        // Auto-process the document
        try {
          await this.processDocument(result.document_id, true);
        } catch (processError) {
          console.warn(`Auto-processing failed for ${file.name}:`, processError);
        }

      } catch (error) {
        const errorMessage = error && typeof error === 'object' && 'message' in error ? (error as Error).message : 'Unknown error';
        onError?.(file.name, errorMessage);
      }
    }

    return results;
  }

  /**
   * List documents with filters, pagination and stats (TF-355).
   */
  static async listDocuments(params: DocumentListParams): Promise<DocumentListResponse> {
    const qs = new URLSearchParams();
    if (params.q) qs.set('q', params.q);
    if (params.visibility) qs.set('visibility', params.visibility);
    (params.status ?? []).forEach((s) => qs.append('status', s));
    (params.mime_family ?? []).forEach((m) => qs.append('mime_family', m));
    (params.tag_ids ?? []).forEach((id) => qs.append('tag_ids', String(id)));
    if (params.sort) qs.set('sort', params.sort);
    if (params.page) qs.set('page', String(params.page));
    if (params.page_size) qs.set('page_size', String(params.page_size));

    const response = await fetch(`${API_BASE_URL}/api/v1/documents/?${qs.toString()}`, {
      method: 'GET', headers: this.getAuthHeaders(),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to fetch documents: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * List all document tags visible to the current user.
   */
  static async listDocumentTags(): Promise<DocumentTag[]> {
    const response = await fetch(`${API_BASE_URL}/api/v1/documents/tags`, {
      method: 'GET', headers: this.getAuthHeaders(),
    });
    if (!response.ok) {
      const e = await response.json().catch(() => ({}));
      throw new Error(e.detail || `Failed to fetch tags: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Create a new document tag.
   */
  static async createDocumentTag(name: string, scope: 'user' | 'institution' = 'user'): Promise<DocumentTag> {
    const response = await fetch(`${API_BASE_URL}/api/v1/documents/tags`, {
      method: 'POST', headers: this.getAuthHeaders(), body: JSON.stringify({ name, scope }),
    });
    if (!response.ok) {
      const e = await response.json().catch(() => ({}));
      throw new Error(e.detail || `Failed to create tag: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Attach tags to a document.
   */
  static async attachDocumentTags(documentId: number, tagIds: number[]): Promise<Document> {
    const response = await fetch(`${API_BASE_URL}/api/v1/documents/${documentId}/tags`, {
      method: 'POST', headers: this.getAuthHeaders(), body: JSON.stringify({ tag_ids: tagIds }),
    });
    if (!response.ok) {
      const e = await response.json().catch(() => ({}));
      throw new Error(e.detail || `Failed to attach tags: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Detach a single tag from a document.
   */
  static async detachDocumentTag(documentId: number, tagId: number): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/v1/documents/${documentId}/tags/${tagId}`, {
      method: 'DELETE', headers: this.getAuthHeaders(),
    });
    if (!response.ok) {
      const e = await response.json().catch(() => ({}));
      throw new Error(e.detail || `Failed to detach tag: ${response.statusText}`);
    }
  }

  /**
   * Batch process documents
   */
  static async batchProcessDocuments(
    documentIds: number[],
    createVectors: boolean = true,
    onProgress?: (documentId: number, progress: number) => void,
    onComplete?: (documentId: number, result: DocumentProcessingResponse) => void,
    onError?: (documentId: number, error: string) => void
  ): Promise<DocumentProcessingResponse[]> {
    const results: DocumentProcessingResponse[] = [];

    for (const documentId of documentIds) {
      try {
        onProgress?.(documentId, 0);

        const result = await this.processDocument(documentId, createVectors);
        results.push(result);

        onProgress?.(documentId, 100);
        onComplete?.(documentId, result);

      } catch (error) {
        const errorMessage = error && typeof error === 'object' && 'message' in error ? (error as Error).message : 'Unknown error';
        onError?.(documentId, errorMessage);
      }
    }

    return results;
  }
}
