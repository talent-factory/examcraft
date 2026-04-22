# ChatBot Documento

Il ChatBot consente conversazioni interattive con i vostri documenti caricati.

!!! warning "Funzione Premium"
    Il Chat Documento è disponibile da **abbonamento Starter** e richiede
    il permesso `document_chatbot`. Con l'abbonamento Free questa funzione non è accessibile.
    Vedere [Abbonamento](subscription.md).

## Selezione documento

1. Fate clic su **ChatBot Documento** nella navigazione
2. Selezionate un documento dal menu a discesa
3. Il ChatBot carica il contesto (2–5 secondi)

## Avvio chat

Ponete domande al vostro documento:

- "Spiegami l'algoritmo Heapsort"
- "Quali sono le differenze tra Quicksort e Mergesort?"
- "Riassumi il Capitolo 3"

!!! tip "Suggerimenti per buone domande"
    - Formulate in modo specifico e chiaro
    - Riferimento al contenuto del documento
    - Utilizzate domande di follow-up per una comprensione più profonda

## Comprensione delle risposte

Ogni risposta contiene:

- **Testo principale** – Risposta generata dall'IA
- **Fonti** – Passaggi di testo rilevanti dal documento
- **Confidenza** – Affidabilità (0–1)

| Confidenza | Significato |
|---|---|
| > 0.8 | Molto affidabile |
| 0.6–0.8 | Affidabile |
| < 0.6 | Utilizzare con cautela |

## Cronologia chat

- Tutti i messaggi vengono salvati all'interno della sessione
- Il contesto rimane preservato (Multi-Turn)
- Selezionate un altro documento per iniziare una nuova conversazione

## Limitazioni

- **Solo documenti caricati** come fonte di conoscenza — nessun accesso a Internet
- **Nessun accesso** ai contenuti non caricati come documento
- **Limitato alla sessione** — la cronologia conversazioni non viene conservata tra le sessioni
- Iniziate una nuova conversazione selezionando un altro documento

## Prompt di esempio

Formulate le vostre domande con precisione per ottenere risposte migliori:

| Invece di... | Meglio... |
|---|---|
| "Spiega il documento" | "Riassumi il Capitolo 3 su algoritmi di ordinamento in tre punti" |
| "Che cosa c'è scritto?" | "Secondo questo documento, quali sono le differenze tra Quicksort e Mergesort?" |
| "Come funziona?" | "Spiega l'algoritmo Heapsort passo dopo passo in base al documento" |

!!! tip "Utilizzare domande di follow-up"
    La chat comprende il contesto della conversazione. Utilizzate domande di follow-up come
    "Spiega in modo più dettagliato" o "Dammi un esempio".

## Passaggi successivi

- [:octicons-arrow-right-24: Gestire documenti](documents.md)
- [:octicons-arrow-right-24: Generare domande da documenti](rag-exam.md)
- [:octicons-arrow-right-24: Gestire abbonamento](subscription.md)
