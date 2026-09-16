"""
Unit tests for StorageService (services/storage_service.py)

boto3 is mocked throughout — no real S3/Tigris endpoint is contacted.
Each test builds its own StorageService instance (not the module-level
singleton) so environment-variable configuration stays isolated.
"""

import pytest
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError

from services.storage_service import (
    StorageService,
    StorageAccessDeniedError,
    StorageThrottledError,
    StorageUnavailableError,
    StorageConfigurationError,
)


def _client_error(code, status=None, message="error"):
    error_response = {"Error": {"Code": code, "Message": message}}
    if status is not None:
        error_response["ResponseMetadata"] = {"HTTPStatusCode": status}
    return ClientError(error_response, "SomeOperation")


@pytest.fixture
def configured_env(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setenv("BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("AWS_ENDPOINT_URL_S3", "https://s3.example.com")
    monkeypatch.setenv("AWS_REGION", "eu-central-1")


@pytest.fixture
def unconfigured_env(monkeypatch):
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)


@pytest.fixture
def mock_boto_client():
    with patch("services.storage_service.boto3.client") as mock_client_factory:
        client = MagicMock()
        mock_client_factory.return_value = client
        yield mock_client_factory, client


class TestConfiguration:
    def test_is_configured_true_when_credentials_present(self, configured_env):
        service = StorageService()
        assert service.is_configured is True

    def test_is_configured_false_when_credentials_missing(self, unconfigured_env):
        service = StorageService()
        assert service.is_configured is False

    def test_bucket_name_defaults(self, unconfigured_env, monkeypatch):
        monkeypatch.delenv("BUCKET_NAME", raising=False)
        service = StorageService()
        assert service.bucket_name == "examcraft-uploads"

    def test_bucket_name_from_env(self, configured_env):
        service = StorageService()
        assert service.bucket_name == "test-bucket"

    def test_region_defaults_to_auto(self, unconfigured_env, monkeypatch):
        monkeypatch.delenv("AWS_REGION", raising=False)
        service = StorageService()
        assert service.region == "auto"

    def test_endpoint_url_from_env(self, configured_env):
        service = StorageService()
        assert service.endpoint_url == "https://s3.example.com"

    def test_s3_client_none_when_not_configured(self, unconfigured_env):
        service = StorageService()
        assert service.s3_client is None

    def test_s3_client_lazily_created_once(self, configured_env, mock_boto_client):
        factory, client = mock_boto_client
        service = StorageService()

        first = service.s3_client
        second = service.s3_client

        assert first is client
        assert second is client
        factory.assert_called_once_with(
            "s3",
            endpoint_url="https://s3.example.com",
            aws_access_key_id="key",
            aws_secret_access_key="secret",
            region_name="eu-central-1",
        )


class TestUploadFile:
    def test_raises_when_not_configured(self, unconfigured_env):
        service = StorageService()
        with pytest.raises(RuntimeError, match="not configured"):
            service.upload_file(b"data", "key.txt")

    def test_success_returns_object_key(self, configured_env, mock_boto_client):
        _, client = mock_boto_client
        service = StorageService()

        result = service.upload_file(b"data", "key.txt", content_type="text/plain")

        assert result == "key.txt"
        client.put_object.assert_called_once_with(
            Bucket="test-bucket", Key="key.txt", Body=b"data", ContentType="text/plain"
        )

    def test_client_error_raises_runtime_error(self, configured_env, mock_boto_client):
        _, client = mock_boto_client
        client.put_object.side_effect = _client_error("InternalError")
        service = StorageService()

        with pytest.raises(RuntimeError, match="S3 upload failed"):
            service.upload_file(b"data", "key.txt")


class TestDownloadFile:
    def test_raises_when_not_configured(self, unconfigured_env):
        service = StorageService()
        with pytest.raises(RuntimeError, match="not configured"):
            service.download_file("key.txt")

    def test_success_returns_bytes(self, configured_env, mock_boto_client):
        _, client = mock_boto_client
        body = MagicMock()
        body.read.return_value = b"file-contents"
        client.get_object.return_value = {"Body": body}
        service = StorageService()

        result = service.download_file("key.txt")

        assert result == b"file-contents"

    @pytest.mark.parametrize("code", ["NoSuchKey", "NoSuchBucket", "404"])
    def test_not_found_raises_file_not_found(
        self, configured_env, mock_boto_client, code
    ):
        _, client = mock_boto_client
        client.get_object.side_effect = _client_error(code)
        service = StorageService()

        with pytest.raises(FileNotFoundError):
            service.download_file("key.txt")

    @pytest.mark.parametrize("code", ["AccessDenied", "403"])
    def test_access_denied_raises_storage_access_denied(
        self, configured_env, mock_boto_client, code
    ):
        _, client = mock_boto_client
        client.get_object.side_effect = _client_error(code)
        service = StorageService()

        with pytest.raises(StorageAccessDeniedError):
            service.download_file("key.txt")

    @pytest.mark.parametrize(
        "code", ["SlowDown", "Throttling", "ThrottlingException", "429"]
    )
    def test_throttled_raises_storage_throttled(
        self, configured_env, mock_boto_client, code
    ):
        _, client = mock_boto_client
        client.get_object.side_effect = _client_error(code)
        service = StorageService()

        with pytest.raises(StorageThrottledError):
            service.download_file("key.txt")

    def test_service_unavailable_by_code_raises_storage_unavailable(
        self, configured_env, mock_boto_client
    ):
        _, client = mock_boto_client
        client.get_object.side_effect = _client_error("ServiceUnavailable")
        service = StorageService()

        with pytest.raises(StorageUnavailableError):
            service.download_file("key.txt")

    def test_service_unavailable_by_5xx_status_raises_storage_unavailable(
        self, configured_env, mock_boto_client
    ):
        _, client = mock_boto_client
        client.get_object.side_effect = _client_error("SomethingElse", status=503)
        service = StorageService()

        with pytest.raises(StorageUnavailableError):
            service.download_file("key.txt")

    @pytest.mark.parametrize(
        "code",
        [
            "InvalidAccessKeyId",
            "SignatureDoesNotMatch",
            "ExpiredToken",
            "InvalidToken",
            "IllegalLocationConstraintException",
        ],
    )
    def test_misconfiguration_raises_storage_configuration_error(
        self, configured_env, mock_boto_client, code
    ):
        _, client = mock_boto_client
        client.get_object.side_effect = _client_error(code)
        service = StorageService()

        with pytest.raises(StorageConfigurationError):
            service.download_file("key.txt")

    def test_unknown_error_code_raises_generic_runtime_error(
        self, configured_env, mock_boto_client
    ):
        _, client = mock_boto_client
        client.get_object.side_effect = _client_error("TotallyUnknownCode")
        service = StorageService()

        with pytest.raises(RuntimeError, match="S3 download failed"):
            service.download_file("key.txt")


class TestDeleteFile:
    def test_raises_when_not_configured(self, unconfigured_env):
        service = StorageService()
        with pytest.raises(RuntimeError, match="not configured"):
            service.delete_file("key.txt")

    def test_success_returns_true(self, configured_env, mock_boto_client):
        _, client = mock_boto_client
        service = StorageService()

        assert service.delete_file("key.txt") is True
        client.delete_object.assert_called_once_with(
            Bucket="test-bucket", Key="key.txt"
        )

    def test_client_error_raises_runtime_error(self, configured_env, mock_boto_client):
        _, client = mock_boto_client
        client.delete_object.side_effect = _client_error("InternalError")
        service = StorageService()

        with pytest.raises(RuntimeError, match="S3 delete failed"):
            service.delete_file("key.txt")


class TestPresignedUrl:
    def test_raises_when_not_configured(self, unconfigured_env):
        service = StorageService()
        with pytest.raises(RuntimeError, match="not configured"):
            service.get_presigned_url("key.txt")

    def test_download_url_uses_get_object(self, configured_env, mock_boto_client):
        _, client = mock_boto_client
        client.generate_presigned_url.return_value = "https://signed.example.com/get"
        service = StorageService()

        result = service.get_presigned_url("key.txt", expires_in=120)

        assert result == "https://signed.example.com/get"
        client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "test-bucket", "Key": "key.txt"},
            ExpiresIn=120,
        )

    def test_upload_url_uses_put_object(self, configured_env, mock_boto_client):
        _, client = mock_boto_client
        client.generate_presigned_url.return_value = "https://signed.example.com/put"
        service = StorageService()

        result = service.get_presigned_url("key.txt", for_upload=True)

        assert result == "https://signed.example.com/put"
        client.generate_presigned_url.assert_called_once_with(
            "put_object",
            Params={"Bucket": "test-bucket", "Key": "key.txt"},
            ExpiresIn=3600,
        )

    def test_client_error_raises_runtime_error(self, configured_env, mock_boto_client):
        _, client = mock_boto_client
        client.generate_presigned_url.side_effect = _client_error("InternalError")
        service = StorageService()

        with pytest.raises(RuntimeError, match="Presigned URL generation failed"):
            service.get_presigned_url("key.txt")


class TestFileExists:
    def test_false_when_not_configured(self, unconfigured_env):
        service = StorageService()
        assert service.file_exists("key.txt") is False

    def test_true_when_head_object_succeeds(self, configured_env, mock_boto_client):
        service = StorageService()
        assert service.file_exists("key.txt") is True

    def test_false_on_client_error(self, configured_env, mock_boto_client):
        _, client = mock_boto_client
        client.head_object.side_effect = _client_error("404")
        service = StorageService()

        assert service.file_exists("key.txt") is False


class TestGetFileMetadata:
    def test_none_when_not_configured(self, unconfigured_env):
        service = StorageService()
        assert service.get_file_metadata("key.txt") is None

    def test_returns_metadata_dict(self, configured_env, mock_boto_client):
        _, client = mock_boto_client
        client.head_object.return_value = {
            "ContentType": "image/png",
            "ContentLength": 1234,
            "LastModified": "2026-01-01T00:00:00Z",
            "ETag": '"abc123"',
        }
        service = StorageService()

        result = service.get_file_metadata("key.txt")

        assert result == {
            "content_type": "image/png",
            "content_length": 1234,
            "last_modified": "2026-01-01T00:00:00Z",
            "etag": '"abc123"',
        }

    def test_none_on_client_error(self, configured_env, mock_boto_client):
        _, client = mock_boto_client
        client.head_object.side_effect = _client_error("404")
        service = StorageService()

        assert service.get_file_metadata("key.txt") is None
