# RAG-Based Exams

!!! note "Prerequisite"
    For RAG exams, documents must be uploaded and processed first.
    See [Manage Documents](documents.md).

## What is RAG?

**RAG** (Retrieval-Augmented Generation) combines:

- **Retrieval**: Semantic search within your documents
- **Generation**: AI-based question creation

The advantage: questions are derived directly from your course materials and include source references.

## Prerequisites

- At least 1 document uploaded and processed
- Document selected in the library

## Step-by-Step

### 1. Select Documents

In the document library:

1. Select 1–10 documents
2. Click **Create Exam from Selection**

!!! tip "Optimal Number of Documents"
    3–5 documents provide the best quality. Too many documents can dilute results.

### 2. RAG Configuration

- **Topic/Focus**: Specific focus (e.g., "Sorting Algorithms Complexity"). Leave empty for general questions.
- **Number of Questions**: 1–20, recommended 5–10
- **Question Types**: Multiple Choice, Open-ended, True/False
- **Difficulty Level**: Easy / Medium / Hard
- **Prompt Template**: Select a prompt template with live preview

### 3. Start Generation

Click **Generate RAG Exam**. Wait time: 20–60 seconds.

### 4. Review Results

Each question contains:

- Question text and answer options
- Correct answer with explanation
- **Source documents** (with page number)
- **Confidence Score** (0–1)

## Quality Indicators

| Confidence Score | Assessment |
|-----------------|-----------|
| 0.9–1.0 | Very high quality |
| 0.7–0.9 | Good quality |
| 0.5–0.7 | Acceptable – Review |
| < 0.5 | Revision recommended |

## After Generation

The generated questions automatically appear in the **[Review Queue](review-queue.md)**.
Review and approve each question there before assembling it into an exam in the
**[Exam Composer](exam-composer.md)**.

!!! tip "Quality of RAG Questions"
    The quality of generated questions depends heavily on the quality of the source documents.
    Well-structured documents with clear headings provide better results.
    See [Best Practices](best-practices.md).

## Frequently Asked Questions about RAG Exams

**What is the difference between Confidence Score and Quality?**

The Confidence Score (0–1) indicates how certain the AI is that the question and answer are correctly derived from the documents. A high score (0.9+) means high relevance and accuracy. Questions with low scores (< 0.5) should be revised or rejected in the Review Queue.

**Which document types work best?**

PDF and Markdown files with clear structure work best:
- PDFs with searchable text (not scans)
- Documents with headings and subheadings
- Structured text content instead of unformatted prose
- Avoid very long paragraphs without structure

**Can AI invent content that is not in the documents?**

It is rare, but possible. A generated question could be logically sound but not appear exactly in the source documents. This is the main reason why review and source verification are important. Check the specified source documents and page numbers with each review.

**How many documents should I select?**

**Optimal: 3–5 documents.** Too few documents (1–2) may result in insufficient context. Too many documents (10+) can lead to diluted or less accurate questions. Experiment and observe the Confidence Scores.

**Can I use RAG with images in documents?**

Currently, RAG is primarily optimized for text content. Images are not used as a source. If your documents consist mainly of diagrams or images, use AI exams (without RAG) instead and describe the topic in the input.

**How do I update documents for better RAG results?**

1. Upload a new version of the document
2. Select the new version in the document library
3. The next RAG generation automatically uses the new version
4. Earlier versions can be deleted (see [Manage Documents](documents.md))

## Optimal Document Structure for RAG

For best RAG results, documents should have the following structure:

```
# Main Topic

## Section 1
Explanatory text with clear concepts and definitions.

### Subsection 1.1
Further details on the topic.

## Section 2
Further related content.

- Bullet points for summaries
- Numbered lists for processes
```

Avoid unstructured text walls. Good documentation with clear headings significantly improves RAG quality.
