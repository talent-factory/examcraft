import {
  Document,
  DocumentUploadResponse,
  DocumentProcessingResponse,
  AvailableDocumentsResponse
} from '../types/document';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export class DocumentService {
  /**
   * Refresh token if expired
   */
  private static async refreshTokenIfNeeded(): Promise<string | null> {
    const token = localStorage.getItem('examcraft_access_token');
    const refreshToken = localStorage.getItem('examcraft_refresh_token');

    if (!token || !refreshToken) {
      return null;
    }

    // Try to use the existing token first
    return token;
  }

  /**
   * Handle 401 errors by refreshing token
   */
  private static async handleAuthError(error: any): Promise<void> {
    if (error.message?.includes('401') || error.message?.includes('Could not validate credentials')) {
      const refreshToken = localStorage.getItem('examcraft_refresh_token');

      if (refreshToken) {
        try {
          // Import AuthService dynamically to avoid circular dependencies
          const { default: AuthService } = await import('./AuthService');
          const tokens = await AuthService.refreshToken({ refresh_token: refreshToken });

          // Update tokens in localStorage
          localStorage.setItem('examcraft_access_token', tokens.access_token);
          localStorage.setItem('examcraft_refresh_token', tokens.refresh_token);

          // Reload the page to retry with new token
          window.location.reload();
        } catch (refreshError) {
          // Refresh failed, clear auth and redirect to login
          localStorage.removeItem('examcraft_access_token');
          localStorage.removeItem('examcraft_refresh_token');
          localStorage.removeItem('examcraft_user');
          window.location.href = '/auth';
        }
      } else {
        // No refresh token, redirect to login
        window.location.href = '/auth';
      }
    }
    throw error;
  }

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
   * Upload a document file
   */
  static async uploadDocument(file: File): Promise<DocumentUploadResponse> {
    try {
      const formData = new FormData();
      formData.append('file', file);

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
        const error = new Error(errorData.detail || `Upload failed: ${response.statusText}`);

        // Handle auth errors
        if (response.status === 401) {
          await this.handleAuthError(error);
        }

        throw error;
      }

      return response.json();
    } catch (error) {
      // Re-throw after potential token refresh
      throw error;
    }
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
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/documents/`, {
        method: 'GET',
        headers: this.getAuthHeaders(),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const error = new Error(errorData.detail || `Failed to fetch documents: ${response.statusText}`);

        // Handle auth errors
        if (response.status === 401) {
          await this.handleAuthError(error);
        }

        throw error;
      }

      const data = await response.json();
      return data.documents || [];
    } catch (error) {
      throw error;
    }
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
