// TF-400 Handlungskompetenzen — Typen für Kompetenzrahmen (HKB/Modul + HK).
// Spiegelt FrameworkOut / CompetencyOut aus core/backend/api/competency_frameworks.py.

// TF-644: 'team' hinzugefügt (mirrors DocumentVisibility/PromptVisibility/
// QuestionReviewVisibility/ExamVisibility). Nur zusammen mit org_unit_id sinnvoll.
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
  // TF-644: gesetzt nur wenn visibility='team'.
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
  // TF-644: nur zusammen mit visibility='team' relevant (backend validiert
  // Mitgliedschaft in der gewählten Org-Unit).
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
