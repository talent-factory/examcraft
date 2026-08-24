// TF-400 competencies — types for competency frameworks (HKB/module + HK).
// Mirrors FrameworkOut / CompetencyOut from core/backend/api/competency_frameworks.py.

// TF-644: added 'team' (mirrors DocumentVisibility/PromptVisibility/
// QuestionReviewVisibility/ExamVisibility). Only meaningful together with org_unit_id.
export type FrameworkVisibility = 'private' | 'team' | 'institution';

export interface CompetencyDescriptor {
  text: string;
  ln_level: number | null;
}

export interface Competency {
  id: number;
  code: string;
  title: string;
  descriptors: CompetencyDescriptor[] | null;
  position: number;
}

export interface CompetencyFramework {
  id: number;
  name: string;
  module_code: string | null;
  description: string | null;
  rendered_text: string;
  language: string;
  institution_id: number | null;
  // TF-644: set only when visibility='team'.
  org_unit_id: number | null;
  created_by: number | null;
  visibility: FrameworkVisibility;
  is_archived: boolean;
  competencies: Competency[];
}

export interface FrameworkCreatePayload {
  name: string;
  module_code?: string;
  description?: string;
  rendered_text: string;
  language?: string;
  visibility?: FrameworkVisibility;
  // TF-644: only relevant together with visibility='team' (backend
  // validates membership in the chosen org unit).
  org_unit_id?: number | null;
}

export interface FrameworkUpdatePayload {
  name?: string;
  module_code?: string;
  description?: string;
  rendered_text?: string;
  language?: string;
  visibility?: FrameworkVisibility;
  org_unit_id?: number | null;
}
