"""
One-time script to enrich existing questions with bloom_level and estimated_time_minutes.
Bloom-level is determined by Claude API in batches.
Estimated time is computed via a lookup table.

Usage:
    cd packages/core/backend
    python ../../../scripts/enrich_question_metadata.py

Requires:
    - DATABASE_URL env var (or .env file)
    - ANTHROPIC_API_KEY env var (or .env file)
"""

import json
import logging
import os
import sys

from dotenv import load_dotenv

# Add backend to path so we can import models
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "packages", "core", "backend"))

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import anthropic
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.question_review import QuestionReview

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

TIME_ESTIMATES = {
    ("multiple_choice", "easy"): 1,
    ("multiple_choice", "medium"): 2,
    ("multiple_choice", "hard"): 3,
    ("true_false", "easy"): 1,
    ("true_false", "medium"): 1,
    ("true_false", "hard"): 2,
    ("open_ended", "easy"): 3,
    ("open_ended", "medium"): 5,
    ("open_ended", "hard"): 8,
}

BATCH_SIZE = 10


def get_bloom_levels(client: anthropic.Anthropic, questions: list[dict]) -> list[dict]:
    """Ask Claude to determine bloom levels for a batch of questions."""
    questions_text = json.dumps(questions, ensure_ascii=False, indent=2)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": f"""Bestimme die Bloom-Taxonomie-Stufe (1-6) fuer jede Frage:
1=Erinnern, 2=Verstehen, 3=Anwenden, 4=Analysieren, 5=Bewerten, 6=Erschaffen

Fragen:
{questions_text}

Antwort als JSON-Array (NUR das Array, kein Markdown):
[{{"id": 1, "bloom_level": 3}}, ...]""",
            }
        ],
    )

    text = response.content[0].text.strip()
    # Handle potential markdown code fences
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    return json.loads(text)


def main():
    database_url = os.getenv("DATABASE_URL", "postgresql://examcraft:examcraft_dev@localhost:5432/examcraft")
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set")
        sys.exit(1)

    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    db = Session()
    client = anthropic.Anthropic(api_key=api_key)

    # Find questions missing bloom_level
    questions_to_enrich = (
        db.query(QuestionReview)
        .filter(QuestionReview.bloom_level.is_(None))
        .all()
    )

    total = len(questions_to_enrich)
    logger.info(f"Found {total} questions to enrich")

    if total == 0:
        logger.info("Nothing to do")
        return

    enriched = 0
    for i in range(0, total, BATCH_SIZE):
        batch = questions_to_enrich[i : i + BATCH_SIZE]

        batch_data = [
            {"id": q.id, "question": q.question_text, "type": q.question_type}
            for q in batch
        ]

        try:
            results = get_bloom_levels(client, batch_data)
            bloom_map = {r["id"]: r["bloom_level"] for r in results}

            for q in batch:
                bloom = bloom_map.get(q.id)
                if bloom and 1 <= bloom <= 6:
                    q.bloom_level = bloom

                if q.estimated_time_minutes is None:
                    q.estimated_time_minutes = TIME_ESTIMATES.get(
                        (q.question_type, q.difficulty), 3
                    )

            db.commit()
            enriched += len(batch)
            logger.info(f"Progress: {enriched}/{total} questions enriched")

        except Exception as e:
            logger.error(f"Batch {i}-{i + BATCH_SIZE} failed: {e}")
            db.rollback()
            continue

    logger.info(f"Done. Enriched {enriched}/{total} questions.")
    db.close()


if __name__ == "__main__":
    main()
