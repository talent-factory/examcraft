/**
 * Form model of the portfolio template editor (TF-988).
 */
import type { TFunction } from 'i18next';
import type { PortfolioTemplate } from '../../../../types/portfolio';
import {
  criterionErrorsByName,
  draftFromTemplate,
  draftToPayload,
  emptyCriterion,
  emptyDraft,
  hasErrors,
  mergeErrors,
  moveItem,
  parseMaxPoints,
  phasesPayloadFromTemplate,
  samePhases,
  TemplateDraft,
  validateDraft,
  withMaxPoints,
} from '../templateDraft';

// Key plus params, so assertions see which message was chosen.
const t = ((key: string, params?: Record<string, unknown>) =>
  params ? `${key} ${JSON.stringify(params)}` : key) as unknown as TFunction;

function template(overrides: Partial<PortfolioTemplate> = {}): PortfolioTemplate {
  return {
    id: 't-1',
    name: 'HERMES',
    description: null,
    visibility: 'team',
    org_unit_id: 4,
    institution_id: 1,
    created_by: 1,
    version: 2,
    is_active: false,
    created_at: null,
    updated_at: null,
    phases: [
      {
        id: 'p-2',
        position: 1,
        name: 'Umsetzung',
        description: null,
        expected_folder_patterns: null,
        criteria: [
          {
            id: 'c-3',
            position: 0,
            name: 'Code',
            type_tag: null,
            max_points: 1,
            rubric_by_score: { '0': 'nichts', '1': 'alles' },
            checklist_items: null,
          },
        ],
      },
      {
        id: 'p-1',
        position: 0,
        name: 'Initialisierung',
        description: 'Auftrag klären',
        expected_folder_patterns: ['01_init', 'auftrag'],
        criteria: [
          {
            id: 'c-2',
            position: 1,
            name: 'Zeitplan',
            type_tag: '[P]',
            max_points: 2,
            rubric_by_score: { '0': 'a', '1': 'b', '2': 'c' },
            checklist_items: ['Meilensteine', 'Puffer'],
          },
          {
            id: 'c-1',
            position: 0,
            name: 'Ausgangslage',
            type_tag: null,
            max_points: 1,
            rubric_by_score: { '0': 'x', '1': 'y' },
            checklist_items: null,
          },
        ],
      },
    ],
    ...overrides,
  };
}

function validDraft(): TemplateDraft {
  const draft = emptyDraft();
  draft.name = 'Neu';
  draft.phases[0].name = 'Phase';
  const criterion = withMaxPoints(draft.phases[0].criteria[0], '1');
  draft.phases[0].criteria[0] = { ...criterion, name: 'K', rubric: ['null', 'eins'] };
  return draft;
}

describe('parseMaxPoints', () => {
  it.each([
    ['1', 1],
    ['100', 100],
    [' 7 ', 7],
    ['0', null],
    ['101', null],
    ['2.5', null],
    ['-1', null],
    ['', null],
  ])('%p → %p', (raw, expected) => {
    expect(parseMaxPoints(raw)).toBe(expected);
  });
});

describe('withMaxPoints', () => {
  it('grows the rubric to 0…max and keeps existing texts', () => {
    const criterion = { ...emptyCriterion(), rubric: ['a', 'b', 'c', 'd'] };
    expect(withMaxPoints(criterion, '5').rubric).toEqual(['a', 'b', 'c', 'd', '', '']);
  });

  it('keeps texts beyond a lower max, so typing «10» via «1» loses nothing', () => {
    const criterion = { ...emptyCriterion(), rubric: ['a', 'b', 'c', 'd'] };
    const lowered = withMaxPoints(criterion, '1');
    expect(lowered.rubric).toEqual(['a', 'b', 'c', 'd']);
    expect(lowered.maxPoints).toBe('1');
  });

  it('leaves the rubric alone on invalid input', () => {
    const criterion = emptyCriterion();
    expect(withMaxPoints(criterion, '500').rubric).toBe(criterion.rubric);
  });
});

describe('moveItem', () => {
  it('swaps with the neighbour and ignores moves past the ends', () => {
    expect(moveItem(['a', 'b', 'c'], 1, -1)).toEqual(['b', 'a', 'c']);
    expect(moveItem(['a', 'b', 'c'], 1, 1)).toEqual(['a', 'c', 'b']);
    const list = ['a', 'b'];
    expect(moveItem(list, 0, -1)).toBe(list);
    expect(moveItem(list, 1, 1)).toBe(list);
  });
});

describe('draftFromTemplate', () => {
  it('orders phases and criteria by position and maps raw fields', () => {
    const draft = draftFromTemplate(template());
    expect(draft.phases.map((p) => p.name)).toEqual(['Initialisierung', 'Umsetzung']);
    expect(draft.phases[0].criteria.map((c) => c.name)).toEqual(['Ausgangslage', 'Zeitplan']);
    expect(draft.phases[0].folderPatterns).toBe('01_init, auftrag');
    expect(draft.phases[0].criteria[1]).toMatchObject({
      typeTag: '[P]',
      maxPoints: '2',
      rubric: ['a', 'b', 'c'],
      checklist: 'Meilensteine\nPuffer',
    });
    expect(draft).toMatchObject({ visibility: 'team', orgUnitId: 4, isActive: false });
  });

  it('reads a legacy dict of folder patterns as its keys (what the classifier used)', () => {
    const legacy = template();
    (legacy.phases[1] as { expected_folder_patterns: unknown }).expected_folder_patterns = {
      init: true,
      auftrag: 1,
    };
    const draft = draftFromTemplate(legacy);
    expect(draft.phases[0].folderPatterns).toBe('init, auftrag');
    expect(samePhases(draft.phases, draftFromTemplate(legacy).phases)).toBe(true);
    expect(phasesPayloadFromTemplate(legacy)[0].expected_folder_patterns).toEqual(['init', 'auftrag']);
  });

  it('round-trips to the same content', () => {
    const payload = draftToPayload(draftFromTemplate(template()));
    expect(payload.phases[0]).toEqual({
      name: 'Initialisierung',
      description: 'Auftrag klären',
      expected_folder_patterns: ['01_init', 'auftrag'],
      criteria: [
        {
          name: 'Ausgangslage',
          type_tag: null,
          max_points: 1,
          rubric_by_score: { '0': 'x', '1': 'y' },
          checklist_items: null,
        },
        {
          name: 'Zeitplan',
          type_tag: '[P]',
          max_points: 2,
          rubric_by_score: { '0': 'a', '1': 'b', '2': 'c' },
          checklist_items: ['Meilensteine', 'Puffer'],
        },
      ],
    });
    expect(payload).toMatchObject({ visibility: 'team', org_unit_id: 4, is_active: false });
  });
});

describe('draftToPayload', () => {
  it('sends only the rubric up to max_points and trims everything', () => {
    const draft = validDraft();
    draft.name = '  Neu  ';
    draft.description = '   ';
    draft.phases[0].folderPatterns = ' a ,, b\nc ';
    draft.phases[0].criteria[0].rubric = [' null ', 'eins', 'versteckt'];
    draft.phases[0].criteria[0].checklist = 'x\n\n y ';

    const payload = draftToPayload(draft);

    expect(payload.name).toBe('Neu');
    expect(payload.description).toBeNull();
    expect(payload.phases[0].expected_folder_patterns).toEqual(['a', 'b', 'c']);
    expect(payload.phases[0].criteria[0].rubric_by_score).toEqual({ '0': 'null', '1': 'eins' });
    expect(payload.phases[0].criteria[0].checklist_items).toEqual(['x', 'y']);
  });

  it('sends org_unit_id only for team visibility', () => {
    const draft = { ...validDraft(), visibility: 'private' as const, orgUnitId: 4 };
    expect(draftToPayload(draft).org_unit_id).toBeNull();
    expect(draftToPayload({ ...draft, visibility: 'team' }).org_unit_id).toBe(4);
  });

  it('always sends every master-data field (PUT is a full replace)', () => {
    expect(Object.keys(draftToPayload(validDraft())).sort()).toEqual(
      ['description', 'is_active', 'name', 'org_unit_id', 'phases', 'visibility'].sort(),
    );
  });
});

describe('validateDraft', () => {
  it('accepts a complete draft', () => {
    expect(hasErrors(validateDraft(t, validDraft()))).toBe(false);
  });

  it('marks missing names, bad max points, missing rubric texts and org unit', () => {
    const draft = validDraft();
    draft.name = ' ';
    draft.visibility = 'team';
    const phase = draft.phases[0];
    phase.name = '';
    phase.criteria.push({ ...emptyCriterion(), name: 'Zwei', maxPoints: '0' });
    phase.criteria[0].rubric = ['null', ' '];

    const errors = validateDraft(t, draft);

    expect(errors.name).toBe('pages.portfolio.templates.validation.required');
    expect(errors.orgUnit).toBe('pages.portfolio.templates.validation.orgUnitRequired');
    const phaseErrors = errors.phases[phase.key];
    expect(phaseErrors.name).toBe('pages.portfolio.templates.validation.required');
    expect(phaseErrors.criteria[phase.criteria[0].key].rubricScores).toEqual([1]);
    expect(phaseErrors.criteria[phase.criteria[1].key].maxPoints).toBe(
      'pages.portfolio.templates.validation.maxPoints {"max":100}',
    );
  });

  it('flags a type tag over 50 characters', () => {
    const draft = validDraft();
    draft.phases[0].criteria[0].typeTag = 'x'.repeat(51);
    const errors = validateDraft(t, draft);
    expect(errors.phases[draft.phases[0].key].criteria[draft.phases[0].criteria[0].key].typeTag).toBe(
      'pages.portfolio.templates.validation.tooLong {"max":50}',
    );
  });
});

describe('criterionErrorsByName / mergeErrors', () => {
  it('marks every criterion with that name and merges field by field', () => {
    const draft = draftFromTemplate(template());
    const [first, second] = draft.phases;
    second.criteria[0].name = 'Zeitplan';

    const server = criterionErrorsByName(draft, 'Zeitplan', 'rubric', 'fehlt');
    expect(server.phases[first.key].criteria[first.criteria[1].key]).toEqual({ rubric: 'fehlt' });
    expect(server.phases[second.key].criteria[second.criteria[0].key]).toEqual({ rubric: 'fehlt' });

    const client = { name: 'leer', phases: { [first.key]: { criteria: { [first.criteria[1].key]: { name: 'x' } } } } };
    const merged = mergeErrors(client, server);
    expect(merged.name).toBe('leer');
    expect(merged.phases[first.key].criteria[first.criteria[1].key]).toEqual({ name: 'x', rubric: 'fehlt' });
  });
});

describe('samePhases / phasesPayloadFromTemplate', () => {
  it('treats an untouched draft as unchanged and sends the stored phases verbatim', () => {
    // Data draftToPayload would normalise: padding, '' → null, [] → null,
    // a rubric key above max_points.
    const stored = template();
    const criterionRow = stored.phases[0].criteria[0];
    stored.phases[0].description = '';
    criterionRow.type_tag = '';
    criterionRow.checklist_items = [];
    criterionRow.rubric_by_score = { '0': ' nichts ', '1': 'alles', '2': 'übrig' };

    const draft = draftFromTemplate(stored);
    expect(samePhases(draft.phases, draftFromTemplate(stored).phases)).toBe(true);

    const phases = phasesPayloadFromTemplate(stored);
    expect(phases.map((p) => p.name)).toEqual(['Initialisierung', 'Umsetzung']);
    expect(phases[1]).toEqual({
      name: 'Umsetzung',
      description: '',
      expected_folder_patterns: null,
      criteria: [
        {
          name: 'Code',
          type_tag: '',
          max_points: 1,
          rubric_by_score: { '0': ' nichts ', '1': 'alles', '2': 'übrig' },
          checklist_items: [],
        },
      ],
    });
  });

  it('notices a change and ignores hidden rubric texts above max_points', () => {
    const base = draftFromTemplate(template());
    const edited = draftFromTemplate(template());
    edited.phases[0].criteria[0].name = 'Anders';
    expect(samePhases(edited.phases, base.phases)).toBe(false);

    const grownAndBack = draftFromTemplate(template());
    const c = grownAndBack.phases[0].criteria[0];
    grownAndBack.phases[0].criteria[0] = withMaxPoints(withMaxPoints(c, '3'), '1');
    expect(samePhases(grownAndBack.phases, base.phases)).toBe(true);
  });
});
