/**
 * Form model of the portfolio template editor (TF-988) — pure functions only,
 * so the rubric resizing, validation and payload mapping are testable without
 * rendering the dialog.
 *
 * The draft keeps raw input strings (`maxPoints`, `checklist`,
 * `folderPatterns`) and converts them only in `draftToPayload`, so a
 * half-typed value never gets rewritten under the cursor.
 */
import type { TFunction } from 'i18next';
import {
  NonEmptyArray,
  PORTFOLIO_MAX_CRITERION_POINTS,
  PortfolioTemplate,
  PortfolioTemplateCriterionPayload,
  PortfolioTemplatePhasePayload,
  PortfolioTemplateUpdatePayload,
  PortfolioTemplateVisibility,
} from '../../../types/portfolio';

/** `Field(max_length=…)` in `premium/backend/api/v1/portfolio_templates.py`. */
export const NAME_MAX_LENGTH = 255;
export const TYPE_TAG_MAX_LENGTH = 50;

const DEFAULT_MAX_POINTS = 3;

export interface CriterionDraft {
  /** React key only; the payload carries no ids. */
  key: string;
  name: string;
  typeTag: string;
  maxPoints: string;
  /**
   * Index = score. Only grows: lowering `maxPoints` hides the upper texts
   * instead of dropping them, so typing «10» via «1» loses nothing.
   */
  rubric: string[];
  /** One item per line. */
  checklist: string;
}

export interface PhaseDraft {
  key: string;
  name: string;
  description: string;
  /** Comma-separated. */
  folderPatterns: string;
  criteria: CriterionDraft[];
}

export interface TemplateDraft {
  name: string;
  description: string;
  visibility: PortfolioTemplateVisibility;
  orgUnitId: number | null;
  isActive: boolean;
  phases: PhaseDraft[];
}

let keyCounter = 0;
const nextKey = (prefix: string) => `${prefix}-${++keyCounter}`;

export function parseMaxPoints(raw: string): number | null {
  if (!/^\d+$/.test(raw.trim())) return null;
  const value = Number(raw.trim());
  return value >= 1 && value <= PORTFOLIO_MAX_CRITERION_POINTS ? value : null;
}

export function emptyCriterion(): CriterionDraft {
  return {
    key: nextKey('criterion'),
    name: '',
    typeTag: '',
    maxPoints: String(DEFAULT_MAX_POINTS),
    rubric: Array(DEFAULT_MAX_POINTS + 1).fill(''),
    checklist: '',
  };
}

export function emptyPhase(): PhaseDraft {
  return {
    key: nextKey('phase'),
    name: '',
    description: '',
    folderPatterns: '',
    criteria: [emptyCriterion()],
  };
}

export function emptyDraft(): TemplateDraft {
  return {
    name: '',
    description: '',
    visibility: 'private',
    orgUnitId: null,
    isActive: true,
    phases: [emptyPhase()],
  };
}

const byPosition = <T extends { position: number }>(a: T, b: T) => a.position - b.position;

/**
 * Rows written before TF-988 may hold a dict (the API took one), of which the
 * classifier's `", ".join` only ever used the keys. Read as that key list —
 * the backend's change detection does the same (`_existing_phases_as_data`),
 * so sending it back as a list is no phase change.
 */
function folderPatternList(stored: unknown): string[] | null {
  if (stored === null || stored === undefined) return null;
  if (Array.isArray(stored)) return stored.map(String);
  if (typeof stored === 'object') return Object.keys(stored);
  return null;
}

export function draftFromTemplate(template: PortfolioTemplate): TemplateDraft {
  return {
    name: template.name,
    description: template.description ?? '',
    visibility: template.visibility,
    orgUnitId: template.org_unit_id,
    isActive: template.is_active,
    phases: [...template.phases].sort(byPosition).map((phase) => ({
      key: nextKey('phase'),
      name: phase.name,
      description: phase.description ?? '',
      folderPatterns: (folderPatternList(phase.expected_folder_patterns) ?? []).join(', '),
      criteria: [...phase.criteria].sort(byPosition).map((criterion) => ({
        key: nextKey('criterion'),
        name: criterion.name,
        typeTag: criterion.type_tag ?? '',
        maxPoints: String(criterion.max_points),
        rubric: Array.from(
          { length: criterion.max_points + 1 },
          (_, score) => criterion.rubric_by_score[String(score)] ?? '',
        ),
        checklist: (criterion.checklist_items ?? []).join('\n'),
      })),
    })),
  };
}

/** New `maxPoints` input; grows the rubric once the value is valid. */
export function withMaxPoints(criterion: CriterionDraft, raw: string): CriterionDraft {
  const maxPoints = parseMaxPoints(raw);
  const rubric =
    maxPoints !== null && criterion.rubric.length < maxPoints + 1
      ? [...criterion.rubric, ...Array(maxPoints + 1 - criterion.rubric.length).fill('')]
      : criterion.rubric;
  return { ...criterion, maxPoints: raw, rubric };
}

/** Swaps `list[index]` with its neighbour; out-of-range moves are a no-op. */
export function moveItem<T>(list: T[], index: number, delta: -1 | 1): T[] {
  const target = index + delta;
  if (target < 0 || target >= list.length) return list;
  const next = [...list];
  [next[index], next[target]] = [next[target], next[index]];
  return next;
}

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

export interface CriterionErrors {
  name?: string;
  typeTag?: string;
  maxPoints?: string;
  rubric?: string;
  /** Scores whose rubric text is missing, to mark those fields. */
  rubricScores?: number[];
}

export interface PhaseErrors {
  name?: string;
  criteria: Record<string, CriterionErrors>;
}

export interface DraftErrors {
  name?: string;
  visibility?: string;
  orgUnit?: string;
  /** Keyed by `PhaseDraft.key`; only phases with at least one error. */
  phases: Record<string, PhaseErrors>;
}

const KEY = 'pages.portfolio.templates.validation';

function lengthError(t: TFunction, value: string, max: number, required: boolean) {
  if (required && !value.trim()) return t(`${KEY}.required`);
  if (value.trim().length > max) return t(`${KEY}.tooLong`, { max });
  return undefined;
}

function validateCriterion(t: TFunction, criterion: CriterionDraft): CriterionErrors {
  const errors: CriterionErrors = {};
  const name = lengthError(t, criterion.name, NAME_MAX_LENGTH, true);
  if (name) errors.name = name;
  const typeTag = lengthError(t, criterion.typeTag, TYPE_TAG_MAX_LENGTH, false);
  if (typeTag) errors.typeTag = typeTag;

  const maxPoints = parseMaxPoints(criterion.maxPoints);
  if (maxPoints === null) {
    errors.maxPoints = t(`${KEY}.maxPoints`, { max: PORTFOLIO_MAX_CRITERION_POINTS });
    return errors;
  }
  const missing = criterion.rubric
    .slice(0, maxPoints + 1)
    .map((text, score) => (text.trim() ? null : score))
    .filter((score): score is number => score !== null);
  if (missing.length > 0) {
    errors.rubric = t(`${KEY}.rubricMissing`, { scores: missing.join(', ') });
    errors.rubricScores = missing;
  }
  return errors;
}

export function validateDraft(t: TFunction, draft: TemplateDraft): DraftErrors {
  const errors: DraftErrors = { phases: {} };
  const name = lengthError(t, draft.name, NAME_MAX_LENGTH, true);
  if (name) errors.name = name;
  if (draft.visibility === 'team' && draft.orgUnitId === null) {
    errors.orgUnit = t(`${KEY}.orgUnitRequired`);
  }
  for (const phase of draft.phases) {
    const phaseErrors: PhaseErrors = { criteria: {} };
    const phaseName = lengthError(t, phase.name, NAME_MAX_LENGTH, true);
    if (phaseName) phaseErrors.name = phaseName;
    for (const criterion of phase.criteria) {
      const criterionErrors = validateCriterion(t, criterion);
      if (Object.keys(criterionErrors).length > 0) {
        phaseErrors.criteria[criterion.key] = criterionErrors;
      }
    }
    if (phaseErrors.name || Object.keys(phaseErrors.criteria).length > 0) {
      errors.phases[phase.key] = phaseErrors;
    }
  }
  return errors;
}

export function hasErrors(errors: DraftErrors): boolean {
  return Boolean(
    errors.name || errors.visibility || errors.orgUnit || Object.keys(errors.phases).length > 0,
  );
}

/** Combines two error sets field by field; `b` wins where both are set. */
export function mergeErrors(a: DraftErrors, b: DraftErrors): DraftErrors {
  const phases: Record<string, PhaseErrors> = { ...a.phases };
  for (const [phaseKey, phaseErrors] of Object.entries(b.phases)) {
    const base = phases[phaseKey] ?? { criteria: {} };
    const criteria = { ...base.criteria };
    for (const [criterionKey, criterionErrors] of Object.entries(phaseErrors.criteria)) {
      criteria[criterionKey] = { ...criteria[criterionKey], ...criterionErrors };
    }
    phases[phaseKey] = { ...base, ...(phaseErrors.name ? { name: phaseErrors.name } : {}), criteria };
  }
  return {
    name: b.name ?? a.name,
    visibility: b.visibility ?? a.visibility,
    orgUnit: b.orgUnit ?? a.orgUnit,
    phases,
  };
}

/**
 * Marks every criterion named `criterionName` — the backend reports rubric
 * errors by name only (`error_params.criterion`), and names are not unique.
 */
export function criterionErrorsByName(
  draft: TemplateDraft,
  criterionName: string,
  field: 'maxPoints' | 'rubric',
  message: string,
): DraftErrors {
  const errors: DraftErrors = { phases: {} };
  for (const phase of draft.phases) {
    for (const criterion of phase.criteria) {
      if (criterion.name.trim() !== criterionName) continue;
      errors.phases[phase.key] ??= { criteria: {} };
      errors.phases[phase.key].criteria[criterion.key] = { [field]: message };
    }
  }
  return errors;
}

// ---------------------------------------------------------------------------
// Payload
// ---------------------------------------------------------------------------

const orNull = (value: string) => (value.trim() ? value.trim() : null);

function splitList(raw: string, separator: RegExp): string[] | null {
  const items = raw
    .split(separator)
    .map((item) => item.trim())
    .filter(Boolean);
  return items.length > 0 ? items : null;
}

function criterionPayload(criterion: CriterionDraft): PortfolioTemplateCriterionPayload {
  const maxPoints = parseMaxPoints(criterion.maxPoints);
  if (maxPoints === null) {
    throw new Error(`draftToPayload on an unvalidated draft: max points «${criterion.maxPoints}»`);
  }
  return {
    name: criterion.name.trim(),
    type_tag: orNull(criterion.typeTag),
    max_points: maxPoints,
    rubric_by_score: Object.fromEntries(
      criterion.rubric.slice(0, maxPoints + 1).map((text, score) => [String(score), text.trim()]),
    ),
    checklist_items: splitList(criterion.checklist, /\n/),
  };
}

const phaseContent = (phases: PhaseDraft[]) =>
  phases.map(({ key: _phaseKey, criteria, ...phase }) => ({
    ...phase,
    criteria: criteria.map(({ key: _criterionKey, rubric, ...criterion }) => {
      const maxPoints = parseMaxPoints(criterion.maxPoints);
      return { ...criterion, rubric: maxPoints === null ? rubric : rubric.slice(0, maxPoints + 1) };
    }),
  }));

/** Same phases and criteria as far as the user can see (keys ignored). */
export function samePhases(a: PhaseDraft[], b: PhaseDraft[]): boolean {
  return JSON.stringify(phaseContent(a)) === JSON.stringify(phaseContent(b));
}

/**
 * The stored phases exactly as the backend has them. `update_template`
 * compares phase content verbatim, so re-sending unchanged phases through
 * `draftToPayload` (which trims, turns `''` into `null` and drops rubric keys
 * above `max_points`) could count as a change: a version bump, or a 409
 * `phases_locked` although the user touched only master data. A legacy dict
 * in `expected_folder_patterns` goes back as its key list (see
 * `folderPatternList`), which the backend compares as equal.
 */
export function phasesPayloadFromTemplate(
  template: PortfolioTemplate,
): NonEmptyArray<PortfolioTemplatePhasePayload> {
  return [...template.phases].sort(byPosition).map(
    (phase): PortfolioTemplatePhasePayload => ({
      name: phase.name,
      description: phase.description,
      expected_folder_patterns: folderPatternList(phase.expected_folder_patterns),
      criteria: [...phase.criteria].sort(byPosition).map((criterion) => ({
        name: criterion.name,
        type_tag: criterion.type_tag,
        max_points: criterion.max_points,
        rubric_by_score: criterion.rubric_by_score,
        checklist_items: criterion.checklist_items,
      })) as NonEmptyArray<PortfolioTemplateCriterionPayload>,
    }),
  ) as NonEmptyArray<PortfolioTemplatePhasePayload>;
}

/**
 * Full body for `POST` and `PUT` alike (PUT replaces everything, see
 * `PortfolioTemplateUpdatePayload`). Call only when `validateDraft` found
 * nothing: the editor never lets the last phase or criterion be removed, so
 * the non-empty casts hold.
 */
export function draftToPayload(draft: TemplateDraft): PortfolioTemplateUpdatePayload {
  return {
    name: draft.name.trim(),
    description: orNull(draft.description),
    visibility: draft.visibility,
    org_unit_id: draft.visibility === 'team' ? draft.orgUnitId : null,
    is_active: draft.isActive,
    phases: draft.phases.map(
      (phase): PortfolioTemplatePhasePayload => ({
        name: phase.name.trim(),
        description: orNull(phase.description),
        expected_folder_patterns: splitList(phase.folderPatterns, /[,\n]/),
        criteria: phase.criteria.map(criterionPayload) as NonEmptyArray<PortfolioTemplateCriterionPayload>,
      }),
    ) as NonEmptyArray<PortfolioTemplatePhasePayload>,
  };
}
