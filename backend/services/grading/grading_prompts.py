"""Prompt-Library für LLM-Grading (Phase 2 — TF-334).

Versionierte Konstanten statt DB-Lookup: das Premium-``PromptService``
ist im Core-Mode nicht verfügbar (Placeholder), und für ein Bewertungs-
Prompt sind die Vorteile einer DB-versionierten Variante (Override pro
Institution) erst in Phase 4 relevant. Der Versions-Suffix
(``v1``) bleibt im Code erhalten, sodass spätere Override-Mechanik
kompatibel bleibt.

Cache-Strategie: Der ``SYSTEM_PROMPT`` und der pro-Frage statische
Block (Frage + Musterlösung + Erklärung + Maximalpunktzahl + Bloom)
sind Cache-Kandidaten — sie wiederholen sich über alle Studis einer
Prüfung. Nur die Studi-Antwort variiert. ``LlmGrader`` setzt deshalb
``cache_control: ephemeral`` auf System- und statischen User-Block,
nicht auf den variablen Antwort-Block.
"""

from __future__ import annotations


GRADING_OPEN_ENDED_PROMPT_ID = "grading.open_ended.v1"


SYSTEM_PROMPT = (
    "Du bewertest offene Prüfungsantworten von Studierenden. Vergleiche "
    "die Studi-Antwort mit der Musterlösung und vergib eine Punktzahl "
    "zwischen 0 und der Maximalpunktzahl der Frage. Belohne inhaltlich "
    "korrekte Aspekte, auch wenn die Formulierung von der Musterlösung "
    "abweicht. Bestrafe fehlende Kernaspekte und sachliche Fehler.\n"
    "\n"
    "Antworte ausschliesslich mit einem JSON-Objekt mit den Feldern "
    '"points_awarded" (float, 0..points_max), "confidence" (float, 0..1 — '
    "wie sicher du dir bist, dass deine Bewertung korrekt ist), "
    '"rationale" (string, kurze Begründung in 1–3 Sätzen auf Deutsch), '
    '"matched_aspects" (list[string], abgedeckte Aspekte aus der '
    'Musterlösung), "missing_aspects" (list[string], fehlende oder '
    "fehlerhafte Aspekte). Keine Markdown-Code-Blöcke, kein Vorspann."
)


def build_question_context_block(
    *,
    question_text: str,
    correct_answer: str,
    explanation: str | None,
    points_max: float,
    difficulty: str | None = None,
    bloom_level: str | None = None,
) -> str:
    """Statischer Cache-Block: Frage + Musterlösung + Bewertungsregeln.

    Identisch über alle Studis einer Prüfung; deshalb cacht der LLM-
    Grader genau diesen Block. Der variable Studi-Antwort-Teil wird in
    einem separaten Content-Block gesendet.
    """
    parts = [
        f"## Frage\n{question_text.strip()}",
        f"\n## Musterlösung\n{correct_answer.strip()}",
    ]
    if explanation:
        parts.append(f"\n## Erklärung / Bewertungskriterien\n{explanation.strip()}")
    parts.append(f"\n## Maximalpunktzahl\n{points_max}")
    if difficulty:
        parts.append(f"\n## Schwierigkeit\n{difficulty}")
    if bloom_level:
        parts.append(f"\n## Bloom-Level\n{bloom_level}")
    parts.append(
        "\n## Bewertungsregeln\n"
        "- Vergib volle Punktzahl bei vollständig korrekter Antwort.\n"
        "- Vergib Teilpunkte für teilweise korrekte Antworten anhand "
        "der abgedeckten Kernaspekte.\n"
        "- 0 Punkte bei sachlich falscher oder leerer Antwort.\n"
        "- Confidence niedrig (≤ 0.6) bei mehrdeutigen Antworten oder "
        "wenn die Musterlösung selbst lückenhaft scheint."
    )
    return "".join(parts)


def build_student_answer_block(given_answer: str | None) -> str:
    """Variabler Block: Studi-Antwort. NICHT gecached."""
    answer = (given_answer or "").strip() or "[Antwort leer]"
    return f"## Studi-Antwort\n{answer}\n\n## Aufgabe\nBewerte die Studi-Antwort gemäss den Regeln oben."
