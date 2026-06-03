# Integrazione Moodle

!!! note "Prerequisito per l'importazione via API"
    Per l'importazione via API, un amministratore deve prima configurare una connessione Moodle in `/admin/integrations/moodle`. L'importazione CSV funziona senza questo prerequisito su tutti i tier. Dettagli: [Configurare Moodle (Guida amministratore)](../admin-guide/moodle.md).

I risultati degli esami possono essere importati in due modi: come file CSV (tutti i tier) o direttamente tramite l'API Web Service di Moodle (Professional ed Enterprise). L'importazione via API recupera i dati con un clic — senza esportazione manuale da Moodle.

## Importazione CSV vs. importazione API

| Caratteristica | Importazione CSV | Importazione API |
|----------------|-----------------|-----------------|
| Disponibilità | Tutti i tier | Professional / Enterprise |
| Configurazione | Nessuna | L'amministratore configura la connessione una volta |
| Attualità | Snapshot al momento dell'esportazione | Stato attuale da Moodle |
| Mappatura domande | Mappatura manuale delle colonne | Automatica tramite ID domande Moodle |

## Eseguire l'importazione via API

![Importazione API — Selezione fonte](../screenshots/moodle/moodle-import-api.png)

1. Aprire **Importa risultati** per l'esame desiderato
2. Selezionare **Moodle API** come fonte
3. Scegliere il corso Moodle e il quiz dall'elenco
4. Fare clic su **Recupera risultati**

L'associazione tra le domande Moodle e le domande ExamCraft avviene automaticamente tramite gli ID domande Moodle memorizzati. Se non sono stati memorizzati ID, si apre la finestra di mappatura manuale delle colonne.

## Memorizzare gli ID domande Moodle (ciclo completo Question-ID)

Per attivare l'associazione automatica durante l'importazione via API, gli ID domande Moodle devono essere inseriti una volta in ExamCraft:

![Sincronizza ID Moodle](../screenshots/moodle/moodle-sync-question-ids.png)

1. Aprire l'esame nel [Compositore d'esame](exam-composer.md)
2. Fare clic su **Sincronizza ID Moodle**
3. La finestra di dialogo mostra le domande ExamCraft affiancate alle corrispondenti domande Moodle
4. Confermare l'associazione — gli ID vengono salvati in modo permanente

Dopo questo passaggio, l'importazione via API funziona in modo completamente automatico senza mappatura manuale — anche dopo ulteriori esportazioni da Moodle.

## Limiti di quota

| Tier | Metodo di importazione | Esami/mese | Submission max. |
|------|----------------------|-----------|----------------|
| Free | Solo CSV | 3 | 30 |
| Starter | Solo CSV | Illimitati | 50 |
| Professional | CSV + API | Illimitati | Illimitati |
| Enterprise | CSV + API + Bulk | Illimitati | Illimitati |

## Passi successivi

- [:octicons-arrow-right-24: Amministratore: configurare connessione Moodle](../admin-guide/moodle.md)
- [:octicons-arrow-right-24: Valutazioni](auswertungen.md)
- [:octicons-arrow-right-24: Classi e studenti](klassen.md)
- [:octicons-arrow-right-24: Quote di abbonamento](subscription.md)
