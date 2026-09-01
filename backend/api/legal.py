"""Public compliance-document endpoints (TF-746).

Unauthenticated by design — prospective school customers need to
inspect and download the AVV/TOM before they have an account, just
like ``/api/auth/register``. No DB access: the content is static (see
``services.compliance_content``), so there is nothing to authorize or
look up.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel
from services.compliance_content import (
    ComplianceDocument,
    Subprocessor,
    get_compliance_content,
)
from services.compliance_pdf_service import AvvPdfExporter, TomPdfExporter

router = APIRouter(prefix="/api/v1/legal", tags=["legal"])


class ComplianceSectionResponse(BaseModel):
    heading: str
    paragraphs: list[str]


class ComplianceDocumentResponse(BaseModel):
    title: str
    last_updated: str
    draft_notice: str
    sections: list[ComplianceSectionResponse]


class SubprocessorResponse(BaseModel):
    name: str
    purpose: str
    location: str
    transfer_mechanism: str
    change_notice: str


class ComplianceResponse(BaseModel):
    avv: ComplianceDocumentResponse
    tom: ComplianceDocumentResponse
    subprocessors: list[SubprocessorResponse]
    vvt_text: str
    state_specific_notes: ComplianceSectionResponse


def _to_subprocessor_response(subprocessor: Subprocessor) -> SubprocessorResponse:
    return SubprocessorResponse(
        name=subprocessor.name,
        purpose=subprocessor.purpose,
        location=subprocessor.location,
        transfer_mechanism=subprocessor.transfer_mechanism,
        change_notice=subprocessor.change_notice,
    )


def _to_document_response(document: ComplianceDocument) -> ComplianceDocumentResponse:
    return ComplianceDocumentResponse(
        title=document.title,
        last_updated=document.last_updated,
        draft_notice=document.draft_notice,
        sections=[
            ComplianceSectionResponse(
                heading=section.heading, paragraphs=list(section.paragraphs)
            )
            for section in document.sections
        ],
    )


@router.get("/compliance", response_model=ComplianceResponse)
async def get_compliance() -> ComplianceResponse:
    """Return the full AVV/TOM/subprocessor/VVT content for the compliance page."""
    content = get_compliance_content()
    return ComplianceResponse(
        avv=_to_document_response(content.avv),
        tom=_to_document_response(content.tom),
        subprocessors=[_to_subprocessor_response(sp) for sp in content.subprocessors],
        vvt_text=content.vvt_text,
        state_specific_notes=ComplianceSectionResponse(
            heading=content.state_specific_notes.heading,
            paragraphs=list(content.state_specific_notes.paragraphs),
        ),
    )


@router.get("/avv.pdf")
def get_avv_pdf() -> Response:
    """Return the Muster-AVV as a downloadable PDF.

    Sync handler (not ``async def``): FastAPI runs sync route functions in
    the threadpool, keeping the CPU-bound reportlab render (cached, but
    the first call per process still pays it) off the event loop — this
    endpoint is public/unauthenticated, so it can be hit at any time.
    """
    content = get_compliance_content()
    pdf_bytes = AvvPdfExporter.export(content.avv)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="ExamCraft-AVV.pdf"'},
    )


@router.get("/tom.pdf")
def get_tom_pdf() -> Response:
    """Return the TOM annex as a downloadable PDF. See ``get_avv_pdf`` for
    why this is a sync handler."""
    content = get_compliance_content()
    pdf_bytes = TomPdfExporter.export(content.tom)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="ExamCraft-TOM.pdf"'},
    )
