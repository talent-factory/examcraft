# Caricamento e gestione documenti

## Formati file supportati

| Formato | Estensione | Max. Dimensione | Particolarità |
|---------|-----------|-----------------|---------------|
| PDF | `.pdf` | 50 MB | Tabelle, formule, immagini |
| Word | `.doc`, `.docx` | 25 MB | Formattazione mantenuta |
| Markdown | `.md` | 10 MB | Blocchi di codice, LaTeX |
| Testo | `.txt` | 5 MB | Plain Text |

## Caricamento documenti

### 1. Apertura della scheda "Carica documenti"

Fate clic sulla scheda **Carica documenti** nella navigazione.

### 2. Selezione file

Avete due opzioni:

- **Drag & Drop**: Trascinatei file nell'area di caricamento
- **Browser file**: Fate clic su **Seleziona file**

### 3. Monitoraggio del progresso di caricamento

Durante il caricamento vedete:

- Nome e dimensione del file
- Barra di avanzamento (0–100%)
- Stato: "In elaborazione..." poi "Elaborato"

### 4. Attesa elaborazione

Dopo il caricamento i documenti vengono automaticamente:

1. Estratto il testo
2. Diviso in chunk semantici
3. Indicizzato nel database vettoriale
4. Preparato per la ricerca RAG

| Tipo documento | Tempo di elaborazione tipico |
|---|---|
| PDF (10 pagine) | ~30 secondi |
| Word (20 pagine) | ~45 secondi |
| Markdown (5 pagine) | ~15 secondi |

!!! tip "Migliori pratiche per i caricamenti"
    - Utilizzate nomi di file chiari (ad es. `Algoritmi_Capitolo_3.pdf`)
    - I documenti strutturati con intestazioni generano risultati migliori
    - Caricate documenti correlati insieme in batch

!!! warning "Evitare"
    - PDF acquisiti senza OCR
    - File protetti da password
    - File più grandi di 50 MB
    - Duplicati

## Libreria documenti

La libreria documenti mostra tutti i documenti caricati in un elenco ordinato con nome file, data di caricamento, dimensione file, numero di pagine e stato di elaborazione.

### Ricerca documenti

Inserite parole chiave nel campo di ricerca. I risultati vengono filtrati in tempo reale (nome file, tag, contenuto).

**Filtri:**

- Tutti i formati
- Solo PDF
- Solo Word
- Solo Markdown

### Selezione documenti per esami

1. Attivate le caselle di controllo accanto ai documenti desiderati
2. Fate clic su **Crea esame da selezione**
3. Verrete reindirizzati al creator esame RAG

### Eliminazione documenti

1. Fate clic sull'icona Elimina
2. Confermate la richiesta di sicurezza
3. Il documento viene rimosso dalla libreria e dal database vettoriale

!!! warning "Attenzione"
    I documenti eliminati non possono essere ripristinati.

## Passaggi successivi

Dopo il caricamento potete iniziare immediatamente la generazione di domande:

- **[Generare domande da documenti (RAG)](rag-exam.md)**: Utilizzate i vostri documenti
  come fonte di conoscenza per domande d'esame basate su IA.
- **[Revisionare domande (Review Queue)](review-queue.md)**: Verificate e approvate
  le domande generate prima del loro utilizzo.
- **[Chat Documento](chatbot.md)**: Ponete domande dirette ai vostri documenti
  (Funzione Premium).
