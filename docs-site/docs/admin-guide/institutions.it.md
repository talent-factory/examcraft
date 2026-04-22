# Istituzioni

Le istituzioni organizzano gli utenti in gruppi — ad esempio una scuola, un'università o un dipartimento. Ogni utente appartiene a esattamente un'istituzione.

Navigate a `/admin` e selezionate la scheda **Istituzioni**.

## Creazione istituzione

1. Fate clic su **Nuova istituzione**
2. Inserite le seguenti informazioni:

| Campo | Descrizione | Campo obbligatorio |
|-------|-------------|:-----------:|
| Nome | Denominazione dell'istituzione (ad es. "Liceo Cantonale Zurigo") | ✓ |
| Descrizione | Informazione supplementare facoltativa | — |

3. Fate clic su **Crea istituzione**

La nuova istituzione appare immediatamente nell'elenco ed è disponibile per la selezione nella gestione utenti.

## Assegnazione utenti a istituzione

Potete assegnare gli utenti a un'istituzione in due modi:

**Durante la creazione di un nuovo utente**: Selezionate l'istituzione direttamente nel modulo di creazione. Vedere [Gestione utenti](user-mgmt.md).

**Tramite dettagli istituzione**:

1. Fate clic sull'istituzione
2. Passate alla scheda **Utenti**
3. Fate clic su **Aggiungi utente**
4. Selezionate l'utente dall'elenco

## Modifica istituzione

1. Fate clic sul nome nell'elenco istituzioni
2. Adattate nome o descrizione
3. Fate clic su **Salva modifiche**

## Impostazioni specifiche dell'istituzione

A seconda della configurazione dell'installazione ExamCraft, potete apportare le seguenti impostazioni specifiche dell'istituzione:

- **Abbonamento Standard**: Quale piano viene assegnato per impostazione predefinita ai nuovi utenti di questa istituzione
- **Metodi di accesso consentiti**: E-mail/password e/o Google OAuth

!!! note "Le impostazioni dipendono dall'installazione"
    Le impostazioni disponibili possono variare a seconda della versione ExamCraft.
    Contattate l'amministratore IT in caso di domande.

## Eliminazione istituzione

!!! warning "Attenzione: non reversibile"
    L'eliminazione di un'istituzione rimuove l'istituzione e tutte le assegnazioni.
    Gli utenti dell'istituzione non vengono eliminati, ma perdono l'assegnazione all'istituzione.
    Riflettete bene se l'eliminazione è davvero la misura giusta — spesso è sufficiente rinominare l'istituzione.

1. Fate clic sull'istituzione
2. Fate clic su **Elimina istituzione**
3. Confermate l'azione inserendo il nome dell'istituzione

## Passaggi successivi

- [:octicons-arrow-right-24: Gestire utenti](user-mgmt.md)
- [:octicons-arrow-right-24: Panoramica utilizzo](monitoring.md)
