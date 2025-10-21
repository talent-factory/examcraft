import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import RAGExamCreator from '../RAGExamCreator';
import { DocumentService } from '../../services/DocumentService';
import { RAGService } from '../../services/RAGService';
import { Document, DocumentStatus, RAGExamResponse, QuestionTypesResponse } from '../../types/document';

// Mock services
jest.mock('../../services/DocumentService');
jest.mock('../../services/RAGService');

const mockDocumentService = DocumentService as jest.Mocked<typeof DocumentService>;
const mockRAGService = RAGService as jest.Mocked<typeof RAGService>;

// Mock theme
const theme = createTheme();

// Test wrapper with theme
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider theme={theme}>
    {children}
  </ThemeProvider>
);

// Sample test data
const mockDocuments: Document[] = [
  {
    id: 1,
    filename: 'test-document.pdf',
    mime_type: 'application/pdf',
    status: DocumentStatus.PROCESSED,
    created_at: '2025-09-22T10:00:00Z',
    processed_at: '2025-09-22T10:01:00Z',
    file_size: 1024000,
    has_vectors: true,
    metadata: {
      total_chunks: 5,
      embedding_model: 'test-model',
      processing_time: 1.5
    }
  },
  {
    id: 2,
    filename: 'another-doc.txt',
    mime_type: 'text/plain',
    status: DocumentStatus.PROCESSED,
    created_at: '2025-09-22T10:05:00Z',
    processed_at: '2025-09-22T10:06:00Z',
    file_size: 512000,
    has_vectors: true,
    metadata: {
      total_chunks: 3,
      embedding_model: 'test-model',
      processing_time: 0.8
    }
  }
];

const mockQuestionTypes: QuestionTypesResponse = {
  supported_types: [
    {
      type: 'multiple_choice',
      name: 'Multiple Choice',
      description: 'Frage mit 4 Antwortoptionen',
      example: 'Welche Aussage ist korrekt?'
    },
    {
      type: 'open_ended',
      name: 'Offene Frage',
      description: 'Frage die eine ausführliche Antwort erfordert',
      example: 'Erläutern Sie...'
    }
  ],
  difficulty_levels: [
    {
      level: 'easy',
      name: 'Einfach',
      description: 'Grundlegende Fakten'
    },
    {
      level: 'medium',
      name: 'Mittel',
      description: 'Anwendung von Konzepten'
    },
    {
      level: 'hard',
      name: 'Schwer',
      description: 'Kritisches Denken'
    }
  ],
  supported_languages: [
    { code: 'de', name: 'Deutsch' },
    { code: 'en', name: 'English' }
  ]
};

const mockRAGExamResponse: RAGExamResponse = {
  exam_id: 'test_exam_123',
  topic: 'Test Topic',
  questions: [
    {
      question_text: 'Was ist ein Test?',
      question_type: 'multiple_choice',
      options: ['A) Ein Verfahren', 'B) Ein Dokument', 'C) Ein System', 'D) Ein Prozess'],
      correct_answer: 'A',
      explanation: 'Ein Test ist ein Verfahren zur Überprüfung',
      difficulty: 'medium',
      source_chunks: ['chunk_1'],
      source_documents: ['test-document.pdf'],
      confidence_score: 0.85
    }
  ],
  context_summary: {
    query: 'Test Topic',
    total_chunks: 3,
    total_similarity_score: 2.1,
    source_documents: [{ id: 1, filename: 'test-document.pdf', chunks_used: 2 }],
    context_length: 150
  },
  generation_time: 2.5,
  quality_metrics: {
    total_questions: 1,
    average_confidence: 0.85,
    source_coverage: 1.0,
    question_type_distribution: { multiple_choice: 1 },
    context_chunks_used: 3,
    total_context_length: 150,
    average_similarity_score: 0.7
  }
};

describe('RAGExamCreator', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Default mocks
    mockDocumentService.getAvailableDocuments.mockResolvedValue({
      total_documents: 2,
      processed_documents: 2,
      documents_with_vectors: 2,
      documents: mockDocuments
    });

    mockRAGService.getQuestionTypes.mockResolvedValue(mockQuestionTypes);
  });

  describe('Initialization', () => {
    it('renders RAG exam creator with stepper', async () => {
      render(
        <TestWrapper>
          <RAGExamCreator />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('RAG-basierte Prüfung erstellen')).toBeInTheDocument();
        expect(screen.getByText('Dokumente auswählen')).toBeInTheDocument();
        expect(screen.getByText('Prüfungsparameter konfigurieren')).toBeInTheDocument();
        expect(screen.getByText('Kontext-Vorschau')).toBeInTheDocument();
        expect(screen.getByText('Prüfung generieren')).toBeInTheDocument();
      });
    });

    it('loads initial data on mount', async () => {
      render(
        <TestWrapper>
          <RAGExamCreator />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(mockDocumentService.getAvailableDocuments).toHaveBeenCalledWith(true);
        expect(mockRAGService.getQuestionTypes).toHaveBeenCalled();
      });
    });

    it('shows loading state during initialization', () => {
      mockDocumentService.getAvailableDocuments.mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({
          total_documents: 0,
          processed_documents: 0,
          documents_with_vectors: 0,
          documents: []
        }), 100))
      );

      render(
        <TestWrapper>
          <RAGExamCreator />
        </TestWrapper>
      );

      expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });

    it('handles initialization errors', async () => {
      const errorMessage = 'Failed to load data';
      mockDocumentService.getAvailableDocuments.mockRejectedValue(new Error(errorMessage));

      render(
        <TestWrapper>
          <RAGExamCreator />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText(errorMessage)).toBeInTheDocument();
      });
    });
  });

  describe('Document Selection Step', () => {
    it('displays available documents', async () => {
      render(
        <TestWrapper>
          <RAGExamCreator />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
        expect(screen.getByText('another-doc.txt')).toBeInTheDocument();
        expect(screen.getByText('5 Textabschnitte')).toBeInTheDocument();
        expect(screen.getByText('3 Textabschnitte')).toBeInTheDocument();
      });
    });

    it('allows selecting documents', async () => {
      render(
        <TestWrapper>
          <RAGExamCreator />
        </TestWrapper>
      );

      await waitFor(() => {
        const documentCard = screen.getByText('test-document.pdf').closest('[role="button"]');
        fireEvent.click(documentCard!);
      });

      // Should enable the "Weiter" button
      const nextButton = screen.getByText('Weiter');
      expect(nextButton).not.toBeDisabled();
    });

    it('shows info when no documents available', async () => {
      mockDocumentService.getAvailableDocuments.mockResolvedValue({
        total_documents: 0,
        processed_documents: 0,
        documents_with_vectors: 0,
        documents: []
      });

      render(
        <TestWrapper>
          <RAGExamCreator />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Keine verarbeiteten Dokumente verfügbar.')).toBeInTheDocument();
      });
    });

    it('pre-selects documents when provided', async () => {
      render(
        <TestWrapper>
          <RAGExamCreator selectedDocuments={[1]} />
        </TestWrapper>
      );

      await waitFor(() => {
        const nextButton = screen.getByText('Weiter');
        expect(nextButton).not.toBeDisabled();
      });
    });
  });

  describe('Configuration Step', () => {
    beforeEach(async () => {
      render(
        <TestWrapper>
          <RAGExamCreator />
        </TestWrapper>
      );

      await waitFor(() => {
        const documentCard = screen.getByText('test-document.pdf').closest('[role="button"]');
        fireEvent.click(documentCard!);
        fireEvent.click(screen.getByText('Weiter'));
      });
    });

    it('shows configuration form', () => {
      expect(screen.getByLabelText('Prüfungsthema')).toBeInTheDocument();
      expect(screen.getByLabelText('Anzahl Fragen')).toBeInTheDocument();
      expect(screen.getByLabelText('Schwierigkeitsgrad')).toBeInTheDocument();
      expect(screen.getByLabelText('Sprache')).toBeInTheDocument();
    });

    it('allows configuring exam parameters', () => {
      const topicInput = screen.getByLabelText('Prüfungsthema');
      fireEvent.change(topicInput, { target: { value: 'Machine Learning' } });
      expect(topicInput).toHaveValue('Machine Learning');

      const questionCountInput = screen.getByLabelText('Anzahl Fragen');
      fireEvent.change(questionCountInput, { target: { value: '10' } });
      expect(questionCountInput).toHaveValue(10);
    });

    it('shows question type chips', () => {
      expect(screen.getByText('Multiple Choice')).toBeInTheDocument();
      expect(screen.getByText('Offene Frage')).toBeInTheDocument();
    });

    it('allows selecting question types', () => {
      const multipleChoiceChip = screen.getByText('Multiple Choice');
      fireEvent.click(multipleChoiceChip);
      
      // Should toggle selection
      expect(multipleChoiceChip).toHaveClass('MuiChip-colorDefault');
    });

    it('validates required fields', () => {
      const nextButton = screen.getByText('Weiter');
      expect(nextButton).toBeDisabled(); // Topic is required
    });

    it('enables next button when topic is provided', () => {
      const topicInput = screen.getByLabelText('Prüfungsthema');
      fireEvent.change(topicInput, { target: { value: 'Test Topic' } });

      const nextButton = screen.getByText('Weiter');
      expect(nextButton).not.toBeDisabled();
    });
  });

  describe('Context Preview Step', () => {
    beforeEach(async () => {
      render(
        <TestWrapper>
          <RAGExamCreator />
        </TestWrapper>
      );

      await waitFor(() => {
        const documentCard = screen.getByText('test-document.pdf').closest('[role="button"]');
        fireEvent.click(documentCard!);
        fireEvent.click(screen.getByText('Weiter'));
      });

      const topicInput = screen.getByLabelText('Prüfungsthema');
      fireEvent.change(topicInput, { target: { value: 'Test Topic' } });
      fireEvent.click(screen.getByText('Weiter'));
    });

    it('shows context preview step', () => {
      expect(screen.getByText('Kontext-Vorschau')).toBeInTheDocument();
      expect(screen.getByText('Kontext-Vorschau laden')).toBeInTheDocument();
    });

    it('loads context preview when button clicked', async () => {
      const mockContextPreview = {
        context: mockRAGExamResponse.context_summary,
        preview_text: 'Test preview text',
        estimated_questions: 3
      };

      mockRAGService.previewContext.mockResolvedValue(mockContextPreview);

      const previewButton = screen.getByText('Kontext-Vorschau laden');
      fireEvent.click(previewButton);

      await waitFor(() => {
        expect(mockRAGService.previewContext).toHaveBeenCalledWith('Test Topic', [1]);
        expect(screen.getByText('Gefundener Kontext')).toBeInTheDocument();
        expect(screen.getByText('Test preview text')).toBeInTheDocument();
      });
    });

    it('shows recommendations after context preview', async () => {
      const mockContextPreview = {
        context: mockRAGExamResponse.context_summary,
        preview_text: 'Test preview text',
        estimated_questions: 3
      };

      mockRAGService.previewContext.mockResolvedValue(mockContextPreview);

      const previewButton = screen.getByText('Kontext-Vorschau laden');
      fireEvent.click(previewButton);

      await waitFor(() => {
        expect(screen.getByText('Empfehlungen')).toBeInTheDocument();
      });
    });

    it('handles context preview errors', async () => {
      const errorMessage = 'Context preview failed';
      mockRAGService.previewContext.mockRejectedValue(new Error(errorMessage));

      const previewButton = screen.getByText('Kontext-Vorschau laden');
      fireEvent.click(previewButton);

      await waitFor(() => {
        expect(screen.getByText(errorMessage)).toBeInTheDocument();
      });
    });
  });

  describe('Exam Generation', () => {
    beforeEach(async () => {
      render(
        <TestWrapper>
          <RAGExamCreator />
        </TestWrapper>
      );

      // Navigate through steps
      await waitFor(() => {
        const documentCard = screen.getByText('test-document.pdf').closest('[role="button"]');
        fireEvent.click(documentCard!);
        fireEvent.click(screen.getByText('Weiter'));
      });

      const topicInput = screen.getByLabelText('Prüfungsthema');
      fireEvent.change(topicInput, { target: { value: 'Test Topic' } });
      fireEvent.click(screen.getByText('Weiter'));

      // Load context preview
      const mockContextPreview = {
        context: mockRAGExamResponse.context_summary,
        preview_text: 'Test preview text',
        estimated_questions: 3
      };
      mockRAGService.previewContext.mockResolvedValue(mockContextPreview);

      const previewButton = screen.getByText('Kontext-Vorschau laden');
      fireEvent.click(previewButton);

      await waitFor(() => {
        expect(screen.getByText('Prüfung generieren')).toBeInTheDocument();
      });
    });

    it('generates RAG exam successfully', async () => {
      mockRAGService.generateRAGExam.mockResolvedValue(mockRAGExamResponse);

      const generateButton = screen.getByText('Prüfung generieren');
      fireEvent.click(generateButton);

      await waitFor(() => {
        expect(mockRAGService.generateRAGExam).toHaveBeenCalled();
        expect(screen.getByText('Prüfung erfolgreich generiert!')).toBeInTheDocument();
        expect(screen.getByText('1 Fragen in 2.50s erstellt')).toBeInTheDocument();
      });
    });

    it('shows quality metrics after generation', async () => {
      mockRAGService.generateRAGExam.mockResolvedValue(mockRAGExamResponse);

      const generateButton = screen.getByText('Prüfung generieren');
      fireEvent.click(generateButton);

      await waitFor(() => {
        expect(screen.getByText('Qualitätsmetriken')).toBeInTheDocument();
        expect(screen.getByText('85.0%')).toBeInTheDocument(); // Confidence
        expect(screen.getByText('100.0%')).toBeInTheDocument(); // Coverage
      });
    });

    it('handles exam generation errors', async () => {
      const errorMessage = 'Exam generation failed';
      mockRAGService.generateRAGExam.mockRejectedValue(new Error(errorMessage));

      const generateButton = screen.getByText('Prüfung generieren');
      fireEvent.click(generateButton);

      await waitFor(() => {
        expect(screen.getByText(errorMessage)).toBeInTheDocument();
      });
    });

    it('calls onExamGenerated callback', async () => {
      const mockOnExamGenerated = jest.fn();
      mockRAGService.generateRAGExam.mockResolvedValue(mockRAGExamResponse);

      render(
        <TestWrapper>
          <RAGExamCreator onExamGenerated={mockOnExamGenerated} />
        </TestWrapper>
      );

      // Navigate through steps quickly
      await waitFor(() => {
        const documentCard = screen.getByText('test-document.pdf').closest('[role="button"]');
        fireEvent.click(documentCard!);
        fireEvent.click(screen.getByText('Weiter'));
      });

      const topicInput = screen.getByLabelText('Prüfungsthema');
      fireEvent.change(topicInput, { target: { value: 'Test Topic' } });
      fireEvent.click(screen.getByText('Weiter'));

      const mockContextPreview = {
        context: mockRAGExamResponse.context_summary,
        preview_text: 'Test preview text',
        estimated_questions: 3
      };
      mockRAGService.previewContext.mockResolvedValue(mockContextPreview);

      const previewButton = screen.getByText('Kontext-Vorschau laden');
      fireEvent.click(previewButton);

      await waitFor(() => {
        const generateButton = screen.getByText('Prüfung generieren');
        fireEvent.click(generateButton);
      });

      await waitFor(() => {
        expect(mockOnExamGenerated).toHaveBeenCalledWith(mockRAGExamResponse);
      });
    });
  });

  describe('Export Functionality', () => {
    beforeEach(async () => {
      // Mock successful exam generation
      mockRAGService.generateRAGExam.mockResolvedValue(mockRAGExamResponse);
      mockRAGService.exportRAGExam.mockReturnValue('exported content');

      render(
        <TestWrapper>
          <RAGExamCreator />
        </TestWrapper>
      );

      // Navigate through all steps and generate exam
      await waitFor(() => {
        const documentCard = screen.getByText('test-document.pdf').closest('[role="button"]');
        fireEvent.click(documentCard!);
        fireEvent.click(screen.getByText('Weiter'));
      });

      const topicInput = screen.getByLabelText('Prüfungsthema');
      fireEvent.change(topicInput, { target: { value: 'Test Topic' } });
      fireEvent.click(screen.getByText('Weiter'));

      const mockContextPreview = {
        context: mockRAGExamResponse.context_summary,
        preview_text: 'Test preview text',
        estimated_questions: 3
      };
      mockRAGService.previewContext.mockResolvedValue(mockContextPreview);

      const previewButton = screen.getByText('Kontext-Vorschau laden');
      fireEvent.click(previewButton);

      await waitFor(() => {
        const generateButton = screen.getByText('Prüfung generieren');
        fireEvent.click(generateButton);
      });

      await waitFor(() => {
        expect(screen.getByText('Als JSON exportieren')).toBeInTheDocument();
      });
    });

    it('exports exam as JSON', async () => {
      // Mock URL.createObjectURL and related functions
      global.URL.createObjectURL = jest.fn(() => 'mock-url');
      global.URL.revokeObjectURL = jest.fn();
      
      const mockLink = {
        href: '',
        download: '',
        click: jest.fn()
      };
      jest.spyOn(document, 'createElement').mockReturnValue(mockLink as any);
      jest.spyOn(document.body, 'appendChild').mockImplementation();
      jest.spyOn(document.body, 'removeChild').mockImplementation();

      const exportButton = screen.getByText('Als JSON exportieren');
      fireEvent.click(exportButton);

      expect(mockRAGService.exportRAGExam).toHaveBeenCalledWith(mockRAGExamResponse, 'json');
      expect(mockLink.download).toBe('rag-exam-test_exam_123.json');
      expect(mockLink.click).toHaveBeenCalled();
    });

    it('exports exam as text', async () => {
      global.URL.createObjectURL = jest.fn(() => 'mock-url');
      global.URL.revokeObjectURL = jest.fn();
      
      const mockLink = {
        href: '',
        download: '',
        click: jest.fn()
      };
      jest.spyOn(document, 'createElement').mockReturnValue(mockLink as any);
      jest.spyOn(document.body, 'appendChild').mockImplementation();
      jest.spyOn(document.body, 'removeChild').mockImplementation();

      const exportButton = screen.getByText('Als Text exportieren');
      fireEvent.click(exportButton);

      expect(mockRAGService.exportRAGExam).toHaveBeenCalledWith(mockRAGExamResponse, 'txt');
      expect(mockLink.download).toBe('rag-exam-test_exam_123.txt');
      expect(mockLink.click).toHaveBeenCalled();
    });
  });

  describe('Navigation', () => {
    it('allows going back to previous steps', async () => {
      render(
        <TestWrapper>
          <RAGExamCreator />
        </TestWrapper>
      );

      await waitFor(() => {
        const documentCard = screen.getByText('test-document.pdf').closest('[role="button"]');
        fireEvent.click(documentCard!);
        fireEvent.click(screen.getByText('Weiter'));
      });

      // Should be on configuration step
      expect(screen.getByLabelText('Prüfungsthema')).toBeInTheDocument();

      // Go back
      fireEvent.click(screen.getByText('Zurück'));

      // Should be back on document selection
      expect(screen.getByText('Wählen Sie die Dokumente aus')).toBeInTheDocument();
    });

    it('calls onBack callback when back button clicked', () => {
      const mockOnBack = jest.fn();

      render(
        <TestWrapper>
          <RAGExamCreator onBack={mockOnBack} />
        </TestWrapper>
      );

      const backButton = screen.getByText('Zurück');
      fireEvent.click(backButton);

      expect(mockOnBack).toHaveBeenCalled();
    });

    it('allows creating new exam after completion', async () => {
      mockRAGService.generateRAGExam.mockResolvedValue(mockRAGExamResponse);

      render(
        <TestWrapper>
          <RAGExamCreator />
        </TestWrapper>
      );

      // Complete the flow
      await waitFor(() => {
        const documentCard = screen.getByText('test-document.pdf').closest('[role="button"]');
        fireEvent.click(documentCard!);
        fireEvent.click(screen.getByText('Weiter'));
      });

      const topicInput = screen.getByLabelText('Prüfungsthema');
      fireEvent.change(topicInput, { target: { value: 'Test Topic' } });
      fireEvent.click(screen.getByText('Weiter'));

      const mockContextPreview = {
        context: mockRAGExamResponse.context_summary,
        preview_text: 'Test preview text',
        estimated_questions: 3
      };
      mockRAGService.previewContext.mockResolvedValue(mockContextPreview);

      const previewButton = screen.getByText('Kontext-Vorschau laden');
      fireEvent.click(previewButton);

      await waitFor(() => {
        const generateButton = screen.getByText('Prüfung generieren');
        fireEvent.click(generateButton);
      });

      await waitFor(() => {
        const newExamButton = screen.getByText('Neue Prüfung erstellen');
        fireEvent.click(newExamButton);
      });

      // Should be back at the beginning
      expect(screen.getByText('Wählen Sie die Dokumente aus')).toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    it('displays error messages appropriately', async () => {
      render(
        <TestWrapper>
          <RAGExamCreator />
        </TestWrapper>
      );

      await waitFor(() => {
        const documentCard = screen.getByText('test-document.pdf').closest('[role="button"]');
        fireEvent.click(documentCard!);
        fireEvent.click(screen.getByText('Weiter'));
      });

      const topicInput = screen.getByLabelText('Prüfungsthema');
      fireEvent.change(topicInput, { target: { value: 'Test Topic' } });
      fireEvent.click(screen.getByText('Weiter'));

      const errorMessage = 'Context preview failed';
      mockRAGService.previewContext.mockRejectedValue(new Error(errorMessage));

      const previewButton = screen.getByText('Kontext-Vorschau laden');
      fireEvent.click(previewButton);

      await waitFor(() => {
        expect(screen.getByText(errorMessage)).toBeInTheDocument();
      });

      // Error should be dismissible
      const closeButton = screen.getByLabelText('Close');
      fireEvent.click(closeButton);

      expect(screen.queryByText(errorMessage)).not.toBeInTheDocument();
    });
  });
});
