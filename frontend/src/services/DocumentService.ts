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
import { AppError, AppErrorCode, ErrorParams, appErrorFromResponse } from '../errors';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

/**
 * Error thrown by document fetches that need to react to HTTP status
 * (per-status messaging, auth-redirect, retry decisions). Carries the
 * raw `status` so callers can map to a localized message instead of
 * showing a stack-trace string. `status === 0` means the network call
 * itself failed (offline, DNS, CORS) — no HTTP response was received.
 *
 * An `AppError` subclass since TF-772, which is what lets `translateError()`
 * handle it like any other service error while the two call sites that branch
 * on `.status` (DocumentLibrary's preview and rename paths) keep working
 * unchanged. `status` is redeclared non-optional here (every construction
 * site below supplies a real HTTP status, or `0` for a network failure) so a
 * future `instanceof DocumentFetchError` caller gets that guarantee from the
 * type instead of re-deriving it with its own runtime check. `detail` stays
 * optional like the base class — the backend does not always send response
 * text, and forwarding `undefined` rather than defaulting to `''` lets
 * `AppError`'s constructor fall back to a message built from `code` instead
 * of an empty string. Kept as a distinct class rather than folded into
 * AppError because those call sites duck-type on
 * `name === 'DocumentFetchError'` — deliberately, because jest's automocking
 * can give the component and the test different class identities and break
 * `instanceof`.
 */
export class DocumentFetchError extends AppError {
  constructor(
    code: AppErrorCode,
    readonly detail: string | undefined,
    readonly status: number,
    params?: ErrorParams,
  ) {
    super(code, detail, status, params);
    this.name = 'DocumentFetchError';
  }
}

/**
 * A `fetch()` that rejects means no HTTP response existed at all — offline,
 * DNS, CORS. There is no `error_code` to read, so the caller's operation code
 * is all we have; `status === 0` is what tells the UI to say "check your
 * connection" rather than name the operation.
 */
function networkError(e: unknown, code: AppErrorCode): DocumentFetchError {
  const detail =
    e && typeof e === 'object' && 'message' in e ? String((e as Error).message) : '';
  return new DocumentFetchError(code, detail, 0);
}

/**
 * Log a snippet of a non-JSON error body so a developer reproducing the bug
 * can recover it — an HTML error page from a proxy tells you something a
 * status code does not. Reads a clone, leaving the original body for
 * `appErrorFromResponse`. Diagnostics only: the user-facing message stays the
 * translated fallback either way, so a failure to read the body is ignored.
 */
async function logNonJsonBody(response: Response, documentId: number): Promise<void> {
  let body: string;
  try {
    body = await response.clone().text();
  } catch {
    return; // Body unavailable or Response is a test double without clone().
  }
  if (!body) return;

  try {
    JSON.parse(body);
  } catch {
    // eslint-disable-next-line no-console
    console.error(
      `getDocumentRaw(${documentId}): non-JSON ${response.status} body`,
      body.slice(0, 200),
    );
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
   * @param visibility Sharing scope (TF-354/TF-620). Defaults to `private` so
   *   an upload is owner-only unless the user explicitly shares it.
   * @param orgUnitId Target OrgUnit for `visibility=team` — required by the
   *   backend in that case, ignored otherwise.
   */
  static async uploadDocument(
    file: File,
    visibility: DocumentVisibility = DocumentVisibility.PRIVATE,
    orgUnitId?: number | null,
  ): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('visibility', visibility);
    if (visibility === DocumentVisibility.TEAM && orgUnitId != null) {
      formData.append('org_unit_id', String(orgUnitId));
    }

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
      throw await appErrorFromResponse(response, 'documents_upload_failed');
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
      throw await appErrorFromResponse(response, 'documents_processing_failed');
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
      throw await appErrorFromResponse(response, 'documents_list_failed');
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
      throw await appErrorFromResponse(response, 'rag_get_documents_failed');
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
      throw await appErrorFromResponse(response, 'documents_load_failed');
    }

    return response.json();
  }

  /**
   * Set or clear the user-editable display name for a document.
   * Pass null to clear the override and fall back to the resolver chain
   * (filtered metadata title → original filename).
   *
   * Throws {@link DocumentFetchError} so callers can distinguish a 403
   * (owner-only, never retryable) from a transient failure (TF-606).
   * `status === 0` means the network call itself failed (offline, DNS,
   * CORS) — no HTTP response was received — same convention as
   * {@link getDocumentRaw}. `code` carries the backend's `error_code` when it
   * sent one — for a 403 that is `documents_rename_owner_only`, which is what
   * lets the caller explain the restriction instead of saying "rename failed"
   * (TF-606, now via the code rather than via the raw `detail` text).
   */
  static async renameDocument(
    documentId: number,
    displayName: string | null,
  ): Promise<Document> {
    let response: Response;
    try {
      response = await fetch(`${API_BASE_URL}/api/v1/documents/${documentId}`, {
        method: 'PATCH',
        headers: this.getAuthHeaders(),
        body: JSON.stringify({ display_name: displayName }),
      });
    } catch (e) {
      throw networkError(e, 'documents_rename_failed');
    }

    if (!response.ok) {
      const { code, detail, status, params } = await appErrorFromResponse(
        response,
        'documents_rename_failed',
      );
      throw new DocumentFetchError(code, detail?.trim() || undefined, status ?? response.status, params);
    }

    return response.json();
  }

  /**
   * Update a document's visibility (TF-354/TF-620). Owner-only on the backend.
   *
   * @param orgUnitId Target OrgUnit when switching to (or re-scoping within)
   *   `visibility=team`. Omit when switching to `private`/`institution`.
   */
  static async updateVisibility(
    documentId: number,
    visibility: DocumentVisibility,
    orgUnitId?: number | null,
  ): Promise<Document> {
    const body: { visibility: DocumentVisibility; org_unit_id?: number } = { visibility };
    if (visibility === DocumentVisibility.TEAM && orgUnitId != null) {
      body.org_unit_id = orgUnitId;
    }
    const response = await fetch(`${API_BASE_URL}/api/v1/documents/${documentId}`, {
      method: 'PATCH',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      throw await appErrorFromResponse(response, 'documents_visibility_update_failed');
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
      throw await appErrorFromResponse(response, 'documents_delete_failed');
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
      throw await appErrorFromResponse(response, 'documents_download_failed');
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
      throw networkError(e, 'documents_preview_failed');
    }

    if (!response.ok) {
      await logNonJsonBody(response, documentId);
      const { code, detail, status, params } = await appErrorFromResponse(
        response,
        'documents_preview_failed',
      );
      throw new DocumentFetchError(code, detail?.trim() || undefined, status ?? response.status, params);
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
      throw await appErrorFromResponse(response, 'documents_content_load_failed');
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
      throw await appErrorFromResponse(response, 'documents_chunks_load_failed');
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
      throw await appErrorFromResponse(response, 'documents_chunks_load_failed');
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
      throw await appErrorFromResponse(response, 'documents_reindex_failed');
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
      throw await appErrorFromResponse(response, 'documents_status_failed');
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
    onError?: (filename: string, error: unknown) => void
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
        // The error itself, not `error.message`: the caller renders this, and
        // a raw message string is exactly what translateError() exists to keep
        // out of the UI. The AppError arrives intact and carries its code.
        onError?.(file.name, error);
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
      throw await appErrorFromResponse(response, 'documents_list_failed');
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
      throw await appErrorFromResponse(response, 'documents_tags_load_failed');
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
      throw await appErrorFromResponse(response, 'documents_tag_failed');
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
      throw await appErrorFromResponse(response, 'documents_tag_failed');
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
      throw await appErrorFromResponse(response, 'documents_tag_failed');
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
    onError?: (documentId: number, error: unknown) => void
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
        // See uploadMultipleDocuments: the error travels, not its text.
        onError?.(documentId, error);
      }
    }

    return results;
  }
}
