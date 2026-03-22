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
export interface AutoFillRequest {
  count?: number;
  topic?: string;
  difficulty?: string[];
  bloom_level_min?: number;
  question_types?: string[];
  exclude_question_ids?: number[];
  // Composition mode fields
  target_points?: number;
  target_duration_minutes?: number;
  bloom_distribution?: Record<number, number>;
  difficulty_distribution?: Record<string, number>;
  preview?: boolean;
}

export interface DistributionResult {
  target_pct: number;
  achieved_pct: number;
  within_tolerance: boolean;
}

export interface ConstraintReport {
  points_target: number | null;
  points_achieved: number;
  duration_target: number | null;
  duration_achieved: number;
  bloom_distribution: Record<number, DistributionResult>;
  difficulty_distribution: Record<string, DistributionResult>;
  overall_satisfaction: number;
}

export interface ProposedQuestion {
  id: number;
  question_text: string;
  question_type: string;
  difficulty: string;
  topic: string;
  bloom_level: number | null;
  estimated_time_minutes: number | null;
  suggested_points: number;
}

export interface AutoComposePreview {
  questions: ProposedQuestion[];
  total_points: number;
  total_duration_minutes: number;
  constraint_report: ConstraintReport;
}
