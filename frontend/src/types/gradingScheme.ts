/**
 * TypeScript types for `/api/v1/grading-schemes/*` (TF-335 Spec 4.5).
 *
 * Mirrors the Pydantic schemas in `core/backend/api/grading_schemes.py`.
 * Three config variants — `linear`, `linear_segments`, `stepped` —
 * share a discriminated union on the `type` field; the evaluator on
 * the backend dispatches on it and the admin editor uses it to swap
 * the form layout.
 */

export const DISPLAY_FORMATS = ['numeric', 'letter', 'pass_fail'] as const;
export type GradingSchemeDisplayFormat = (typeof DISPLAY_FORMATS)[number];

export interface LinearSegmentConfig {
  type: 'linear_segments';
  round_to?: number;
  pass_grade_label?: string;
  segments: Array<{
    from_pct: number;
    to_pct: number;
    from_grade: number;
    to_grade: number;
  }>;
}

export interface LinearConfig {
  type: 'linear';
  min_pct: number;
  max_pct: number;
  min_grade: number;
  max_grade: number;
  round_to?: number;
  pass_grade_label?: string;
}

export interface SteppedConfig {
  type: 'stepped';
  steps: Array<{
    min_pct: number;
    grade_label: string;
    is_passing: boolean;
  }>;
}

export type GradingSchemeConfig =
  | LinearSegmentConfig
  | LinearConfig
  | SteppedConfig;

export interface GradingSchemeOut {
  id: number;
  institution_id: number | null;
  name: string;
  display_format: GradingSchemeDisplayFormat;
  config: GradingSchemeConfig;
  is_default_for_institution: boolean;
  is_system_scheme: boolean;
  created_at: string;
  updated_at: string;
}

export interface GradingSchemeListOut {
  schemes: GradingSchemeOut[];
}

export interface GradingSchemeCreate {
  name: string;
  display_format: GradingSchemeDisplayFormat;
  config: GradingSchemeConfig;
  is_default_for_institution?: boolean;
}

export interface GradingSchemeUpdate {
  name?: string;
  display_format?: GradingSchemeDisplayFormat;
  config?: GradingSchemeConfig;
  is_default_for_institution?: boolean;
}
