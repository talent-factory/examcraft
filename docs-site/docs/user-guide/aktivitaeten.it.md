# Attività

!!! note "Tutte le attività a colpo d'occhio"
    La pagina Attività mostra tutti gli eventi dell'istituzione in ordine cronologico — con paginazione, chip di filtro e un'opzione per alternare tra le proprie attività e tutte le attività.

Route: `/aktivitaeten`

## Panoramica attività

![Attività — Panoramica](../screenshots/aktivitaeten/aktivitaeten-overview.png)

La pagina elenca tutte le attività con timestamp, tipo, descrizione e utente che ha eseguito l'azione. Per impostazione predefinita, sono visibili solo le proprie attività.

### Opzione: Proprie / Tutte

Con l'interruttore **Proprie / Tutte** in alto a destra si alterna tra:

| Modalità | Attività visibili |
|----------|------------------|
| **Proprie** | Solo le proprie azioni (predefinito) |
| **Tutte** | Tutte le attività dell'istituzione (richiede l'autorizzazione appropriata) |

Il widget del dashboard mostra sempre solo le proprie attività — la pagina Attività è l'unico posto per la vista a livello istituzionale.

## Chip di filtro

![Attività — Filtri](../screenshots/aktivitaeten/aktivitaeten-filter.png)

Sette chip di filtro limitano la visualizzazione per tipo di attività:

| Filtro | Eventi inclusi |
|--------|---------------|
| **Documenti** | Caricamento, elaborazione, eliminazione di documenti |
| **Esami** | Creazione, modifica, archiviazione di esami |
| **Domande** | Generazione, review, modifiche alle domande |
| **Valutazioni** | Importazione CSV, valutazione LLM, completamento review |
| **Esportazione** | Esportazione voti (CSV, Moodle-CSV, PDF) |
| **Classi** | Creazione classi, assegnazione membri |
| **Utenti** | Login, logout, modifiche al profilo |

È possibile attivare più filtri contemporaneamente. Un clic su un chip attivo lo disattiva.

## Paginazione

L'elenco attività è suddiviso in pagine. Selezionare la dimensione della pagina tramite il menu a tendina in basso a destra:

- **25** voci per pagina (predefinito)
- **50** voci per pagina
- **100** voci per pagina

Con le frecce avanti/indietro si naviga tra le pagine.

## Stato vuoto

Se nessuna attività corrisponde ai filtri attivi, viene visualizzato uno stato vuoto con un avviso sui filtri attivi e un pulsante **Reimposta filtri**.

## Cosa conta come attività?

Le attività vengono registrate lato server — ogni azione che modifica dati o consuma una risorsa importante genera un'entry. Le operazioni di sola lettura (ad es. aprire un documento, visualizzare un esame) non compaiono nell'elenco.

## Nota sulla privacy

Nella modalità **Proprie** si vedono esclusivamente le proprie attività. La modalità **Tutte** mostra nomi e azioni di tutti gli utenti dell'istituzione — utilizzare questa vista in modo responsabile.

## Passi successivi

- [:octicons-arrow-right-24: Dashboard](dashboard.md)
- [:octicons-arrow-right-24: Valutazioni](auswertungen.md)
- [:octicons-arrow-right-24: Quote di abbonamento](subscription.md)
