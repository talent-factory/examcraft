import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
} from '@mui/material';
import { ComposerService, getErrorMessage } from '../../services/ComposerService';
import type { ApprovedQuestion, AutoFillRequest, AutoComposePreview, ProposedQuestion } from '../../types/composer';

interface QuestionPoolPanelProps {
  addedQuestionIds: Set<number>;
  onAddQuestions: (ids: number[]) => void;
  examId: number;
  disabled: boolean;
  onInvalidate: () => void;
}

const DIFFICULTY_COLORS: Record<string, string> = {
  easy: 'bg-green-100 text-green-700',
  medium: 'bg-yellow-100 text-yellow-700',
  hard: 'bg-red-100 text-red-700',
};

const DIFFICULTY_LABELS: Record<string, string> = {
  easy: 'Einfach',
  medium: 'Mittel',
  hard: 'Schwer',
};

const TYPE_ABBREV: Record<string, string> = {
  multiple_choice: 'MC',
  true_false: 'W/F',
  open_ended: 'Offen',
};

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

const BLOOM_LABELS: Record<number, string> = {
  1: 'Erinnern',
  2: 'Verstehen',
  3: 'Anwenden',
  4: 'Analysieren',
  5: 'Bewerten',
  6: 'Erschaffen',
};

const PRESETS: Record<string, {
  bloom: Record<number, number>;
  difficulty: Record<string, number>;
  label: string;
}> = {
  balanced: {
    label: 'Ausgewogen',
    bloom: { 1: 15, 2: 25, 3: 25, 4: 20, 5: 10, 6: 5 },
    difficulty: { easy: 30, medium: 40, hard: 30 },
  },
  application: {
    label: 'Anwendungsfokus',
    bloom: { 1: 10, 2: 15, 3: 35, 4: 25, 5: 10, 6: 5 },
    difficulty: { easy: 20, medium: 40, hard: 40 },
  },
};

const QuestionPoolPanel: React.FC<QuestionPoolPanelProps> = ({
  addedQuestionIds,
  onAddQuestions,
  examId,
  disabled,
  onInvalidate,
}) => {
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState('');
  const [filterDifficulty, setFilterDifficulty] = useState('');
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

  const { data, isLoading } = useQuery({
    queryKey: ['approved-questions', search, filterType, filterDifficulty],
    queryFn: () =>
      ComposerService.listApprovedQuestions({
        search: search || undefined,
        question_type: filterType || undefined,
        difficulty: filterDifficulty || undefined,
        limit: 50,
      }),
    staleTime: 30_000,
  });

  const autoFillMutation = useMutation({
    mutationFn: (req: AutoFillRequest) => ComposerService.autoFill(examId, req),
    onSuccess: () => {
      setAutoFillError(null);
      setAutoFillOpen(false);
      onInvalidate();
    },
    onError: (err) => {
      setAutoFillError(getErrorMessage(err, 'Auto-Fill fehlgeschlagen. Nicht genug passende Fragen?'));
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

  const toggleAutoFillType = (t: string) => {
    setAutoFillForm((f) => ({
      ...f,
      question_types: f.question_types.includes(t)
        ? f.question_types.filter((x) => x !== t)
        : [...f.question_types, t],
    }));
  };

  const composeMutation = useMutation({
    mutationFn: (req: AutoFillRequest) => ComposerService.autoFill(examId, req),
    onSuccess: (data) => {
      if ('constraint_report' in data) {
        setPreview(data as AutoComposePreview);
        setAutoFillError(null);
      } else {
        setPreview(null);
        setAutoFillOpen(false);
        setAutoFillError(null);
        onInvalidate();
      }
    },
    onError: (err) => {
      setAutoFillError(getErrorMessage(err, 'Komposition fehlgeschlagen.'));
    },
  });

  const handleCompose = () => {
    const bloomDist: Record<number, number> = {};
    let hasBloom = false;
    for (const [k, v] of Object.entries(compositionForm.bloom_distribution)) {
      const num = parseFloat(v);
      if (num > 0) {
        bloomDist[parseInt(k)] = num;
        hasBloom = true;
      }
    }

    const diffDist: Record<string, number> = {};
    let hasDiff = false;
    for (const [k, v] of Object.entries(compositionForm.difficulty_distribution)) {
      const num = parseFloat(v);
      if (num > 0) {
        diffDist[k] = num;
        hasDiff = true;
      }
    }

    const req: AutoFillRequest = {
      target_points: parseFloat(compositionForm.target_points) || undefined,
      target_duration_minutes: parseInt(compositionForm.target_duration_minutes) || undefined,
      bloom_distribution: hasBloom ? bloomDist : undefined,
      difficulty_distribution: hasDiff ? diffDist : undefined,
      topic: compositionForm.topic || undefined,
      question_types: compositionForm.question_types.length > 0 ? compositionForm.question_types : undefined,
      exclude_question_ids: Array.from(addedQuestionIds),
      preview: true,
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

  return (
    <div className="card p-4 bg-white rounded-lg border border-gray-200 h-full flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-gray-900">Fragenpool</h3>
        {!disabled && (
          <button
            onClick={() => setAutoFillOpen(true)}
            className="text-sm px-3 py-1 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
          >
            Auto-Fill
          </button>
        )}
      </div>

      {/* Search */}
      <input
        type="text"
        placeholder="Fragen durchsuchen..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent mb-2"
      />

      {/* Filter chips */}
      <div className="flex gap-2 flex-wrap mb-3">
        {/* Type filters */}
        {(['multiple_choice', 'true_false', 'open_ended'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setFilterType(filterType === t ? '' : t)}
            className={`text-xs px-2 py-1 rounded-full border transition-colors ${
              filterType === t
                ? 'bg-indigo-600 text-white border-indigo-600'
                : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'
            }`}
          >
            {TYPE_ABBREV[t]}
          </button>
        ))}

        {/* Difficulty filters */}
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
      </div>

      {/* Question list */}
      <div className="flex-1 overflow-y-auto space-y-2 min-h-0">
        {isLoading ? (
          <div className="text-center py-8 text-gray-500 text-sm">Lade Fragen...</div>
        ) : !data?.questions.length ? (
          <div className="text-center py-8 text-gray-400 text-sm">
            Keine genehmigten Fragen gefunden.
          </div>
        ) : (
          data.questions.map((q) => (
            <PoolQuestionCard
              key={q.id}
              question={q}
              isAdded={addedQuestionIds.has(q.id)}
              disabled={disabled}
              onAdd={() => onAddQuestions([q.id])}
            />
          ))
        )}
      </div>

      {data && (
        <p className="text-xs text-gray-400 mt-2 text-right">
          {data.total} Fragen verfügbar
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
              Einfach
            </button>
            <button
              onClick={() => { setCompositionMode(true); setPreview(null); }}
              className={`px-3 py-1 rounded-lg text-sm ${compositionMode ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-600'}`}
            >
              Komposition
            </button>
          </div>
        </DialogTitle>
        <DialogContent>
          {!compositionMode ? (
            /* --- Simple mode (existing) --- */
            <div className="space-y-4 mt-2">
              <TextField label="Anzahl Fragen" type="number" fullWidth
                inputProps={{ min: 1, max: 20 }} value={autoFillForm.count}
                onChange={(e) => setAutoFillForm({ ...autoFillForm, count: e.target.value })} />
              <TextField label="Thema (optional)" fullWidth value={autoFillForm.topic}
                onChange={(e) => setAutoFillForm({ ...autoFillForm, topic: e.target.value })} />
              <div>
                <p className="text-sm text-gray-600 mb-1">Schwierigkeitsgrad</p>
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
                <p className="text-sm text-gray-600 mb-1">Fragetypen</p>
                <div className="flex gap-2 flex-wrap">
                  {(['multiple_choice', 'true_false', 'open_ended'] as const).map((t) => (
                    <button key={t} type="button" onClick={() => toggleAutoFillType(t)}
                      className={`text-xs px-2 py-1 rounded-full border transition-colors ${
                        autoFillForm.question_types.includes(t) ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-gray-600 border-gray-300'
                      }`}>{TYPE_ABBREV[t]}</button>
                  ))}
                </div>
              </div>
              <TextField label="Min. Bloom-Level (1-6, optional)" type="number" fullWidth
                inputProps={{ min: 1, max: 6 }} value={autoFillForm.bloom_level_min}
                onChange={(e) => setAutoFillForm({ ...autoFillForm, bloom_level_min: e.target.value })} />
            </div>
          ) : preview ? (
            /* --- Preview panel --- */
            <div className="space-y-4 mt-2">
              <div className="grid grid-cols-3 gap-2 text-center text-sm">
                <div className="p-2 bg-gray-50 rounded">
                  <div className="text-gray-500">Punkte</div>
                  <div className="font-semibold">{preview.total_points} / {preview.constraint_report.points_target ?? '–'}</div>
                </div>
                <div className="p-2 bg-gray-50 rounded">
                  <div className="text-gray-500">Dauer</div>
                  <div className="font-semibold">{preview.total_duration_minutes} / {preview.constraint_report.duration_target ?? '–'} min</div>
                </div>
                <div className="p-2 bg-gray-50 rounded">
                  <div className="text-gray-500">Zufriedenheit</div>
                  <div className={`font-semibold ${preview.constraint_report.overall_satisfaction >= 80 ? 'text-green-600' : 'text-yellow-600'}`}>
                    {preview.constraint_report.overall_satisfaction}%
                  </div>
                </div>
              </div>
              {/* Distribution reports */}
              {Object.keys(preview.constraint_report.bloom_distribution).length > 0 && (
                <div>
                  <p className="text-sm font-medium text-gray-700 mb-1">Bloom-Verteilung</p>
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
                  <p className="text-sm font-medium text-gray-700 mb-1">Schwierigkeitsverteilung</p>
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
              {/* Proposed questions */}
              <div>
                <p className="text-sm font-medium text-gray-700 mb-1">{preview.questions.length} Fragen vorgeschlagen</p>
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
            /* --- Composition form --- */
            <div className="space-y-4 mt-2">
              <div className="grid grid-cols-2 gap-3">
                <TextField label="Zielpunkte" type="number" fullWidth
                  inputProps={{ min: 1 }} value={compositionForm.target_points}
                  onChange={(e) => setCompositionForm({ ...compositionForm, target_points: e.target.value })} />
                <TextField label="Zieldauer (Min.)" type="number" fullWidth
                  inputProps={{ min: 1 }} value={compositionForm.target_duration_minutes}
                  onChange={(e) => setCompositionForm({ ...compositionForm, target_duration_minutes: e.target.value })} />
              </div>
              <TextField label="Thema (optional)" fullWidth value={compositionForm.topic}
                onChange={(e) => setCompositionForm({ ...compositionForm, topic: e.target.value })} />
              {/* Presets */}
              <div>
                <p className="text-sm text-gray-600 mb-1">Vorlagen</p>
                <div className="flex gap-2">
                  {Object.entries(PRESETS).map(([key, preset]) => (
                    <button key={key} type="button" onClick={() => applyPreset(key)}
                      className="text-xs px-3 py-1 rounded-full border border-indigo-300 text-indigo-700 hover:bg-indigo-50">
                      {preset.label}
                    </button>
                  ))}
                </div>
              </div>
              {/* Bloom distribution */}
              <div>
                <p className="text-sm text-gray-600 mb-1">Bloom-Verteilung (%)</p>
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
              {/* Difficulty distribution */}
              <div>
                <p className="text-sm text-gray-600 mb-1">Schwierigkeitsverteilung (%)</p>
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
              {/* Question type filter */}
              <div>
                <p className="text-sm text-gray-600 mb-1">Fragetypen</p>
                <div className="flex gap-2 flex-wrap">
                  {(['multiple_choice', 'true_false', 'open_ended'] as const).map((t) => (
                    <button key={t} type="button"
                      onClick={() => setCompositionForm((f) => ({
                        ...f, question_types: f.question_types.includes(t)
                          ? f.question_types.filter((x) => x !== t)
                          : [...f.question_types, t],
                      }))}
                      className={`text-xs px-2 py-1 rounded-full border transition-colors ${
                        compositionForm.question_types.includes(t) ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-gray-600 border-gray-300'
                      }`}>{TYPE_ABBREV[t]}</button>
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
              <Button onClick={() => { setAutoFillOpen(false); setAutoFillError(null); setPreview(null); }}>Abbrechen</Button>
              <Button onClick={() => setPreview(null)}>Zurueck</Button>
              <Button onClick={handleAcceptPreview} variant="contained"
                disabled={composeMutation.isPending}>
                {composeMutation.isPending ? 'Fuege hinzu...' : 'Uebernehmen'}
              </Button>
            </>
          ) : (
            <>
              <Button onClick={() => { setAutoFillOpen(false); setAutoFillError(null); setPreview(null); }}
                disabled={compositionMode ? composeMutation.isPending : autoFillMutation.isPending}>
                Abbrechen
              </Button>
              <Button variant="contained"
                onClick={compositionMode ? handleCompose : handleAutoFill}
                disabled={compositionMode ? composeMutation.isPending : autoFillMutation.isPending}>
                {compositionMode
                  ? (composeMutation.isPending ? 'Generiere...' : 'Vorschau generieren')
                  : (autoFillMutation.isPending ? 'Fuelle...' : 'Auto-Fill starten')}
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
}

const PoolQuestionCard: React.FC<PoolQuestionCardProps> = ({
  question,
  isAdded,
  disabled,
  onAdd,
}) => {
  return (
    <div
      className={`p-3 rounded-lg border transition-colors ${
        isAdded
          ? 'bg-gray-50 border-gray-200 opacity-60'
          : 'bg-white border-gray-200 hover:border-gray-300'
      }`}
    >
      <p className="text-sm text-gray-800 line-clamp-2 mb-2">{question.question_text}</p>
      <div className="flex items-center justify-between gap-2">
        <div className="flex gap-1 flex-wrap">
          <span
            className={`text-xs px-1.5 py-0.5 rounded-full ${
              DIFFICULTY_COLORS[question.difficulty] || 'bg-gray-100 text-gray-600'
            }`}
          >
            {DIFFICULTY_LABELS[question.difficulty] || question.difficulty}
          </span>
          <span className="text-xs px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-600">
            {TYPE_ABBREV[question.question_type] || question.question_type}
          </span>
          {question.bloom_level && (
            <span className="text-xs px-1.5 py-0.5 rounded-full bg-purple-100 text-purple-700">
              B{question.bloom_level}
            </span>
          )}
        </div>
        {isAdded ? (
          <span className="text-xs text-green-600 font-medium flex-shrink-0">&#10003; Hinzugefügt</span>
        ) : (
          <button
            onClick={onAdd}
            disabled={disabled}
            className="text-xs px-2 py-1 bg-indigo-50 text-indigo-700 border border-indigo-200 rounded hover:bg-indigo-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
          >
            + Hinzufügen
          </button>
        )}
      </div>
    </div>
  );
};

export default QuestionPoolPanel;
