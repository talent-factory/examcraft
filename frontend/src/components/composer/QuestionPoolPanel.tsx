import React, { useState, useMemo, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation } from '@tanstack/react-query';
import { tagsApi } from '../../api/tagsApi';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
} from '@mui/material';
import { ComposerService, getErrorMessage } from '../../services/ComposerService';
import { competencyFrameworksApi } from '../../api/competencyFrameworksApi';
import type {
  ApprovedQuestion,
  AutoFillRequest,
  AutoComposePreview,
  QuestionSort,
} from '../../types/composer';
import { isAutoComposePreview } from '../../types/composer';

interface QuestionPoolPanelProps {
  addedQuestionIds: Set<number>;
  onAddQuestions: (ids: number[]) => void;
  examId: number;
  disabled: boolean;
  onInvalidate: () => void;
  defaultDocumentIds?: number[];
  /** TF-405: open the read-only preview modal (owned by the parent). */
  onPreview: (questionId: number) => void;
}

const DIFFICULTY_COLORS: Record<string, string> = {
  easy: 'bg-green-100 text-green-700',
  medium: 'bg-yellow-100 text-yellow-700',
  hard: 'bg-red-100 text-red-700',
};

// TF-406: gemeinsame Optik der Facetten-/Sortier-Dropdowns.
const FACET_SELECT_CLS =
  'text-xs px-2 py-1.5 border border-gray-300 rounded-lg bg-white text-gray-700 ' +
  'focus:ring-2 focus:ring-primary-500 focus:border-transparent ' +
  'disabled:opacity-50 disabled:cursor-not-allowed';

interface AutoFillForm {
  count: string;
  topic: string;
  difficulty: string[];
  bloom_level_min: string;
  question_types: string[];
}

interface CompositionForm {
  target_points: string;
  target_duration_minutes: string;
  bloom_distribution: Record<number, string>;
  difficulty_distribution: Record<string, string>;
  topic: string;
  question_types: string[];
}

const QuestionPoolPanel: React.FC<QuestionPoolPanelProps> = ({
  addedQuestionIds,
  onAddQuestions,
  examId,
  disabled,
  onInvalidate,
  defaultDocumentIds = [],
  onPreview,
}) => {
  const { t } = useTranslation();

  const DIFFICULTY_LABELS = useMemo<Record<string, string>>(() => ({
    easy: t('composer.questionPool.difficultyEasy'),
    medium: t('composer.questionPool.difficultyMedium'),
    hard: t('composer.questionPool.difficultyHard'),
  }), [t]);

  const TYPE_ABBREV = useMemo<Record<string, string>>(() => ({
    multiple_choice: t('composer.questionPool.typeMultipleChoice'),
    true_false: t('composer.questionPool.typeTrueFalse'),
    open_ended: t('composer.questionPool.typeOpenEnded'),
  }), [t]);

  const BLOOM_LABELS = useMemo<Record<number, string>>(() => ({
    1: t('composer.questionPool.bloomRemember'),
    2: t('composer.questionPool.bloomUnderstand'),
    3: t('composer.questionPool.bloomApply'),
    4: t('composer.questionPool.bloomAnalyze'),
    5: t('composer.questionPool.bloomEvaluate'),
    6: t('composer.questionPool.bloomCreate'),
  }), [t]);

  const PRESETS = useMemo<Record<string, {
    bloom: Record<number, number>;
    difficulty: Record<string, number>;
    label: string;
  }>>(() => ({
    balanced: {
      label: t('composer.questionPool.presetBalanced'),
      bloom: { 1: 15, 2: 25, 3: 25, 4: 20, 5: 10, 6: 5 },
      difficulty: { easy: 30, medium: 40, hard: 30 },
    },
    application: {
      label: t('composer.questionPool.presetApplication'),
      bloom: { 1: 10, 2: 15, 3: 35, 4: 25, 5: 10, 6: 5 },
      difficulty: { easy: 20, medium: 40, hard: 40 },
    },
  }), [t]);

  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState('');
  const [filterDifficulty, setFilterDifficulty] = useState('');
  const [selectedTagIds, setSelectedTagIds] = useState<number[]>([]);
  const [tagFilterOpen, setTagFilterOpen] = useState(false);
  const [tagSearch, setTagSearch] = useState('');
  const tagFilterRef = useRef<HTMLDivElement>(null);
  const tagSearchRef = useRef<HTMLInputElement>(null);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<number[]>([]);
  const [docFilterOpen, setDocFilterOpen] = useState(false);
  const docFilterRef = useRef<HTMLDivElement>(null);
  // TF-406: Fachfilter-Facetten + Sortierung. Leerstring = Facette inaktiv.
  const [filterBloom, setFilterBloom] = useState<number | ''>('');
  const [filterLnLevel, setFilterLnLevel] = useState<number | ''>('');
  const [filterCompetencyId, setFilterCompetencyId] = useState<number | ''>('');
  const [filterQualityTier, setFilterQualityTier] = useState('');
  const [filterUnused, setFilterUnused] = useState(false);
  const [sortBy, setSortBy] = useState<QuestionSort>('newest');

  useEffect(() => {
    if (!docFilterOpen) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (docFilterRef.current && !docFilterRef.current.contains(e.target as Node)) {
        setDocFilterOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [docFilterOpen]);
  const [autoFillOpen, setAutoFillOpen] = useState(false);
  const [autoFillError, setAutoFillError] = useState<string | null>(null);
  const [autoFillForm, setAutoFillForm] = useState<AutoFillForm>({
    count: '5',
    topic: '',
    difficulty: [],
    bloom_level_min: '',
    question_types: [],
  });
  const [compositionMode, setCompositionMode] = useState(false);
  const [compositionForm, setCompositionForm] = useState<CompositionForm>({
    target_points: '',
    target_duration_minutes: '',
    bloom_distribution: { 1: '', 2: '', 3: '', 4: '', 5: '', 6: '' },
    difficulty_distribution: { easy: '', medium: '', hard: '' },
    topic: '',
    question_types: [],
  });
  const [preview, setPreview] = useState<AutoComposePreview | null>(null);
  const [lastPreviewRequest, setLastPreviewRequest] = useState<AutoFillRequest | null>(null);

  const { data: allTagsRaw = [] } = useQuery({
    queryKey: ['tags', 'includeArchived'],
    queryFn: () => tagsApi.listTags(true),
    staleTime: 60_000,
  });
  const activeTags = allTagsRaw.filter((t) => !t.is_archived);
  const archivedTagsWithQuestions = allTagsRaw.filter((t) => t.is_archived && t.usage_count > 0);

  // TF-406: Handlungskompetenzen für die Kompetenz-Facette (über alle aktiven
  // Frameworks der Institution geflacht).
  const { data: frameworks = [] } = useQuery({
    queryKey: ['competency-frameworks', 'active'],
    queryFn: () => competencyFrameworksApi.listFrameworks(false),
    staleTime: 60_000,
  });
  const competencies = useMemo(
    () =>
      frameworks
        .flatMap((fw) => fw.competencies)
        .sort((a, b) => a.code.localeCompare(b.code)),
    [frameworks],
  );

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (tagFilterRef.current && !tagFilterRef.current.contains(event.target as Node)) {
        setTagFilterOpen(false);
      }
    };
    if (tagFilterOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [tagFilterOpen]);

  const {
    data: allDocs = [],
    isError: isDocsError,
    error: docsError,
  } = useQuery({
    queryKey: ['documents-with-questions'],
    queryFn: () => ComposerService.listDocumentsWithQuestions(),
    staleTime: 0,
    refetchOnMount: 'always',
  });
  const availableDocs = defaultDocumentIds.length > 0
    ? allDocs.filter((d) => defaultDocumentIds.includes(d.id))
    : allDocs;

  const {
    data,
    isLoading,
    isError: isQuestionsError,
    error: questionsError,
  } = useQuery({
    queryKey: [
      'approved-questions',
      search,
      filterType,
      filterDifficulty,
      filterBloom,
      filterLnLevel,
      filterCompetencyId,
      filterQualityTier,
      filterUnused,
      sortBy,
      selectedTagIds,
      selectedDocumentIds,
      defaultDocumentIds,
    ],
    queryFn: () =>
      ComposerService.listApprovedQuestions({
        search: search || undefined,
        question_type: filterType || undefined,
        difficulty: filterDifficulty || undefined,
        bloom_level: filterBloom === '' ? undefined : filterBloom,
        ln_level: filterLnLevel === '' ? undefined : filterLnLevel,
        competency_id: filterCompetencyId === '' ? undefined : filterCompetencyId,
        quality_tier: filterQualityTier || undefined,
        unused: filterUnused || undefined,
        sort: sortBy,
        tag_ids: selectedTagIds.length > 0 ? selectedTagIds : undefined,
        document_ids: selectedDocumentIds.length > 0
          ? selectedDocumentIds
          : defaultDocumentIds.length > 0 ? defaultDocumentIds : undefined,
        limit: 50,
      }),
    staleTime: 0,
    refetchOnMount: 'always',
  });

  const autoFillMutation = useMutation({
    mutationFn: (req: AutoFillRequest) => ComposerService.autoFill(examId, req),
    onSuccess: () => {
      setAutoFillError(null);
      setAutoFillOpen(false);
      onInvalidate();
    },
    onError: (err) => {
      setAutoFillError(getErrorMessage(err, t('composer.questionPool.autoFillFailed')));
    },
  });

  const handleAutoFill = () => {
    const req: AutoFillRequest = {
      count: parseInt(autoFillForm.count) || 5,
      topic: autoFillForm.topic || undefined,
      difficulty: autoFillForm.difficulty.length > 0 ? autoFillForm.difficulty : undefined,
      bloom_level_min: autoFillForm.bloom_level_min
        ? parseInt(autoFillForm.bloom_level_min)
        : undefined,
      question_types:
        autoFillForm.question_types.length > 0 ? autoFillForm.question_types : undefined,
      exclude_question_ids: Array.from(addedQuestionIds),
      document_ids: selectedDocumentIds.length > 0 ? selectedDocumentIds : undefined,
    };
    autoFillMutation.mutate(req);
  };

  const toggleAutoFillDifficulty = (d: string) => {
    setAutoFillForm((f) => ({
      ...f,
      difficulty: f.difficulty.includes(d)
        ? f.difficulty.filter((x) => x !== d)
        : [...f.difficulty, d],
    }));
  };

  const toggleAutoFillType = (type: string) => {
    setAutoFillForm((f) => ({
      ...f,
      question_types: f.question_types.includes(type)
        ? f.question_types.filter((x) => x !== type)
        : [...f.question_types, type],
    }));
  };

  const composeMutation = useMutation({
    mutationFn: (req: AutoFillRequest) => ComposerService.autoFill(examId, req),
    onSuccess: (responseData) => {
      if (isAutoComposePreview(responseData)) {
        setPreview(responseData);
        setAutoFillError(null);
      } else {
        setPreview(null);
        setAutoFillOpen(false);
        setAutoFillError(null);
        onInvalidate();
      }
    },
    onError: (err) => {
      setAutoFillError(getErrorMessage(err, t('composer.questionPool.compositionFailed')));
    },
  });

  const handleCompose = () => {
    const targetPoints = compositionForm.target_points.trim() !== ''
      ? parseFloat(compositionForm.target_points) : undefined;
    const targetDuration = compositionForm.target_duration_minutes.trim() !== ''
      ? parseInt(compositionForm.target_duration_minutes) : undefined;

    if (targetPoints !== undefined && (isNaN(targetPoints) || targetPoints <= 0)) {
      setAutoFillError(t('composer.questionPool.targetPointsRequired'));
      return;
    }
    if (targetDuration !== undefined && (isNaN(targetDuration) || targetDuration <= 0)) {
      setAutoFillError(t('composer.questionPool.targetDurationRequired'));
      return;
    }

    const bloomDist: Record<number, number> = {};
    let hasBloom = false;
    for (const [k, v] of Object.entries(compositionForm.bloom_distribution)) {
      const num = parseFloat(v);
      if (num > 0) { bloomDist[parseInt(k)] = num; hasBloom = true; }
    }

    const diffDist: Record<string, number> = {};
    let hasDiff = false;
    for (const [k, v] of Object.entries(compositionForm.difficulty_distribution)) {
      const num = parseFloat(v);
      if (num > 0) { diffDist[k] = num; hasDiff = true; }
    }

    if (targetPoints === undefined && targetDuration === undefined && !hasBloom && !hasDiff) {
      setAutoFillError(t('composer.questionPool.noConstraints'));
      return;
    }

    setAutoFillError(null);
    const req: AutoFillRequest = {
      target_points: targetPoints,
      target_duration_minutes: targetDuration,
      bloom_distribution: hasBloom ? bloomDist : undefined,
      difficulty_distribution: hasDiff ? diffDist : undefined,
      topic: compositionForm.topic || undefined,
      question_types: compositionForm.question_types.length > 0 ? compositionForm.question_types : undefined,
      exclude_question_ids: Array.from(addedQuestionIds),
      preview: true,
      document_ids: selectedDocumentIds.length > 0 ? selectedDocumentIds : undefined,
    };
    setLastPreviewRequest(req);
    composeMutation.mutate(req);
  };

  const handleAcceptPreview = () => {
    if (!lastPreviewRequest) return;
    composeMutation.mutate({ ...lastPreviewRequest, preview: false });
  };

  const applyPreset = (presetKey: string) => {
    const preset = PRESETS[presetKey];
    if (!preset) return;
    const bloomDist: Record<number, string> = { 1: '', 2: '', 3: '', 4: '', 5: '', 6: '' };
    for (const [k, v] of Object.entries(preset.bloom)) {
      bloomDist[parseInt(k)] = v.toString();
    }
    const diffDist: Record<string, string> = { easy: '', medium: '', hard: '' };
    for (const [k, v] of Object.entries(preset.difficulty)) {
      diffDist[k] = v.toString();
    }
    setCompositionForm((f) => ({ ...f, bloom_distribution: bloomDist, difficulty_distribution: diffDist }));
  };

  const getDocTitle = (id: number) => {
    const doc = allDocs.find((d) => d.id === id);
    return doc ? `${doc.title} (${doc.approved_question_count})` : `Doc ${id}`;
  };

  // TF-406: Auto-Komposition (constraint-basiert) als 1-Klick-Einstieg sichtbar
  // machen — öffnet den Dialog direkt im Kompositions-Modus.
  const openAutoFill = (composition: boolean) => {
    setCompositionMode(composition);
    setPreview(null);
    setAutoFillError(null);
    setAutoFillOpen(true);
  };

  const resetAllFilters = () => {
    setSearch('');
    setFilterType('');
    setFilterDifficulty('');
    setSelectedTagIds([]);
    setSelectedDocumentIds([]);
    setFilterBloom('');
    setFilterLnLevel('');
    setFilterCompetencyId('');
    setFilterQualityTier('');
    setFilterUnused(false);
    setSortBy('newest');
  };

  const competencyChipLabel = (id: number) => {
    const c = competencies.find((x) => x.id === id);
    return c ? c.code : `#${id}`;
  };

  // TF-406: aktive Fachfilter-Facetten als Chips. Bestehende Filter (Suche,
  // Typ, Difficulty, Tags, Dokument) behalten ihre eigene Inline-Darstellung.
  const facetChips: { key: string; label: string; onClear: () => void }[] = [];
  if (filterLnLevel !== '') {
    facetChips.push({
      key: 'ln',
      label: t('composer.questionPool.lnLevelOption', { level: filterLnLevel }),
      onClear: () => setFilterLnLevel(''),
    });
  }
  if (filterQualityTier) {
    facetChips.push({
      key: 'quality',
      label: t('composer.questionPool.qualityOption', { tier: filterQualityTier }),
      onClear: () => setFilterQualityTier(''),
    });
  }
  if (filterBloom !== '') {
    facetChips.push({
      key: 'bloom',
      label: BLOOM_LABELS[filterBloom],
      onClear: () => setFilterBloom(''),
    });
  }
  if (filterCompetencyId !== '') {
    facetChips.push({
      key: 'competency',
      label: competencyChipLabel(filterCompetencyId),
      onClear: () => setFilterCompetencyId(''),
    });
  }
  if (filterUnused) {
    facetChips.push({
      key: 'unused',
      label: t('composer.questionPool.unusedLabel'),
      onClear: () => setFilterUnused(false),
    });
  }

  const hasAnyFilter =
    Boolean(search) ||
    Boolean(filterType) ||
    Boolean(filterDifficulty) ||
    selectedTagIds.length > 0 ||
    selectedDocumentIds.length > 0 ||
    facetChips.length > 0 ||
    sortBy !== 'newest';

  return (
    <div className="card p-4 bg-white rounded-lg border border-gray-200 h-full flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-gray-900">{t('composer.questionPool.title')}</h3>
        {!disabled && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => openAutoFill(false)}
              className="text-sm px-3 py-1 border border-indigo-600 text-indigo-700 rounded-lg hover:bg-indigo-50 transition-colors"
            >
              {t('composer.questionPool.autoFill')}
            </button>
            <button
              onClick={() => openAutoFill(true)}
              className="text-sm px-3 py-1 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
            >
              {t('composer.questionPool.autoComposeButton')}
            </button>
          </div>
        )}
      </div>

      {/* Search */}
      <input
        type="text"
        placeholder={t('composer.questionPool.searchPlaceholder')}
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent mb-2"
      />

      {/* Document filter — show error banner if the document list query failed
          so the filter UI doesn't silently disappear (which is identical to
          the "institution has no documents" state and looks like a bug). */}
      {isDocsError && (
        <div
          className="mb-2 px-3 py-2 rounded-lg border border-red-200 bg-red-50 text-red-700 text-sm"
          role="alert"
        >
          {getErrorMessage(docsError, t('composer.questionPool.errorLoadingDocuments'))}
        </div>
      )}
      {!isDocsError && availableDocs.length > 0 && (
        <div className="mb-2">
          <div className="relative w-fit" ref={docFilterRef}>
            <button
              onClick={() => setDocFilterOpen((o) => !o)}
              className={`flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-full border font-medium transition-colors ${
                selectedDocumentIds.length > 0
                  ? 'bg-indigo-600 text-white border-indigo-600'
                  : 'bg-indigo-50 text-indigo-700 border-indigo-200 hover:bg-indigo-100'
              }`}
            >
              {t('composer.questionPool.documentFilterLabel')}
              {selectedDocumentIds.length > 0 && ` (${selectedDocumentIds.length})`}
              <svg
                className={`w-3.5 h-3.5 transition-transform duration-200 ${docFilterOpen ? 'rotate-180' : ''}`}
                fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            {docFilterOpen && (
              <div className="absolute top-full left-0 mt-1 z-10 bg-white border border-gray-200 rounded-lg shadow-lg w-64 max-h-48 overflow-y-auto">
                {availableDocs.map((doc) => (
                  <label
                    key={doc.id}
                    className="flex items-center gap-2 px-3 py-2 hover:bg-gray-50 cursor-pointer text-sm"
                  >
                    <input
                      type="checkbox"
                      checked={selectedDocumentIds.includes(doc.id)}
                      onChange={() =>
                        setSelectedDocumentIds((ids) =>
                          ids.includes(doc.id)
                            ? ids.filter((id) => id !== doc.id)
                            : [...ids, doc.id]
                        )
                      }
                      className="rounded"
                    />
                    <span className="flex-1 truncate">{doc.title}</span>
                    <span className="text-gray-400 flex-shrink-0">({doc.approved_question_count})</span>
                  </label>
                ))}
              </div>
            )}
          </div>
          {selectedDocumentIds.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1">
              {selectedDocumentIds.map((id) => (
                <span
                  key={id}
                  className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700"
                >
                  {getDocTitle(id)}
                  <button
                    onClick={() =>
                      setSelectedDocumentIds((ids) => ids.filter((x) => x !== id))
                    }
                    className="hover:text-indigo-900 ml-0.5"
                    aria-label={t('composer.questionPool.documentFilterRemove')}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Type + difficulty filter chips */}
      <div className="flex gap-2 flex-wrap mb-3">
        {(['multiple_choice', 'true_false', 'open_ended'] as const).map((type) => (
          <button
            key={type}
            onClick={() => setFilterType(filterType === type ? '' : type)}
            className={`text-xs px-2 py-1 rounded-full border transition-colors ${
              filterType === type
                ? 'bg-indigo-600 text-white border-indigo-600'
                : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'
            }`}
          >
            {TYPE_ABBREV[type]}
          </button>
        ))}
        {(['easy', 'medium', 'hard'] as const).map((d) => (
          <button
            key={d}
            onClick={() => setFilterDifficulty(filterDifficulty === d ? '' : d)}
            className={`text-xs px-2 py-1 rounded-full border transition-colors ${
              filterDifficulty === d
                ? DIFFICULTY_COLORS[d] + ' border-current font-semibold'
                : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'
            }`}
          >
            {DIFFICULTY_LABELS[d]}
          </button>
        ))}

        {/* Tag filter */}
        <div className="relative" ref={tagFilterRef}>
          <button
            type="button"
            onClick={() => {
              const opening = !tagFilterOpen;
              setTagFilterOpen(opening);
              if (opening) {
                setTagSearch('');
                setTimeout(() => tagSearchRef.current?.focus(), 50);
              }
            }}
            className={`inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-md border transition-colors ${
              selectedTagIds.length > 0 || tagFilterOpen
                ? 'bg-indigo-600 text-white border-indigo-600'
                : 'bg-indigo-50 text-indigo-600 border-indigo-200 hover:bg-indigo-100 hover:border-indigo-300'
            }`}
          >
            <svg className="w-3 h-3 opacity-70" viewBox="0 0 16 16" fill="currentColor">
              <path d="M2 4.5A.5.5 0 0 1 2.5 4h11a.5.5 0 0 1 0 1h-11A.5.5 0 0 1 2 4.5zm2 3A.5.5 0 0 1 4.5 7h7a.5.5 0 0 1 0 1h-7A.5.5 0 0 1 4 7.5zm2 3a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 0 1h-3a.5.5 0 0 1-.5-.5z"/>
            </svg>
            {t('composer.questionPool.tagFilterLabel')}
            {selectedTagIds.length > 0 && ` (${selectedTagIds.length})`}
            <svg
              className={`w-2.5 h-2.5 opacity-60 transition-transform ${tagFilterOpen ? 'rotate-180' : ''}`}
              viewBox="0 0 16 16" fill="currentColor"
            >
              <path d="M7.247 11.14L2.451 5.658C1.885 5.013 2.345 4 3.204 4h9.592a1 1 0 0 1 .753 1.659l-4.796 5.48a1 1 0 0 1-1.506 0z"/>
            </svg>
          </button>

          {tagFilterOpen && (
            <div className="absolute z-10 mt-1 bg-white border border-gray-200 rounded-xl shadow-lg w-[280px]">
              {/* Suchfeld */}
              <div className="p-2 border-b border-gray-100">
                <input
                  ref={tagSearchRef}
                  type="text"
                  value={tagSearch}
                  onChange={(e) => setTagSearch(e.target.value)}
                  placeholder={t('composer.questionPool.tagFilterSearch', 'Tag suchen…')}
                  className="w-full text-xs px-2.5 py-1.5 rounded-lg border border-gray-200 bg-gray-50 focus:outline-none focus:border-purple-300 focus:bg-white transition-colors"
                />
              </div>

              {/* Tag-Chips — aktive und archivierte Sektionen */}
              {(() => {
                const q = tagSearch.toLowerCase();
                const filteredActive = activeTags
                  .filter((tag) => tag.name.toLowerCase().includes(q))
                  .sort((a, b) => a.name.localeCompare(b.name));
                const filteredGlobal = filteredActive.filter((t) => t.scope === 'global');
                const filteredInstitution = filteredActive.filter((t) => t.scope === 'institution');
                const filteredArchived = archivedTagsWithQuestions
                  .filter((tag) => tag.name.toLowerCase().includes(q))
                  .sort((a, b) => a.name.localeCompare(b.name));
                const hasAny = filteredActive.length > 0 || filteredArchived.length > 0;

                const renderChip = (tag: typeof activeTags[0], archived = false) => {
                  const active = selectedTagIds.includes(tag.id);
                  return (
                    <button
                      key={tag.id}
                      type="button"
                      onClick={() =>
                        setSelectedTagIds((ids) =>
                          ids.includes(tag.id)
                            ? ids.filter((id) => id !== tag.id)
                            : [...ids, tag.id]
                        )
                      }
                      className={`text-xs px-2.5 py-1 rounded-full border transition-all flex items-center gap-1 ${
                        active
                          ? archived
                            ? 'bg-gray-200 text-gray-600 border-gray-400 font-medium shadow-sm'
                            : 'bg-purple-100 text-purple-700 border-purple-400 font-medium shadow-sm'
                          : archived
                          ? 'bg-gray-50 text-gray-400 border-gray-200 hover:bg-gray-100 hover:border-gray-300'
                          : 'bg-gray-50 text-gray-600 border-gray-200 hover:bg-gray-100 hover:border-gray-300'
                      }`}
                    >
                      {archived && <span className="opacity-60">📦</span>}
                      {tag.name}
                    </button>
                  );
                };

                return (
                  <div className="p-2" style={{ maxHeight: '280px', overflowY: 'auto' }}>
                    {activeTags.length === 0 && archivedTagsWithQuestions.length === 0 ? (
                      <p className="text-xs text-gray-400 px-1">
                        {t('composer.questionPool.tagFilterEmpty')}
                      </p>
                    ) : !hasAny ? (
                      <p className="text-xs text-gray-400 px-1">
                        {t('composer.questionPool.tagFilterNoResults', 'Keine Tags gefunden')}
                      </p>
                    ) : (
                      <>
                        {filteredGlobal.length > 0 && (
                          <>
                            <div className="flex items-center gap-1.5 mb-1.5 px-1 py-0.5 bg-gray-50 rounded">
                              <svg className="w-3 h-3 text-gray-400 flex-shrink-0" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
                              </svg>
                              <span className="text-[10px] font-bold uppercase tracking-wide text-gray-500">
                                Vorgegebene Tags
                              </span>
                            </div>
                            <div className="flex flex-wrap gap-1.5 mb-2">
                              {filteredGlobal.map((tag) => renderChip(tag, false))}
                            </div>
                          </>
                        )}
                        {filteredInstitution.length > 0 && (
                          <>
                            {filteredGlobal.length > 0 && (
                              <div className="flex items-center gap-1.5 mb-1.5 px-1 py-0.5 bg-blue-50 rounded">
                                <svg className="w-3 h-3 text-blue-500 flex-shrink-0" viewBox="0 0 24 24" fill="currentColor">
                                  <path d="M12 7V3H2v18h20V7H12zM6 19H4v-2h2v2zm0-4H4v-2h2v2zm0-4H4V9h2v2zm0-4H4V5h2v2zm4 12H8v-2h2v2zm0-4H8v-2h2v2zm0-4H8V9h2v2zm0-4H8V5h2v2zm10 12h-8v-2h2v-2h-2v-2h2v-2h-2V9h8v10zm-2-8h-2v2h2v-2zm0 4h-2v2h2v-2z"/>
                                </svg>
                                <span className="text-[10px] font-bold uppercase tracking-wide text-blue-600">
                                  Tags dieser Institution
                                </span>
                              </div>
                            )}
                            <div className="flex flex-wrap gap-1.5">
                              {filteredInstitution.map((tag) => renderChip(tag, false))}
                            </div>
                          </>
                        )}

                        {filteredArchived.length > 0 && (
                          <>
                            <div className="flex items-center gap-2 my-2">
                              <div className="flex-1 border-t border-gray-100" />
                              <span className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">
                                Archiviert
                              </span>
                              <div className="flex-1 border-t border-gray-100" />
                            </div>
                            <div className="flex flex-wrap gap-1.5">
                              {filteredArchived.map((tag) => renderChip(tag, true))}
                            </div>
                          </>
                        )}
                      </>
                    )}

                    {selectedTagIds.length > 0 && (
                      <button
                        type="button"
                        onClick={() => setSelectedTagIds([])}
                        className="mt-2 w-full text-xs text-gray-400 hover:text-gray-600 transition-colors text-right"
                      >
                        {t('composer.questionPool.tagFilterClear', 'Alle entfernen')}
                      </button>
                    )}
                  </div>
                );
              })()}
            </div>
          )}
        </div>

        {/* Aktive Tag-Chips unter dem Button */}
        {selectedTagIds.map((id) => {
          const tag = allTagsRaw.find((tag) => tag.id === id);
          if (!tag) return null;
          return (
            <span
              key={id}
              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border ${
                tag.is_archived
                  ? 'bg-gray-100 text-gray-500 border-gray-300'
                  : 'bg-purple-100 text-purple-700 border-purple-200'
              }`}
            >
              {tag.is_archived && <span className="opacity-60 text-[10px]">📦</span>}
              {tag.name}
              <button
                type="button"
                onClick={() => setSelectedTagIds((ids) => ids.filter((x) => x !== id))}
                aria-label={t('composer.questionPool.tagFilterRemove')}
                className={`font-bold leading-none ${tag.is_archived ? 'hover:text-gray-700' : 'hover:text-purple-900'}`}
              >
                ×
              </button>
            </span>
          );
        })}
      </div>

      {/* TF-406: Fachfilter-Facetten, Sortierung & aktive-Filter-Chips */}
      {!disabled && (
        <div className="mb-3 space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <select
              value={filterLnLevel}
              onChange={(e) =>
                setFilterLnLevel(e.target.value === '' ? '' : Number(e.target.value))
              }
              aria-label={t('composer.questionPool.lnLevelSelectLabel')}
              className={FACET_SELECT_CLS}
            >
              <option value="">{t('composer.questionPool.lnLevelAll')}</option>
              {[1, 2, 3, 4].map((n) => (
                <option key={n} value={n}>
                  {t('composer.questionPool.lnLevelOption', { level: n })}
                </option>
              ))}
            </select>
            <select
              value={filterQualityTier}
              onChange={(e) => setFilterQualityTier(e.target.value)}
              aria-label={t('composer.questionPool.qualitySelectLabel')}
              className={FACET_SELECT_CLS}
            >
              <option value="">{t('composer.questionPool.qualityAll')}</option>
              {['A', 'B', 'C'].map((tier) => (
                <option key={tier} value={tier}>
                  {t('composer.questionPool.qualityOption', { tier })}
                </option>
              ))}
            </select>
            <select
              value={filterBloom}
              onChange={(e) =>
                setFilterBloom(e.target.value === '' ? '' : Number(e.target.value))
              }
              aria-label={t('composer.questionPool.bloomSelectLabel')}
              className={FACET_SELECT_CLS}
            >
              <option value="">{t('composer.questionPool.bloomAll')}</option>
              {[1, 2, 3, 4, 5, 6].map((b) => (
                <option key={b} value={b}>
                  {BLOOM_LABELS[b]}
                </option>
              ))}
            </select>
            <select
              value={filterCompetencyId}
              onChange={(e) =>
                setFilterCompetencyId(e.target.value === '' ? '' : Number(e.target.value))
              }
              aria-label={t('composer.questionPool.competencySelectLabel')}
              disabled={competencies.length === 0}
              className={FACET_SELECT_CLS}
            >
              <option value="">{t('composer.questionPool.competencyAll')}</option>
              {competencies.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.code} — {c.title}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-center justify-between gap-2">
            <label className="flex items-center gap-1.5 text-xs text-gray-600 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={filterUnused}
                onChange={(e) => setFilterUnused(e.target.checked)}
                className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
              />
              {t('composer.questionPool.unusedLabel')}
            </label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as QuestionSort)}
              aria-label={t('composer.questionPool.sortLabel')}
              className={FACET_SELECT_CLS}
            >
              <option value="newest">{t('composer.questionPool.sortNewest')}</option>
              <option value="most_used">{t('composer.questionPool.sortMostUsed')}</option>
              <option value="difficulty">{t('composer.questionPool.sortDifficulty')}</option>
            </select>
          </div>
          {(facetChips.length > 0 || hasAnyFilter) && (
            <div className="flex flex-wrap items-center gap-1.5">
              {facetChips.map((chip) => (
                <span
                  key={chip.key}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border bg-indigo-50 text-indigo-700 border-indigo-200"
                >
                  {chip.label}
                  <button
                    type="button"
                    onClick={chip.onClear}
                    aria-label={t('composer.questionPool.filterChipRemove')}
                    className="font-bold leading-none hover:text-indigo-900"
                  >
                    ×
                  </button>
                </span>
              ))}
              {hasAnyFilter && (
                <button
                  type="button"
                  onClick={resetAllFilters}
                  className="text-xs text-indigo-600 hover:text-indigo-800 font-medium ml-auto"
                >
                  {t('composer.questionPool.resetFilters')}
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {/* Question list */}
      <div className="flex-1 overflow-y-auto space-y-2 min-h-0">
        {isLoading ? (
          <div className="text-center py-8 text-gray-500 text-sm">{t('composer.questionPool.loading')}</div>
        ) : isQuestionsError ? (
          <div
            className="mx-auto my-4 max-w-sm px-3 py-2 rounded-lg border border-red-200 bg-red-50 text-red-700 text-sm text-center"
            role="alert"
          >
            {getErrorMessage(questionsError, t('composer.questionPool.errorLoadingQuestions'))}
          </div>
        ) : !data?.questions.length ? (
          <div className="text-center py-8 text-gray-400 text-sm">
            {t('composer.questionPool.noQuestions')}
          </div>
        ) : (
          data.questions.map((q) => (
            <PoolQuestionCard
              key={q.id}
              question={q}
              isAdded={addedQuestionIds.has(q.id)}
              disabled={disabled}
              onAdd={() => onAddQuestions([q.id])}
              onPreview={() => onPreview(q.id)}
            />
          ))
        )}
      </div>

      {data && (
        <p className="text-xs text-gray-400 mt-2 text-right">
          {t('composer.questionPool.available', { count: data.total })}
        </p>
      )}

      {/* Auto-Fill Dialog */}
      <Dialog
        open={autoFillOpen}
        onClose={() => { setAutoFillOpen(false); setAutoFillError(null); setPreview(null); }}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          <div className="flex gap-2">
            <button
              onClick={() => { setCompositionMode(false); setPreview(null); }}
              className={`px-3 py-1 rounded-lg text-sm ${!compositionMode ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-600'}`}
            >
              {t('composer.questionPool.modeSimple')}
            </button>
            <button
              onClick={() => { setCompositionMode(true); setPreview(null); }}
              className={`px-3 py-1 rounded-lg text-sm ${compositionMode ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-600'}`}
            >
              {t('composer.questionPool.modeComposition')}
            </button>
          </div>
        </DialogTitle>
        <DialogContent>
          {!compositionMode ? (
            <div className="space-y-4 mt-2">
              <TextField label={t('composer.questionPool.autoFillCount')} type="number" fullWidth
                inputProps={{ min: 1, max: 20 }} value={autoFillForm.count}
                onChange={(e) => setAutoFillForm({ ...autoFillForm, count: e.target.value })} />
              <TextField label={t('composer.questionPool.autoFillTopic')} fullWidth value={autoFillForm.topic}
                onChange={(e) => setAutoFillForm({ ...autoFillForm, topic: e.target.value })} />
              <div>
                <p className="text-sm text-gray-600 mb-1">{t('composer.questionPool.autoFillDifficulty')}</p>
                <div className="flex gap-2">
                  {(['easy', 'medium', 'hard'] as const).map((d) => (
                    <button key={d} type="button" onClick={() => toggleAutoFillDifficulty(d)}
                      className={`text-xs px-2 py-1 rounded-full border transition-colors ${
                        autoFillForm.difficulty.includes(d) ? DIFFICULTY_COLORS[d] + ' border-current font-semibold' : 'bg-white text-gray-600 border-gray-300'
                      }`}>{DIFFICULTY_LABELS[d]}</button>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-sm text-gray-600 mb-1">{t('composer.questionPool.autoFillTypes')}</p>
                <div className="flex gap-2 flex-wrap">
                  {(['multiple_choice', 'true_false', 'open_ended'] as const).map((qt) => (
                    <button key={qt} type="button" onClick={() => toggleAutoFillType(qt)}
                      className={`text-xs px-2 py-1 rounded-full border transition-colors ${
                        autoFillForm.question_types.includes(qt) ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-gray-600 border-gray-300'
                      }`}>{TYPE_ABBREV[qt]}</button>
                  ))}
                </div>
              </div>
              <TextField label={t('composer.questionPool.autoFillBloomLevel')} type="number" fullWidth
                inputProps={{ min: 1, max: 6 }} value={autoFillForm.bloom_level_min}
                onChange={(e) => setAutoFillForm({ ...autoFillForm, bloom_level_min: e.target.value })} />
            </div>
          ) : preview ? (
            <div className="space-y-4 mt-2">
              <div className="grid grid-cols-3 gap-2 text-center text-sm">
                <div className="p-2 bg-gray-50 rounded">
                  <div className="text-gray-500">{t('composer.questionPool.points')}</div>
                  <div className="font-semibold">{preview.total_points} / {preview.constraint_report.points_target ?? '–'}</div>
                </div>
                <div className="p-2 bg-gray-50 rounded">
                  <div className="text-gray-500">{t('composer.questionPool.duration')}</div>
                  <div className="font-semibold">{preview.total_duration_minutes} / {preview.constraint_report.duration_target ?? '–'} min</div>
                </div>
                <div className="p-2 bg-gray-50 rounded">
                  <div className="text-gray-500">{t('composer.questionPool.satisfaction')}</div>
                  <div className={`font-semibold ${preview.constraint_report.overall_satisfaction >= 80 ? 'text-green-600' : 'text-yellow-600'}`}>
                    {preview.constraint_report.overall_satisfaction}%
                  </div>
                </div>
              </div>
              {Object.keys(preview.constraint_report.bloom_distribution).length > 0 && (
                <div>
                  <p className="text-sm font-medium text-gray-700 mb-1">{t('composer.questionPool.bloomDistribution')}</p>
                  <div className="space-y-1">
                    {Object.entries(preview.constraint_report.bloom_distribution).map(([level, dr]) => (
                      <div key={level} className="flex items-center gap-2 text-xs">
                        <span className="w-24 text-gray-600">B{level} {BLOOM_LABELS[parseInt(level)] || ''}</span>
                        <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                          <div className={`h-full rounded-full ${dr.within_tolerance ? 'bg-green-500' : 'bg-yellow-500'}`}
                            style={{ width: `${Math.min(dr.achieved_pct, 100)}%` }} />
                        </div>
                        <span className="w-20 text-right">{dr.achieved_pct}% / {dr.target_pct}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {Object.keys(preview.constraint_report.difficulty_distribution).length > 0 && (
                <div>
                  <p className="text-sm font-medium text-gray-700 mb-1">{t('composer.questionPool.difficultyDistribution')}</p>
                  <div className="space-y-1">
                    {Object.entries(preview.constraint_report.difficulty_distribution).map(([diff, dr]) => (
                      <div key={diff} className="flex items-center gap-2 text-xs">
                        <span className="w-24 text-gray-600">{DIFFICULTY_LABELS[diff] || diff}</span>
                        <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                          <div className={`h-full rounded-full ${dr.within_tolerance ? 'bg-green-500' : 'bg-yellow-500'}`}
                            style={{ width: `${Math.min(dr.achieved_pct, 100)}%` }} />
                        </div>
                        <span className="w-20 text-right">{dr.achieved_pct}% / {dr.target_pct}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              <div>
                <p className="text-sm font-medium text-gray-700 mb-1">{t('composer.questionPool.questionsProposed', { count: preview.questions.length })}</p>
                <div className="max-h-48 overflow-y-auto space-y-1">
                  {preview.questions.map((q) => (
                    <div key={q.id} className="p-2 bg-gray-50 rounded text-xs flex items-center justify-between">
                      <span className="line-clamp-1 flex-1 mr-2">{q.question_text}</span>
                      <div className="flex gap-1 flex-shrink-0">
                        <span className={`px-1.5 py-0.5 rounded-full ${DIFFICULTY_COLORS[q.difficulty] || 'bg-gray-100'}`}>
                          {DIFFICULTY_LABELS[q.difficulty] || q.difficulty}
                        </span>
                        {q.bloom_level && <span className="px-1.5 py-0.5 rounded-full bg-purple-100 text-purple-700">B{q.bloom_level}</span>}
                        <span className="px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700">{q.suggested_points}P</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-4 mt-2">
              <div className="grid grid-cols-2 gap-3">
                <TextField label={t('composer.questionPool.targetPoints')} type="number" fullWidth
                  inputProps={{ min: 1 }} value={compositionForm.target_points}
                  onChange={(e) => setCompositionForm({ ...compositionForm, target_points: e.target.value })} />
                <TextField label={t('composer.questionPool.targetDuration')} type="number" fullWidth
                  inputProps={{ min: 1 }} value={compositionForm.target_duration_minutes}
                  onChange={(e) => setCompositionForm({ ...compositionForm, target_duration_minutes: e.target.value })} />
              </div>
              <TextField label={t('composer.questionPool.autoFillTopic')} fullWidth value={compositionForm.topic}
                onChange={(e) => setCompositionForm({ ...compositionForm, topic: e.target.value })} />
              <div>
                <p className="text-sm text-gray-600 mb-1">{t('composer.questionPool.presets')}</p>
                <div className="flex gap-2">
                  {Object.entries(PRESETS).map(([key, preset]) => (
                    <button key={key} type="button" onClick={() => applyPreset(key)}
                      className="text-xs px-3 py-1 rounded-full border border-indigo-300 text-indigo-700 hover:bg-indigo-50">
                      {preset.label}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-sm text-gray-600 mb-1">{t('composer.questionPool.bloomDistributionPct')}</p>
                <div className="grid grid-cols-3 gap-2">
                  {([1, 2, 3, 4, 5, 6] as const).map((level) => (
                    <TextField key={level} label={`B${level} ${BLOOM_LABELS[level]}`} type="number"
                      size="small" inputProps={{ min: 0, max: 100 }}
                      value={compositionForm.bloom_distribution[level]}
                      onChange={(e) => setCompositionForm((f) => ({
                        ...f, bloom_distribution: { ...f.bloom_distribution, [level]: e.target.value },
                      }))} />
                  ))}
                </div>
              </div>
              <div>
                <p className="text-sm text-gray-600 mb-1">{t('composer.questionPool.difficultyDistributionPct')}</p>
                <div className="grid grid-cols-3 gap-2">
                  {(['easy', 'medium', 'hard'] as const).map((d) => (
                    <TextField key={d} label={DIFFICULTY_LABELS[d]} type="number"
                      size="small" inputProps={{ min: 0, max: 100 }}
                      value={compositionForm.difficulty_distribution[d]}
                      onChange={(e) => setCompositionForm((f) => ({
                        ...f, difficulty_distribution: { ...f.difficulty_distribution, [d]: e.target.value },
                      }))} />
                  ))}
                </div>
              </div>
              <div>
                <p className="text-sm text-gray-600 mb-1">{t('composer.questionPool.autoFillTypes')}</p>
                <div className="flex gap-2 flex-wrap">
                  {(['multiple_choice', 'true_false', 'open_ended'] as const).map((qt) => (
                    <button key={qt} type="button"
                      onClick={() => setCompositionForm((f) => ({
                        ...f, question_types: f.question_types.includes(qt)
                          ? f.question_types.filter((x) => x !== qt)
                          : [...f.question_types, qt],
                      }))}
                      className={`text-xs px-2 py-1 rounded-full border transition-colors ${
                        compositionForm.question_types.includes(qt) ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-gray-600 border-gray-300'
                      }`}>{TYPE_ABBREV[qt]}</button>
                  ))}
                </div>
              </div>
            </div>
          )}
          {autoFillError && <p className="text-red-500 text-sm mt-2">{autoFillError}</p>}
        </DialogContent>
        <DialogActions>
          {compositionMode && preview ? (
            <>
              <Button onClick={() => { setAutoFillOpen(false); setAutoFillError(null); setPreview(null); }}>{t('composer.questionPool.cancel')}</Button>
              <Button onClick={() => setPreview(null)}>{t('composer.questionPool.back')}</Button>
              <Button onClick={handleAcceptPreview} variant="contained" disabled={composeMutation.isPending}>
                {composeMutation.isPending ? t('composer.questionPool.accepting') : t('composer.questionPool.accept')}
              </Button>
            </>
          ) : (
            <>
              <Button onClick={() => { setAutoFillOpen(false); setAutoFillError(null); setPreview(null); }}
                disabled={compositionMode ? composeMutation.isPending : autoFillMutation.isPending}>
                {t('composer.questionPool.cancel')}
              </Button>
              <Button variant="contained"
                onClick={compositionMode ? handleCompose : handleAutoFill}
                disabled={compositionMode ? composeMutation.isPending : autoFillMutation.isPending}>
                {compositionMode
                  ? (composeMutation.isPending ? t('composer.questionPool.generating') : t('composer.questionPool.generatePreview'))
                  : (autoFillMutation.isPending ? t('composer.questionPool.autoFillRunning') : t('composer.questionPool.autoFillStart'))}
              </Button>
            </>
          )}
        </DialogActions>
      </Dialog>
    </div>
  );
};

interface PoolQuestionCardProps {
  question: ApprovedQuestion;
  isAdded: boolean;
  disabled: boolean;
  onAdd: () => void;
  onPreview: () => void;
}

const TAG_LIMIT = 4;

const PoolQuestionCard: React.FC<PoolQuestionCardProps> = ({ question, isAdded, disabled, onAdd, onPreview }) => {
  const { t } = useTranslation();
  const [tagsExpanded, setTagsExpanded] = useState(false);

  const DIFFICULTY_LABELS = useMemo<Record<string, string>>(() => ({
    easy: t('composer.questionPool.difficultyEasy'),
    medium: t('composer.questionPool.difficultyMedium'),
    hard: t('composer.questionPool.difficultyHard'),
  }), [t]);

  const TYPE_ABBREV = useMemo<Record<string, string>>(() => ({
    multiple_choice: t('composer.questionPool.typeMultipleChoice'),
    true_false: t('composer.questionPool.typeTrueFalse'),
    open_ended: t('composer.questionPool.typeOpenEnded'),
  }), [t]);

  const sortedTags = useMemo(
    () => question.tags ? [...question.tags].sort((a, b) => a.name.localeCompare(b.name)) : [],
    [question.tags]
  );

  const visibleTags = sortedTags.slice(0, TAG_LIMIT);
  const hiddenTags = sortedTags.slice(TAG_LIMIT);

  const tagChipStyle = {
    backgroundColor: 'rgb(245 243 255)',
    color: 'rgb(109 40 217)',
    border: '1px solid rgb(221 214 254)',
  };

  return (
    <div
      onDoubleClick={onPreview}
      title={t('composer.questionPool.previewHint')}
      className={`p-3 rounded-lg border transition-colors ${
        isAdded
          ? 'bg-gray-50 border-gray-200 opacity-60'
          : 'bg-white border-gray-200 hover:border-gray-300'
      }`}
    >
      <div className="flex items-start gap-2 mb-3">
        <p className="flex-1 min-w-0 text-[15px] font-medium text-gray-800 line-clamp-2">
          {question.question_text}
        </p>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onPreview();
          }}
          aria-label={t('composer.questionPool.previewAria')}
          title={t('composer.questionPool.preview')}
          className="shrink-0 p-1 -m-1 text-gray-400 hover:text-indigo-600 transition-colors rounded focus:outline-none focus:ring-2 focus:ring-indigo-300"
        >
          <svg className="w-[18px] h-[18px]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8} aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12s3.75-7.5 9.75-7.5 9.75 7.5 9.75 7.5-3.75 7.5-9.75 7.5S2.25 12 2.25 12z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>
      </div>

      {/* Zwei-Spalten: links (Badges + Tags), rechts (Button) */}
      <div className="flex gap-2 items-start">

        {/* Linke Spalte — begrenzt auf Breite vor dem Button */}
        <div className="flex-1 min-w-0">
          {/* Badges */}
          <div className="flex flex-wrap gap-1.5">
            <span className={`text-[13px] px-2 py-0.5 rounded-full ${DIFFICULTY_COLORS[question.difficulty] || 'bg-gray-100 text-gray-600'}`}>
              {DIFFICULTY_LABELS[question.difficulty] || question.difficulty}
            </span>
            <span className="text-[13px] px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">
              {TYPE_ABBREV[question.question_type] || question.question_type}
            </span>
            {question.bloom_level && (
              <span className="text-[13px] px-2 py-0.5 rounded-full bg-purple-100 text-purple-700">
                B{question.bloom_level}
              </span>
            )}
          </div>

          {/* Tags — unterhalb Badges, gleiche Breite wie linke Spalte */}
          {sortedTags.length > 0 && (
            <div className="mt-1.5">
              <div className="flex flex-wrap gap-1">
                {visibleTags.map((tag) => (
                  <span key={tag.id} className="text-xs px-1.5 py-0.5 rounded-full" style={tagChipStyle}>
                    #{tag.name}
                  </span>
                ))}
                {!tagsExpanded && hiddenTags.length > 0 && (
                  <button
                    type="button"
                    onClick={() => setTagsExpanded(true)}
                    className="text-xs px-1.5 py-0.5 rounded-full transition-colors"
                    style={{ backgroundColor: 'rgb(237 233 254)', color: 'rgb(109 40 217)', border: '1px solid rgb(221 214 254)' }}
                  >
                    +{hiddenTags.length}
                  </button>
                )}
                {tagsExpanded && hiddenTags.map((tag) => (
                  <span key={tag.id} className="text-xs px-1.5 py-0.5 rounded-full" style={tagChipStyle}>
                    #{tag.name}
                  </span>
                ))}
              </div>
              {tagsExpanded && hiddenTags.length > 0 && (
                <button
                  type="button"
                  onClick={() => setTagsExpanded(false)}
                  className="mt-1 text-xs text-purple-600 hover:text-purple-800 hover:underline transition-colors"
                >
                  — {t('composer.questionPool.tagsShowLess', 'weniger anzeigen')}
                </button>
              )}
            </div>
          )}
        </div>

        {/* Rechte Spalte — Button, immer fixiert rechts */}
        <div className="flex-shrink-0 pt-0.5">
          {isAdded ? (
            <span className="text-[13px] text-green-600 font-medium">
              &#10003; {t('composer.questionPool.added')}
            </span>
          ) : (
            <button
              onClick={onAdd}
              disabled={disabled}
              className="text-[13px] px-2.5 py-1 bg-indigo-50 text-indigo-700 border border-indigo-200 rounded hover:bg-indigo-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              + {t('composer.questionPool.add')}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default QuestionPoolPanel;
