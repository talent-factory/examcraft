# IBM Docling Integration

## Übersicht

ExamCraft AI verwendet IBM Docling für erweiterte Dokumentenverarbeitung mit automatischem Fallback auf Legacy-Prozessoren.

## Features

### IBM Docling Processor

**Erweiterte Features:**
- ✅ Advanced PDF-Layout-Erkennung
- ✅ Tabellen-Extraktion mit Strukturerhaltung
- ✅ Multi-Format-Support (PDF, DOCX, PPTX, XLSX, Images)
- ✅ OCR für gescannte Dokumente
- ✅ Semantic Chunking basierend auf Dokumentstruktur
- ✅ Erweiterte Metadaten-Extraktion (Sektionen, Tabellen, Bilder)

**Unterstützte Formate:**
- PDF (mit Layout-Erkennung)
- DOCX, PPTX, XLSX
- Images (mit OCR)
- Markdown

### Legacy Processor (Fallback)

**Standard-Features:**
- ✅ PDF-Verarbeitung mit PyPDF
- ✅ DOCX-Verarbeitung mit python-docx
- ✅ Markdown-Support
- ✅ Text-Dateien
- ✅ Word-based Chunking mit Überlappung

## Architektur

### Factory Pattern

```python
from services.document_processors.processor_factory import document_processor

# Automatische Auswahl basierend auf Environment Variable
result = await document_processor.process_document(
    document_id=1,
    file_path="document.pdf",
    filename="document.pdf",
    mime_type="application/pdf"
)
```

### Processor-Auswahl

Die Processor-Auswahl erfolgt über die Environment Variable `DOCUMENT_PROCESSOR_TYPE`:

```bash
# Docling verwenden (Standard, wenn verfügbar)
DOCUMENT_PROCESSOR_TYPE=docling

# Legacy Processor verwenden
DOCUMENT_PROCESSOR_TYPE=legacy

# Auto-Detection (Standard)
DOCUMENT_PROCESSOR_TYPE=auto
```

**Auto-Detection Logik:**
1. Versucht Docling zu laden
2. Fällt auf Legacy zurück wenn Docling nicht verfügbar
3. Loggt Warnung bei Fallback

## Installation

### Docling Dependencies

```bash
# Für erweiterte Features
pip install docling==2.23.0
pip install docling-core==2.48.4
pip install docling-ibm-models==3.9.1
```

### Legacy Dependencies (immer installiert)

```bash
pip install pypdf==3.17.1
pip install python-docx==1.1.2
pip install markdown==3.5.1
```

## Konfiguration

### Docker Environment

In `docker-compose.yml`:

```yaml
services:
  backend:
    environment:
      - DOCUMENT_PROCESSOR_TYPE=auto  # oder 'docling', 'legacy'
```

### Lokale Entwicklung

In `.env`:

```bash
DOCUMENT_PROCESSOR_TYPE=auto
```

## Verwendung

### Basic Usage

```python
from services.docling_service import DoclingService

service = DoclingService()

# Verarbeite Dokument (verwendet automatisch konfigurierten Processor)
result = await service.process_document(
    document_id=1,
    file_path="path/to/document.pdf",
    filename="document.pdf",
    mime_type="application/pdf"
)

print(f"Chunks: {result.total_chunks}")
print(f"Processing Time: {result.processing_time}s")
print(f"Metadata: {result.metadata}")
```

### Advanced Usage - Docling Features

```python
from services.document_processors.docling_processor import DoclingProcessor

processor = DoclingProcessor(
    chunk_size=1000,
    chunk_overlap=200
)

result = await processor.process_document(
    document_id=1,
    file_path="document.pdf",
    filename="document.pdf",
    mime_type="application/pdf"
)

# Zugriff auf erweiterte Metadaten
print(f"Title: {result.metadata.get('title')}")
print(f"Sections: {result.metadata.get('sections')}")
print(f"Tables: {result.metadata.get('table_count')}")
print(f"Images: {result.metadata.get('image_count')}")

# Zugriff auf extrahierte Tabellen
for table in result.metadata.get('tables', []):
    print(f"Table Markdown:\n{table['markdown']}")
```

### Legacy Processor Usage

```python
from services.document_processors.legacy_processor import LegacyProcessor

processor = LegacyProcessor(
    chunk_size=1000,
    chunk_overlap=200
)

result = await processor.process_document(
    document_id=1,
    file_path="document.pdf",
    filename="document.pdf",
    mime_type="application/pdf"
)
```

## Output Format

### ProcessedDocument

```python
@dataclass
class ProcessedDocument:
    document_id: int
    filename: str
    mime_type: str
    total_pages: Optional[int]
    total_chunks: int
    chunks: List[DocumentChunk]
    metadata: Dict[str, Any]
    processing_time: float
```

### DocumentChunk

```python
@dataclass
class DocumentChunk:
    content: str
    chunk_index: int
    metadata: Dict[str, Any]
```

### Metadata Structure

**Docling Processor:**
```json
{
  "title": "Document Title",
  "sections": ["Section 1", "Section 2"],
  "table_count": 3,
  "image_count": 5,
  "tables": [
    {
      "markdown": "| Header | Value |\n|--------|-------|\n| A | 1 |"
    }
  ]
}
```

**Legacy Processor:**
```json
{
  "pages": 10,
  "title": "Document Title",
  "author": "Author Name"
}
```

## Performance

### Benchmarks

**Small Documents (< 1000 words):**
- Legacy: < 1s
- Docling: < 2s

**Medium Documents (1000-5000 words):**
- Legacy: < 2s
- Docling: < 5s

**Large Documents (> 5000 words):**
- Legacy: < 5s
- Docling: < 10s

### Memory Usage

- Legacy: ~10-20 MB per document
- Docling: ~50-100 MB per document (wegen ML-Modellen)

## Testing

### Unit Tests

```bash
# Alle Processor Tests
pytest backend/tests/test_docling_processor.py
pytest backend/tests/test_legacy_processor.py
pytest backend/tests/test_processor_factory.py

# Performance Tests
pytest backend/tests/test_processor_performance.py
```

### Integration Tests

```bash
# End-to-End Document Processing
pytest backend/tests/test_document_service.py
```

## Troubleshooting

### Docling Import Errors

**Problem:** `cannot import name 'TableFormatMode'`

**Lösung:** Docling-core API hat sich geändert. Der Code enthält Fallback-Imports:

```python
try:
    from docling_core.types.doc import TableFormatMode
except ImportError:
    from docling_core.types.doc.table import TableFormatMode
```

### Dependency Conflicts

**Problem:** `python-docx version conflict`

**Lösung:** Docling benötigt `python-docx>=1.1.2`:

```bash
pip install python-docx==1.1.2
```

### Memory Issues

**Problem:** Out of Memory bei großen Dokumenten

**Lösungen:**
1. Verwende Legacy Processor: `DOCUMENT_PROCESSOR_TYPE=legacy`
2. Reduziere Chunk-Größe
3. Verarbeite Dokumente sequentiell statt parallel

## Migration Guide

### Von Legacy zu Docling

1. **Installiere Docling Dependencies:**
   ```bash
   pip install docling docling-core docling-ibm-models
   ```

2. **Setze Environment Variable:**
   ```bash
   export DOCUMENT_PROCESSOR_TYPE=docling
   ```

3. **Teste mit Sample-Dokumenten:**
   ```bash
   pytest backend/tests/test_docling_processor.py
   ```

4. **Vergleiche Ergebnisse:**
   ```bash
   pytest backend/tests/test_processor_performance.py
   ```

### Von Docling zu Legacy (Rollback)

1. **Setze Environment Variable:**
   ```bash
   export DOCUMENT_PROCESSOR_TYPE=legacy
   ```

2. **Restart Services:**
   ```bash
   docker-compose restart backend
   ```

## Best Practices

### Processor-Auswahl

- **Docling verwenden für:**
  - Dokumente mit komplexen Layouts
  - Tabellen-Extraktion
  - Gescannte PDFs (OCR)
  - Multi-Format-Support

- **Legacy verwenden für:**
  - Einfache Text-Dokumente
  - Ressourcen-limitierte Umgebungen
  - Schnelle Verarbeitung ohne erweiterte Features

### Chunking-Strategie

- **Semantic Chunking (Docling):**
  - Basiert auf Dokumentstruktur (Sections)
  - Bessere Kontext-Erhaltung
  - Ideal für RAG-Systeme

- **Word-based Chunking (Legacy):**
  - Feste Wortanzahl mit Überlappung
  - Vorhersagbare Chunk-Größen
  - Schneller

### Error Handling

```python
try:
    result = await document_processor.process_document(...)
except ImportError as e:
    # Docling nicht verfügbar
    logger.warning(f"Falling back to legacy processor: {e}")
    # Automatischer Fallback durch Factory
except Exception as e:
    # Processing-Fehler
    logger.error(f"Document processing failed: {e}")
    raise
```

## Roadmap

### Geplante Features

- [ ] **Table Extractor Analyzer** - Erweiterte Tabellen-Analyse
- [ ] **Layout Analyzer** - Detaillierte Layout-Informationen
- [ ] **Metadata Enricher** - Automatische Metadaten-Anreicherung
- [ ] **Custom Chunking Strategies** - Konfigurierbare Chunking-Algorithmen
- [ ] **Batch Processing** - Parallele Verarbeitung mehrerer Dokumente
- [ ] **Caching** - Caching von verarbeiteten Dokumenten

## Support

Bei Fragen oder Problemen:
- GitHub Issues: https://gitlab.com/talent-factory/software/examcraft/-/issues
- Linear: TF-110

