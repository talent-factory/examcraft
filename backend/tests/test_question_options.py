"""Unit tests for ``utils.question_options.normalize_options`` (TF-330)."""

from unittest.mock import patch

import pytest

from utils.question_options import normalize_options


class TestNormalizeOptions:
    def test_none_passes_through(self):
        assert normalize_options(None) is None

    def test_list_kept_with_str_coercion(self):
        assert normalize_options(["A", "B", "C"]) == ["A", "B", "C"]

    def test_list_with_non_str_items_is_coerced(self):
        assert normalize_options([1, 2, 3]) == ["1", "2", "3"]

    def test_empty_list_stays_empty(self):
        assert normalize_options([]) == []

    def test_dict_a_b_c_d_ordered_by_sorted_key(self):
        legacy = {
            "A": "Verwenden Sie aktive Sprache",
            "B": "Schreiben Sie passiv",
            "C": "Antworten Sie spät",
            "D": "Melden Sie sich bis Freitag",
        }
        assert normalize_options(legacy) == [
            "Verwenden Sie aktive Sprache",
            "Schreiben Sie passiv",
            "Antworten Sie spät",
            "Melden Sie sich bis Freitag",
        ]

    def test_dict_unsorted_input_is_sorted_by_key(self):
        legacy = {"D": "vier", "B": "zwei", "A": "eins", "C": "drei"}
        assert normalize_options(legacy) == ["eins", "zwei", "drei", "vier"]

    def test_dict_with_non_str_values_is_coerced(self):
        assert normalize_options({"A": 1, "B": 2}) == ["1", "2"]

    def test_dict_with_none_value_is_coerced_to_str_none(self):
        # 'None' is the str() of None — explicit so a future maintainer
        # doesn't accidentally swallow it as Python ``None``.
        assert normalize_options({"A": None, "B": "x"}) == ["None", "x"]

    def test_empty_dict_returns_empty_list(self):
        assert normalize_options({}) == []

    @pytest.mark.parametrize("value", [42, 3.14, "string", True])
    def test_unsupported_scalar_returns_none(self, value):
        # Defensive: never crash a read path on a corrupt legacy row.
        assert normalize_options(value) is None

    def test_dict_branch_emits_warning(self):
        # Patch the module logger directly: caplog is fragile when the full
        # suite runs (other tests reconfigure root logging / propagation).
        with patch("utils.question_options.logger") as mock_log:
            normalize_options({"A": "x", "B": "y"})
        mock_log.warning.assert_called_once()
        msg = mock_log.warning.call_args[0][0]
        assert "legacy_dict_shape" in msg, (
            "dict shape must be logged at WARNING for migration tracking"
        )

    def test_unsupported_type_emits_error(self):
        with patch("utils.question_options.logger") as mock_log:
            normalize_options(42)
        mock_log.error.assert_called_once()
        msg = mock_log.error.call_args[0][0]
        assert "unsupported_type" in msg, (
            "unknown shapes must surface as ERROR — silent None hides corruption"
        )

    def test_list_path_does_not_log(self):
        # Hot path: canonical list must not flood logs.
        with patch("utils.question_options.logger") as mock_log:
            normalize_options(["a", "b"])
        mock_log.warning.assert_not_called()
        mock_log.error.assert_not_called()
