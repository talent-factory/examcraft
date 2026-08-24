# Ruoli e autorizzazioni

ExamCraft AI utilizza un sistema di autorizzazioni basato sui ruoli (RBAC). Ogni utente riceve un ruolo che determina quali funzioni può utilizzare.

Navigate a `/admin` e selezionate la scheda **Ruoli** per visualizzare le assegnazioni dei ruoli della vostra istituzione.

![Admin Ruoli e autorizzazioni](../screenshots/admin/admin-roles.png)

## Ruoli disponibili

ExamCraft AI prevede due ruoli:

| Ruolo | Descrizione |
|-------|-------------|
| **DOCENTE** | Ruolo standard per gli insegnanti — accesso a tutte le funzioni didattiche |
| **ADMIN** | Ruolo esteso per gli amministratori dell'istituzione — accesso aggiuntivo al pannello admin |

## Panoramica delle autorizzazioni

| Funzione | DOCENTE | ADMIN |
|----------|:-------:|:-----:|
| Caricamento e gestione documenti | ✓ | ✓ |
| Generazione esami IA | ✓ | ✓ |
| Generazione esami RAG | ✓ | ✓ |
| Utilizzo Review Queue | ✓ | ✓ |
| Utilizzo Exam Composer | ✓ | ✓ |
| Utilizzo libreria Prompt | ✓ | ✓ |
| Modifica profilo personale | ✓ | ✓ |
| **Gestione utenti** | — | ✓ |
| **Gestione istituzioni** | — | ✓ |
| **Visualizzazione panoramica utilizzo** | — | ✓ |
| **Assegnazione ruoli** | — | ✓ |
| **Gestione abbonamento e quote** | — | ✓ |
| Visualizzazione valutazioni (`submissions:read`) | ✓ | ✓ |
| Importazione submissions (`submissions:import`) | ✓ | ✓ |
| Valutazione submissions (`submissions:grade`) | ✓ | ✓ |
| Gestione studenti (`students:manage`) | — | ✓ |
| Configurazione connessione Moodle (`moodle:configure`) | — | ✓ |
| Gestione schemi di valutazione (`grading_schemes:manage`) | — | ✓ (Enterprise) |
| Gestione unità organizzative (`manage_org_units`) | — | ✓ |

## Assegnare o modificare un ruolo

L'assegnazione dei ruoli avviene nella [gestione utenti](user-mgmt.md):

1. Navigate a `/admin` → scheda **Utenti**
2. Aprite l'utente desiderato
3. Selezionate il nuovo valore nel campo **Ruolo** (`DOCENTE` o `ADMIN`)
4. Fate clic su **Salva modifiche**

Il nuovo ruolo è immediatamente attivo — l'utente vede l'interfaccia aggiornata al prossimo caricamento della pagina.

!!! warning "Assegnare il ruolo ADMIN con parsimonia"
    Assegnate il ruolo ADMIN solo alle persone che devono effettivamente gestire utenti e
    impostazioni dell'istituzione. Troppi amministratori aumentano
    il rischio di modifiche di configurazione involontarie.

## Tier di abbonamento e autorizzazioni

Il ruolo (DOCENTE / ADMIN) controlla **chi** può accedere a quali funzioni. Il [tier di abbonamento](subscription.md) (Free, Starter, Professional, Enterprise) controlla inoltre **quanto** un utente può utilizzare — ad esempio il numero di documenti o di domande generabili al mese.

I due meccanismi agiscono indipendentemente l'uno dall'altro: un ADMIN con tier Free ha accesso al pannello admin, ma gli stessi limiti di utilizzo di un DOCENTE con tier Free.

## Nota di aggiornamento v1.4 — Nuove permissions

!!! warning "Assegnazione automatica al ruolo Reviewer"
    Con l'aggiornamento v1.4, il ruolo Reviewer riceve automaticamente la permission `submissions:grade`. Chi desidera separare la valutazione (grading) dalla semplice attività di revisione deve definire **prima dell'aggiornamento** un ruolo personalizzato senza questa permission.

    La permission `grading_schemes:manage` **non** viene assegnata automaticamente — è riservata esclusivamente ai ruoli Admin e Institution Owner nel tier Enterprise.

### Mapping ruoli predefiniti (da v1.4)

| Ruolo | Nuove permissions |
|-------|------------------|
| DOCENTE | `submissions:read`, `submissions:import`, `submissions:grade` |
| ADMIN | Tutte le precedenti + `students:manage`, `moodle:configure` |
| Institution Owner | Aggiuntivamente `grading_schemes:manage` (Enterprise) |

## Nota di aggiornamento v1.8 — Nuova permission

!!! info "Unità organizzative"
    Con la v1.8 è stata introdotta la permission `manage_org_units`. È assegnata di default al ruolo di sistema ADMIN e controlla la creazione, lo spostamento, l'eliminazione e la visualizzazione dell'elenco completo delle unità organizzative (dipartimenti/team) nel pannello admin. Senza questa permission la scheda resta invisibile; ogni utente continua a vedere le proprie appartenenze.

    Un'unità organizzativa può inoltre concedere automaticamente un ruolo ai propri membri diretti e controllare chi può vedere le risorse con visibilità team. Per i dettagli vedi [Unità organizzative](org-units.md).

### Mapping ruoli predefiniti (da v1.8)

| Ruolo | Nuove permissions |
|-------|--------------------|
| ADMIN | `manage_org_units` |
| DOCENTE | — |

## Passaggi successivi

- [:octicons-arrow-right-24: Gestione utenti](user-mgmt.md)
- [:octicons-arrow-right-24: Gestione unità organizzative](org-units.md)
- [:octicons-arrow-right-24: Abbonamento e quote](subscription.md)
- [:octicons-arrow-right-24: Gestione istituzioni](institutions.md)
