// TF-400 Handlungskompetenzen — Typen für Kompetenzrahmen (HKB/Modul + HK).
// Spiegelt FrameworkOut / CompetencyOut aus core/backend/api/competency_frameworks.py.

export type FrameworkVisibility = 'private' | 'institution';

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
}

export interface FrameworkUpdatePayload {
  name?: string;
  module_code?: string;
  description?: string;
  rendered_text?: string;
  language?: string;
  visibility?: FrameworkVisibility;
}
