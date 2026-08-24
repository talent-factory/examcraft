"""Tests for the quality/OCR fields in Document.to_dict (TF-360)."""


def test_to_dict_exposes_quality_and_ocr_flag():
    from models.document import Document

    doc = Document()
    doc.processing_info = {
        "quality": {"ok": False, "reason": "scanned_low_text", "signals": {}},
        "processed_with_ocr": True,
        "escalation": "completed",
    }

    payload = doc.to_dict()
    assert payload["quality"] == {
        "ok": False,
        "reason": "scanned_low_text",
        "signals": {},
    }
    assert payload["processed_with_ocr"] is True
    # TF-365 follow-up: the escalation field (which makes the UI badges
    # effective in the first place) must also be passed through by to_dict,
    # not just by the response schema.
    assert payload["escalation"] == "completed"


def test_to_dict_quality_defaults_when_processing_info_missing():
    from models.document import Document

    doc = Document()
    doc.processing_info = None

    payload = doc.to_dict()
    assert payload["quality"] is None
    assert payload["processed_with_ocr"] is False
