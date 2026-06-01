"""TF-365: DocumentResponse muss die OCR-/Qualitäts-Felder durchreichen.

TF-361 ergänzte ``quality`` + ``processed_with_ocr`` in ``Document.to_dict()``
sowie die Frontend-Badges — aber das Pydantic-Schema ``DocumentResponse`` (über
das jede Listen-/Detail-Antwort serialisiert wird, ``DocumentResponse(**to_dict())``)
deklarierte diese Felder nie. Pydantic verwirft unbekannte Keys still
(``extra='ignore'``), also kamen die Badge-Daten nie im Frontend an — die
TF-361-Badges waren faktisch tot. Dieser Test pinnt, dass ``quality``,
``processed_with_ocr`` und ``escalation`` (TF-365) im serialisierten Response
erhalten bleiben.
"""

from api.documents import DocumentResponse


def _payload(**overrides):
    base = {
        "id": 1,
        "filename": "scan.pdf",
        "original_filename": "scan.pdf",
        "title": "scan",
        "display_name": None,
        "file_size": 100,
        "mime_type": "application/pdf",
        "status": "processed",
        "visibility": None,
        "user_id": 1,
        "metadata": {},
        "content_preview": None,
        "vector_collection": None,
        "has_vectors": True,
        "created_at": None,
        "updated_at": None,
        "processed_at": None,
    }
    base.update(overrides)
    return base


def test_document_response_preserves_quality_and_ocr_and_escalation():
    resp = DocumentResponse(
        **_payload(
            quality={"ok": False, "reason": "scanned_low_text"},
            processed_with_ocr=True,
            escalation="queued",
        )
    )
    dumped = resp.model_dump()

    assert dumped["quality"] == {"ok": False, "reason": "scanned_low_text"}
    assert dumped["processed_with_ocr"] is True
    assert dumped["escalation"] == "queued"


def test_document_response_defaults_when_fields_absent():
    """Ältere Rows ohne OCR-/Qualitäts-Felder serialisieren mit sicheren Defaults."""
    dumped = DocumentResponse(**_payload()).model_dump()

    assert dumped["quality"] is None
    assert dumped["processed_with_ocr"] is False
    assert dumped["escalation"] is None
