# Document Processing mit PyMuPDF

## Übersicht

ExamCraft AI verwendet **PyMuPDF** (fitz) für schnelle und effiziente Dokumentenverarbeitung. PyMuPDF ist **10x schneller** als IBM Docling und benötigt deutlich weniger Ressourcen.

## Features

### PyMuPDF Processor (Standard)

**Features:**

- ✅ **Sehr schnelle** PDF-Verarbeitung mit fitz
- ✅ Layout-bewusste Text-Extraktion
- ✅ Erweiterte Metadaten-Extraktion (Autor, Titel, Creation Date)
- ✅ Heading-Erkennung mit Heuristik
- ✅ Multi-Format-Support (PDF, DOCX, TXT, Markdown)
- ✅ Semantic Chunking mit Überlappung
- ✅ Minimaler Memory-Footprint (~10-20 MB pro Dokument)

**Performance:**

- **Small Documents (< 1000 words):** < 0.5s
- **Medium Documents (1000-5000 words):** < 1s
- **Large Documents (> 5000 words):** < 2s

**Unterstützte Formate:**

- PDF (mit erweiterten Metadaten)
- DOCX (mit python-docx)
- Text-Dateien
- Markdown

### Legacy Processor (Fallback)

**Standard-Features:**

- ✅ PDF-Verarbeitung mit pypdf
- ✅ DOCX-Verarbeitung mit python-docx
- ✅ Markdown-Support
- ✅ Text-Dateien
- ✅ Word-based Chunking mit Überlappung

### Docling Processor (Deprecated)

**⚠️ DEPRECATED:** IBM Docling ist aufgrund von Performance-Problemen deprecated.

**Warum PyMuPDF statt Docling?**

- **10x schneller** - PyMuPDF verarbeitet Dokumente in Millisekunden statt Sekunden
- **Geringerer Memory-Verbrauch** - 10-20 MB vs. 50-100 MB pro Dokument
- **Keine ML-Models** - Keine Model-Downloads erforderlich
- **Einfacher** - Weniger Dependencies, einfacheres Setup
- **Zuverlässiger** - Keine Breaking Changes in der API

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
# PyMuPDF verwenden (Standard, empfohlen)
DOCUMENT_PROCESSOR_TYPE=pymupdf

# Legacy Processor verwenden
DOCUMENT_PROCESSOR_TYPE=legacy

# Docling verwenden (deprecated, nicht empfohlen)
DOCUMENT_PROCESSOR_TYPE=docling

# Auto-Detection (Standard: PyMuPDF → Docling → Legacy)
DOCUMENT_PROCESSOR_TYPE=auto
```

**Auto-Detection Logik:**

1. Versucht PyMuPDF zu laden (Standard)
2. Fällt auf Docling zurück wenn PyMuPDF nicht verfügbar
3. Fällt auf Legacy zurück wenn beides nicht verfügbar
4. Loggt Warnung bei Fallback

## Installation

### PyMuPDF Dependencies (Empfohlen)

```bash
# Fast PDF processing
pip install PyMuPDF==1.24.14
```

### Legacy Dependencies

```bash
pip install pypdf==3.17.1
pip install python-docx==1.1.2
pip install markdown==3.5.1
```

### Docling Dependencies (Optional, Deprecated)

```bash
# Nicht empfohlen - nur für Legacy-Kompatibilität
pip install docling==2.23.0
pip install docling-core==2.48.4
pip install docling-ibm-models==3.9.1
```

## Konfiguration

### Docker Environment

In `docker-compose.yml`:

```yaml
services:
  backend:
    environment:
      - DOCUMENT_PROCESSOR_TYPE=pymupdf  # Standard
```

### Lokale Entwicklung

In `.env`:

```bash
DOCUMENT_PROCESSOR_TYPE=pymupdf
```

## Verwendung

### Basic Usage

```python
from services.docling_service import DoclingService

service = DoclingService()

# Verarbeite Dokument (verwendet automatisch PyMuPDF)
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

### Advanced Usage - PyMuPDF Features

```python
from services.document_processors.pymupdf_processor import PyMuPDFProcessor

processor = PyMuPDFProcessor(
    chunk_size=1000,
    chunk_overlap=200
)

result = await processor.process_document(
    document_id=1,
    file_path="document.pdf",
    filename="document.pdf",
    mime_type="application/pdf"
)

# Zugriff auf Metadaten
print(f"Title: {result.metadata.get('title')}")
print(f"Author: {result.metadata.get('author')}")
print(f"Creation Date: {result.metadata.get('creation_date')}")
print(f"Pages: {result.metadata.get('pages')}")
print(f"Sections: {result.metadata.get('sections')}")
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
    page_number: Optional[int]
    metadata: Dict[str, Any]
```

### Metadata Structure

**PyMuPDF Processor:**

```json
{
  "title": "Document Title",
  "author": "Author Name",
  "creation_date": "2024-01-15",
  "pages": 10,
  "sections": ["Introduction", "Methodology", "Results"],
  "section_count": 3,
  "processing_method": "pymupdf",
  "processor_type": "PyMuPDF"
}
```

**Legacy Processor:**

```json
{
  "title": "Document Title",
  "author": "Author Name",
  "pages": 10,
  "processing_method": "legacy",
  "processor_type": "pypdf/python-docx"
}
```

## Performance

### Benchmarks (PyMuPDF vs Docling)

**Small Documents (< 1000 words):**

- PyMuPDF: **< 0.5s** ✅
- Docling: ~2s ❌ (4x langsamer)

**Medium Documents (1000-5000 words):**

- PyMuPDF: **< 1s** ✅
- Docling: ~5s ❌ (5x langsamer)

**Large Documents (> 5000 words):**

- PyMuPDF: **< 2s** ✅
- Docling: ~10s ❌ (5x langsamer)

### Memory Usage

- PyMuPDF: **~10-20 MB** per document ✅
- Docling: ~50-100 MB per document ❌ (5x mehr Memory)

## Testing

### Unit Tests

```bash
# PyMuPDF Processor Tests
pytest packages/core/backend/tests/test_pymupdf_processor.py

# Legacy Processor Tests
pytest packages/core/backend/tests/test_legacy_processor.py

# Factory Tests
pytest packages/core/backend/tests/test_processor_factory.py

# Performance Tests
pytest packages/core/backend/tests/test_processor_performance.py
```

### Integration Tests

```bash
# End-to-End Document Processing
pytest packages/core/backend/tests/test_document_service.py
```

## Troubleshooting

### PyMuPDF Import Errors

**Problem:** `cannot import name 'fitz'`

**Lösung:** PyMuPDF installieren:

```bash
pip install PyMuPDF==1.24.14
```

### Dependency Conflicts

**Problem:** `PyMuPDF version conflict`

**Lösung:** Spezifische Version installieren:

```bash
pip install PyMuPDF==1.24.14
```

### Memory Issues

**Problem:** Out of Memory bei sehr großen Dokumenten

**Lösungen:**

1. Reduziere Chunk-Größe: `chunk_size=500`
2. Verarbeite Dokumente sequentiell statt parallel
3. Verwende Legacy Processor als Fallback

## Migration Guide

### Von Docling zu PyMuPDF (Empfohlen)

1. **Installiere PyMuPDF:**

   ```bash
   pip install PyMuPDF==1.24.14
   ```

2. **Setze Environment Variable:**

   ```bash
   export DOCUMENT_PROCESSOR_TYPE=pymupdf
   ```

3. **Restart Services:**

   ```bash
   docker-compose restart backend
   ```

4. **Verifiziere Logs:**

   ```bash
   docker-compose logs backend | grep "PyMuPDFProcessor"
   ```

   Expected: `Using PyMuPDFProcessor (fast PDF processing)`

5. **Performance vergleichen:**

   ```bash
   pytest packages/core/backend/tests/test_processor_performance.py
   ```

### Von Legacy zu PyMuPDF

1. **Installiere PyMuPDF** (siehe oben)

2. **Teste mit Sample-Dokumenten:**

   ```bash
   pytest packages/core/backend/tests/test_pymupdf_processor.py
   ```

3. **Switch zu PyMuPDF:**

   ```bash
   export DOCUMENT_PROCESSOR_TYPE=pymupdf
   docker-compose restart backend
   ```

## Best Practices

### Processor-Auswahl

- **PyMuPDF verwenden für (Empfohlen):**
  - Alle PDF-Dokumente
  - Schnelle Verarbeitung
  - Produktionsumgebungen
  - Ressourcen-limitierte Umgebungen

- **Legacy verwenden für:**
  - Einfache Text-Dokumente
  - Wenn PyMuPDF nicht verfügbar ist

- **Docling vermeiden:**
  - Zu langsam für Produktionsumgebungen
  - Hoher Memory-Verbrauch
  - Komplexe Dependencies

### Chunking-Strategie

- **Word-based Chunking:**
  - Feste Wortanzahl mit Überlappung
  - Vorhersagbare Chunk-Größen
  - Optimal für RAG-Systeme

- **Empfohlene Werte:**
  - `chunk_size=1000` (Standard)
  - `chunk_overlap=200` (20% Überlappung)

### Error Handling

```python
try:
    result = await document_processor.process_document(...)
except ImportError as e:
    # PyMuPDF nicht verfügbar
    logger.warning(f"Falling back to legacy processor: {e}")
    # Automatischer Fallback durch Factory
except Exception as e:
    # Processing-Fehler
    logger.error(f"Document processing failed: {e}")
    raise
```

## Roadmap

### Geplante Features

- [ ] **Table Extraction** - Tabellen-Erkennung mit PyMuPDF
- [ ] **Image Extraction** - Bilder extrahieren und verarbeiten
- [ ] **Layout Analysis** - Erweiterte Layout-Erkennung
- [ ] **Custom Chunking Strategies** - Konfigurierbare Chunking-Algorithmen
- [ ] **Batch Processing** - Parallele Verarbeitung mehrerer Dokumente
- [ ] **Caching** - Caching von verarbeiteten Dokumenten

## Support

Bei Fragen oder Problemen:

- GitHub Issues: <https://gitlab.com/talent-factory/software/examcraft/-/issues>
- Linear: TF-152
