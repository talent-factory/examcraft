import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Grid,
  Alert,
  CircularProgress,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  LinearProgress,
  Tooltip,
  IconButton
} from '@mui/material';
import {
  Psychology,
  Description,
  Preview,
  Settings,
  CheckCircle,
  Warning,
  Info,
  ExpandMore,
  Refresh,
  Download,
  Share
} from '@mui/icons-material';
import { RAGService } from '../services/RAGService';
import { DocumentService } from '../services/DocumentService';
import {
  RAGExamRequest,
  RAGExamResponse,
  Document,
  QuestionTypesResponse,
  RAGContextSummary
} from '../types/document';
import { PromptTemplateSelector } from './prompts';
import { PromptSelection, QuestionType } from '../types/prompt';

interface RAGExamCreatorProps {
  selectedDocuments?: number[];
  onExamGenerated?: (exam: RAGExamResponse) => void;
  onBack?: () => void;
}

const RAGExamCreator: React.FC<RAGExamCreatorProps> = ({
  selectedDocuments = [],
  onExamGenerated,
  onBack
}) => {
  const [activeStep, setActiveStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Documents
  const [availableDocuments, setAvailableDocuments] = useState<Document[]>([]);
  const [selectedDocs, setSelectedDocs] = useState<number[]>(selectedDocuments);
  
  // RAG Request
  const [ragRequest, setRAGRequest] = useState<RAGExamRequest>({
    topic: '',
    document_ids: selectedDocuments,
    question_count: 5,
    question_types: ['multiple_choice'],
    difficulty: 'medium',
    language: 'de',
    context_chunks_per_question: 3
  });

  // Question Types
  const [questionTypes, setQuestionTypes] = useState<QuestionTypesResponse | null>(null);

  // Prompt Selection
  const [promptSelection, setPromptSelection] = useState<PromptSelection>({
    multiple_choice: null,
    open_ended: null,
    true_false: null
  });

  // Template Variables for each question type
  const [templateVariables, setTemplateVariables] = useState<{
    multiple_choice: Record<string, any>;
    open_ended: Record<string, any>;
    true_false: Record<string, any>;
  }>({
    multiple_choice: {},
    open_ended: {},
    true_false: {}
  });
  
  // Context Preview
  const [contextPreview, setContextPreview] = useState<{
    context: RAGContextSummary;
    preview_text: string;
    estimated_questions: number;
  } | null>(null);
  
  // Generated Exam
  const [generatedExam, setGeneratedExam] = useState<RAGExamResponse | null>(null);

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    setRAGRequest(prev => ({ ...prev, document_ids: selectedDocs }));
  }, [selectedDocs]);

  // Helper function to get automatic template variables from form fields
  const getAutoTemplateVariables = (): Record<string, any> => {
    // Map difficulty from German to English
    const difficultyMap: Record<string, string> = {
      'easy': 'easy',
      'medium': 'medium',
      'hard': 'hard'
    };

    // Map language from German to code
    const languageMap: Record<string, string> = {
      'de': 'de',
      'en': 'en'
    };

    return {
      topic: ragRequest.topic,
      difficulty: difficultyMap[ragRequest.difficulty] || ragRequest.difficulty,
      language: languageMap[ragRequest.language] || ragRequest.language,
      // context will be auto-filled by backend
    };
  };

  const loadInitialData = async () => {
    try {
      setLoading(true);
      
      // Load available documents
      const docsResponse = await DocumentService.getAvailableDocuments(true);
      setAvailableDocuments(docsResponse.documents);
      
      // Load question types
      const typesResponse = await RAGService.getQuestionTypes();
      setQuestionTypes(typesResponse);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Laden der Daten');
    } finally {
      setLoading(false);
    }
  };

  const handleDocumentSelection = (documentId: number) => {
    setSelectedDocs(prev => 
      prev.includes(documentId)
        ? prev.filter(id => id !== documentId)
        : [...prev, documentId]
    );
  };

  const handlePreviewContext = async () => {
    if (!ragRequest.topic.trim() || selectedDocs.length === 0) {
      setError('Bitte geben Sie ein Thema ein und wählen Sie mindestens ein Dokument aus.');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      const preview = await RAGService.previewContext(ragRequest.topic, selectedDocs);
      setContextPreview(preview);
      
      // Auto-adjust question count based on available context
      if (preview.estimated_questions > 0) {
        setRAGRequest(prev => ({
          ...prev,
          question_count: Math.min(prev.question_count, preview.estimated_questions)
        }));
      }
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler bei der Kontext-Vorschau');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateExam = async () => {
    // Validate request
    const validationErrors = RAGService.validateRAGRequest(ragRequest);
    if (validationErrors.length > 0) {
      setError(validationErrors.join(', '));
      return;
    }

    try {
      setLoading(true);
      setError(null);

      // Build prompt_config from promptSelection and templateVariables
      const promptConfig: RAGExamRequest['prompt_config'] = {};

      // Auto-filled variables (from main form)
      const autoVariables = getAutoTemplateVariables();

      // Multiple Choice
      if (promptSelection.multiple_choice) {
        promptConfig.multiple_choice = {
          prompt_id: promptSelection.multiple_choice,
          variables: {
            ...autoVariables,
            ...templateVariables.multiple_choice
          }
        };
      }

      // Open-Ended
      if (promptSelection.open_ended) {
        promptConfig.open_ended = {
          prompt_id: promptSelection.open_ended,
          variables: {
            ...autoVariables,
            ...templateVariables.open_ended
          }
        };
      }

      // True/False
      if (promptSelection.true_false) {
        promptConfig.true_false = {
          prompt_id: promptSelection.true_false,
          variables: {
            ...autoVariables,
            ...templateVariables.true_false
          }
        };
      }

      // Include prompt_config in the request
      const requestWithPrompts: RAGExamRequest = {
        ...ragRequest,
        prompt_config: Object.keys(promptConfig).length > 0 ? promptConfig : undefined
      };

      const exam = await RAGService.generateRAGExam(requestWithPrompts);
      setGeneratedExam(exam);

      if (onExamGenerated) {
        onExamGenerated(exam);
      }

      setActiveStep(3); // Move to results step

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler bei der Prüfungserstellung');
    } finally {
      setLoading(false);
    }
  };

  const handleExportExam = (format: 'json' | 'txt') => {
    if (!generatedExam) return;
    
    const content = RAGService.exportRAGExam(generatedExam, format);
    const blob = new Blob([content], { type: format === 'json' ? 'application/json' : 'text/plain' });
    const url = URL.createObjectURL(blob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = `rag-exam-${generatedExam.exam_id}.${format}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const getRecommendations = () => {
    if (!contextPreview) return null;
    
    return RAGService.getRAGRecommendations(
      selectedDocs.length,
      contextPreview.context.total_chunks,
      contextPreview.context.total_similarity_score / Math.max(contextPreview.context.total_chunks, 1)
    );
  };

  const steps = [
    'Dokumente auswählen',
    'Prüfungsparameter konfigurieren', 
    'Kontext-Vorschau',
    'Prüfung generieren'
  ];

  if (loading && activeStep === 0) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Psychology color="primary" />
          <Typography variant="h5">
            RAG-basierte Prüfung erstellen
          </Typography>
        </Box>
        {onBack && (
          <Button onClick={onBack} variant="outlined">
            Zurück
          </Button>
        )}
      </Box>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Stepper */}
      <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
        <Stepper activeStep={activeStep} orientation="vertical">
          
          {/* Step 1: Document Selection */}
          <Step>
            <StepLabel>Dokumente auswählen</StepLabel>
            <StepContent>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Wählen Sie die Dokumente aus, aus denen Prüfungsfragen generiert werden sollen.
              </Typography>
              
              {availableDocuments.length === 0 ? (
                <Alert severity="info">
                  Keine verarbeiteten Dokumente verfügbar. Laden Sie zuerst Dokumente hoch und lassen Sie sie verarbeiten.
                </Alert>
              ) : (
                <Grid container spacing={2}>
                  {availableDocuments.map((doc) => (
                    <Grid item xs={12} sm={6} md={4} key={doc.id}>
                      <Card 
                        sx={{ 
                          cursor: 'pointer',
                          border: selectedDocs.includes(doc.id) ? 2 : 1,
                          borderColor: selectedDocs.includes(doc.id) ? 'primary.main' : 'divider'
                        }}
                        onClick={() => handleDocumentSelection(doc.id)}
                      >
                        <CardContent>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                            <Description color="primary" />
                            <Typography variant="subtitle2" noWrap>
                              {doc.filename}
                            </Typography>
                          </Box>
                          <Typography variant="caption" color="text.secondary">
                            {doc.metadata?.total_chunks || 0} Textabschnitte
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                  ))}
                </Grid>
              )}
              
              <Box sx={{ mt: 2 }}>
                <Button
                  variant="contained"
                  onClick={() => setActiveStep(1)}
                  disabled={selectedDocs.length === 0}
                >
                  Weiter
                </Button>
              </Box>
            </StepContent>
          </Step>

          {/* Step 2: Configuration */}
          <Step>
            <StepLabel>Prüfungsparameter konfigurieren</StepLabel>
            <StepContent>
              <Grid container spacing={3}>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Prüfungsthema"
                    value={ragRequest.topic}
                    onChange={(e) => setRAGRequest(prev => ({ ...prev, topic: e.target.value }))}
                    placeholder="z.B. Machine Learning Grundlagen, Python Programmierung..."
                    helperText="Das Thema wird verwendet, um relevante Inhalte aus den Dokumenten zu finden"
                  />
                </Grid>

                <Grid item xs={12} md={4}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Anzahl Fragen"
                    value={ragRequest.question_count}
                    onChange={(e) => setRAGRequest(prev => ({
                      ...prev,
                      question_count: Math.max(1, Math.min(20, parseInt(e.target.value) || 5))
                    }))}
                    inputProps={{ min: 1, max: 20 }}
                  />
                </Grid>

                <Grid item xs={12} md={4}>
                  <FormControl fullWidth>
                    <InputLabel>Schwierigkeitsgrad</InputLabel>
                    <Select
                      value={ragRequest.difficulty}
                      label="Schwierigkeitsgrad"
                      onChange={(e) => setRAGRequest(prev => ({ ...prev, difficulty: e.target.value }))}
                    >
                      {questionTypes?.difficulty_levels.map((level) => (
                        <MenuItem key={level.level} value={level.level}>
                          {level.name}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>

                <Grid item xs={12} md={4}>
                  <FormControl fullWidth>
                    <InputLabel>Sprache</InputLabel>
                    <Select
                      value={ragRequest.language}
                      label="Sprache"
                      onChange={(e) => setRAGRequest(prev => ({ ...prev, language: e.target.value }))}
                    >
                      {questionTypes?.supported_languages.map((lang) => (
                        <MenuItem key={lang.code} value={lang.code}>
                          {lang.name}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>

                <Grid item xs={12}>
                  <Typography variant="subtitle1" sx={{ mb: 1 }}>
                    Fragetypen:
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    {questionTypes?.supported_types.map((type) => (
                      <Chip
                        key={type.type}
                        label={type.name}
                        color={ragRequest.question_types.includes(type.type) ? 'primary' : 'default'}
                        onClick={() => {
                          const newTypes = ragRequest.question_types.includes(type.type)
                            ? ragRequest.question_types.filter(t => t !== type.type)
                            : [...ragRequest.question_types, type.type];
                          setRAGRequest(prev => ({ ...prev, question_types: newTypes }));
                        }}
                        sx={{ cursor: 'pointer' }}
                      />
                    ))}
                  </Box>
                </Grid>

                {/* Prompt Template Selection */}
                <Grid item xs={12}>
                  <Divider sx={{ my: 2 }} />
                  <Typography variant="subtitle1" sx={{ mb: 2 }}>
                    Prompt-Templates (Optional):
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    Wählen Sie für jeden Fragetyp ein spezifisches Prompt-Template aus der Library.
                    Wenn kein Template ausgewählt wird, werden die Standard-Prompts verwendet.
                  </Typography>
                </Grid>

                {/* Multiple Choice Prompt Selector */}
                {ragRequest.question_types.includes('multiple_choice') && (
                  <Grid item xs={12}>
                    <PromptTemplateSelector
                      questionType={QuestionType.MULTIPLE_CHOICE}
                      selectedPromptId={promptSelection.multiple_choice}
                      onPromptSelect={(promptId) =>
                        setPromptSelection(prev => ({ ...prev, multiple_choice: promptId }))
                      }
                      onVariablesChange={(variables) =>
                        setTemplateVariables(prev => ({ ...prev, multiple_choice: variables }))
                      }
                      autoFilledVariables={getAutoTemplateVariables()}
                      showPreview={true}
                    />
                  </Grid>
                )}

                {/* Open-Ended Prompt Selector */}
                {ragRequest.question_types.includes('open_ended') && (
                  <Grid item xs={12}>
                    <PromptTemplateSelector
                      questionType={QuestionType.OPEN_ENDED}
                      selectedPromptId={promptSelection.open_ended}
                      onPromptSelect={(promptId) =>
                        setPromptSelection(prev => ({ ...prev, open_ended: promptId }))
                      }
                      onVariablesChange={(variables) =>
                        setTemplateVariables(prev => ({ ...prev, open_ended: variables }))
                      }
                      autoFilledVariables={getAutoTemplateVariables()}
                      showPreview={true}
                    />
                  </Grid>
                )}

                {/* True/False Prompt Selector */}
                {ragRequest.question_types.includes('true_false') && (
                  <Grid item xs={12}>
                    <PromptTemplateSelector
                      questionType={QuestionType.TRUE_FALSE}
                      selectedPromptId={promptSelection.true_false}
                      onPromptSelect={(promptId) =>
                        setPromptSelection(prev => ({ ...prev, true_false: promptId }))
                      }
                      onVariablesChange={(variables) =>
                        setTemplateVariables(prev => ({ ...prev, true_false: variables }))
                      }
                      autoFilledVariables={getAutoTemplateVariables()}
                      showPreview={true}
                    />
                  </Grid>
                )}
              </Grid>

              <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
                <Button onClick={() => setActiveStep(0)}>
                  Zurück
                </Button>
                <Button
                  variant="contained"
                  onClick={() => setActiveStep(2)}
                  disabled={!ragRequest.topic.trim()}
                >
                  Weiter
                </Button>
              </Box>
            </StepContent>
          </Step>

          {/* Step 3: Context Preview */}
          <Step>
            <StepLabel>Kontext-Vorschau</StepLabel>
            <StepContent>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Überprüfen Sie den gefundenen Kontext und die Empfehlungen vor der Generierung.
              </Typography>

              <Box sx={{ mb: 2 }}>
                <Button
                  variant="outlined"
                  onClick={handlePreviewContext}
                  disabled={loading}
                  startIcon={loading ? <CircularProgress size={20} /> : <Preview />}
                >
                  {loading ? 'Lade Vorschau...' : 'Kontext-Vorschau laden'}
                </Button>
              </Box>

              {contextPreview && (
                <Box>
                  {/* Context Summary */}
                  <Card sx={{ mb: 2 }}>
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        Gefundener Kontext
                      </Typography>
                      <pre style={{ fontSize: '0.875rem', whiteSpace: 'pre-wrap' }}>
                        {contextPreview.preview_text}
                      </pre>
                    </CardContent>
                  </Card>

                  {/* Recommendations */}
                  {(() => {
                    const recommendations = getRecommendations();
                    return recommendations && (
                      <Accordion>
                        <AccordionSummary expandIcon={<ExpandMore />}>
                          <Typography variant="h6">
                            <Settings sx={{ mr: 1, verticalAlign: 'middle' }} />
                            Empfehlungen
                          </Typography>
                        </AccordionSummary>
                        <AccordionDetails>
                          <Grid container spacing={2}>
                            <Grid item xs={12} md={6}>
                              <Typography variant="subtitle2">Empfohlene Anzahl Fragen:</Typography>
                              <Typography variant="body2" color="primary">
                                {recommendations.recommended_question_count}
                              </Typography>
                            </Grid>
                            <Grid item xs={12} md={6}>
                              <Typography variant="subtitle2">Empfohlener Schwierigkeitsgrad:</Typography>
                              <Typography variant="body2" color="primary">
                                {recommendations.recommended_difficulty}
                              </Typography>
                            </Grid>
                            <Grid item xs={12}>
                              <Typography variant="subtitle2">Empfohlene Fragetypen:</Typography>
                              <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                                {recommendations.recommended_question_types.map(type => (
                                  <Chip key={type} label={type} size="small" color="primary" />
                                ))}
                              </Box>
                            </Grid>
                            {recommendations.quality_warning && (
                              <Grid item xs={12}>
                                <Alert severity="warning">
                                  {recommendations.quality_warning}
                                </Alert>
                              </Grid>
                            )}
                          </Grid>
                        </AccordionDetails>
                      </Accordion>
                    );
                  })()}
                </Box>
              )}

              <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
                <Button onClick={() => setActiveStep(1)}>
                  Zurück
                </Button>
                <Button
                  variant="contained"
                  onClick={handleGenerateExam}
                  disabled={!contextPreview || loading}
                  startIcon={loading ? <CircularProgress size={20} /> : <Psychology />}
                >
                  {loading ? 'Generiere Prüfung...' : 'Prüfung generieren'}
                </Button>
              </Box>
            </StepContent>
          </Step>

          {/* Step 4: Results */}
          <Step>
            <StepLabel>Prüfung generiert</StepLabel>
            <StepContent>
              {generatedExam && (
                <Box>
                  <Alert severity="success" sx={{ mb: 2 }}>
                    <Typography variant="h6">
                      Prüfung erfolgreich generiert!
                    </Typography>
                    <Typography variant="body2">
                      {generatedExam.questions.length} Fragen in {generatedExam.generation_time.toFixed(2)}s erstellt
                    </Typography>
                  </Alert>

                  {/* Quality Metrics */}
                  <Card sx={{ mb: 2 }}>
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        Qualitätsmetriken
                      </Typography>
                      <Grid container spacing={2}>
                        <Grid item xs={6} md={3}>
                          <Typography variant="body2" color="text.secondary">
                            Durchschnittliche Konfidenz
                          </Typography>
                          <Typography variant="h6" color="primary">
                            {(generatedExam.quality_metrics.average_confidence * 100).toFixed(1)}%
                          </Typography>
                        </Grid>
                        <Grid item xs={6} md={3}>
                          <Typography variant="body2" color="text.secondary">
                            Quellenabdeckung
                          </Typography>
                          <Typography variant="h6" color="primary">
                            {(generatedExam.quality_metrics.source_coverage * 100).toFixed(1)}%
                          </Typography>
                        </Grid>
                        <Grid item xs={6} md={3}>
                          <Typography variant="body2" color="text.secondary">
                            Verwendete Textabschnitte
                          </Typography>
                          <Typography variant="h6" color="primary">
                            {generatedExam.quality_metrics.context_chunks_used}
                          </Typography>
                        </Grid>
                        <Grid item xs={6} md={3}>
                          <Typography variant="body2" color="text.secondary">
                            Quelldokumente
                          </Typography>
                          <Typography variant="h6" color="primary">
                            {generatedExam.context_summary.source_documents.length}
                          </Typography>
                        </Grid>
                      </Grid>
                    </CardContent>
                  </Card>

                  {/* Actions */}
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    <Button
                      variant="contained"
                      onClick={() => onExamGenerated?.(generatedExam)}
                    >
                      Prüfung anzeigen
                    </Button>
                    <Button
                      variant="outlined"
                      startIcon={<Download />}
                      onClick={() => handleExportExam('json')}
                    >
                      Als JSON exportieren
                    </Button>
                    <Button
                      variant="outlined"
                      startIcon={<Download />}
                      onClick={() => handleExportExam('txt')}
                    >
                      Als Text exportieren
                    </Button>
                    <Button
                      variant="outlined"
                      onClick={() => {
                        setActiveStep(0);
                        setGeneratedExam(null);
                        setContextPreview(null);
                      }}
                    >
                      Neue Prüfung erstellen
                    </Button>
                  </Box>
                </Box>
              )}
            </StepContent>
          </Step>
        </Stepper>
      </Paper>
    </Box>
  );
};

export default RAGExamCreator;
