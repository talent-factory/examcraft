# Upload and Manage Documents

## Supported File Formats

| Format | Extension | Max. Size | Special Features |
|--------|-----------|-----------|-----------------|
| PDF | `.pdf` | 50 MB | Tables, formulas, images |
| Word | `.doc`, `.docx` | 25 MB | Formatting preserved |
| Markdown | `.md` | 10 MB | Code blocks, LaTeX |
| Text | `.txt` | 5 MB | Plain text |

## Upload Documents

### 1. Open "Upload Documents" Tab

Click the **Upload Documents** tab in the navigation.

### 2. Select Files

You have two options:

- **Drag & Drop**: Drag files into the upload area
- **File Browser**: Click **Select Files**

### 3. Monitor Upload Progress

During upload you will see:

- Filename and size
- Progress bar (0–100%)
- Status: "Processing..." then "Processed"

### 4. Wait for Processing

After upload, documents are automatically:

1. Text extracted
2. Split into semantic chunks
3. Indexed in the vector database
4. Prepared for RAG search

| Document Type | Typical Processing Time |
|--------------|------------------------|
| PDF (10 pages) | ~30 seconds |
| Word (20 pages) | ~45 seconds |
| Markdown (5 pages) | ~15 seconds |

!!! tip "Best Practices for Uploads"
    - Use clear filenames (e.g., `Algorithms_Chapter_3.pdf`)
    - Structured documents with headings provide better results
    - Upload related documents in batch

!!! warning "Avoid"
    - Scanned PDFs without OCR
    - Password-protected files
    - Files larger than 50 MB
    - Duplicates

## Document Library

The document library displays all uploaded documents in a clear list with filename, upload date, file size, page count, and processing status.

### Search Documents

Enter search terms in the search field. Results are filtered in real-time (filename, tags, content).

**Filters:**

- All formats
- PDF only
- Word only
- Markdown only

### Select Documents for Exams

1. Check the boxes next to the desired documents
2. Click **Create Exam from Selection**
3. You will be redirected to the RAG Exam Creator

### Delete Documents

1. Click the delete icon
2. Confirm the security prompt
3. Document is removed from library and vector database

!!! warning "Attention"
    Deleted documents cannot be recovered.

## Next Steps

After uploading, you can start generating questions directly:

- **[Generate Questions from Documents (RAG)](rag-exam.md)**: Use your documents
  as a knowledge source for AI-powered exam questions.
- **[Review Questions (Review Queue)](review-queue.md)**: Check and approve
  generated questions before they are used in exams.
- **[Document Chat](chatbot.md)**: Ask direct questions to your documents
  (Premium feature).
