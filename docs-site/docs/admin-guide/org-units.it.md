# Unità organizzative

!!! note "Nuova autorizzazione richiesta"
    La creazione, lo spostamento, l'eliminazione e la visualizzazione dell'elenco completo delle unità organizzative richiedono la permission `manage_org_units`, assegnata di default al ruolo ADMIN. Senza questa permission la scheda **Unità organizzative** non è visibile — ogni utente autenticato vede solo le proprie appartenenze, ad esempio nella scelta di una visibilità team.

ExamCraft AI rappresenta la struttura interna di un'istituzione tramite unità organizzative — **dipartimenti** con **team** annidati al di sotto. Navigate a `/admin` e selezionate la scheda **Unità organizzative**.

## Creare un'unità organizzativa

1. Navigate a `/admin` → scheda **Unità organizzative**
2. Fate clic su **+ Crea**
3. Inserite un **nome** e scegliete il **tipo** (`Dipartimento` o `Team`)
4. Selezionate facoltativamente un'**unità superiore** — un team si trova tipicamente sotto un dipartimento
5. Assegnate facoltativamente un **ruolo concesso** (vedi sotto)
6. **Salvate**

!!! warning "Tipo fisso dopo la creazione"
    Il tipo (`Dipartimento`/`Team`) non può più essere modificato dopo la creazione dell'unità.

    Il nome deve inoltre essere univoco all'interno dello stesso livello — due unità con lo stesso nome e la stessa unità superiore non sono ammesse.

## Spostare un'unità organizzativa

Aprite l'unità tramite l'icona di modifica e selezionate una nuova unità superiore nel campo **Unità superiore**. Un'unità non può essere spostata sotto una delle proprie sotto-unità.

## Eliminare un'unità organizzativa

Se un'unità organizzativa contiene sotto-unità, l'eliminazione rimuove definitivamente anche **tutte** le sotto-unità annidate. La finestra di conferma mostra il numero di sotto-unità interessate.

Se documenti, prompt, domande, esami o quadri di competenze con visibilità team fanno ancora riferimento all'unità o a una delle sue sotto-unità, l'eliminazione viene rifiutata — rimuovete o riassegnate prima le risorse interessate.

## Ruolo concesso e visibilità team

La struttura organizzativa non è puramente informativa — può controllare due aspetti:

- **Ruolo concesso**: se a un'unità organizzativa è assegnato un ruolo, tutti i membri **diretti** di quell'unità ricevono automaticamente i permessi di quel ruolo — in aggiunta al proprio ruolo. Questa ereditarietà non si propaga a cascata alle sotto-unità.
- **Visibilità team**: per documenti, prompt, domande, esami e quadri di competenze con visibilità impostata su "Team", l'appartenenza all'unità organizzativa — inclusa la gerarchia — determina chi può vederli.

Assegnate gli utenti alle unità organizzative tramite il pulsante **Unità org.** nella [gestione utenti](user-mgmt.md).

## Passaggi successivi

- [:octicons-arrow-right-24: Ruoli e autorizzazioni](roles.md)
- [:octicons-arrow-right-24: Gestione utenti](user-mgmt.md)
