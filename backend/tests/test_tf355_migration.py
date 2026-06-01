"""TF-355: schema-presence guard for document_tags table + ux_tags_user_name index.

These pass via Base.metadata.create_all() (the model declares both). They lock in
that the table + index stay in the ORM schema. The migration itself is verified by
an alembic round-trip (see the task notes), because the test DB never runs migrations.
"""

from sqlalchemy import inspect, text


def test_document_tags_table_exists(test_db):
    insp = inspect(test_db.get_bind())
    assert "document_tags" in insp.get_table_names()
    cols = {c["name"] for c in insp.get_columns("document_tags")}
    assert {"document_id", "tag_id", "created_at"} <= cols


def test_ux_tags_user_name_partial_index_exists(test_db):
    row = test_db.execute(
        text("SELECT indexdef FROM pg_indexes WHERE indexname = 'ux_tags_user_name'")
    ).first()
    assert row is not None, "ux_tags_user_name index missing"
    assert "scope" in row[0].lower()
