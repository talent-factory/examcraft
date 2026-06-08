# Schemi di valutazione

!!! note "Funzione Enterprise"
    La creazione di schemi di valutazione personalizzati richiede la permission `grading_schemes:manage`, assegnata per impostazione predefinita ai ruoli Admin e Institution Owner nel tier Enterprise.

ExamCraft AI include otto schemi di sistema preinstallati (in sola lettura) e consente alle istituzioni di definire schemi personalizzati. Rotta: `/admin/grading-schemes`.

## Schemi di sistema vs. schemi istituzione

| Tipo | Provenienza | Modificabile? |
|------|-------------|---------------|
| Schema di sistema | ExamCraft AI (preinstallato) | No |
| Schema istituzione | Creato da voi | Sì — modificabile ed eliminabile |

Gli schemi di sistema coprono i sistemi di voto nazionali più comuni (Svizzero, Tedesco, Austriaco, Francese, Olandese, ECTS, Percentuale, Superato/Non superato). Gli schemi personalizzati estendono questo elenco.

## Tipi di configurazione

### `linear`

Conversione lineare dalla percentuale al voto tra `min_score` e `max_score`.

```yaml
type: linear
min_score: 1.0
max_score: 6.0
passing_percentage: 60
```

### `linear_segments`

Due segmenti lineari con un punto di flesso a `passing_percentage`. I voti sotto la soglia di superamento hanno una pendenza inferiore rispetto a quelli sopra.

```yaml
type: linear_segments
min_score: 1.0
max_score: 6.0
passing_percentage: 60
passing_score: 4.0
```

### `stepped`

Voti a gradini fissi. Ogni gradino definisce un intervallo percentuale e il voto corrispondente.

```yaml
type: stepped
steps:
  - { min_percent: 0,  max_percent: 49,  grade: "F" }
  - { min_percent: 50, max_percent: 64,  grade: "D" }
  - { min_percent: 65, max_percent: 79,  grade: "C" }
  - { min_percent: 80, max_percent: 89,  grade: "B" }
  - { min_percent: 90, max_percent: 100, grade: "A" }
```

## Creare uno schema personalizzato

1. Navigate a `/admin/grading-schemes`
2. Fate clic su **Nuovo schema**
3. Scegliete il tipo di configurazione
4. Compilate i parametri
5. L'**anteprima live** mostra immediatamente quale voto viene assegnato per ogni percentuale
6. **Salva** — lo schema è disponibile per i docenti durante l'esportazione voti

## Impostare lo standard istituzione

Fate clic sull'icona stella accanto a uno schema per impostarlo come standard per la vostra istituzione. Questo valore compare preselezionato durante l'esportazione voti. I docenti possono sovrascrivere la selezione per singola esportazione.

## Passaggi successivi

- [:octicons-arrow-right-24: Connessione Moodle](moodle.md)
- [:octicons-arrow-right-24: Ruoli e autorizzazioni](roles.md)
- [:octicons-arrow-right-24: Esportazione voti (Manuale utente)](../user-guide/notenexport.md)
