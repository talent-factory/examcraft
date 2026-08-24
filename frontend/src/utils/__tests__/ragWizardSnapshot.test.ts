import {
  sanitizeWizardSnapshot,
  MAX_RESTORABLE_WIZARD_STEP,
} from '../ragWizardSnapshot';

const FULL_SNAPSHOT = {
  activeStep: 1,
  selectedDocs: [3, 7],
  ragRequest: {
    topic: 'Heapsort',
    document_ids: [3, 7],
    question_count: 8,
    question_types: ['single_choice'],
    difficulty: 'hard',
    language: 'de',
    context_chunks_per_question: 3,
  },
  promptSelection: { single_choice: 'prompt-1', open_ended: null, true_false: null },
  templateVariables: { single_choice: { tone: 'formal' } },
  selectedTags: [{ id: 4, name: 'algorithmen' }],
  frameworkId: 12,
  competenciesOverride: 'K1: Heaps erklären',
};

describe('sanitizeWizardSnapshot', () => {
  it('passes a well-formed snapshot through unchanged', () => {
    expect(sanitizeWizardSnapshot(FULL_SNAPSHOT)).toEqual(FULL_SNAPSHOT);
  });

  it.each([null, undefined, 'string', 42, []])('rejects %p', (raw) => {
    expect(sanitizeWizardSnapshot(raw)).toBeNull();
  });

  it('returns null when nothing usable is left', () => {
    expect(sanitizeWizardSnapshot({ unrelated: true })).toBeNull();
  });

  it('clamps activeStep to the last restorable step', () => {
    // Step 3 is the results view — it depends on a generated exam object
    // that isn't in the snapshot. Without a cap, the user would land on
    // an empty results step.
    expect(sanitizeWizardSnapshot({ activeStep: 3 })?.activeStep).toBe(
      MAX_RESTORABLE_WIZARD_STEP
    );
    expect(sanitizeWizardSnapshot({ activeStep: 99 })?.activeStep).toBe(
      MAX_RESTORABLE_WIZARD_STEP
    );
  });

  it('clamps a negative activeStep to zero', () => {
    expect(sanitizeWizardSnapshot({ activeStep: -5 })?.activeStep).toBe(0);
  });

  it('truncates a fractional activeStep', () => {
    expect(sanitizeWizardSnapshot({ activeStep: 1.9 })?.activeStep).toBe(1);
  });

  it('drops a non-numeric activeStep instead of restoring it', () => {
    const result = sanitizeWizardSnapshot({
      activeStep: 'zwei',
      competenciesOverride: 'K1',
    });
    expect(result).not.toBeNull();
    expect(result).not.toHaveProperty('activeStep');
  });

  it('drops NaN activeStep', () => {
    const result = sanitizeWizardSnapshot({ activeStep: NaN, competenciesOverride: 'K1' });
    expect(result).not.toHaveProperty('activeStep');
  });

  it('filters non-numeric document ids', () => {
    expect(sanitizeWizardSnapshot({ selectedDocs: [1, 'zwei', null, 3] })?.selectedDocs).toEqual(
      [1, 3]
    );
  });

  it('ignores fields of the wrong type', () => {
    const result = sanitizeWizardSnapshot({
      selectedDocs: 'nope',
      ragRequest: 'nope',
      promptSelection: 5,
      templateVariables: null,
      selectedTags: {},
      frameworkId: 'zwölf',
      competenciesOverride: 42,
      activeStep: 1,
    });
    expect(result).toEqual({ activeStep: 1 });
  });

  it('keeps a partial snapshot so unaffected fields still survive', () => {
    // Shape drift must not discard everything: whatever still fits is kept.
    const result = sanitizeWizardSnapshot({
      ragRequest: { topic: 'Heapsort' },
      frameworkId: 12,
      selectedDocs: 'kaputt',
    });
    expect(result).toEqual({ ragRequest: { topic: 'Heapsort' }, frameworkId: 12 });
  });
});
