# Gestione utenti

Come amministratore gestite tutti gli utenti della vostra istituzione tramite il pannello Admin. Navigate a `/admin` e selezionate la scheda **Utenti**.

## Creazione utenti

1. Fate clic su **Nuovo utente**
2. Compilate il modulo:

| Campo | Descrizione | Campo obbligatorio |
|-------|-------------|:-----------:|
| Nome e cognome | Nome completo della persona | ✓ |
| Indirizzo e-mail | Viene utilizzato come nome di login | ✓ |
| Ruolo | ADMIN o DOZENT (vedere sotto) | ✓ |
| Istituzione | Assegnazione all'istituzione | ✓ |
| Password temporanea | Prima password (l'utente può cambiarla) | ✓ |

3. Fate clic su **Crea utente**
4. Il nuovo utente riceve un'e-mail di benvenuto con credenziali di accesso

!!! tip "Consiglio Google OAuth"
    Consigliate ai nuovi utenti di passare a Google OAuth al primo accesso.
    Questo semplifica la gestione delle password e aumenta la sicurezza.

## Ruoli utente

ExamCraft AI conosce due ruoli:

| Ruolo | Permessi |
|-------|----------|
| **DOZENT** | Caricamento documenti, generazione domande, Review Queue, Exam Composer, Libreria Prompt |
| **ADMIN** | Tutti i permessi DOZENT + Gestione utenti, Istituzioni, Pannello Admin |

Assegnate il ruolo ADMIN solo a persone che effettivamente dovranno gestire gli utenti.

## Modifica utenti

1. Fate clic sul nome della persona nell'elenco utenti
2. Adattate i campi desiderati (Nome, E-mail, Ruolo, Istituzione)
3. Fate clic su **Salva modifiche**

## Ripristino password (come Admin)

1. Aprite l'utente nella gestione
2. Fate clic su **Ripristina password**
3. Viene generata una nuova password temporanea e inviata per e-mail all'utente
4. L'utente deve cambiare la password al prossimo accesso

## Disabilitazione utenti

Quando un utente lascia l'istituzione o non ha più bisogno di accesso:

1. Aprite l'utente
2. Fate clic su **Disabilita utente**
3. Confermate l'azione

!!! warning "Disabilitare anziché eliminare"
    Disabilitate gli utenti anziché eliminarli. In questo modo tutte le domande
    e gli esami creati rimangono e rimangono assegnabili. Un utente disabilitato
    non può più accedere, ma i dati rimangono.

## Assegnazione utenti a istituzione

Potete cambiare l'assegnazione dell'istituzione in qualsiasi momento:

1. Aprite l'utente
2. Selezionate la nuova istituzione nel campo **Istituzione**
3. Salvate la modifica

Ulteriori informazioni sulle istituzioni: [Gestire istituzioni](institutions.md)

## Passaggi successivi

- [:octicons-arrow-right-24: Gestire istituzioni](institutions.md)
- [:octicons-arrow-right-24: Panoramica utilizzo](monitoring.md)
