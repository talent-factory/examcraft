"""TF-401: Kompetenz-Variablen in Default-Prompt-Templates (Data-Migration).

Aktualisiert die bereits geseedeten Default-Prompt-Zeilen (Jinja2-Pfad) in
bestehenden Datenbanken um den Handlungskompetenzen-Block und die beiden
Output-Keys (competency_code, ln_level). Die NEUEN Bodies sind byte-identisch
zu premium/backend/scripts/seed_prompts.py; die ALTEN (downgrade) byte-identisch
zum git-HEAD-Stand vor dieser Migration.

Revision ID: tf401_competency_prompt_vars
Revises: tf400_competency_frameworks
Create Date: 2026-06-09
"""

import sqlalchemy as sa
from alembic import op

revision = "tf401_competency_prompt_vars"
down_revision = "tf400_competency_frameworks"
branch_labels = None
depends_on = None


NEW_MULTIPLE_CHOICE = "You are an expert in educational assessment and exam question generation.\n\nYour task is to create a high-quality multiple-choice question based on the provided context.\n\nContext:\n{context}\n\nTopic: {topic}\nDifficulty: {difficulty}\nLanguage: {language}\n\n{% if competencies %}\nZU PRÜFENDE HANDLUNGSKOMPETENZEN:\n{{ competencies }}\n\nJede Frage prüft genau EINE der oben genannten Handlungskompetenzen. Trage deren Kürzel als 'competency_code' und die zugehörige LN-Stufe (1-4) als 'ln_level' in die JSON-Antwort ein.\n{% endif %}\nGenerate a multiple-choice question that:\n1. Tests understanding of key concepts from the context\n2. Is suitable for open-book examination format\n3. Has one clearly correct answer\n4. Includes 3-4 plausible distractors (incorrect options)\n5. Avoids ambiguity and trick questions\n\nFormat your response as structured JSON with the following fields:\n- question_text: The question text\n- options: Array of 4 answer options (strings)\n- correct_answer: The correct option (exact match from options array)\n- explanation: Detailed explanation of why the correct answer is right and why distractors are wrong\n- difficulty: The difficulty level (easy/medium/hard)\n- source_reference: Reference to the specific part of the context used\n- competency_code: Kürzel der geprüften Handlungskompetenz (z.B. B3) oder null\n- ln_level: LN-Stufe der geprüften Kompetenz (1-4) oder null"

NEW_OPEN_ENDED = "You are an expert in educational assessment and exam question generation.\n\nYour task is to create a high-quality open-ended question based on the provided context.\n\nContext:\n{context}\n\nTopic: {topic}\nDifficulty: {difficulty}\nLanguage: {language}\n\n{% if competencies %}\nZU PRÜFENDE HANDLUNGSKOMPETENZEN:\n{{ competencies }}\n\nJede Frage prüft genau EINE der oben genannten Handlungskompetenzen. Trage deren Kürzel als 'competency_code' und die zugehörige LN-Stufe (1-4) als 'ln_level' in die JSON-Antwort ein.\n{% endif %}\nGenerate an open-ended question that:\n1. Requires critical thinking and analysis\n2. Is suitable for open-book examination format\n3. Cannot be answered with simple facts (requires synthesis and evaluation)\n4. Has clear evaluation criteria\n5. Allows for multiple valid approaches or perspectives\n\nFormat your response as structured JSON with the following fields:\n- question_text: The question text\n- evaluation_criteria: Array of criteria for grading (each with description and points)\n- sample_answer: A high-quality example answer\n- explanation: What makes a good answer to this question\n- difficulty: The difficulty level (easy/medium/hard)\n- estimated_time_minutes: Estimated time to answer (5-30 minutes)\n- source_reference: Reference to the specific part of the context used\n- competency_code: Kürzel der geprüften Handlungskompetenz (z.B. B3) oder null\n- ln_level: LN-Stufe der geprüften Kompetenz (1-4) oder null"

NEW_TRUE_FALSE = """You are an expert in educational assessment and exam question generation.\n\nYour task is to create a high-quality true/false question based on the provided context.\n\nContext:\n{context}\n\nTopic: {topic}\nDifficulty: {difficulty}\nLanguage: {language}\n\n{% if competencies %}\nZU PRÜFENDE HANDLUNGSKOMPETENZEN:\n{{ competencies }}\n\nJede Frage prüft genau EINE der oben genannten Handlungskompetenzen. Trage deren Kürzel als 'competency_code' und die zugehörige LN-Stufe (1-4) als 'ln_level' in die JSON-Antwort ein.\n{% endif %}\nGenerate a true/false question that:\n1. Tests understanding of a specific concept or fact from the context\n2. Is unambiguous (clearly true or clearly false)\n3. Avoids double negatives and trick wording\n4. Is suitable for open-book examination format\n5. Includes a detailed explanation\n\nFormat your response as structured JSON with the following fields:\n- question_text: The statement to evaluate (true or false)\n- correct_answer: Either "true" or "false"\n- explanation: Detailed explanation of why the statement is true or false, with reference to the context\n- difficulty: The difficulty level (easy/medium/hard)\n- source_reference: Reference to the specific part of the context used\n- competency_code: Kürzel der geprüften Handlungskompetenz (z.B. B3) oder null\n- ln_level: LN-Stufe der geprüften Kompetenz (1-4) oder null"""

OLD_MULTIPLE_CHOICE = "You are an expert in educational assessment and exam question generation.\n\nYour task is to create a high-quality multiple-choice question based on the provided context.\n\nContext:\n{context}\n\nTopic: {topic}\nDifficulty: {difficulty}\nLanguage: {language}\n\nGenerate a multiple-choice question that:\n1. Tests understanding of key concepts from the context\n2. Is suitable for open-book examination format\n3. Has one clearly correct answer\n4. Includes 3-4 plausible distractors (incorrect options)\n5. Avoids ambiguity and trick questions\n\nFormat your response as structured JSON with the following fields:\n- question_text: The question text\n- options: Array of 4 answer options (strings)\n- correct_answer: The correct option (exact match from options array)\n- explanation: Detailed explanation of why the correct answer is right and why distractors are wrong\n- difficulty: The difficulty level (easy/medium/hard)\n- source_reference: Reference to the specific part of the context used"

OLD_OPEN_ENDED = "You are an expert in educational assessment and exam question generation.\n\nYour task is to create a high-quality open-ended question based on the provided context.\n\nContext:\n{context}\n\nTopic: {topic}\nDifficulty: {difficulty}\nLanguage: {language}\n\nGenerate an open-ended question that:\n1. Requires critical thinking and analysis\n2. Is suitable for open-book examination format\n3. Cannot be answered with simple facts (requires synthesis and evaluation)\n4. Has clear evaluation criteria\n5. Allows for multiple valid approaches or perspectives\n\nFormat your response as structured JSON with the following fields:\n- question_text: The question text\n- evaluation_criteria: Array of criteria for grading (each with description and points)\n- sample_answer: A high-quality example answer\n- explanation: What makes a good answer to this question\n- difficulty: The difficulty level (easy/medium/hard)\n- estimated_time_minutes: Estimated time to answer (5-30 minutes)\n- source_reference: Reference to the specific part of the context used"

OLD_TRUE_FALSE = """You are an expert in educational assessment and exam question generation.\n\nYour task is to create a high-quality true/false question based on the provided context.\n\nContext:\n{context}\n\nTopic: {topic}\nDifficulty: {difficulty}\nLanguage: {language}\n\nGenerate a true/false question that:\n1. Tests understanding of a specific concept or fact from the context\n2. Is unambiguous (clearly true or clearly false)\n3. Avoids double negatives and trick wording\n4. Is suitable for open-book examination format\n5. Includes a detailed explanation\n\nFormat your response as structured JSON with the following fields:\n- question_text: The statement to evaluate (true or false)\n- correct_answer: Either "true" or "false"\n- explanation: Detailed explanation of why the statement is true or false, with reference to the context\n- difficulty: The difficulty level (easy/medium/hard)\n- source_reference: Reference to the specific part of the context used"""

_NEW = {
    "default_prompt_multiple_choice": NEW_MULTIPLE_CHOICE,
    "default_prompt_open_ended": NEW_OPEN_ENDED,
    "default_prompt_true_false": NEW_TRUE_FALSE,
}

_OLD = {
    "default_prompt_multiple_choice": OLD_MULTIPLE_CHOICE,
    "default_prompt_open_ended": OLD_OPEN_ENDED,
    "default_prompt_true_false": OLD_TRUE_FALSE,
}


def upgrade() -> None:
    bind = op.get_bind()
    # Nur Zeilen migrieren, die noch byte-identisch auf dem bekannten ALTEN Body
    # stehen. Individuell angepasste Default-Prompts (via Prompt-KB-UI editiert)
    # bleiben unangetastet — sonst ginge ihre Anpassung verloren.
    for name, new_content in _NEW.items():
        bind.execute(
            sa.text(
                "UPDATE prompts SET content = :new WHERE name = :n AND content = :old"
            ),
            {"new": new_content, "old": _OLD[name], "n": name},
        )


def downgrade() -> None:
    bind = op.get_bind()
    # Spiegelbildlich: nur die von upgrade() tatsächlich geänderten Zeilen
    # zurücksetzen (noch byte-identisch auf dem NEUEN Body) — ein zwischenzeitlich
    # angepasster Prompt wird nicht überschrieben.
    for name, old_content in _OLD.items():
        bind.execute(
            sa.text(
                "UPDATE prompts SET content = :old WHERE name = :n AND content = :new"
            ),
            {"old": old_content, "new": _NEW[name], "n": name},
        )
