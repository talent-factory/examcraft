# Statistiche

!!! note "Nota sul tier"
    Le KPI card e l'istogramma sono disponibili per tutti i tier. L'analisi per domanda (discriminazione) e le statistiche di andamento della classe sono funzionalità Professional ed Enterprise.

La scheda Statistiche mostra una panoramica completa delle prestazioni della coorte d'esame — dalla distribuzione complessiva all'analisi delle singole domande. Route: scheda **Statistiche** in `/auswertungen/:examId/submissions`.

![Statistiche — KPI card](../screenshots/statistik/statistik-kpis.png)

## KPI card

| Indicatore | Significato |
|------------|-------------|
| Media | Punteggio medio di tutte le submission |
| Tasso di superamento | Quota di submission che hanno raggiunto la soglia di superamento |
| Submission | Numero totale di invii |
| Revisionate | Numero di submission con stato `fully_reviewed` |

## Distribuzione dei punteggi

![Istogramma — Distribuzione punteggi](../screenshots/statistik/statistik-histogramm.png)

L'istogramma raggruppa tutte le submission in bucket del 10 % (0–10 %, 10–20 %, …). Un massimo ripido al centro indica un esame ben calibrato. Una forte asimmetria verso sinistra può indicare domande troppo difficili.

## Analisi per domanda

![Tabella per domanda](../screenshots/statistik/statistik-per-question.png)

| Colonna | Descrizione |
|---------|-------------|
| Domanda | Testo breve della domanda |
| Tasso di superamento | Quota di candidati con punteggio pieno |
| Difficoltà | Inverso del tasso di superamento — 100 % significa che tutti hanno fallito |
| Discriminazione | Quanto bene questa domanda distingue i candidati forti da quelli deboli? |

### Comprendere la discriminazione

L'indice di discriminazione misura se una domanda distingue tra i risultati dei candidati forti e deboli:

| Valore | Interpretazione |
|--------|-----------------|
| ≥ 0.40 | Discriminazione eccellente |
| 0.30–0.39 | Buona discriminazione |
| 0.20–0.29 | Sufficiente — revisione consigliata |
| < 0.20 | Discriminazione debole — la domanda dovrebbe essere rivista o rimossa |

Una discriminazione negativa è un segnale d'allarme: i candidati più deboli hanno risposto correttamente alla domanda più spesso dei candidati più forti.

## Effetto apprendimento con tentativi multipli

![Effetto apprendimento — Tentativi multipli](../screenshots/statistik/statistik-lerneffekt.png)

Quando gli studenti sostengono lo stesso esame più volte (ad es. in caso di esami di recupero), questa sezione mostra l'evoluzione dei valori medi nel corso dei tentativi. Una tendenza crescente conferma un effetto di apprendimento misurabile.

## Passi successivi

- [:octicons-arrow-right-24: Esporta voti](notenexport.md)
- [:octicons-arrow-right-24: Statistiche di andamento della classe](klassen.md)
- [:octicons-arrow-right-24: Quote di abbonamento](subscription.md)
