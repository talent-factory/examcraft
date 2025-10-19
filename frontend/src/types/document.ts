export enum DocumentStatus {
  UPLOADED = 'uploaded',
  PROCESSING = 'processing',
  PROCESSED = 'processed',
  ERROR = 'error'
}

export interface Document {
  id: number;
  filename: string;
  original_filename: string;
  title: string;
  mime_type: string;
  status: DocumentStatus;
  created_at: string;
  processed_at?: string;
  file_size?: number;
  has_vectors: boolean;
  user_id?: string;
  content_preview?: string;
  vector_collection?: string;
  updated_at?: string;
  metadata?: {
    total_chunks?: number;
    embedding_model?: string;
    processing_time?: number;
    [key: string]: any;
  };
}

export interface DocumentUploadResponse {
  document_id: number;
  filename: string;
  message: string;
}

export interface DocumentProcessingResponse {
  message: string;
  document_id: number;
  processing_stats?: {
    total_chunks: number;
    embedding_dimension: number;
    model_name: string;
    processing_time: number;
  };
}

export interface AvailableDocumentsResponse {
  total_documents: number;
  processed_documents: number;
  documents_with_vectors: number;
  documents: Document[];
}

export interface RAGExamRequest {
  topic: string;
  document_ids?: number[];
  question_count: number;
  question_types: string[];
  difficulty: string;
  language: string;
  context_chunks_per_question?: number;
  prompt_ids?: {
    multiple_choice?: string | null;
    open_ended?: string | null;
    true_false?: string | null;
  };
}

export interface RAGQuestion {
  question_text: string;
  question_type: string;
  options?: string[];
  correct_answer?: string;
  explanation?: string | string[];
  difficulty: string;
  source_chunks: string[];
  source_documents: string[];
  confidence_score: number;
}

export interface RAGContextSummary {
  query: string;
  total_chunks: number;
  total_similarity_score: number;
  source_documents: Array<{
    id: number;
    filename: string;
    chunks_used: number;
  }>;
  context_length: number;
}

export interface RAGExamResponse {
  exam_id: string;
  topic: string;
  questions: RAGQuestion[];
  context_summary: RAGContextSummary;
  generation_time: number;
  quality_metrics: {
    total_questions: number;
    average_confidence: number;
    source_coverage: number;
    question_type_distribution: Record<string, number>;
    context_chunks_used: number;
    total_context_length: number;
    average_similarity_score: number;
  };
}

export interface QuestionType {
  type: string;
  name: string;
  description: string;
  example: string;
}

export interface DifficultyLevel {
  level: string;
  name: string;
  description: string;
}

export interface SupportedLanguage {
  code: string;
  name: string;
}

export interface QuestionTypesResponse {
  supported_types: QuestionType[];
  difficulty_levels: DifficultyLevel[];
  supported_languages: SupportedLanguage[];
}
