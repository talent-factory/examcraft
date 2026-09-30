/**
 * «Neue Portfolio-Bewertung» (TF-989).
 *
 * Creates the assessment only; the upload (ZIP and/or GitHub) happens on the
 * detail page, which the caller opens via `onCreated`. That keeps one place
 * for the first upload and for a retry after a failed ingestion.
 */
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Autocomplete,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  ListSubheader,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { portfolioApi } from '../../api/portfolioApi';
import { GradingSchemesService } from '../../services/gradingSchemesService';
import { translateError } from '../../errors';
import { useDebounce } from '../../hooks/useDebounce';
import { portfolioAssessmentsQueryKey } from '../../hooks/usePortfolioAssessment';
import { portfolioTemplatesQueryKey } from '../../pages/portfolio/PortfolioTemplatesPage';
import type { PortfolioStudentOption } from '../../types/portfolio';
import { PortfolioMutationError } from './PortfolioMutationError';

/**
 * Same shape as `_REPO_URL_PATTERN` in `portfolio_github_service.py`, so an
 * obvious typo is caught before the round trip. The backend stays the
 * authority (it also rejects owner/repo names made of dots only).
 */
const GITHUB_REPO_URL = /^https:\/\/github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+?(?:\.git)?\/?$/;

export function isGithubRepoUrl(value: string): boolean {
  return GITHUB_REPO_URL.test(value.trim());
}

export function portfolioStudentLabel(student: PortfolioStudentOption): string {
  return student.display_name || student.external_id;
}

interface PortfolioAssessmentCreateDialogProps {
  open: boolean;
  onClose: () => void;
  onCreated: (assessmentId: string) => void;
}

export const PortfolioAssessmentCreateDialog: React.FC<PortfolioAssessmentCreateDialogProps> = ({
  open,
  onClose,
  onCreated,
}) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [templateId, setTemplateId] = useState('');
  const [student, setStudent] = useState<PortfolioStudentOption | null>(null);
  const [studentInput, setStudentInput] = useState('');
  const [gradingSchemeId, setGradingSchemeId] = useState<number | null>(null);
  const [frameworkConditions, setFrameworkConditions] = useState('');
  const [repositoryUrl, setRepositoryUrl] = useState('');
  const [repositoryUrlTouched, setRepositoryUrlTouched] = useState(false);

  const debouncedStudentInput = useDebounce(studentInput.trim(), 300);

  const templatesQuery = useQuery({
    queryKey: portfolioTemplatesQueryKey,
    queryFn: () => portfolioApi.listTemplates(),
    enabled: open,
  });
  const activeTemplates = (templatesQuery.data ?? []).filter((template) => template.is_active);

  const studentsQuery = useQuery({
    queryKey: ['portfolioStudents', debouncedStudentInput],
    queryFn: () => portfolioApi.searchStudents(debouncedStudentInput),
    enabled: open,
  });

  const gradingSchemesQuery = useQuery({
    queryKey: ['grading-schemes'],
    queryFn: () => GradingSchemesService.list(true),
    enabled: open,
  });
  const gradingSchemes = gradingSchemesQuery.data?.schemes ?? [];
  const systemSchemes = gradingSchemes.filter((s) => s.is_system_scheme);
  const institutionSchemes = gradingSchemes.filter((s) => !s.is_system_scheme);

  const trimmedUrl = repositoryUrl.trim();
  const urlInvalid = trimmedUrl !== '' && !isGithubRepoUrl(trimmedUrl);

  const createMutation = useMutation({
    mutationFn: () =>
      portfolioApi.createAssessment({
        template_id: templateId,
        student_id: (student as PortfolioStudentOption).id,
        framework_conditions: frameworkConditions.trim() || null,
        source_repository_url: trimmedUrl || null,
        grading_scheme_id: gradingSchemeId,
      }),
    onSuccess: (created) => {
      void queryClient.invalidateQueries({ queryKey: portfolioAssessmentsQueryKey });
      reset();
      onCreated(created.id);
    },
  });

  function reset() {
    setTemplateId('');
    setStudent(null);
    setStudentInput('');
    setGradingSchemeId(null);
    setFrameworkConditions('');
    setRepositoryUrl('');
    setRepositoryUrlTouched(false);
    createMutation.reset();
  }

  const handleClose = () => {
    if (createMutation.isPending) return;
    reset();
    onClose();
  };

  // A failed scheme list would leave «Kein Notenschema» looking like a choice,
  // and an assessment's scheme cannot be changed after creation.
  const canSubmit =
    templateId !== '' &&
    student !== null &&
    !urlInvalid &&
    gradingSchemesQuery.isSuccess &&
    !createMutation.isPending;

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>{t('pages.portfolio.create.title')}</DialogTitle>
      <DialogContent>
        <Stack spacing={2.5} sx={{ mt: 1 }}>
          <FormControl fullWidth required>
            <InputLabel id="portfolio-template-label">{t('pages.portfolio.create.template')}</InputLabel>
            <Select
              labelId="portfolio-template-label"
              label={t('pages.portfolio.create.template')}
              value={templateId}
              onChange={(e) => setTemplateId(e.target.value)}
              data-testid="portfolio-create-template"
            >
              {activeTemplates.map((template) => (
                <MenuItem key={template.id} value={template.id}>
                  {template.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          {templatesQuery.isError && (
            <Typography variant="body2" color="error">
              {translateError(templatesQuery.error, t, 'errors.portfolio_template_list_failed')}
            </Typography>
          )}
          {templatesQuery.isSuccess && activeTemplates.length === 0 && (
            <Typography variant="body2" color="textSecondary">
              {t('pages.portfolio.create.noTemplates')}
            </Typography>
          )}

          <Autocomplete
            options={studentsQuery.data ?? []}
            value={student}
            onChange={(_, value) => setStudent(value)}
            inputValue={studentInput}
            onInputChange={(_, value) => setStudentInput(value)}
            // The backend already filtered by the search term.
            filterOptions={(options) => options}
            getOptionLabel={portfolioStudentLabel}
            isOptionEqualToValue={(option, value) => option.id === value.id}
            loading={studentsQuery.isFetching}
            noOptionsText={
              studentsQuery.isError
                ? translateError(studentsQuery.error, t, 'errors.portfolio_assessment_student_search_failed')
                : t('pages.portfolio.create.noStudents')
            }
            renderOption={(props, option) => (
              <li {...props} key={option.id}>
                <Box>
                  <Typography variant="body2">{portfolioStudentLabel(option)}</Typography>
                  <Typography variant="caption" color="textSecondary">
                    {[
                      option.display_name ? option.external_id : null,
                      ...option.classes.map((c) => c.class_name),
                    ]
                      .filter(Boolean)
                      .join(' · ')}
                  </Typography>
                </Box>
              </li>
            )}
            renderInput={(params) => (
              <TextField
                {...params}
                required
                label={t('pages.portfolio.create.student')}
                error={studentsQuery.isError}
                helperText={
                  studentsQuery.isError
                    ? translateError(
                        studentsQuery.error,
                        t,
                        'errors.portfolio_assessment_student_search_failed',
                      )
                    : t('pages.portfolio.create.studentHelp')
                }
                InputProps={{
                  ...params.InputProps,
                  endAdornment: (
                    <>
                      {studentsQuery.isFetching && <CircularProgress color="inherit" size={18} />}
                      {params.InputProps.endAdornment}
                    </>
                  ),
                }}
                inputProps={{ ...params.inputProps, 'data-testid': 'portfolio-create-student' }}
              />
            )}
          />

          <FormControl fullWidth>
            <InputLabel id="portfolio-grading-scheme-label" shrink>
              {t('pages.portfolio.create.gradingScheme')}
            </InputLabel>
            <Select
              displayEmpty
              notched
              labelId="portfolio-grading-scheme-label"
              label={t('pages.portfolio.create.gradingScheme')}
              value={gradingSchemeId ?? ''}
              onChange={(e) =>
                setGradingSchemeId(e.target.value === '' ? null : Number(e.target.value))
              }
              data-testid="portfolio-create-grading-scheme"
            >
              <MenuItem value="">
                <em>{t('pages.portfolio.create.gradingSchemeNone')}</em>
              </MenuItem>
              {systemSchemes.length > 0 && (
                <ListSubheader>{t('composer.examMetadata.gradingSchemeSystemGroup')}</ListSubheader>
              )}
              {systemSchemes.map((s) => (
                <MenuItem key={s.id} value={s.id}>
                  {s.name}
                </MenuItem>
              ))}
              {institutionSchemes.length > 0 && (
                <ListSubheader>
                  {t('composer.examMetadata.gradingSchemeInstitutionGroup')}
                </ListSubheader>
              )}
              {institutionSchemes.map((s) => (
                <MenuItem key={s.id} value={s.id}>
                  {s.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          {gradingSchemesQuery.isError && (
            <Typography variant="body2" color="error">
              {translateError(gradingSchemesQuery.error, t, 'errors.grading_schemes_list_failed')}
            </Typography>
          )}

          <TextField
            label={t('pages.portfolio.create.frameworkConditions')}
            helperText={t('pages.portfolio.create.frameworkConditionsHelp')}
            value={frameworkConditions}
            onChange={(e) => setFrameworkConditions(e.target.value)}
            multiline
            minRows={3}
            fullWidth
            inputProps={{ 'data-testid': 'portfolio-create-framework-conditions' }}
          />

          <TextField
            label={t('pages.portfolio.create.repositoryUrl')}
            placeholder={t('pages.portfolio.create.repositoryUrlPlaceholder')}
            value={repositoryUrl}
            onChange={(e) => setRepositoryUrl(e.target.value)}
            onBlur={() => setRepositoryUrlTouched(true)}
            error={repositoryUrlTouched && urlInvalid}
            helperText={
              repositoryUrlTouched && urlInvalid
                ? t('pages.portfolio.create.repositoryUrlInvalid')
                : t('pages.portfolio.create.repositoryUrlHelp')
            }
            fullWidth
            inputProps={{ 'data-testid': 'portfolio-create-repository-url' }}
          />

          <PortfolioMutationError
            error={createMutation.error}
            message={createMutation.error ? translateError(createMutation.error, t, 'errors.portfolio_assessment_create_failed') : ''}
          />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={createMutation.isPending}>
          {t('common.cancel')}
        </Button>
        <Button
          variant="contained"
          onClick={() => createMutation.mutate()}
          disabled={!canSubmit}
          data-testid="portfolio-create-submit"
        >
          {t('pages.portfolio.create.submit')}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
