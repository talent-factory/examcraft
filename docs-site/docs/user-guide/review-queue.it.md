# Review Queue

La Review Queue è il luogo centrale per la revisione manuale e l'approvazione di domande generate dall'IA. Solo dopo l'approvazione nella Review Queue le domande sono disponibili in [Exam Composer](exam-composer.md).

!!! note "Perché una Review Queue?"
    Le domande generate dall'IA sono un punto di partenza, non un prodotto finale. La Review Queue
    vi dà il controllo sulla qualità dei vostri esami — voi decidete quali domande sono abbastanza buone.

<!-- screenshot: review-queue-overview.png -->

## Panoramica dello stato

Ogni domanda ha uno di quattro stati possibili:

| Stato | Colore | Significato |
|-------|--------|-------------|
| In sospeso | Arancione | Generata di recente, non ancora revisionata |
| In revisione | Blu | Attualmente in fase di revisione |
| Approvata | Verde | Rilasciata per Exam Composer |
| Rifiutata | Rosso | Non utilizzabile, archiviata |

## Filtraggio e ricerca domande

Utilizzate le opzioni di filtro per mantenere la Queue ordinata:

- **Stato**: In sospeso / In revisione / Approvata / Rifiutata
- **Difficoltà**: Facile / Medio / Difficile
- **Tipo domanda**: Scelta multipla / Domanda aperta
- **Periodo**: Filtra per data di generazione

## Revisione domanda — Passo per passo

### Passaggio 1: Apertura domanda

Fate clic su una domanda con stato "In sospeso" nella vista elenco.
La domanda passa automaticamente allo stato "In revisione".

<!-- screenshot: review-queue-detail.png -->

### Passaggio 2: Controllo contenuto

Nella vista dettagli vedete:

| Campo | Descrizione |
|-------|-------------|
| Testo domanda | La vera domanda d'esame |
| Tipo domanda | Scelta multipla o domanda aperta |
| Difficoltà | Facile / Medio / Difficile |
| Opzioni risposta | Per scelta multipla: tutte le opzioni inclusa la risposta corretta |
| Spiegazione | Giustificazione della risposta corretta |
| Citazione fonte | Passaggio di testo dal documento di origine |
| Valore affidabilità | Stima della confidenza IA (0–1) |

Verificate in particolare:
- Il testo della domanda è chiaro e univoco?
- La risposta corretta è effettivamente corretta?
- La spiegazione è comprensibile e didattica?
- La fonte indicata corrisponde al contenuto della domanda?

### Passaggio 3: Decisione

**Approva domanda**: Fate clic su **Approva**. La domanda passa a "Approvata"
ed è immediatamente disponibile in Exam Composer.

**Rifiuta domanda**: Fate clic su **Rifiuta**. La domanda viene archiviata e non può
più essere utilizzata. Facoltativamente potete inserire un motivo del rifiuto.

!!! tip "Quando rifiutare?"
    Rifiutate le domande quando: il testo è poco chiaro o ambiguo, la risposta corretta è sbagliata,
    la domanda non corrisponde all'argomento, o più opzioni di risposta potrebbero essere corrette.

## Vista dettagli di singole domande

Ogni domanda ha un proprio URL: `/questions/review/:id`

Potete condividere questo URL per attirare l'attenzione dei colleghi su una domanda specifica.

## Passaggi successivi

Le domande approvate sono immediatamente disponibili in [Exam Composer](exam-composer.md).
Da lì potete assemblare un esame completo ed esportarlo.

- [:octicons-arrow-right-24: Assembla esame](exam-composer.md)
- [:octicons-arrow-right-24: Genera più domande](exam-create.md)
- [:octicons-arrow-right-24: Migliori pratiche](best-practices.md)
