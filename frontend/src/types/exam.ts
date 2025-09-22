// Type definitions for ExamCraft AI

export interface ExamRequest {
  topic: string;
  difficulty: 'easy' | 'medium' | 'hard';
  question_count: number;
  question_types: string[];
  language: 'de' | 'en';
}

export interface Question {
  id: string;
  type: 'multiple_choice' | 'open_ended' | 'true_false' | 'short_answer';
  question: string;
  options?: string[];
  correct_answer?: string;
  explanation?: string;
  difficulty: string;
  topic: string;
}

export interface ExamResponse {
  exam_id: string;
  topic: string;
  questions: Question[];
  created_at: string;
  metadata: {
    difficulty: string;
    question_count: number;
    language: string;
    generated_by: string;
  };
}

export interface ApiResponse<T> {
  data?: T;
  error?: string;
  message?: string;
}
