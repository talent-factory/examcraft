# Abbonamento

Nella pagina Abbonamento vedete il vostro piano attuale, il vostro utilizzo e potete gestire il vostro abbonamento. ExamCraft AI offre quattro piani di abbonamento flessibilmente scalabili per diverse esigenze.

## Piani disponibili

ExamCraft AI offre quattro piani di abbonamento con caratteristiche crescenti e limiti superiori:

| Funzione | Free | Starter | Professional | Enterprise |
|---------|:----:|:-------:|:------------:|:----------:|
| Documenti | 5 | 50 | Illimitati | Illimitati |
| Domande al mese | 20 | 200 | Illimitate | Illimitate |
| Tipi domanda | MC + Aperta | MC + Aperta | MC + Aperta + Matching | MC + Aperta + Matching |
| Chat Documento | — | ✓ | ✓ | ✓ |
| Caricamento Prompt | — | — | ✓ | ✓ |
| Esami RAG | — | ✓ | ✓ | ✓ |
| Esportazione esame | PDF | PDF + Word | PDF + Word + Excel | PDF + Word + Excel + LMS |
| Supporto | Community | E-mail | Priorità | Dedicato |
| SLA | — | — | 99,5% | 99,9% |

### Dettagli dei piani

**Free** – Gratuito, per valutazione e progetti piccoli. Base ottimale per conoscere la piattaforma.

**Starter** – EUR 49/mese, per docenti con utilizzo regolare. Include esami RAG e Chat Documento.

**Professional** – EUR 149/mese, per istituzioni con volume elevato. Risorse illimitate e gestione Prompt.

**Enterprise** – Su richiesta, per organizzazioni grandi. Supporto dedicato e SLA personalizzato.

## Visualizzazione abbonamento attuale

Navigate a `/subscription` o fate clic su **Abbonamento** nel menu principale. Lì vedete:

- **Il vostro piano attuale** con panoramica completa delle funzioni
- **Il vostro utilizzo** (ad es. documenti utilizzati, domande generate)
- **La prossima data di fatturazione** e stato abbonamento
- **Il badge abbonamento** – visibile anche in alto a sinistra nel Dashboard

Le metriche di utilizzo vengono aggiornate in tempo reale e mostrano:

| Metrica | Descrizione |
|---------|-------------|
| Documenti caricati | Numero documenti attivi vs. limite |
| Domande questo mese | Domande generate vs. limite mensile |
| Spazio utilizzato | Dimensione documenti vs. disponibile |
| Richieste RAG | Ricerche eseguite in questa fatturazione |

## Upgrade del piano

Potete passare in qualsiasi momento a un piano superiore. Il nuovo piano viene attivato immediatamente.

### Esecuzione upgrade abbonamento

1. Navigate a `/subscription`
2. Fate clic su **Upgrade** o selezionate il piano desiderato
3. Verrete reindirizzati a Stripe Checkout
4. Inserite le vostre informazioni di pagamento:
    - Carta di credito (VISA, Mastercard, American Express)
    - SEPA-Lastschrift
5. Dopo il pagamento riuscito il vostro piano è immediatamente attivato

La fatturazione avviene nello stesso giorno del mese successivo. Per piani mensili pagate ogni 30 giorni, per piani annuali a prezzo scontato.

!!! tip "Abbonamento annuale"
    Con un abbonamento annuale risparmiate fino al 20% rispetto alla
    fatturazione mensile. Lo sconto esatto viene visualizzato al checkout. Gli abbonamenti annuali
    vengono fatturati una volta.

!!! note "Costi di upgrade"
    Durante l'upgrade da un piano mensile, vi viene addebitata proporzionalmente la nuova tariffa del piano
    per i giorni rimanenti. Non pagate due volte.

## Fatture e dettagli di pagamento

Gestite il vostro metodo di pagamento e scaricate fatture.

### Apertura portale pagamento

1. Fate clic su **Apri portale Stripe** o **Gestisci fatture**
2. Verrete reindirizzati a un dashboard cliente sicuro
3. Lì potete:
    - **Scaricare fatture precedenti** – File PDF per la vostra contabilità
    - **Modificare metodo di pagamento** – Aggiungere/aggiornare carta di credito o SEPA
    - **Modificare indirizzo fatturazione** – Per fatture corrette
    - **Annullare abbonamento** – Se desiderato

Le fatture contengono tutte le informazioni necessarie per la vostra contabilità e il vostro numero di partita, se fornito.

### Aggiornamento metodo di pagamento

1. Aprite il portale di pagamento
2. Fate clic su **Metodo di pagamento**
3. Scegliete **Aggiungi nuova carta** o **Modifica esistente**
4. Inserite i dati o selezionate un metodo salvato
5. Salvate le modifiche

I vostri dati di pagamento vengono gestiti crittografati via Stripe e salvati in modo sicuro.

## Cambio o downgrade del piano

Potete passare in qualsiasi momento a un piano inferiore o annullare l'abbonamento.

### Cosa accade durante il downgrade?

Se passate da un piano superiore a uno inferiore, il vostro account è immediatamente limitato al nuovo piano:

- **I vostri dati rimangono conservati** – Tutti i documenti, domande e esami sono ancora accessibili
- **Le nuove funzioni sono disabilitate** – Le funzioni Premium del vecchio livello non funzionano più
- **I limiti si applicano immediatamente** – Se avete superato il limite documenti, non potete caricare nuovi documenti fino a quando non ne eliminate alcuni

### Cosa accade allo scadere?

Se annullate o il vostro abbonamento scade:

- **Il vostro account viene downgradate a Free** – Automaticamente dopo l'ultimo giorno di pagamento
- **I vostri dati rimangono 90 giorni** – Potete ancora accedervi ed esportarli
- **Dopo 90 giorni i dati vengono eliminati** – Se non tornate a fare un upgrade
- **Potete eseguire upgrade in qualsiasi momento** – I vostri dati vengono ripristinati se tornate entro 90 giorni

!!! note "I dati rimangono conservati"
    Durante il passaggio a un piano inferiore i vostri dati non vengono eliminati.
    Potete utilizzarli di nuovo completamente dopo un upgrade successivo.
    Se avete bisogno di un backup, esportate prima tutti gli esami.

## Comprensione dei contingenti e dei limiti

Ogni piano ha limiti specifici per lo spazio di archiviazione, le richieste e le funzioni.

### Limiti per piano

**Piano Free:**
- 5 documenti caricabili
- 20 domande al mese
- Nessun Chat Documento
- Nessun esame RAG

**Piano Starter:**
- 50 documenti caricabili
- 200 domande al mese
- Richieste RAG illimitate
- Chat Documento con fino a 100 coppie di messaggi al mese

**Professional + Enterprise:**
- Documenti e domande illimitati
- Spettro completo di tutte le funzioni

### Cosa accade al superamento dei limiti?

Se raggiungete i vostri limiti:

1. **Limite documenti** – Non potete caricare più documenti
2. **Limite domande** – La generazione di domande è disabilitata fino alla prossima fatturazione
3. **Limite RAG** – La ricerca semantica non funziona più

Potete eseguire immediatamente un upgrade per aumentare i limiti.

## Passaggi successivi

- [:octicons-arrow-right-24: Torna al Dashboard](dashboard.md)
- [:octicons-arrow-right-24: Profilo e account](profile.md)
- [:octicons-arrow-right-24: Carica documenti](documents.md)
