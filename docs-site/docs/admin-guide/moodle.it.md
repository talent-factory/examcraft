# Configurazione connessione Moodle

!!! warning "Configurazione obbligatoria per l'ambiente di produzione"
    Il token di accesso Moodle viene memorizzato crittografato con Fernet. Per l'ambiente di produzione **è obbligatorio** impostare la variabile d'ambiente `MOODLE_TOKEN_ENCRYPTION_KEY` con una chiave Fernet di 44 caratteri. In sua assenza, l'applicazione utilizza un meccanismo predefinito inadatto alla produzione.

La connessione Moodle consente ai docenti di importare direttamente i risultati degli esami tramite API senza esportazione manuale in CSV. Questa configurazione viene eseguita una volta per istituzione da un amministratore.

## Prerequisiti in Moodle

1. **Amministrazione sito → Plugin → Web Services → Panoramica**: Attivare i Web Services
2. Attivare il protocollo REST
3. Creare un servizio esterno e assegnare le seguenti funzioni:
   - `mod_quiz_get_quizzes_by_courses`
   - `mod_quiz_get_user_attempts`
   - `mod_quiz_get_attempt_review`
   - `core_webservice_get_site_info` (per il pulsante Test)
4. Generare un token per un utente di sistema con le autorizzazioni necessarie

## Generazione della chiave di cifratura

Eseguite il seguente comando sul server e inserite l'output come `MOODLE_TOKEN_ENCRYPTION_KEY` nel file `.env`:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

La chiave ha esattamente 44 caratteri e deve essere mantenuta segreta. In caso di smarrimento, tutti i token memorizzati devono essere reinseriti.

## Configurazione della connessione

![Moodle — Modulo di connessione](../screenshots/moodle/moodle-connection-form.png)

1. Navigate come Admin a `/admin/integrations/moodle`
2. Fate clic su **Nuova connessione**
3. Compilate i campi:

| Campo | Esempio | Nota |
|-------|---------|------|
| Nome | "Moodle Università di Berna" | Nome visualizzato per i docenti |
| Base-URL | `https://moodle.example.ch` | Senza `/` finale |
| Token | `abc123...` | Copiato da Moodle |

4. Fate clic su **Testa connessione** — ExamCraft chiama `core_webservice_get_site_info`. In caso di successo compare il nome del sito Moodle come conferma.
5. **Salva**

## Come funziona internamente l'importazione API

Durante l'importazione viene eseguita la seguente sequenza di query:

1. `mod_quiz_get_quizzes_by_courses` — elenca tutti i quiz nel corso
2. `mod_quiz_get_user_attempts` — recupera tutti i tentativi per studente
3. `mod_quiz_get_attempt_review` — recupera le risposte dettagliate per tentativo

La corrispondenza delle domande avviene tramite gli ID domanda di Moodle, che i docenti inseriscono una volta nell'[ID-Round-Trip Moodle](../user-guide/moodle-integration.md).

## Isolamento multi-tenant

Ogni istituzione gestisce le proprie connessioni. I token e i dati di connessione non sono accessibili tra le istituzioni.

## Passaggi successivi

- [:octicons-arrow-right-24: Guida docenti Moodle](../user-guide/moodle-integration.md)
- [:octicons-arrow-right-24: Schemi di valutazione](grading-schemes.md)
- [:octicons-arrow-right-24: Ruoli e autorizzazioni](roles.md)
