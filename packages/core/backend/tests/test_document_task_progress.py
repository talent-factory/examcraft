"""Tests für ProgressTask und process_document Progress Updates"""

import sys
from unittest.mock import MagicMock

# Mock system-level dependencies before any project imports
if "magic" not in sys.modules:
    sys.modules["magic"] = MagicMock()

from unittest.mock import patch  # noqa: F811


class TestProgressTask:
    def test_update_progress_sets_celery_state(self):
        """update_progress() ruft self.update_state() mit korrekten Meta-Daten auf"""
        from tasks.document_tasks import ProgressTask

        task = ProgressTask()
        task.update_state = MagicMock()

        task.update_progress(3, 10, "Docling-Verarbeitung läuft...")

        task.update_state.assert_called_once_with(
            state="PROGRESS",
            meta={
                "current": 3,
                "total": 10,
                "progress": 30,
                "message": "Docling-Verarbeitung läuft...",
            },
        )

    def test_update_progress_calculates_percentage(self):
        """update_progress() berechnet progress korrekt"""
        from tasks.document_tasks import ProgressTask

        task = ProgressTask()
        task.update_state = MagicMock()

        task.update_progress(1, 10, "Test")
        call_meta = task.update_state.call_args[1]["meta"]
        assert call_meta["progress"] == 10

        task.update_state.reset_mock()
        task.update_progress(5, 10, "Test")
        call_meta = task.update_state.call_args[1]["meta"]
        assert call_meta["progress"] == 50

        task.update_state.reset_mock()
        task.update_progress(10, 10, "Test")
        call_meta = task.update_state.call_args[1]["meta"]
        assert call_meta["progress"] == 100

    def test_process_document_sends_progress_updates(self):
        """process_document sendet mindestens 5 Progress-Updates"""
        from tasks.document_tasks import process_document

        with (
            patch("tasks.document_tasks.SessionLocal") as mock_session,
            patch("tasks.document_tasks.run_async") as mock_run_async,
            patch("tasks.document_tasks.document_service"),
        ):
            mock_db = MagicMock()
            mock_session.return_value = mock_db

            mock_doc = MagicMock()
            mock_doc.id = 1
            mock_doc.original_filename = "test.pdf"
            mock_doc.status.value = "completed"
            mock_doc.has_vectors = True
            mock_db.query.return_value.filter.return_value.first.return_value = mock_doc

            mock_run_async.return_value = {
                "docling_processing": {},
                "vector_embeddings": {},
            }

            with patch.object(
                process_document, "update_progress"
            ) as mock_update_progress:
                process_document("1", "user-1")
                assert mock_update_progress.call_count >= 5, (
                    f"Erwartet >= 5 Progress-Updates, erhalten: {mock_update_progress.call_count}"
                )

    def test_process_document_progress_messages_are_german(self):
        """Alle Progress-Messages sind auf Deutsch"""
        from tasks.document_tasks import process_document

        german_messages = []

        with (
            patch("tasks.document_tasks.SessionLocal") as mock_session,
            patch("tasks.document_tasks.run_async") as mock_run_async,
            patch("tasks.document_tasks.document_service"),
        ):
            mock_db = MagicMock()
            mock_session.return_value = mock_db

            mock_doc = MagicMock()
            mock_doc.id = 1
            mock_doc.original_filename = "test.pdf"
            mock_doc.status.value = "completed"
            mock_doc.has_vectors = True
            mock_db.query.return_value.filter.return_value.first.return_value = mock_doc
            mock_run_async.return_value = {
                "docling_processing": {},
                "vector_embeddings": {},
            }

            with patch.object(
                process_document, "update_progress"
            ) as mock_update_progress:
                process_document("1", "user-1")
                for c in mock_update_progress.call_args_list:
                    msg = c[0][2]  # 3rd positional arg: message
                    german_messages.append(msg)

        assert any("..." in m for m in german_messages), (
            f"Messages scheinen nicht deutsch zu sein: {german_messages}"
        )
