# Statistik

!!! note "Tier-Hinweis"
    KPI-Cards und Histogramm stehen allen Tiers zur Verfügung. Die Pro-Frage-Analyse (Trennschärfe) und die Klassen-Verlaufsstatistik sind Professional- und Enterprise-Features.

Der Statistik-Tab zeigt einen vollständigen Überblick über die Leistung Ihrer Prüfungskohorte — von der Gesamtverteilung bis zur Analyse einzelner Fragen. Route: Tab **Statistik** in `/auswertungen/:examId/submissions`.

![Statistik — KPI-Cards](../screenshots/statistik/statistik-kpis.png)

## KPI-Cards

| Kennzahl | Bedeutung |
|----------|-----------|
| Durchschnitt | Mittlere Punktzahl aller Submissions |
| Erfolgsquote | Anteil der Submissions, die die Bestehensgrenze erreicht haben |
| Submissions | Gesamtanzahl der Einreichungen |
| Reviewed | Anzahl der Submissions mit Status `fully_reviewed` |

## Punkteverteilung

![Histogramm — Punkteverteilung](../screenshots/statistik/statistik-histogramm.png)

Das Histogramm gruppiert alle Submissions in 10 %-Buckets (0–10 %, 10–20 %, …). Ein steiles Maximum in der Mitte deutet auf eine gut kalibrierte Prüfung hin. Eine starke Linksschiefe kann auf zu schwere Fragen hinweisen.

## Pro-Frage-Analyse

![Pro-Frage-Tabelle](../screenshots/statistik/statistik-per-question.png)

| Spalte | Beschreibung |
|--------|-------------|
| Frage | Kurztext der Frage |
| Erfolgsquote | Anteil der Prüflinge mit voller Punktzahl |
| Schwierigkeit | Umgekehrt zur Erfolgsquote — 100 % bedeutet, alle haben versagt |
| Trennschärfe | Wie gut unterscheidet diese Frage starke von schwachen Prüflingen? |

### Trennschärfe verstehen

Der Diskriminationsindex misst, ob eine Frage zwischen starken und schwachen Prüflings-Resultaten unterscheidet:

| Wert | Interpretation |
|------|---------------|
| ≥ 0.40 | Ausgezeichnete Trennschärfe |
| 0.30–0.39 | Gute Trennschärfe |
| 0.20–0.29 | Befriedigend — Überarbeitung empfohlen |
| < 0.20 | Schwache Trennschärfe — Frage sollte überarbeitet oder entfernt werden |

Eine negative Trennschärfe ist ein Warnsignal: Schwächere Prüflinge haben die Frage häufiger korrekt beantwortet als stärkere.

## Lerneffekt bei Mehrfach-Versuchen

![Lerneffekt — Mehrfach-Versuche](../screenshots/statistik/statistik-lerneffekt.png)

Wenn Studierende dieselbe Prüfung mehrfach ablegen (z.B. bei Nachholprüfungen), zeigt dieser Bereich die Entwicklung der Durchschnittswerte über die Versuche. Ein ansteigender Trend bestätigt einen messbaren Lerneffekt.

## Nächste Schritte

- [:octicons-arrow-right-24: Noten exportieren](notenexport.md)
- [:octicons-arrow-right-24: Klassen-Verlaufsstatistik](klassen.md)
- [:octicons-arrow-right-24: Subscription-Quotas](subscription.md)
