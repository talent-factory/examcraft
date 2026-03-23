import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
} from '@mui/material';
import { ComposerService, getErrorMessage } from '../../services/ComposerService';
import type { ApprovedQuestion, AutoFillRequest } from '../../types/composer';

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

interface AutoFillForm {
  count: string;
  topic: string;
  difficulty: string[];
  bloom_level_min: string;
  question_types: string[];
}

const QuestionPoolPanel: React.FC<QuestionPoolPanelProps> = ({
  addedQuestionIds,
  onAddQuestions,
  examId,
  disabled,
  onInvalidate,
}) => {
  const { t } = useTranslation();

  const DIFFICULTY_LABELS: Record<string, string> = {
    easy: t('composer.questionPool.difficultyEasy'),
    medium: t('composer.questionPool.difficultyMedium'),
    hard: t('composer.questionPool.difficultyHard'),
  };

  const TYPE_ABBREV: Record<string, string> = {
    multiple_choice: t('composer.questionPool.typeMultipleChoice'),
    true_false: t('composer.questionPool.typeTrueFalse'),
    open_ended: t('composer.questionPool.typeOpenEnded'),
  };

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
      setAutoFillError(getErrorMessage(err, t('composer.questionPool.errorAutoFill')));
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

  return (
    <div className="card p-4 bg-white rounded-lg border border-gray-200 h-full flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-gray-900">{t('composer.questionPool.panelTitle')}</h3>
        {!disabled && (
          <button
            onClick={() => setAutoFillOpen(true)}
            className="text-sm px-3 py-1 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
          >
            {t('composer.questionPool.autoFill')}
          </button>
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
          <div className="text-center py-8 text-gray-500 text-sm">{t('composer.questionPool.loading')}</div>
        ) : !data?.questions.length ? (
          <div className="text-center py-8 text-gray-400 text-sm">
            {t('composer.questionPool.empty')}
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
          {t('composer.questionPool.available', { count: data.total })}
        </p>
      )}

      {/* Auto-Fill Dialog */}
      <Dialog open={autoFillOpen} onClose={() => { setAutoFillOpen(false); setAutoFillError(null); }} maxWidth="xs" fullWidth>
        <DialogTitle>{t('composer.questionPool.autoFillDialogTitle')}</DialogTitle>
        <DialogContent>
          <div className="space-y-4 mt-2">
            <TextField
              label={t('composer.questionPool.autoFillCount')}
              type="number"
              fullWidth
              inputProps={{ min: 1, max: 20 }}
              value={autoFillForm.count}
              onChange={(e) => setAutoFillForm({ ...autoFillForm, count: e.target.value })}
            />
            <TextField
              label={t('composer.questionPool.autoFillTopic')}
              fullWidth
              value={autoFillForm.topic}
              onChange={(e) => setAutoFillForm({ ...autoFillForm, topic: e.target.value })}
            />
            <div>
              <p className="text-sm text-gray-600 mb-1">{t('composer.questionPool.autoFillDifficulty')}</p>
              <div className="flex gap-2">
                {(['easy', 'medium', 'hard'] as const).map((d) => (
                  <button
                    key={d}
                    type="button"
                    onClick={() => toggleAutoFillDifficulty(d)}
                    className={`text-xs px-2 py-1 rounded-full border transition-colors ${
                      autoFillForm.difficulty.includes(d)
                        ? DIFFICULTY_COLORS[d] + ' border-current font-semibold'
                        : 'bg-white text-gray-600 border-gray-300'
                    }`}
                  >
                    {DIFFICULTY_LABELS[d]}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <p className="text-sm text-gray-600 mb-1">{t('composer.questionPool.autoFillTypes')}</p>
              <div className="flex gap-2 flex-wrap">
                {(['multiple_choice', 'true_false', 'open_ended'] as const).map((qt) => (
                  <button
                    key={qt}
                    type="button"
                    onClick={() => toggleAutoFillType(qt)}
                    className={`text-xs px-2 py-1 rounded-full border transition-colors ${
                      autoFillForm.question_types.includes(qt)
                        ? 'bg-indigo-600 text-white border-indigo-600'
                        : 'bg-white text-gray-600 border-gray-300'
                    }`}
                  >
                    {TYPE_ABBREV[qt]}
                  </button>
                ))}
              </div>
            </div>
            <TextField
              label={t('composer.questionPool.autoFillBloomLevel')}
              type="number"
              fullWidth
              inputProps={{ min: 1, max: 6 }}
              value={autoFillForm.bloom_level_min}
              onChange={(e) =>
                setAutoFillForm({ ...autoFillForm, bloom_level_min: e.target.value })
              }
            />
          </div>
          {autoFillError && (
            <p className="text-red-500 text-sm mt-2">{autoFillError}</p>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => { setAutoFillOpen(false); setAutoFillError(null); }} disabled={autoFillMutation.isPending}>
            {t('composer.questionPool.cancel')}
          </Button>
          <Button
            onClick={handleAutoFill}
            variant="contained"
            disabled={autoFillMutation.isPending}
          >
            {autoFillMutation.isPending ? t('composer.questionPool.autoFillRunning') : t('composer.questionPool.autoFillStart')}
          </Button>
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
  const { t } = useTranslation();

  const DIFFICULTY_LABELS: Record<string, string> = {
    easy: t('composer.questionPool.difficultyEasy'),
    medium: t('composer.questionPool.difficultyMedium'),
    hard: t('composer.questionPool.difficultyHard'),
  };

  const TYPE_ABBREV: Record<string, string> = {
    multiple_choice: t('composer.questionPool.typeMultipleChoice'),
    true_false: t('composer.questionPool.typeTrueFalse'),
    open_ended: t('composer.questionPool.typeOpenEnded'),
  };

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
          <span className="text-xs text-green-600 font-medium flex-shrink-0">&#10003; {t('composer.questionPool.added')}</span>
        ) : (
          <button
            onClick={onAdd}
            disabled={disabled}
            className="text-xs px-2 py-1 bg-indigo-50 text-indigo-700 border border-indigo-200 rounded hover:bg-indigo-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
          >
            {t('composer.questionPool.addQuestion')}
          </button>
        )}
      </div>
    </div>
  );
};

export default QuestionPoolPanel;
