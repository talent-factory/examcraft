"""Rebuild a generation task's result from the database (TF-964).

The Celery result is not reliable for a finished generation: it expires
(``result_expires``), and a task that died after its questions were
committed can end as FAILURE in Celery although the job row says SUCCESS.
The job row and the questions linked to it (``QuestionReview.generation_job_id``)
are the lasting record, so the result endpoint, the WebSocket and a
redelivered task all rebuild the payload from there.

The payload has the same keys as the dict ``generate_questions_task``
returns. What the generation did not persist is filled with neutral values:
the retrieval context (``context_summary.retrieved_chunks``, similarity
scores, context length) and ``generation_time``.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from models.question_generation_job import QuestionGenerationJob


def linked_question_ids(db: "Session", job: "QuestionGenerationJob") -> List[int]:
    """IDs of the questions the job created, in creation order."""
    from models.question_review import QuestionReview

    rows = (
        db.query(QuestionReview.id)
        .filter(QuestionReview.generation_job_id == job.id)
        .order_by(QuestionReview.id)
        .all()
    )
    return [row[0] for row in rows]


def build_job_result(
    db: "Session", job: "QuestionGenerationJob"
) -> Optional[Dict[str, Any]]:
    """The task result of a finished job, or None if no questions are linked.

    None covers jobs from before TF-964 (no link recorded) and jobs that
    never produced questions; callers then keep their previous behaviour.
    """
    from models.document import Document
    from models.question_review import QuestionReview, QuestionSourceDocument

    reviews = (
        db.query(QuestionReview)
        .filter(QuestionReview.generation_job_id == job.id)
        .order_by(QuestionReview.id)
        .all()
    )
    if not reviews:
        return None

    review_ids = [review.id for review in reviews]
    doc_ids_by_review: Dict[int, List[int]] = {}
    for question_id, document_id in (
        db.query(QuestionSourceDocument.question_id, QuestionSourceDocument.document_id)
        .filter(QuestionSourceDocument.question_id.in_(review_ids))
        .order_by(QuestionSourceDocument.id)
        .all()
    ):
        doc_ids_by_review.setdefault(question_id, []).append(document_id)
    all_doc_ids = list(
        dict.fromkeys(d for ids in doc_ids_by_review.values() for d in ids)
    )
    documents = (
        db.query(Document).filter(Document.id.in_(all_doc_ids)).all()
        if all_doc_ids
        else []
    )

    questions = [
        {
            "question_text": review.question_text,
            "question_type": review.question_type,
            "options": review.options,
            "correct_answer": review.correct_answer,
            "explanation": review.explanation,
            "difficulty": review.difficulty,
            "source_chunks": review.source_chunks or [],
            "source_documents": review.source_documents or [],
            "source_document_ids": doc_ids_by_review.get(review.id, []),
            "confidence_score": review.confidence_score or 0.0,
            "bloom_level": review.bloom_level,
            "estimated_time_minutes": review.estimated_time_minutes,
            "generation_metadata": review.generation_metadata,
            "competency_code": (
                review.competency.code if review.competency is not None else None
            ),
            "ln_level": review.ln_level,
        }
        for review in reviews
    ]

    # Same keys and rounding as the premium RAG service's quality metrics, but
    # only from what the questions carry; the retrieval context is gone.
    type_distribution: Dict[str, int] = {}
    for question in questions:
        qtype = question["question_type"]
        type_distribution[qtype] = type_distribution.get(qtype, 0) + 1
    generated = len(questions)
    quality_metrics: Dict[str, Any] = {
        "total_questions": generated,
        "average_confidence": round(
            sum(q["confidence_score"] for q in questions) / generated, 3
        ),
        "source_coverage": 0,
        "question_type_distribution": type_distribution,
        "context_chunks_used": 0,
        "total_context_length": 0,
        "average_similarity_score": 0,
        "requested_question_count": job.question_count,
        "generated_question_count": generated,
    }
    if job.context_limited:
        quality_metrics["context_limited"] = True

    topic = job.topic or reviews[0].topic
    return {
        "exam_id": reviews[0].exam_id,
        "topic": topic,
        "questions": questions,
        "context_summary": {
            "query": topic,
            "retrieved_chunks": [],
            "total_similarity_score": 0.0,
            "source_documents": [
                {
                    "id": document.id,
                    "filename": document.original_filename,
                    "title": document.title,
                    "chunks_used": 0,
                }
                for document in documents
            ],
            "context_length": 0,
        },
        "generation_time": 0.0,
        "quality_metrics": quality_metrics,
        "review_question_ids": review_ids,
    }
