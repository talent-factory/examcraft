# Exam Composer

Exam Composer consente di assemblare domande approvate in un esame completo e di esportarlo in vari formati.

!!! note "Prerequisito"
    In Exam Composer sono disponibili solo domande approvate nella [Review Queue](review-queue.md). Generare prima domande e revisionarle prima di assemblare un esame.

## Creazione nuovo esame

### Passaggio 1: Apertura di Exam Composer

Fate clic su **Exam Composer** nella navigazione o selezionate il riquadro corrispondente sul [Dashboard](dashboard.md). Rotta: `/exams/compose`.

### Passaggio 2: Avvio nuovo esame

Fate clic su **Crea nuovo esame** e compilate i seguenti campi:

| Campo | Descrizione |
|-------|-------------|
| Titolo | Denominazione dell'esame (ad es. "Algoritmi — Esame semestrale 2026") |
| Descrizione | Informazioni supplementari facoltative sull'esame |
| Data | Data prevista dell'esame |

Il titolo è l'elemento chiave che identifica univocamente l'esame. Scegliete una denominazione significativa che indichi chiaramente la materia, il corso e la classificazione temporale. La descrizione fornisce contesto aggiuntivo per voi e i vostri colleghi — ad esempio informazioni sul livello di difficoltà, il gruppo target o i focus specifici.

### Passaggio 3: Selezione domande

Selezionate domande dall'elenco delle domande approvate:

- Cliccate su **+ Aggiungi** accanto a ogni domanda desiderata
- Utilizzate i filtri per trovare selettivamente domande per **tipo**, **difficoltà** o **documento di origine**
- Il numero totale di domande selezionate è visualizzato sopra

!!! tip "Assemblare un esame equilibrato"
    Prestate attenzione a un mix equilibrato: diversi tipi di domanda (Scelta multipla e domande aperte), diversi livelli di difficoltà e possibilmente diversi argomenti. Un esame equilibrato promuove una valutazione equa e una comprensione autentica dei contenuti.

Le funzioni di filtraggio vi aiutano a trovare efficientemente le domande appropriate. Utilizzate sistematicamente le opzioni di filtro: iniziate con il tipo di domanda desiderato (ad es. solo domande a scelta multipla per test veloci o un mix di MC e domande aperte per esami più completi). Successivamente filtrate per difficoltà per ottenere una distribuzione equilibrata. Infine, potete filtrare selettivamente per documenti di origine se desiderate testare prioritariamente capitoli o aree tematiche specifiche.

### Passaggio 4: Ordinamento delle domande

Ordinate le domande selezionate tramite Drag & Drop nella sequenza desiderata. Le domande vengono numerate automaticamente. Considerate se iniziare con domande più semplici per introdurre gli esaminandi all'argomento, o se preferite iniziare deliberatamente con domande più difficili. L'ordinamento può anche essere significativo dal punto di vista tematico — raggruppate le domande correlate per consentire agli esaminandi di comprendere i collegamenti.

### Passaggio 5: Esportazione esame

Fate clic su **Esporta** e scegliete il formato desiderato:

| Formato | Descrizione |
|---------|-------------|
| Markdown (.md) | Formato testuale, ideale per ulteriori modifiche o pubblicazione. Le soluzioni possono essere incluse facoltativamente. |
| JSON (.json) | Formato leggibile da macchina per ulteriore elaborazione, integrazione con sistemi esterni o analisi dati |
| Moodle XML (.xml) | Formato direttamente importabile nel sistema di gestione dell'apprendimento Moodle |

!!! tip "Includere le soluzioni"
    Nell'esportazione in formato Markdown, è possibile includere facoltativamente le soluzioni. Attivate la casella **Includi soluzioni** nella finestra di dialogo di esportazione — pratico per creare fogli di risposta o per la revisione interna.

Il formato Markdown è adatto per ulteriori modifiche o l'integrazione in sistemi di documentazione. Il formato JSON è ideale per l'integrazione tecnica — ad esempio se desiderate importare dati d'esame in un sistema personalizzato o eseguire valutazioni automatizzate. Il formato Moodle XML consente l'importazione diretta in Moodle senza elaborazione manuale successiva.

## Gestione esami esistenti

Tutti gli esami creati appaiono nell'elenco di panoramica. Lì potete:

- **Aprire**: Modificare e integrare esame
- **Duplicare**: Utilizzare come base per un nuovo esame simile
- **Esportare**: Esportare nuovamente in qualsiasi formato
- **Eliminare**: Rimuovere esame (non reversibile)

L'elenco di panoramica mostra metadati importanti come data di creazione, numero di domande e timestamp dell'ultima modifica. Utilizzate la funzione di duplicazione per creare rapidamente esami simili — ad es. per diverse classi dello stesso anno scolastico o per un esame di recupero. Questa funzione risparmia tempo nell'assemblaggio di esami simili e minimizza gli errori.

!!! warning "Esami eliminati"
    L'eliminazione di un esame rimuove solo l'assemblaggio esame, non le singole domande. Le domande rimangono nella Review Queue e possono essere riutilizzate per esami futuri.

## Passaggi successivi

- [:octicons-arrow-right-24: Genera più domande](exam-create.md)
- [:octicons-arrow-right-24: Esame RAG da documenti](rag-exam.md)
- [:octicons-arrow-right-24: Review Queue — Rivedi domande](review-queue.md)
- [:octicons-arrow-right-24: Migliori pratiche](best-practices.md)
