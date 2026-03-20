export enum ExamStatus {
  DRAFT = 'draft',
  FINALIZED = 'finalized',
  EXPORTED = 'exported',
}

export interface ExamQuestion {
  id: number;
  question_id: number;
  position: number;
  points: number;
  section: string | null;
  question_text: string;
  question_type: string;
  difficulty: string;
  topic: string;
  bloom_level: number | null;
  review_status: string;
  options: string[] | null;
  correct_answer: string | null;
  explanation: string | null;
}

export interface Exam {
  id: number;
  title: string;
  course: string | null;
  exam_date: string | null;
  time_limit_minutes: number | null;
  allowed_aids: string | null;
  instructions: string | null;
  passing_percentage: number;
  total_points: number;
  status: ExamStatus;
  language: string;
  created_at: string;
  updated_at: string;
  question_count: number;
}

export interface ExamDetail extends Exam {
  questions: ExamQuestion[];
}

export interface ExamListResponse { total: number; exams: Exam[]; }
export interface CreateExamRequest { title: string; course?: string; exam_date?: string; time_limit_minutes?: number; allowed_aids?: string; instructions?: string; passing_percentage?: number; language?: string; }
export interface UpdateExamRequest extends Partial<CreateExamRequest> { updated_at: string; }
export interface ApprovedQuestion { id: number; question_text: string; question_type: string; difficulty: string; topic: string; bloom_level: number | null; options: string[] | null; usage_count: number; }
export interface ApprovedQuestionsResponse { total: number; questions: ApprovedQuestion[]; }
export interface AutoFillRequest { count?: number; topic?: string; difficulty?: string[]; bloom_level_min?: number; question_types?: string[]; exclude_question_ids?: number[]; }
