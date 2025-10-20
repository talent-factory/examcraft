import { 
  Document, 
  DocumentUploadResponse, 
  DocumentProcessingResponse,
  AvailableDocumentsResponse 
} from '../types/document';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export class DocumentService {
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
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/api/v1/documents/upload`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
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
