# Panoramica utilizzo

La panoramica utilizzo nel pannello Admin fornisce una panoramica delle attività e del consumo di risorse dell'istituzione.

Navigate a `/admin` e selezionate la scheda **Utilizzo**.

## Metriche disponibili

| Metrica | Descrizione |
|---------|-------------|
| Utenti attivi | Numero di utenti con almeno un'attività nel periodo selezionato |
| Domande generate | Numero totale di domande create dall'IA |
| Domande convalidate | Numero di domande approvate nella Review Queue |
| Documenti caricati | Numero e dimensione totale dei documenti elaborati |
| Richieste API | Numero di richieste API Claude (rilevante per il controllo dei costi) |

## Selezione del periodo

Filtrate la visualizzazione per periodo:

- **Oggi** — Attività del giorno corrente
- **Questa settimana** — Settimana in corso (lunedì fino a oggi)
- **Questo mese** — Mese di calendario in corso
- **Personalizzato** — Selezionare il proprio periodo tramite il selettore data

## Utilizzo per utente

Nella vista dettagli vedete il dettaglio per utente:

| Colonna | Descrizione |
|---------|-------------|
| Utente | Nome ed e-mail |
| Domande generate | Numero nel periodo selezionato |
| Documenti | Numero di documenti caricati |
| Ultima attività | Data dell'ultima azione |

Fate clic su una riga della tabella per visualizzare i dettagli di un singolo utente.

## Monitoraggio dei contingenti di abbonamento

Prestate particolare attenzione all'utilizzo dei contingenti:

!!! warning "Osservare i limiti dei contingenti"
    Con l'abbonamento Free e Starter si applicano limiti mensili per domande e documenti.
    Se gli utenti raggiungono regolarmente i limiti, dovreste considerare un upgrade.
    Vedere [Abbonamento](../user-guide/subscription.md).

## Nota: Monitoraggio tecnico dell'infrastruttura

La panoramica utilizzo nel pannello Admin mostra **metriche di applicazione** (chi usa cosa). Per il **monitoraggio tecnico dell'infrastruttura** (carico server, log, tasso di errore) contattate l'amministratore IT o il responsabile DevOps — queste informazioni non fanno parte del pannello Admin.

## Domande frequenti sulla panoramica utilizzo

**Con quale frequenza vengono aggiornati i numeri?**

Le metriche vengono aggiornate in tempo reale. Dopo ogni azione (generazione domande, caricamento documento, revisione) le metriche vengono aggiornate entro pochi secondi.

**Posso esportare i dati?**

Attualmente non è disponibile un'esportazione diretta dei dati dal pannello Admin. Potete tuttavia catturare una schermata della panoramica utilizzo nel browser o documentare manualmente i numeri. Un'esportazione CSV/PDF è prevista per versioni future.

**Cosa significa "Richieste API"?**

Ogni generazione di domande IA conta come una o più richieste API alla API Claude. Se ad es. generate 10 domande, possono essere 1–3 richieste API (a seconda della dimensione del batch). Queste informazioni sono rilevanti per il controllo dei costi per i piani Professional e Enterprise, poiché dovete gestire il vostro budget API.

**Le richieste API differiscono tra esami IA e esami RAG?**

Gli esami RAG potrebbero richiedere più richieste API poiché l'IA esegue prima la ricerca semantica e poi genera le domande. Gli esami IA sono solitamente più veloci. La differenza esatta viene misurata nella metrica delle richieste API.

**Posso vedere gli utenti con consumo elevato?**

Sì! Nella vista dettagli "Utilizzo per utente" potete vedere quali utenti hanno generato quante domande e quanti documenti utilizzano. Questo aiuta nell'identificazione di power-user e nella pianificazione delle risorse.

## Passaggi successivi

- [:octicons-arrow-right-24: Gestire utenti](user-mgmt.md)
- [:octicons-arrow-right-24: Gestire istituzioni](institutions.md)
