# Document-Upload & RAG-Integration - Technische Spezifikation 📄

## Übersicht

Implementierung eines Document-Upload-Systems mit Docling-Verarbeitung und lokaler Vektor-Datenbank für RAG-basierte Fragenerstellung aus hochgeladenen Dokumenten.

## 🎯 Ziele

- **Dokumentenbasierte Fragenerstellung**: Fragen ausschließlich aus hochgeladenen Dokumenten generieren
- **Multi-Format-Support**: PDF, DOC, DOCX, TXT, MD Unterstützung
- **Intelligente Verarbeitung**: Docling für strukturierte Dokumentenanalyse
- **Lokale Vektor-Suche**: ChromaDB für schnelle Similarity-Search
- **Benutzerfreundliches Interface**: Drag & Drop Upload mit Fortschrittsanzeige

## 🏗️ Architektur

### Backend-Komponenten

```text
ExamCraft/
├── backend/
│   ├── services/
│   │   ├── document_service.py      # Document Upload & Management
│   │   ├── docling_service.py       # Docling Integration
│   │   ├── vector_service.py        # ChromaDB Integration
│   │   └── rag_service.py           # RAG-basierte Fragenerstellung
│   ├── models/
│   │   ├── document.py              # Document SQLAlchemy Model
│   │   └── document_chunk.py        # Chunk Model für Vektor-DB
│   ├── api/
│   │   └── documents.py             # Document API Endpoints
│   └── storage/
│       ├── uploads/                 # Hochgeladene Dateien
│       └── vector_db/               # ChromaDB Persistierung
```

### Frontend-Komponenten

```text
frontend/src/
├── components/
│   ├── DocumentUpload.tsx           # Drag & Drop Upload
│   ├── DocumentManager.tsx          # Dokumentenverwaltung
│   ├── DocumentPreview.tsx          # Dokument-Vorschau
│   └── RAGExamCreator.tsx           # RAG-basierte Prüfungserstellung
├── services/
│   └── DocumentService.ts           # API Client für Dokumente
└── types/
    └── document.ts                  # TypeScript Interfaces
```

## 🔧 Technische Implementation

### 1. Backend Dependencies

```python
# Neue Requirements für backend/requirements.txt
docling==1.0.0                      # IBM Docling für Dokumentenverarbeitung
chromadb==0.4.18                    # Lokale Vektor-Datenbank
sentence-transformers==2.2.2        # Embedding-Modelle
python-multipart==0.0.6             # File Upload Support
aiofiles==23.2.1                    # Async File Operations
pypdf==3.17.1                       # PDF Fallback Processing
python-docx==1.1.0                  # DOCX Processing
python-magic==0.4.27                # File Type Detection
```

### 2. Document Service

```python
# backend/services/document_service.py
from typing import List, Optional
import aiofiles
import os
from fastapi import UploadFile
from sqlalchemy.orm import Session
from models.document import Document

class DocumentService:
    def __init__(self, upload_dir: str = "storage/uploads"):
        self.upload_dir = upload_dir
        os.makedirs(upload_dir, exist_ok=True)
    
    async def upload_document(
        self, 
        file: UploadFile, 
        user_id: str,
        db: Session
    ) -> Document:
        """Upload und speichere Dokument"""
        # File validation
        if not self._is_supported_format(file.filename):
            raise ValueError("Unsupported file format")
        
        # Save file
        file_path = await self._save_file(file)
        
        # Create database entry
        document = Document(
            filename=file.filename,
            file_path=file_path,
            file_size=file.size,
            mime_type=file.content_type,
            user_id=user_id,
            status="uploaded"
        )
        
        db.add(document)
        db.commit()
        
        return document
    
    def _is_supported_format(self, filename: str) -> bool:
        """Prüfe unterstützte Dateiformate"""
        supported = {'.pdf', '.doc', '.docx', '.txt', '.md'}
        return any(filename.lower().endswith(ext) for ext in supported)
```

### 3. Docling Integration

```python
# backend/services/docling_service.py
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from typing import List, Dict

class DoclingService:
    def __init__(self):
        self.converter = DocumentConverter()
    
    async def process_document(self, file_path: str) -> Dict:
        """Verarbeite Dokument mit Docling"""
        try:
            # Convert document
            result = self.converter.convert(file_path)
            
            # Extract structured content
            content = {
                "text": result.document.export_to_markdown(),
                "metadata": {
                    "title": result.document.name,
                    "pages": len(result.document.pages),
                    "tables": len(result.document.tables),
                    "figures": len(result.document.figures)
                },
                "chunks": self._create_chunks(result.document.export_to_markdown())
            }
            
            return content
            
        except Exception as e:
            raise ProcessingError(f"Docling processing failed: {str(e)}")
    
    def _create_chunks(self, text: str, chunk_size: int = 1000) -> List[Dict]:
        """Erstelle semantische Text-Chunks"""
        # Implementierung für intelligente Chunking-Strategie
        # Berücksichtigung von Absätzen, Überschriften, etc.
        pass
```

### 4. Vector Database Service

```python
# backend/services/vector_service.py
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict

class VectorService:
    def __init__(self, persist_directory: str = "storage/vector_db"):
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
    def create_collection(self, collection_name: str):
        """Erstelle Collection für Dokument"""
        return self.client.create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
    
    def add_document_chunks(
        self, 
        collection_name: str, 
        chunks: List[Dict],
        document_id: str
    ):
        """Füge Document Chunks zur Vektor-DB hinzu"""
        collection = self.client.get_collection(collection_name)
        
        texts = [chunk['text'] for chunk in chunks]
        embeddings = self.embedding_model.encode(texts).tolist()
        
        collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=[{
                "document_id": document_id,
                "chunk_index": i,
                **chunk.get('metadata', {})
            } for i, chunk in enumerate(chunks)],
            ids=[f"{document_id}_chunk_{i}" for i in range(len(chunks))]
        )
    
    def search_similar_content(
        self, 
        collection_name: str, 
        query: str, 
        n_results: int = 5
    ) -> List[Dict]:
        """Suche ähnliche Inhalte für RAG"""
        collection = self.client.get_collection(collection_name)
        query_embedding = self.embedding_model.encode([query]).tolist()
        
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=n_results,
            include=['documents', 'metadatas', 'distances']
        )
        
        return results
```

### 5. RAG-basierte Fragenerstellung

```python
# backend/services/rag_service.py
from services.vector_service import VectorService
from services.claude_service import ClaudeService
from typing import List, Dict

class RAGService:
    def __init__(self):
        self.vector_service = VectorService()
        self.claude_service = ClaudeService()
    
    async def generate_questions_from_documents(
        self,
        topic: str,
        document_ids: List[str],
        question_count: int = 5,
        difficulty: str = "medium"
    ) -> Dict:
        """Generiere Fragen basierend auf Dokumenteninhalten"""
        
        # 1. Suche relevante Inhalte
        relevant_content = []
        for doc_id in document_ids:
            content = self.vector_service.search_similar_content(
                collection_name=f"doc_{doc_id}",
                query=topic,
                n_results=3
            )
            relevant_content.extend(content['documents'])
        
        # 2. Erstelle Kontext für Claude
        context = "\n\n".join(relevant_content)
        
        # 3. Generiere Fragen mit RAG-Prompt
        rag_prompt = f"""
        Basierend auf den folgenden Dokumenteninhalten, erstelle {question_count} 
        Prüfungsfragen zum Thema "{topic}" mit Schwierigkeitsgrad "{difficulty}".
        
        WICHTIG: Verwende AUSSCHLIESSLICH Informationen aus den bereitgestellten 
        Dokumenten. Erfinde keine zusätzlichen Fakten.
        
        Dokumenteninhalte:
        {context}
        
        Erstelle eine Mischung aus Multiple-Choice und offenen Fragen.
        """
        
        questions = await self.claude_service.generate_questions_with_context(
            prompt=rag_prompt,
            context=context
        )
        
        return {
            "questions": questions,
            "source_documents": document_ids,
            "context_used": len(relevant_content)
        }
```

### 6. API Endpoints

```python
# backend/api/documents.py
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from services.document_service import DocumentService
from services.docling_service import DoclingService
from services.vector_service import VectorService

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user)
):
    """Upload und verarbeite Dokument"""
    try:
        # 1. Upload Document
        document = await document_service.upload_document(file, user_id, db)
        
        # 2. Process with Docling
        content = await docling_service.process_document(document.file_path)
        
        # 3. Store in Vector DB
        vector_service.add_document_chunks(
            collection_name=f"doc_{document.id}",
            chunks=content['chunks'],
            document_id=str(document.id)
        )
        
        # 4. Update document status
        document.status = "processed"
        document.metadata = content['metadata']
        db.commit()
        
        return {"document_id": document.id, "status": "processed"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-exam")
async def generate_exam_from_documents(
    request: RAGExamRequest,
    user_id: str = Depends(get_current_user)
):
    """Generiere Prüfung basierend auf Dokumenten"""
    result = await rag_service.generate_questions_from_documents(
        topic=request.topic,
        document_ids=request.document_ids,
        question_count=request.question_count,
        difficulty=request.difficulty
    )
    
    return result
```

### 7. Frontend Components

```typescript
// frontend/src/components/DocumentUpload.tsx
import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { DocumentService } from '../services/DocumentService';

interface DocumentUploadProps {
  onUploadComplete: (documentId: string) => void;
}

export const DocumentUpload: React.FC<DocumentUploadProps> = ({ onUploadComplete }) => {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    setUploading(true);
    
    for (const file of acceptedFiles) {
      try {
        const result = await DocumentService.uploadDocument(file, (progress) => {
          setProgress(progress);
        });
        
        onUploadComplete(result.document_id);
      } catch (error) {
        console.error('Upload failed:', error);
      }
    }
    
    setUploading(false);
    setProgress(0);
  }, [onUploadComplete]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
      'text/markdown': ['.md']
    }
  });

  return (
    <Box
      {...getRootProps()}
      sx={{
        border: '2px dashed #ccc',
        borderRadius: 2,
        p: 4,
        textAlign: 'center',
        cursor: 'pointer',
        bgcolor: isDragActive ? 'action.hover' : 'background.paper'
      }}
    >
      <input {...getInputProps()} />
      {uploading ? (
        <CircularProgress variant="determinate" value={progress} />
      ) : (
        <Typography>
          {isDragActive
            ? 'Dateien hier ablegen...'
            : 'Dokumente hier hinziehen oder klicken zum Auswählen'
          }
        </Typography>
      )}
    </Box>
  );
};
```

## 📋 Implementierungsplan

### Phase 1: Grundlagen (Woche 1-2)

- [ ] Backend Dependencies installieren
- [ ] Document Service implementieren
- [ ] File Upload API erstellen
- [ ] Frontend Upload-Komponente

### Phase 2: Docling Integration (Woche 3)

- [ ] Docling Service implementieren
- [ ] Document Processing Pipeline
- [ ] Error Handling für verschiedene Formate

### Phase 3: Vector Database (Woche 4)

- [ ] ChromaDB Setup
- [ ] Embedding-Pipeline
- [ ] Chunk-Strategien optimieren

### Phase 4: RAG Implementation (Woche 5)

- [ ] RAG Service entwickeln
- [ ] Context-basierte Prompts
- [ ] Quality Assurance für generierte Fragen

### Phase 5: UI/UX (Woche 6)

- [ ] Document Management Interface
- [ ] RAG-basierte Exam Creator
- [ ] Progress Tracking und Feedback

## 🎯 Erfolgs-Metriken

- **Upload Success Rate**: > 95%
- **Processing Time**: < 30s pro Dokument
- **Question Quality**: Basierend auf Dokumenteninhalten
- **User Experience**: Intuitive Drag & Drop Interface
- **Storage Efficiency**: Optimierte Chunk-Größen

## 🔒 Sicherheitsaspekte

- **File Validation**: Strenge Format-Prüfung
- **Virus Scanning**: Integration geplant
- **Access Control**: Benutzer-spezifische Dokumente
- **Data Privacy**: Lokale Speicherung, keine Cloud-Upload

---

**Dieses Feature wird ExamCraft AI zu einem mächtigen Tool für dokumentenbasierte Prüfungserstellung machen!** 🚀
