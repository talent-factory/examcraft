# Esportazione voti

!!! warning "Tutte le review devono essere completate"
    L'esportazione dei voti è bloccata finché sono presenti submission con stato `pending_review` o `partially_reviewed`. Completare prima tutte le review nella [scheda Review](review-grading.md).

L'esportazione voti genera un elenco voti definitivo in tre formati: come CSV per Excel, come CSV per reimportazione in Moodle o come PDF pronto per la stampa. Route: scheda **Esportazione voti** in `/auswertungen/:examId/submissions`.

## Modello di valutazione

### Schemi predefiniti

ExamCraft AI contiene otto schemi di valutazione predefiniti:

| Schema | Intervallo | Nota |
|--------|-----------|------|
| Svizzero 1.0–6.0 | 1.0 (insufficiente) – 6.0 (ottimo) | Scala di valutazione svizzera standard |
| Tedesco 1.0–5.0 | 1.0 (ottimo) – 5.0 (insufficiente) | Scala invertita |
| Austriaco 1–5 | 1 (ottimo) – 5 (non sufficiente) | Intero |
| Francese 0–20 | 0–20 punti | Sistema francese |
| Olandese 1–10 | 1–10 | Sistema olandese |
| ECTS A–F | A–F + FX | Sistema europeo di trasferimento |
| Percentuale | 0–100 % | Visualizzazione percentuale diretta |
| Superato/Non superato | Superato / Non superato | Binario |

### Schemi personalizzati

Le istituzioni con tier Enterprise possono definire schemi personalizzati in `/admin/grading-schemes` e impostarli come standard istituzionale. Ulteriori dettagli: [Schemi di valutazione (Guida amministratore)](../admin-guide/grading-schemes.md).

## Scegliere il formato di esportazione

![Esportazione voti — Selezione formato](../screenshots/notenexport/notenexport-format-selection.png)

| Formato | Utilizzo |
|---------|---------|
| **CSV (Excel)** | UTF-8 con BOM, separato da punto e virgola — si apre direttamente in Excel (DE) |
| **Moodle Reimport CSV** | Formato compatibile con Moodle per reimportare i voti |
| **PDF** | Elenco voti pronto per la stampa con intestazione istituzionale, tabella e footer per la firma |

## Eseguire l'esportazione voti

1. Selezionare lo **Schema di valutazione** nel menu a tendina (predefinito: standard istituzionale)
2. Selezionare il **Formato di esportazione**
3. Le prime 5 righe appaiono come **Anteprima** — verificare nomi e voti
4. Fare clic su **Esporta** — il download inizia immediatamente

## Blocco in caso di review in sospeso

![Esportazione voti bloccata — Banner](../screenshots/notenexport/notenexport-blocked.png)

Finché ci sono review in sospeso, viene visualizzato un banner di avviso giallo con il numero di casi aperti e un link diretto alla [coda di review](review-grading.md). Il pulsante Esporta è disattivato finché tutte le submission non hanno raggiunto lo stato `fully_reviewed`.

## Contenuto del PDF

![Esportazione voti — Esempio PDF](../screenshots/notenexport/notenexport-pdf-preview.png)

Il PDF contiene:
- **Intestazione**: Nome dell'istituzione, titolo dell'esame, data
- **Tabella voti**: Tutti gli studenti con punti, percentuale e voto
- **Footer per la firma**: Spazio per il docente e la direzione dell'esame

## Passi successivi

- [:octicons-arrow-right-24: Gestisci classi](klassen.md)
- [:octicons-arrow-right-24: Integrazione Moodle](moodle-integration.md)
- [:octicons-arrow-right-24: Quote di abbonamento](subscription.md)
