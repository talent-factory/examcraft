/**
 * One phase of the template editor with its criteria (TF-988).
 *
 * Order is changed with up/down buttons, not drag and drop: the position is
 * the grading order and the context chain of the grading engine, so it has
 * to be deliberate and keyboard-reachable.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { Box, Button, IconButton, Paper, Stack, TextField, Tooltip, Typography } from '@mui/material';
import {
  Add as AddIcon,
  ArrowDownward as ArrowDownIcon,
  ArrowUpward as ArrowUpIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import {
  CriterionDraft,
  CriterionErrors,
  emptyCriterion,
  moveItem,
  NAME_MAX_LENGTH,
  parseMaxPoints,
  PhaseDraft,
  PhaseErrors,
  TYPE_TAG_MAX_LENGTH,
  withMaxPoints,
} from './templateDraft';
import { PORTFOLIO_MAX_CRITERION_POINTS } from '../../../types/portfolio';

const KEY = 'pages.portfolio.templates.editor';

interface OrderButtonsProps {
  index: number;
  count: number;
  label: string;
  testId: string;
  onMove: (delta: -1 | 1) => void;
  onRemove: () => void;
}

const OrderButtons: React.FC<OrderButtonsProps> = ({ index, count, label, testId, onMove, onRemove }) => {
  const { t } = useTranslation();
  const buttons = [
    { key: 'up', title: t(`${KEY}.moveUp`, { item: label }), icon: <ArrowUpIcon fontSize="small" />, disabled: index === 0, onClick: () => onMove(-1) },
    { key: 'down', title: t(`${KEY}.moveDown`, { item: label }), icon: <ArrowDownIcon fontSize="small" />, disabled: index === count - 1, onClick: () => onMove(1) },
    // Phases and criteria are `Field(min_length=1)` in the backend.
    { key: 'remove', title: t(`${KEY}.remove`, { item: label }), icon: <DeleteIcon fontSize="small" />, disabled: count <= 1, onClick: onRemove },
  ];
  return (
    <Box sx={{ display: 'flex', flexShrink: 0 }}>
      {buttons.map((button) => (
        <Tooltip key={button.key} title={button.title}>
          <span>
            <IconButton
              size="small"
              aria-label={button.title}
              disabled={button.disabled}
              onClick={button.onClick}
              color={button.key === 'remove' ? 'error' : 'default'}
              data-testid={`${testId}-${button.key}`}
            >
              {button.icon}
            </IconButton>
          </span>
        </Tooltip>
      ))}
    </Box>
  );
};

interface CriterionFieldsProps {
  criterion: CriterionDraft;
  index: number;
  count: number;
  readOnly: boolean;
  errors?: CriterionErrors;
  testId: string;
  onChange: (criterion: CriterionDraft) => void;
  onMove: (delta: -1 | 1) => void;
  onRemove: () => void;
}

const CriterionFields: React.FC<CriterionFieldsProps> = ({
  criterion,
  index,
  count,
  readOnly,
  errors,
  testId,
  onChange,
  onMove,
  onRemove,
}) => {
  const { t } = useTranslation();
  const set = <K extends keyof CriterionDraft>(key: K, value: CriterionDraft[K]) =>
    onChange({ ...criterion, [key]: value });
  const maxPoints = parseMaxPoints(criterion.maxPoints);
  const label = criterion.name.trim() || t(`${KEY}.criterionNumber`, { number: index + 1 });

  return (
    <Paper variant="outlined" sx={{ p: 2 }} data-testid={testId}>
      <Stack spacing={2}>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start' }}>
          <TextField
            label={t(`${KEY}.criterionName`)}
            value={criterion.name}
            required
            size="small"
            sx={{ flex: 2 }}
            error={!!errors?.name}
            helperText={errors?.name}
            InputProps={{ readOnly }}
            inputProps={{ maxLength: NAME_MAX_LENGTH, 'data-testid': `${testId}-name` }}
            onChange={(e) => set('name', e.target.value)}
          />
          <TextField
            label={t(`${KEY}.typeTag`)}
            value={criterion.typeTag}
            size="small"
            sx={{ flex: 1 }}
            error={!!errors?.typeTag}
            helperText={errors?.typeTag ?? t(`${KEY}.typeTagHelper`)}
            InputProps={{ readOnly }}
            inputProps={{ maxLength: TYPE_TAG_MAX_LENGTH, 'data-testid': `${testId}-type-tag` }}
            onChange={(e) => set('typeTag', e.target.value)}
          />
          <TextField
            label={t(`${KEY}.maxPoints`)}
            value={criterion.maxPoints}
            required
            size="small"
            type="number"
            sx={{ width: 140 }}
            error={!!errors?.maxPoints}
            helperText={errors?.maxPoints ?? t(`${KEY}.maxPointsHelper`, { max: PORTFOLIO_MAX_CRITERION_POINTS })}
            InputProps={{ readOnly }}
            inputProps={{ min: 1, max: PORTFOLIO_MAX_CRITERION_POINTS, step: 1, 'data-testid': `${testId}-max-points` }}
            onChange={(e) => onChange(withMaxPoints(criterion, e.target.value))}
          />
          {!readOnly && (
            <OrderButtons
              index={index}
              count={count}
              label={label}
              testId={testId}
              onMove={onMove}
              onRemove={onRemove}
            />
          )}
        </Box>

        <Box>
          <Typography variant="subtitle2">{t(`${KEY}.rubric`)}</Typography>
          <Typography variant="caption" color={errors?.rubric ? 'error' : 'text.secondary'} display="block" sx={{ mb: 1 }}>
            {errors?.rubric ?? t(`${KEY}.rubricHelper`)}
          </Typography>
          {maxPoints === null ? (
            <Typography variant="body2" color="text.secondary" data-testid={`${testId}-rubric-hint`}>
              {t(`${KEY}.rubricNeedsMaxPoints`)}
            </Typography>
          ) : (
            <Stack spacing={1}>
              {criterion.rubric.slice(0, maxPoints + 1).map((text, score) => (
                <TextField
                  key={score}
                  label={t(`${KEY}.rubricScore`, { count: score })}
                  value={text}
                  required
                  size="small"
                  multiline
                  fullWidth
                  error={errors?.rubricScores?.includes(score) ?? false}
                  InputProps={{ readOnly }}
                  inputProps={{ 'data-testid': `${testId}-rubric-${score}` }}
                  onChange={(e) =>
                    set(
                      'rubric',
                      criterion.rubric.map((old, i) => (i === score ? e.target.value : old)),
                    )
                  }
                />
              ))}
            </Stack>
          )}
        </Box>

        <TextField
          label={t(`${KEY}.checklist`)}
          value={criterion.checklist}
          size="small"
          multiline
          minRows={2}
          fullWidth
          helperText={t(`${KEY}.checklistHelper`)}
          InputProps={{ readOnly }}
          inputProps={{ 'data-testid': `${testId}-checklist` }}
          onChange={(e) => set('checklist', e.target.value)}
        />
      </Stack>
    </Paper>
  );
};

export interface PortfolioPhaseFieldsProps {
  phase: PhaseDraft;
  index: number;
  count: number;
  readOnly: boolean;
  errors?: PhaseErrors;
  onChange: (phase: PhaseDraft) => void;
  onMove: (delta: -1 | 1) => void;
  onRemove: () => void;
}

const PortfolioPhaseFields: React.FC<PortfolioPhaseFieldsProps> = ({
  phase,
  index,
  count,
  readOnly,
  errors,
  onChange,
  onMove,
  onRemove,
}) => {
  const { t } = useTranslation();
  const testId = `pt-phase-${index}`;
  const set = <K extends keyof PhaseDraft>(key: K, value: PhaseDraft[K]) =>
    onChange({ ...phase, [key]: value });
  const setCriteria = (criteria: CriterionDraft[]) => set('criteria', criteria);
  const label = phase.name.trim() || t(`${KEY}.phaseNumber`, { number: index + 1 });

  return (
    <Paper variant="outlined" sx={{ p: 2, bgcolor: 'grey.50' }} data-testid={testId}>
      <Stack spacing={2}>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <Typography variant="subtitle1" component="h3" sx={{ flex: 1 }}>
            {t(`${KEY}.phaseNumber`, { number: index + 1 })}
          </Typography>
          {!readOnly && (
            <OrderButtons
              index={index}
              count={count}
              label={label}
              testId={testId}
              onMove={onMove}
              onRemove={onRemove}
            />
          )}
        </Box>
        <TextField
          label={t(`${KEY}.phaseName`)}
          value={phase.name}
          required
          size="small"
          fullWidth
          error={!!errors?.name}
          helperText={errors?.name}
          InputProps={{ readOnly }}
          inputProps={{ maxLength: NAME_MAX_LENGTH, 'data-testid': `${testId}-name` }}
          onChange={(e) => set('name', e.target.value)}
        />
        <TextField
          label={t(`${KEY}.phaseDescription`)}
          value={phase.description}
          size="small"
          multiline
          minRows={2}
          fullWidth
          InputProps={{ readOnly }}
          inputProps={{ 'data-testid': `${testId}-description` }}
          onChange={(e) => set('description', e.target.value)}
        />
        <TextField
          label={t(`${KEY}.folderPatterns`)}
          value={phase.folderPatterns}
          size="small"
          fullWidth
          helperText={t(`${KEY}.folderPatternsHelper`)}
          InputProps={{ readOnly }}
          inputProps={{ 'data-testid': `${testId}-folder-patterns` }}
          onChange={(e) => set('folderPatterns', e.target.value)}
        />

        <Typography variant="subtitle2" component="h4">
          {t(`${KEY}.criteria`)}
        </Typography>
        {phase.criteria.map((criterion, criterionIndex) => (
          <CriterionFields
            key={criterion.key}
            criterion={criterion}
            index={criterionIndex}
            count={phase.criteria.length}
            readOnly={readOnly}
            errors={errors?.criteria[criterion.key]}
            testId={`${testId}-criterion-${criterionIndex}`}
            onChange={(next) =>
              setCriteria(phase.criteria.map((c) => (c.key === criterion.key ? next : c)))
            }
            onMove={(delta) => setCriteria(moveItem(phase.criteria, criterionIndex, delta))}
            onRemove={() => setCriteria(phase.criteria.filter((c) => c.key !== criterion.key))}
          />
        ))}
        {!readOnly && (
          <Box>
            <Button
              size="small"
              startIcon={<AddIcon />}
              onClick={() => setCriteria([...phase.criteria, emptyCriterion()])}
              data-testid={`${testId}-add-criterion`}
            >
              {t(`${KEY}.addCriterion`)}
            </Button>
          </Box>
        )}
      </Stack>
    </Paper>
  );
};

export default PortfolioPhaseFields;
