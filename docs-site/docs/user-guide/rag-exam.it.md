# Esami basati su RAG

!!! note "Prerequisito"
    Per gli esami RAG i documenti devono prima essere caricati e elaborati.
    Vedere [Gestire documenti](documents.md).

## Che cos'è RAG?

**RAG** (Retrieval-Augmented Generation) combina:

- **Retrieval**: Ricerca semantica nei vostri documenti
- **Generation**: Creazione di domande basata su IA

Il vantaggio: le domande sono direttamente derivate dai vostri materiali didattici e includono riferimenti alle fonti.

## Prerequisiti

- Almeno 1 documento caricato e elaborato
- Documento selezionato nella libreria

## Passo per passo

### 1. Selezione documenti

Nella libreria documenti:

1. Selezionate 1–10 documenti
2. Fate clic su **Crea esame da selezione**

!!! tip "Numero ottimale di documenti"
    3–5 documenti forniscono la migliore qualità. Troppi documenti possono diluire i risultati.

### 2. Configurazione RAG

- **Argomento/Focus**: Focus specifico (ad es. "Complessità algoritmi di ordinamento"). Lasciate vuoto per domande generali.
- **Numero domande**: 1–20, consigliato 5–10
- **Tipi di domanda**: Scelta multipla, Domande aperte, Vero/Falso
- **Livello difficoltà**: Facile / Medio / Difficile
- **Modello Prompt**: Selezionate un template Prompt con anteprima dal vivo

### 3. Avvio generazione

Fate clic su **Genera esame RAG**. Tempo di attesa: 20–60 secondi.

### 4. Controllo risultato

Ogni domanda contiene:

- Testo e opzioni di risposta
- Risposta corretta con spiegazione
- **Documenti di origine** (con numero di pagina)
- **Punteggio di confidenza** (0–1)

## Indicatori di qualità

| Punteggio confidenza | Valutazione |
|---|---|
| 0.9–1.0 | Qualità molto alta |
| 0.7–0.9 | Buona qualità |
| 0.5–0.7 | Accettabile – Revisionare |
| < 0.5 | Rielaborazione consigliata |

## Dopo la generazione

Le domande generate appaiono automaticamente nella **[Review Queue](review-queue.md)**.
Revisionate e approvate ogni domanda prima di utilizzarla in
**[Exam Composer](exam-composer.md)** per assemblare un esame completo.

!!! tip "Qualità delle domande RAG"
    La qualità delle domande generate dipende fortemente dalla qualità dei documenti di origine.
    I documenti ben strutturati con intestazioni chiare generano risultati migliori.
    Vedere [Migliori pratiche](best-practices.md).

## Domande frequenti su esami RAG

**Quale differenza c'è tra Punteggio di confidenza e qualità?**

Il Punteggio di confidenza (0–1) mostra quanto l'IA sia sicura che la domanda e la risposta siano correttamente derivate dai documenti. Un punteggio alto (0.9+) significa alta rilevanza e precisione. Le domande con punteggio basso (< 0.5) dovrebbero essere rielaborate o rifiutate nella Review Queue.

**Quali tipi di documento funzionano meglio?**

Funzionano meglio i PDF e i file Markdown con struttura chiara:
- PDF con testo ricercabile (non scansioni)
- Documenti con intestazioni e sottointestazioni
- Contenuti di testo strutturati anziché paragrafi lunghi senza formattazione
- Evitate paragrafi molto lunghi senza divisione

**L'IA può inventare contenuti che non sono nei documenti?**

È raro ma possibile. Una domanda generata potrebbe essere logica ma non comparire esattamente nei documenti di origine. Questo è il motivo principale per cui la revisione e la verifica delle fonti sono importanti. Verificate per ogni revisione i documenti di origine indicati e i numeri di pagina.

**Quanti documenti dovrei selezionare?**

**Ottimale: 3–5 documenti.** Troppi pochi documenti (1–2) potrebbero fornire informazioni di contesto insufficienti. Troppi documenti (10+) possono portare a domande diluite o meno precise. Sperimentate e osservate i Punteggi di confidenza.

**Posso usare RAG con immagini nei documenti?**

Attualmente RAG è principalmente ottimizzato per contenuti testuali. Le immagini non vengono utilizzate come fonte. Se i vostri documenti contengono principalmente diagrammi o immagini, utilizzate invece esami IA (senza RAG) e descrivete l'argomento nell'input.

**Come aggiorno i documenti per risultati RAG migliori?**

1. Caricate una nuova versione del documento
2. Selezionate la nuova versione nella libreria documenti
3. La prossima generazione RAG utilizza automaticamente la nuova versione
4. Le versioni precedenti possono essere eliminate (vedere [Gestire documenti](documents.md))

## Struttura documento ottimale per RAG

Per i migliori risultati con RAG i documenti dovrebbero avere la seguente struttura:

```
# Argomento principale

## Sezione 1
Testo esplicativo con concetti e definizioni chiari.

### Sottosezione 1.1
Ulteriori dettagli sull'argomento.

## Sezione 2
Ulteriori contenuti correlati.

- Punti elenco per riassunti
- Elenchi numerati per processi
```

Evitate testi non strutturati. Una buona documentazione con intestazioni chiare migliora significativamente la qualità RAG.
