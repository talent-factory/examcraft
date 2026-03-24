// Type definitions for ExamCraft AI

export interface ExamRequest {
  topic: string;
  difficulty: 'easy' | 'medium' | 'hard';
  question_count: number;
  question_types: string[];
  language: 'de' | 'en';
}

export interface Question {
  id: number | string;
  type: 'multiple_choice' | 'open_ended' | 'true_false' | 'short_answer';
  question: string;
  options?: string[];
  correct_answer?: string;
  explanation?: string;
  difficulty: string;
  topic: string;
  // RAG-specific properties
  sources?: string[];
  confidence?: number;
}

export interface ExamResponse {
  id?: string;
  exam_id: string;
  topic: string;
  questions: Question[];
  difficulty?: string;
  language?: string;
  created_at: string;
  generation_time?: number;
  metadata: {
    difficulty: string;
    question_count: number;
    language: string;
    generated_by: string;
    generation_time?: number;
    quality_metrics?: any;
    source_documents?: any;
  };
}

export interface ApiResponse<T> {
  data?: T;
  error?: string;
  message?: string;
}
