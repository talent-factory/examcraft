import { 
  RAGExamRequest, 
  RAGExamResponse, 
  RAGContextSummary,
  QuestionTypesResponse 
} from '../types/document';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export class RAGService {
  /**
   * Generate RAG-based exam from documents
   */
  static async generateRAGExam(request: RAGExamRequest): Promise<RAGExamResponse> {
    const response = await fetch(`${API_BASE_URL}/api/v1/rag/generate-exam`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `RAG exam generation failed: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Retrieve context from vector database
   */
  static async retrieveContext(
    query: string,
    documentIds?: number[],
    maxChunks: number = 5,
    minSimilarity: number = 0.3
  ): Promise<RAGContextSummary> {
    const requestBody = {
      query,
      document_ids: documentIds,
      max_chunks: maxChunks,
      min_similarity: minSimilarity,
    };

    const response = await fetch(`${API_BASE_URL}/api/v1/rag/retrieve-context`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Context retrieval failed: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Get supported question types and configurations
   */
  static async getQuestionTypes(): Promise<QuestionTypesResponse> {
    const response = await fetch(`${API_BASE_URL}/api/v1/rag/question-types`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to fetch question types: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Check RAG service health
   */
  static async checkHealth(): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/api/v1/rag/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `RAG health check failed: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Preview context retrieval for a topic
   */
  static async previewContext(
    topic: string,
    documentIds?: number[]
  ): Promise<{
    context: RAGContextSummary;
    preview_text: string;
    estimated_questions: number;
  }> {
    try {
      const context = await this.retrieveContext(topic, documentIds, 10, 0.2);
      
      // Estimate how many questions can be generated
      const estimatedQuestions = Math.min(
        Math.floor(context.total_chunks / 2), // 2 chunks per question
        10 // Maximum 10 questions
      );

      // Create preview text
      const sourceFiles = context.source_documents.map(doc => doc.filename).join(', ');
      const previewText = `
Gefundene Quellen: ${sourceFiles}
Relevante Textabschnitte: ${context.total_chunks}
Durchschnittliche Ähnlichkeit: ${(context.total_similarity_score / Math.max(context.total_chunks, 1)).toFixed(2)}
Geschätzte Fragen: ${estimatedQuestions}
      `.trim();

      return {
        context,
        preview_text: previewText,
        estimated_questions: estimatedQuestions,
      };
    } catch (error) {
      throw new Error(`Context preview failed: ${error && typeof error === 'object' && 'message' in error ? (error as Error).message : 'Unknown error'}`);
    }
  }

  /**
   * Validate RAG exam request
   */
  static validateRAGRequest(request: RAGExamRequest): string[] {
    const errors: string[] = [];

    if (!request.topic || request.topic.trim().length < 3) {
      errors.push('Thema muss mindestens 3 Zeichen lang sein');
    }

    if (request.question_count < 1 || request.question_count > 20) {
      errors.push('Anzahl Fragen muss zwischen 1 und 20 liegen');
    }

    if (!request.question_types || request.question_types.length === 0) {
      errors.push('Mindestens ein Fragetyp muss ausgewählt werden');
    }

    const validQuestionTypes = ['multiple_choice', 'open_ended', 'true_false'];
    const invalidTypes = request.question_types.filter(type => !validQuestionTypes.includes(type));
    if (invalidTypes.length > 0) {
      errors.push(`Ungültige Fragetypen: ${invalidTypes.join(', ')}`);
    }

    const validDifficulties = ['easy', 'medium', 'hard'];
    if (!validDifficulties.includes(request.difficulty)) {
      errors.push('Ungültiger Schwierigkeitsgrad');
    }

    const validLanguages = ['de', 'en'];
    if (!validLanguages.includes(request.language)) {
      errors.push('Ungültige Sprache');
    }

    if (request.document_ids && request.document_ids.length === 0) {
      errors.push('Mindestens ein Dokument muss ausgewählt werden');
    }

    return errors;
  }

  /**
   * Get RAG exam generation recommendations
   */
  static getRAGRecommendations(
    documentCount: number,
    totalChunks: number,
    averageSimilarity: number
  ): {
    recommended_question_count: number;
    recommended_question_types: string[];
    recommended_difficulty: string;
    quality_warning?: string;
  } {
    let recommendedQuestionCount = Math.min(
      Math.floor(totalChunks / 3), // 3 chunks per question for good context
      Math.min(documentCount * 2, 10) // Max 2 questions per document, max 10 total
    );

    recommendedQuestionCount = Math.max(1, recommendedQuestionCount);

    const recommendedQuestionTypes: string[] = ['multiple_choice'];
    if (totalChunks >= 6) {
      recommendedQuestionTypes.push('open_ended');
    }
    if (totalChunks >= 10) {
      recommendedQuestionTypes.push('true_false');
    }

    let recommendedDifficulty = 'medium';
    if (averageSimilarity < 0.3) {
      recommendedDifficulty = 'easy';
    } else if (averageSimilarity > 0.7) {
      recommendedDifficulty = 'hard';
    }

    let qualityWarning: string | undefined;
    if (averageSimilarity < 0.2) {
      qualityWarning = 'Niedrige Ähnlichkeitswerte - Fragen könnten weniger relevant sein';
    } else if (totalChunks < 3) {
      qualityWarning = 'Wenige Textabschnitte verfügbar - begrenzte Fragenvielfalt';
    } else if (documentCount === 1 && totalChunks < 5) {
      qualityWarning = 'Nur ein Dokument mit wenigen Abschnitten - erwägen Sie weitere Dokumente';
    }

    return {
      recommended_question_count: recommendedQuestionCount,
      recommended_question_types: recommendedQuestionTypes,
      recommended_difficulty: recommendedDifficulty,
      quality_warning: qualityWarning,
    };
  }

  /**
   * Format RAG exam for display
   */
  static formatRAGExamForDisplay(ragExam: RAGExamResponse): any {
    return {
      id: ragExam.exam_id,
      topic: ragExam.topic,
      questions: ragExam.questions.map((q, index) => ({
        id: index + 1,
        question: q.question_text,
        type: q.question_type,
        options: q.options || [],
        correct_answer: q.correct_answer,
        explanation: Array.isArray(q.explanation) ? q.explanation.join('\n') : q.explanation,
        difficulty: q.difficulty,
        sources: q.source_documents,
        confidence: q.confidence_score,
      })),
      metadata: {
        generation_time: ragExam.generation_time,
        quality_metrics: ragExam.quality_metrics,
        context_summary: ragExam.context_summary,
        source_documents: ragExam.context_summary.source_documents,
      },
    };
  }

  /**
   * Export RAG exam results
   */
  static exportRAGExam(ragExam: RAGExamResponse, format: 'json' | 'txt' = 'json'): string {
    if (format === 'json') {
      return JSON.stringify(ragExam, null, 2);
    }

    // Text format
    let output = `RAG-Prüfung: ${ragExam.topic}\n`;
    output += `Generiert am: ${new Date().toLocaleString('de-DE')}\n`;
    output += `Exam ID: ${ragExam.exam_id}\n`;
    output += `Generierungszeit: ${ragExam.generation_time.toFixed(2)}s\n\n`;

    output += `Quelldokumente:\n`;
    ragExam.context_summary.source_documents.forEach(doc => {
      output += `- ${doc.filename} (${doc.chunks_used} Abschnitte)\n`;
    });
    output += '\n';

    output += `Qualitätsmetriken:\n`;
    output += `- Durchschnittliche Konfidenz: ${ragExam.quality_metrics.average_confidence.toFixed(2)}\n`;
    output += `- Quellenabdeckung: ${ragExam.quality_metrics.source_coverage.toFixed(2)}\n`;
    output += `- Verwendete Textabschnitte: ${ragExam.quality_metrics.context_chunks_used}\n\n`;

    ragExam.questions.forEach((question, index) => {
      output += `Frage ${index + 1} (${question.question_type}, ${question.difficulty}):\n`;
      output += `${question.question_text}\n`;
      
      if (question.options) {
        question.options.forEach(option => {
          output += `${option}\n`;
        });
      }
      
      output += `Antwort: ${question.correct_answer}\n`;
      if (question.explanation) {
        output += `Erklärung: ${Array.isArray(question.explanation) ? question.explanation.join(' ') : question.explanation}\n`;
      }
      output += `Konfidenz: ${question.confidence_score.toFixed(2)}\n`;
      output += `Quellen: ${question.source_documents.join(', ')}\n\n`;
    });

    return output;
  }
}
