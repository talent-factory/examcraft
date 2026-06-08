# Review e valutazione

!!! note "Solo per domande aperte"
    Le domande a scelta multipla e Vero/Falso vengono valutate in modo deterministico — nessuna review necessaria. Questa sezione riguarda esclusivamente le domande aperte con proposte dell'IA.

La coda di review mostra tutte le proposte di valutazione dell'IA per le domande aperte, ordinate per confidenza in modo crescente — i casi più incerti prima. Route: scheda **Review** in `/auswertungen/:examId/submissions`.

![Coda di review — Panoramica](../screenshots/review-grading/review-queue-overview.png)

## Come funziona la valutazione dell'IA

Per ogni domanda aperta, l'IA analizza la risposta in confronto alla soluzione modello e assegna punti (da 0 al massimo), una confidenza (0–100 %) e un elenco di aspetti soddisfatti e mancanti. Una confidenza dello 0 % indica che la valutazione dell'IA non è riuscita — il caso deve essere valutato manualmente.

## Filtri

| Filtro | Opzioni |
|--------|---------|
| Domanda | Solo le submission per una determinata domanda |
| Studenti | Solo le submission di una determinata persona |
| Confidenza | Intervallo da–a, ad es. 0–50 % per i casi incerti |

![Coda di revisione — Filtri](../screenshots/review-grading/review-queue-filter.png)

## Scheda di valutazione

![Review — Scheda singola](../screenshots/review-grading/review-queue-card.png)

Ogni scheda mostra:

| Elemento | Descrizione |
|----------|-------------|
| Domanda | Testo della domanda |
| Soluzione modello | Risposta attesa |
| Risposta fornita | Ciò che il candidato ha risposto |
| Proposta dell'IA | Punti + badge di confidenza (verde ≥ 80 %, giallo 50–79 %, rosso < 50 %) |
| Aspetti corrispondenti | Aspetti soddisfatti della soluzione modello (chip verdi) |
| Aspetti mancanti | Aspetti mancanti (chip rossi) |

### Azioni per scheda

| Azione | Comportamento |
|--------|---------------|
| **Accetta** | La proposta dell'IA viene salvata come valutazione finale |
| **Modifica** | Si apre l'editor inline — inserire punti e nota opzionale |
| **Apri nel contesto** | Apre la submission completa nel drawer |

![Override — Editor inline](../screenshots/review-grading/review-queue-override.png)

## Approvazione in blocco

![Approva in blocco — Finestra di dialogo](../screenshots/review-grading/review-queue-bulk.png)

Fare clic su **Accetta tutti** oppure selezionare più schede tramite casella di controllo e utilizzare **Accetta selezione**. Nella finestra di dialogo è possibile impostare una soglia di confidenza — vengono accettate solo le proposte pari o superiori a questo valore; i casi incerti rimangono per la revisione manuale.

## Override manuale per MC e Vero/Falso

Anche le risposte a scelta multipla e Vero/Falso valutate automaticamente possono essere sovrascritte. Aprire il drawer di dettaglio della submission e fare clic su **Override** per la domanda desiderata. Inserire il nuovo punteggio e una motivazione opzionale.

## Audit trail

Ogni modifica di valutazione — accettazione, modifica, override — viene registrata con timestamp e utente. I log sono accessibili agli amministratori nei log del backend.

## Passi successivi

- [:octicons-arrow-right-24: Torna all'elenco submission](auswertungen.md)
- [:octicons-arrow-right-24: Visualizza statistiche](statistik.md)
- [:octicons-arrow-right-24: Esporta voti](notenexport.md)
