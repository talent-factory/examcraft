# Upload and Manage Documents

## Supported File Formats

| Format | Extension | Max. Size | Notes |
|--------|-----------|-----------|-------|
| PDF | `.pdf` | 50 MB | Tables, formulas, images |
| Word | `.doc`, `.docx` | 25 MB | Formatting preserved |
| Markdown | `.md` | 10 MB | Code blocks, LaTeX |
| Text | `.txt` | 5 MB | Plain text |

## Uploading Documents

### 1. Open the "Upload Documents" Tab

Click the **Upload Documents** tab in the navigation.

### 2. Select Files

You have two options:

- **Drag & Drop**: Drag files into the upload area
- **File Browser**: Click **Choose Files**

### 3. Monitor Upload Progress

During upload you will see:

- File name and size
- Progress bar (0--100%)
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
    - Use clear file names (e.g., `Algorithms_Chapter_3.pdf`)
    - Structured documents with headings produce better results
    - Upload related documents in batches

!!! warning "Avoid"
    - Scanned PDFs without OCR
    - Password-protected files
    - Files larger than 50 MB
    - Duplicates

## Document Library

The document library shows all uploaded documents in a clear list with file name, upload date, file size, page count, and processing status.

### Searching Documents

Enter search terms in the search field. Results are filtered in real-time (file name, tags, content).

**Filters:**

- All formats
- PDF only
- Word only
- Markdown only

### Selecting Documents for Exams

1. Check the boxes next to the desired documents
2. Click **Create Exam from Selection**
3. You will be redirected to the RAG exam creator

### Deleting Documents

1. Click the delete icon
2. Confirm the safety prompt
3. Document is removed from library and vector database

!!! warning "Caution"
    Deleted documents cannot be recovered.
