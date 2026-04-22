# Libreria Prompt

La Libreria Prompt consente la gestione di Prompt IA riutilizzabili per la generazione di domande. Anziché inserire manualmente lo stesso Prompt ogni volta, salvate i Prompt collaudati centralmente e utilizzateli direttamente durante la creazione di esami.

!!! note "Accesso"
    La Libreria Prompt è disponibile per utenti con i ruoli **ADMIN** e **DOZENT**.
    Rotta: `/prompts`

## Panoramica

- **Versionamento** – Tutte le modifiche vengono tracciate
- **Rollback** – Torna a versioni precedenti
- **Ricerca semantica** – Trova Prompt per significato
- **Analytics** – Monitora performance e costi
- **Sistema Template** – Prompt riutilizzabili con variabili
- **Interfaccia Web** – Nessun cambio di codice necessario

## Vista Prompt

La Libreria Prompt mostra tutti i Prompt disponibili in un layout a griglia con:

- Nome e descrizione Prompt
- Categoria (Sistema / Utente / Template)
- Caso di uso, versione e stato
- Tag e contatore di utilizzo

### Azioni

Potete gestire ogni Prompt con le seguenti azioni:

- **Modifica** – Apri Prompt in editor
- **Versioni** – Visualizza cronologia versioni
- **Elimina** – Rimuovi Prompt

## Creazione nuovo Prompt

1. Fate clic su **Nuovo Prompt**
2. Compilate i seguenti campi:

| Campo | Descrizione |
|---|---|
| Nome | Identificatore univoco (ad es. `system_prompt_question_generation`) |
| Descrizione | Breve spiegazione dello scopo |
| Categoria | System Prompt / User Prompt / Few-Shot Example / Template |
| Caso di uso | Scopo di utilizzo (ad es. `question_generation`) |
| Contenuto | Testo Prompt (Markdown supportato) |
| Tag | Parole chiave per ricerca più facile |
| Attivo | Attivare immediatamente? |

3. Fate clic su **Salva**

Il nuovo Prompt è immediatamente disponibile nella libreria e può essere utilizzato durante la generazione di domande.

## Variabili Template

Con le variabili Template create Prompt dinamici che si adattano automaticamente ai vostri input.

### Sintassi

Utilizzate parentesi graffe: `{variable_name}`

Esempio:
```
Genera {count} domande sull'argomento {topic} al livello di difficoltà {difficulty}
```

### Variabili disponibili negli esami RAG

Le seguenti variabili sono automaticamente disponibili:

- `topic` – Argomento esame
- `difficulty` – Livello difficoltà (easy, medium, hard)
- `language` – Lingua delle domande
- `context` – Contenuti documento estratti automaticamente

Queste variabili vengono sostituite automaticamente al runtime con i vostri input o i dati del documento.

## Controllo versione

La Libreria Prompt gestisce automaticamente tutte le versioni dei vostri Prompt.

### Gestione versioni

- Numeri versione automatici (v1, v2, v3...)
- Una sola versione può essere attiva contemporaneamente
- Le versioni precedenti rimangono conservate (illimitate)

### Ritorno a versione precedente

1. Aprite il Prompt e fate clic su **Versioni**
2. Selezionate la versione desiderata dall'elenco
3. Fate clic su **Attiva**
4. Confermate il rollback

La versione precedente è di nuovo attiva per le nuove generazioni di domande.

## Analytics utilizzo

Monitorate la performance dei vostri Prompt con metriche dettagliate:

| Metrica | Descrizione |
|---|---|
| Utilizzi | Numero di richiami dal creazione |
| Tasso successo | % generazioni riuscite |
| Latenza media | Tempo medio risposta in secondi |
| Token totali | Consumo token totale |

Queste metriche vi aiutano a valutare e ottimizzare l'efficienza dei vostri Prompt.

## Ricerca semantica

Trovate Prompt per significato e non solo per parole chiave.

### Esecuzione ricerca semantica

1. Passate alla scheda **Ricerca semantica**
2. Inserite una query di ricerca (ad es. "Genera domande a scelta multipla")
3. Filtrate se necessario per:
    - **Categoria** – Limitare tipo Prompt
    - **Caso di uso** – Selezionare caso di uso specifico
    - **Soglia somiglianza** – Impostare rilevanza minima
4. I risultati sono automaticamente ordinati per rilevanza

La ricerca semantica comprende il significato della vostra richiesta e trova anche Prompt che non corrispondono completamente dal punto di vista testuale.

## Utilizzo Prompt durante generazione domande

1. Aprite [Crea esame](exam-create.md) o [Crea esame RAG](rag-exam.md)
2. Nella sezione **Configurazione Prompt** fate clic su **Seleziona da libreria**
3. Selezionate il Prompt desiderato dall'elenco
4. Le variabili Template vengono compilate automaticamente con i vostri input
5. Fate clic su **Genera**

!!! tip "Premium: Caricamento Prompt"
    Da **abbonamento Professional** potete caricare file Prompt propri e
    importarli nella libreria. Vedere [Abbonamento](subscription.md).

## Passaggi successivi

- [:octicons-arrow-right-24: Genera domande](exam-create.md)
- [:octicons-arrow-right-24: Crea esame RAG](rag-exam.md)
- [:octicons-arrow-right-24: Gestisci abbonamento](subscription.md)
