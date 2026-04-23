# Migliori pratiche

## Caricamento documenti

### Preparazione ottimale

1. Strutturate i documenti con intestazioni chiare
2. Utilizzate formattazione coerente
3. Aggiungete metadati (titolo, autore, data)
4. Evitate filigrane e immagini di sfondo

### Caricamento in batch

Caricate documenti correlati insieme (ad es. tutti i capitoli di un manuale). Questo facilita i successivi esami RAG.

## Creazione domande

### Formulazione argomento

- Specifico anziché generale
- Fornire contesto
- Tenere a mente il livello Bloom

!!! example "Esempi"
    **Bene:**

    - "Python liste – Metodi append(), extend(), insert()"
    - "Algoritmi – Complessità temporale dei metodi di ordinamento"

    **Male:**

    - "Python" (troppo ampio)
    - "Programmazione" (troppo generale)

### Controllo qualità

- Verificate sempre le domande generate
- Prestate attenzione ai punteggi di confidenza
- Adattate il livello di difficoltà
- Utilizzate riferimenti alle fonti per la verifica

## Esami RAG

- Selezionate 3–5 documenti rilevanti (ottimale)
- Fornite un focus specifico
- Troppi documenti portano a qualità inferiore

## Utilizzo ChatBot

Iniziate con domande di panoramica e approfondite gradualmente:

```text
Utente: "Che cos'è Heapsort?"
Bot: [Spiega Heapsort]

Utente: "Come differisce da Quicksort?"
Bot: [Confronta entrambi gli algoritmi]

Utente: "Quale è più efficiente per grandi quantità di dati?"
Bot: [Analizza complessità]
```

## Utilizzo efficace della Review Queue

- Revisionate le domande tempestivamente dopo la generazione — il contesto è più fresco
- Utilizzate le opzioni di filtro (Stato, Difficoltà, Tipo domanda) per mantenere la Queue ordinata
- **Rifiutare è meglio che consentire domande scadenti**: Qualità prima della quantità
- Se molte domande vengono rifiutate: adattate il Prompt, migliorate il documento di origine o precisate l'argomento
- Approvate solo domande che fareste voi stessi

## Exam Composer

- Pianificate la struttura dell'esame prima di selezionare le domande: Quante domande? Quali tipi? Quale distribuzione di difficoltà?
- Mescolate tipi di domanda (Scelta multipla + domande aperte) per esami vari
- Esportate una versione di prova e leggetela completamente prima di creare la versione finale
- Verificate la numerazione automatica e la formattazione nel documento esportato
