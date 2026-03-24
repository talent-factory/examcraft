"""Tests for preferred_language in profile API."""

import pytest
from pydantic import ValidationError


class TestUserProfileUpdateModel:
    """Test that UserProfileUpdate accepts preferred_language."""

    def test_valid_language_de(self):
        from api.auth import UserProfileUpdate

        update = UserProfileUpdate(preferred_language="de")
        assert update.preferred_language == "de"

    def test_valid_language_en(self):
        from api.auth import UserProfileUpdate

        update = UserProfileUpdate(preferred_language="en")
        assert update.preferred_language == "en"

    def test_valid_language_fr(self):
        from api.auth import UserProfileUpdate

        update = UserProfileUpdate(preferred_language="fr")
        assert update.preferred_language == "fr"

    def test_valid_language_it(self):
        from api.auth import UserProfileUpdate

        update = UserProfileUpdate(preferred_language="it")
        assert update.preferred_language == "it"

    def test_none_language(self):
        from api.auth import UserProfileUpdate

        update = UserProfileUpdate()
        assert update.preferred_language is None

    def test_invalid_language_rejected(self):
        from api.auth import UserProfileUpdate

        with pytest.raises(ValidationError):
            UserProfileUpdate(preferred_language="ja")

    def test_invalid_language_empty_string_rejected(self):
        from api.auth import UserProfileUpdate

        with pytest.raises(ValidationError):
            UserProfileUpdate(preferred_language="")

    def test_language_in_model_dump(self):
        from api.auth import UserProfileUpdate

        update = UserProfileUpdate(preferred_language="fr")
        data = update.model_dump(exclude_unset=True)
        assert data["preferred_language"] == "fr"


class TestUserProfileResponseModel:
    """Test that UserProfileResponse includes preferred_language."""

    def test_response_has_language_field(self):
        from api.auth import UserProfileResponse

        fields = UserProfileResponse.model_fields
        assert "preferred_language" in fields
