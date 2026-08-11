"""Tests for the TF-620 'team' document visibility tier.

Covers:
* DB CHECK constraint: visibility='team' requires org_unit_id (real INSERT,
  not just the model declaration).
* ``filter_documents_for_user`` / ``is_document_visible_for``: direct
  membership, hierarchical membership (parent Org-Unit), and non-member
  colleagues in the same institution.
* ``POST /documents/upload`` validation: team without org_unit_id, team with
  an org_unit_id the uploader doesn't belong to.
* ``PATCH /documents/{id}``: switching to team requires org_unit_id (and only
  the uploader's own memberships are valid), leaving team clears
  org_unit_id, non-owner cannot set org_unit_id.
* ``GET /org-units/mine``: only the caller's own memberships, not gated by
  ``manage_org_units``.
* ``services.org_unit_service.delete_org_unit``: 409 (via ValueError) when a
  document still references the Org-Unit.

Endpoint functions are called directly, matching the established convention
in ``test_document_visibility.py``.
"""

import asyncio

import pytest
from fastapi import HTTPException, UploadFile
from io import BytesIO
from sqlalchemy.exc import IntegrityError

from api.documents import (
    DocumentPatchRequest,
    list_documents,
    update_document,
    upload_document,
)
from api.org_units import list_my_org_units
from models.auth import Institution, User, UserStatus
from models.document import Document, DocumentStatus, DocumentVisibility
from models.org_unit import OrgUnit, UserOrgUnit
from services.org_unit_service import delete_org_unit
from utils.document_visibility import filter_documents_for_user, is_document_visible_for


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def _institution(db, iid, slug):
    inst = Institution(
        id=iid,
        name=f"Inst {iid}",
        slug=slug,
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    db.add(inst)
    db.flush()
    return inst


def _user(db, uid, email, institution_id):
    user = User(
        id=uid,
        email=email,
        first_name="F",
        last_name="L",
        password_hash="x",
        institution_id=institution_id,
        status=UserStatus.ACTIVE.value,
    )
    db.add(user)
    db.flush()
    return user


def _team_tree(db, institution_id):
    """abteilung -> team (two levels, matching the org_unit_service tests)."""
    abteilung = OrgUnit(
        institution_id=institution_id, unit_type="abteilung", name="Info"
    )
    db.add(abteilung)
    db.flush()
    team = OrgUnit(
        institution_id=institution_id,
        unit_type="team",
        name="Backend",
        parent_org_unit_id=abteilung.id,
    )
    db.add(team)
    db.commit()
    return abteilung, team


def _doc(db, did, owner_id, institution_id, visibility, org_unit_id=None):
    doc = Document(
        id=did,
        filename=f"{did}.pdf",
        original_filename=f"{did}.pdf",
        file_path=f"/tmp/{did}.pdf",
        file_size=10,
        mime_type="application/pdf",
        status=DocumentStatus.PROCESSED,
        institution_id=institution_id,
        user_id=owner_id,
        visibility=visibility,
        org_unit_id=org_unit_id,
    )
    db.add(doc)
    db.commit()
    return doc


@pytest.fixture
def team_data(test_db):
    inst = _institution(test_db, 7200, "tf620-inst")
    abteilung, team = _team_tree(test_db, inst.id)

    owner = _user(test_db, 7200, "owner@tf620.ch", inst.id)
    team_member = _user(test_db, 7201, "teammate@tf620.ch", inst.id)
    abteilung_member = _user(test_db, 7202, "abtchef@tf620.ch", inst.id)
    outsider = _user(test_db, 7203, "outsider@tf620.ch", inst.id)

    test_db.add_all(
        [
            UserOrgUnit(user_id=owner.id, org_unit_id=team.id),
            UserOrgUnit(user_id=team_member.id, org_unit_id=team.id),
            UserOrgUnit(user_id=abteilung_member.id, org_unit_id=abteilung.id),
        ]
    )
    test_db.commit()

    doc_team = _doc(
        test_db, 7200, owner.id, inst.id, DocumentVisibility.TEAM, org_unit_id=team.id
    )

    return dict(
        inst=inst,
        abteilung=abteilung,
        team=team,
        owner=owner,
        team_member=team_member,
        abteilung_member=abteilung_member,
        outsider=outsider,
        doc_team=doc_team,
    )


# ---------------------------------------------------------------------------
# DB constraint
# ---------------------------------------------------------------------------


def test_team_visibility_requires_org_unit_id_at_db_level(test_db):
    inst = _institution(test_db, 7210, "tf620-constraint")
    doc = Document(
        id=7210,
        filename="x.pdf",
        original_filename="x.pdf",
        file_path="/tmp/x.pdf",
        file_size=1,
        mime_type="application/pdf",
        status=DocumentStatus.PROCESSED,
        institution_id=inst.id,
        user_id=None,
        visibility=DocumentVisibility.TEAM,
        org_unit_id=None,
    )
    test_db.add(doc)
    with pytest.raises(IntegrityError):
        test_db.commit()
    test_db.rollback()


def test_org_unit_id_set_without_team_visibility_rejected_at_db_level(test_db):
    """The other direction of the biconditional: org_unit_id must be NULL for
    every visibility other than 'team', not just non-NULL for 'team'."""
    inst = _institution(test_db, 7211, "tf620-constraint-2")
    abteilung = OrgUnit(institution_id=inst.id, unit_type="abteilung", name="X")
    test_db.add(abteilung)
    test_db.commit()
    doc = Document(
        id=7211,
        filename="x.pdf",
        original_filename="x.pdf",
        file_path="/tmp/x.pdf",
        file_size=1,
        mime_type="application/pdf",
        status=DocumentStatus.PROCESSED,
        institution_id=inst.id,
        user_id=None,
        visibility=DocumentVisibility.PRIVATE,
        org_unit_id=abteilung.id,
    )
    test_db.add(doc)
    with pytest.raises(IntegrityError):
        test_db.commit()
    test_db.rollback()


# ---------------------------------------------------------------------------
# filter_documents_for_user / is_document_visible_for
# ---------------------------------------------------------------------------


def test_team_doc_visible_to_direct_member(team_data, test_db):
    assert is_document_visible_for(
        team_data["team_member"], team_data["doc_team"], test_db
    )
    ids = {
        d.id
        for d in filter_documents_for_user(
            test_db.query(Document), team_data["team_member"], test_db
        ).all()
    }
    assert team_data["doc_team"].id in ids


def test_team_doc_visible_to_ancestor_org_unit_member(team_data, test_db):
    """Hierarchical read access: a member of the parent 'abteilung' also sees
    documents scoped to a child 'team' (per the approved plan)."""
    assert is_document_visible_for(
        team_data["abteilung_member"], team_data["doc_team"], test_db
    )


def test_team_doc_not_visible_to_unrelated_colleague(team_data, test_db):
    """Same institution, no membership in the team or an ancestor -> hidden."""
    assert not is_document_visible_for(
        team_data["outsider"], team_data["doc_team"], test_db
    )
    ids = {
        d.id
        for d in filter_documents_for_user(
            test_db.query(Document), team_data["outsider"], test_db
        ).all()
    }
    assert team_data["doc_team"].id not in ids


def test_team_doc_visible_to_owner_regardless_of_membership(team_data, test_db):
    assert is_document_visible_for(team_data["owner"], team_data["doc_team"], test_db)


def test_team_doc_not_visible_to_sibling_org_unit_member(team_data, test_db):
    """A member of a SIBLING team (same parent abteilung, not an ancestor of
    `team`) must be denied — distinct from the zero-membership outsider case
    above. get_user_accessible_org_unit_ids only returns each membership's
    own descendant closure, never siblings or ancestors-of-ancestors; this
    pins that a traversal regression widening it would be caught."""
    sibling_team = OrgUnit(
        institution_id=team_data["inst"].id,
        unit_type="team",
        name="Frontend",
        parent_org_unit_id=team_data["abteilung"].id,
    )
    test_db.add(sibling_team)
    test_db.commit()
    sibling_member = _user(test_db, 7205, "frontend@tf620.ch", team_data["inst"].id)
    test_db.add(UserOrgUnit(user_id=sibling_member.id, org_unit_id=sibling_team.id))
    test_db.commit()

    assert not is_document_visible_for(sibling_member, team_data["doc_team"], test_db)
    ids = {
        d.id
        for d in filter_documents_for_user(
            test_db.query(Document), sibling_member, test_db
        ).all()
    }
    assert team_data["doc_team"].id not in ids


# ---------------------------------------------------------------------------
# POST /documents/upload — validation only (fails before touching storage)
# ---------------------------------------------------------------------------


def _upload_file():
    return UploadFile(filename="x.pdf", file=BytesIO(b"x"))


def test_upload_team_without_org_unit_id_rejected(team_data, test_db):
    with pytest.raises(HTTPException) as exc:
        _run(
            upload_document(
                file=_upload_file(),
                visibility=DocumentVisibility.TEAM,
                org_unit_id=None,
                http_request=None,
                current_user=team_data["owner"],
                db=test_db,
            )
        )
    assert exc.value.status_code == 400


def test_upload_team_with_foreign_org_unit_id_rejected(team_data, test_db):
    """org_unit_id must be one of the uploader's own memberships — the
    outsider is not a member of `team`, even though it exists in their own
    institution."""
    with pytest.raises(HTTPException) as exc:
        _run(
            upload_document(
                file=_upload_file(),
                visibility=DocumentVisibility.TEAM,
                org_unit_id=team_data["team"].id,
                http_request=None,
                current_user=team_data["outsider"],
                db=test_db,
            )
        )
    assert exc.value.status_code == 400


# ---------------------------------------------------------------------------
# PATCH /documents/{id}
# ---------------------------------------------------------------------------


def test_patch_switch_to_team_without_org_unit_id_rejected(team_data, test_db):
    private_doc = _doc(
        test_db,
        7220,
        team_data["owner"].id,
        team_data["inst"].id,
        DocumentVisibility.PRIVATE,
    )
    payload = DocumentPatchRequest(visibility=DocumentVisibility.TEAM)
    with pytest.raises(HTTPException) as exc:
        _run(
            update_document(
                document_id=private_doc.id,
                payload=payload,
                request=None,
                current_user=team_data["owner"],
                db=test_db,
            )
        )
    assert exc.value.status_code == 400


def test_patch_switch_to_team_with_own_org_unit_succeeds(team_data, test_db):
    private_doc = _doc(
        test_db,
        7221,
        team_data["owner"].id,
        team_data["inst"].id,
        DocumentVisibility.PRIVATE,
    )
    payload = DocumentPatchRequest(
        visibility=DocumentVisibility.TEAM, org_unit_id=team_data["team"].id
    )
    resp = _run(
        update_document(
            document_id=private_doc.id,
            payload=payload,
            request=None,
            current_user=team_data["owner"],
            db=test_db,
        )
    )
    assert resp.visibility == "team"
    assert resp.org_unit_id == team_data["team"].id
    assert resp.org_unit_name == team_data["team"].name


def test_patch_leaving_team_clears_org_unit_id(team_data, test_db):
    payload = DocumentPatchRequest(visibility=DocumentVisibility.PRIVATE)
    resp = _run(
        update_document(
            document_id=team_data["doc_team"].id,
            payload=payload,
            request=None,
            current_user=team_data["owner"],
            db=test_db,
        )
    )
    assert resp.visibility == "private"
    assert resp.org_unit_id is None
    test_db.refresh(team_data["doc_team"])
    assert team_data["doc_team"].org_unit_id is None


def test_patch_org_unit_id_without_team_visibility_rejected(team_data, test_db):
    private_doc = _doc(
        test_db,
        7222,
        team_data["owner"].id,
        team_data["inst"].id,
        DocumentVisibility.PRIVATE,
    )
    payload = DocumentPatchRequest(org_unit_id=team_data["team"].id)
    with pytest.raises(HTTPException) as exc:
        _run(
            update_document(
                document_id=private_doc.id,
                payload=payload,
                request=None,
                current_user=team_data["owner"],
                db=test_db,
            )
        )
    assert exc.value.status_code == 400


def test_patch_non_owner_cannot_change_org_unit_id(team_data, test_db):
    """team_member can SEE the team-visible doc but is not its owner."""
    payload = DocumentPatchRequest(org_unit_id=team_data["team"].id)
    with pytest.raises(HTTPException) as exc:
        _run(
            update_document(
                document_id=team_data["doc_team"].id,
                payload=payload,
                request=None,
                current_user=team_data["team_member"],
                db=test_db,
            )
        )
    assert exc.value.status_code == 403


def test_patch_display_name_only_by_owner_who_left_org_unit_does_not_revalidate(
    team_data, test_db
):
    """A display_name-only PATCH must not re-check the CALLER's *current*
    org-unit membership just because the document happens to be
    team-visible. Regression for the bug where an owner who has since left
    the Org-Unit could no longer rename their own document."""
    doc = _doc(
        test_db,
        7223,
        team_data["outsider"].id,  # owner has NO membership in team/abteilung
        team_data["inst"].id,
        DocumentVisibility.TEAM,
        org_unit_id=team_data["team"].id,
    )
    payload = DocumentPatchRequest(display_name="Renamed")
    resp = _run(
        update_document(
            document_id=doc.id,
            payload=payload,
            request=None,
            current_user=team_data["outsider"],
            db=test_db,
        )
    )
    assert resp.display_name == "Renamed"
    assert resp.visibility == "team"
    assert resp.org_unit_id == team_data["team"].id


def test_patch_display_name_only_by_superuser_does_not_revalidate_org_unit(
    team_data, test_db
):
    """Same bug, SuperUser variant: the SuperUser bypass preserved elsewhere
    in this endpoint (owner checks) must also apply here — a SuperUser
    editing an unrelated field on someone else's team-visible document must
    not be rejected just because they aren't personally an Org-Unit member."""
    # Belongs to the institution (institution_id is NOT NULL on User) but has
    # no Org-Unit membership of their own -- exactly the situation a platform
    # admin is normally in.
    superuser = _user(test_db, 7204, "root@tf620.ch", team_data["inst"].id)
    superuser.is_superuser = True
    test_db.commit()

    payload = DocumentPatchRequest(display_name="Renamed by root")
    resp = _run(
        update_document(
            document_id=team_data["doc_team"].id,
            payload=payload,
            request=None,
            current_user=superuser,
            db=test_db,
        )
    )
    assert resp.display_name == "Renamed by root"
    assert resp.visibility == "team"
    assert resp.org_unit_id == team_data["team"].id


def test_patch_leaving_team_rejects_simultaneous_org_unit_id_instead_of_dropping_it(
    team_data, test_db
):
    """{visibility: <non-team>, org_unit_id: X} in the same request must be
    rejected, not silently accepted with org_unit_id dropped — branch-order
    regression: the "left team, clear org_unit_id" cleanup must not run
    before the "org_unit_id supplied without team" rejection."""
    payload = DocumentPatchRequest(
        visibility=DocumentVisibility.PRIVATE, org_unit_id=team_data["abteilung"].id
    )
    with pytest.raises(HTTPException) as exc:
        _run(
            update_document(
                document_id=team_data["doc_team"].id,
                payload=payload,
                request=None,
                current_user=team_data["owner"],
                db=test_db,
            )
        )
    assert exc.value.status_code == 400
    # And the document must be unchanged -- the rejected request didn't
    # half-apply before raising.
    test_db.refresh(team_data["doc_team"])
    assert team_data["doc_team"].visibility == DocumentVisibility.TEAM
    assert team_data["doc_team"].org_unit_id == team_data["team"].id


# ---------------------------------------------------------------------------
# GET /org-units/mine
# ---------------------------------------------------------------------------


def test_list_my_org_units_returns_only_own_memberships(team_data, test_db):
    resp = _run(list_my_org_units(current_user=team_data["owner"], db=test_db))
    ids = {item.id for item in resp.items}
    assert ids == {team_data["team"].id}

    resp_outsider = _run(
        list_my_org_units(current_user=team_data["outsider"], db=test_db)
    )
    assert resp_outsider.items == []


# ---------------------------------------------------------------------------
# delete_org_unit — referential integrity (TF-620)
# ---------------------------------------------------------------------------


def test_delete_org_unit_referenced_by_document_raises(team_data, test_db):
    with pytest.raises(ValueError, match="kann nicht geloescht werden"):
        delete_org_unit(test_db, team_data["team"])
    test_db.rollback()
    # The org_unit must still exist — the failed delete didn't half-apply.
    assert (
        test_db.query(OrgUnit).filter_by(id=team_data["team"].id).one_or_none()
        is not None
    )


# ---------------------------------------------------------------------------
# GET /documents (list) — _org_unit_names_map batching
# ---------------------------------------------------------------------------


def test_list_documents_resolves_distinct_org_unit_names_per_row(team_data, test_db):
    """The paginated list endpoint batch-resolves every row's org_unit_name
    in one query (_org_unit_names_map) instead of one query per row. A
    dict-key mismatch or off-by-one there would silently return None (or
    the wrong name) for some rows -- exercise it with >1 distinct org units
    on the page, including a non-team row, to pin the mapping is correct."""
    doc_abteilung = _doc(
        test_db,
        7224,
        team_data["abteilung_member"].id,
        team_data["inst"].id,
        DocumentVisibility.TEAM,
        org_unit_id=team_data["abteilung"].id,
    )
    doc_private = _doc(
        test_db,
        7225,
        team_data["abteilung_member"].id,
        team_data["inst"].id,
        DocumentVisibility.PRIVATE,
    )

    # abteilung_member is a member of the parent -- the hierarchical closure
    # grants them access to both the abteilung- and the team-scoped doc.
    resp = _run(
        list_documents(
            page_size=50,
            request=None,
            current_user=team_data["abteilung_member"],
            db=test_db,
        )
    )
    by_id = {d.id: d for d in resp.documents}

    assert by_id[team_data["doc_team"].id].org_unit_name == team_data["team"].name
    assert by_id[doc_abteilung.id].org_unit_name == team_data["abteilung"].name
    assert by_id[doc_private.id].org_unit_name is None
