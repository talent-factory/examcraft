"""
S3-compatible Storage Service for ExamCraft AI
Supports Fly.io Tigris and AWS S3 for distributed file storage
"""

import os
import logging
from typing import Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class StorageService:
    """S3-compatible storage service for file upload/download operations"""

    def __init__(self):
        # Lazy initialization - don't read env vars at import time
        self._s3_client = None
        self._is_configured = None
        self._bucket_name = None
        self._endpoint_url = None
        self._region = None
        self._init_logged = False

    def _ensure_initialized(self):
        """Initialize configuration from environment variables (lazy)"""
        if self._is_configured is not None:
            return

        self._bucket_name = os.getenv("BUCKET_NAME", "examcraft-uploads")
        self._endpoint_url = os.getenv("AWS_ENDPOINT_URL_S3")
        self._region = os.getenv("AWS_REGION", "auto")

        # Check if S3 is configured
        self._is_configured = bool(
            os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY")
        )

        if not self._init_logged:
            self._init_logged = True
            if self._is_configured:
                logger.info(
                    f"S3 storage configured: bucket={self._bucket_name}, "
                    f"endpoint={self._endpoint_url}"
                )
            else:
                logger.warning(
                    "S3 storage not configured - AWS credentials missing. "
                    "Falling back to local storage."
                )

    @property
    def bucket_name(self) -> str:
        """Get bucket name (lazy initialization)"""
        self._ensure_initialized()
        return self._bucket_name

    @property
    def endpoint_url(self) -> Optional[str]:
        """Get endpoint URL (lazy initialization)"""
        self._ensure_initialized()
        return self._endpoint_url

    @property
    def region(self) -> str:
        """Get region (lazy initialization)"""
        self._ensure_initialized()
        return self._region

    @property
    def s3_client(self):
        """Lazy initialization of S3 client"""
        self._ensure_initialized()
        if self._s3_client is None and self._is_configured:
            self._s3_client = boto3.client(
                "s3",
                endpoint_url=self._endpoint_url,
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name=self._region,
            )
        return self._s3_client

    @property
    def is_configured(self) -> bool:
        """Check if S3 storage is properly configured (lazy initialization)"""
        self._ensure_initialized()
        return self._is_configured

    def upload_file(
        self,
        file_data: bytes,
        object_key: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Upload file to S3 bucket

        Args:
            file_data: File content as bytes
            object_key: S3 object key (path within bucket)
            content_type: MIME type of the file

        Returns:
            The object key on success

        Raises:
            RuntimeError: If S3 is not configured or upload fails
        """
        if not self.is_configured:
            raise RuntimeError("S3 storage not configured")

        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=file_data,
                ContentType=content_type,
            )
            logger.info(f"Uploaded file to S3: {object_key}")
            return object_key

        except ClientError as e:
            logger.error(f"Failed to upload file to S3: {e}")
            raise RuntimeError(f"S3 upload failed: {e}")

    def download_file(self, object_key: str) -> bytes:
        """
        Download file from S3 bucket

        Args:
            object_key: S3 object key (path within bucket)

        Returns:
            File content as bytes

        Raises:
            RuntimeError: If S3 is not configured or download fails
            FileNotFoundError: If object does not exist
        """
        if not self.is_configured:
            raise RuntimeError("S3 storage not configured")

        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=object_key,
            )
            data = response["Body"].read()
            logger.info(f"Downloaded file from S3: {object_key} ({len(data)} bytes)")
            return data

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ("NoSuchKey", "404"):
                logger.error(f"File not found in S3: {object_key}")
                raise FileNotFoundError(f"File not found: {object_key}")
            logger.error(f"Failed to download file from S3: {e}")
            raise RuntimeError(f"S3 download failed: {e}")

    def delete_file(self, object_key: str) -> bool:
        """
        Delete file from S3 bucket

        Args:
            object_key: S3 object key (path within bucket)

        Returns:
            True on success

        Raises:
            RuntimeError: If S3 is not configured or delete fails
        """
        if not self.is_configured:
            raise RuntimeError("S3 storage not configured")

        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=object_key,
            )
            logger.info(f"Deleted file from S3: {object_key}")
            return True

        except ClientError as e:
            logger.error(f"Failed to delete file from S3: {e}")
            raise RuntimeError(f"S3 delete failed: {e}")

    def get_presigned_url(
        self, object_key: str, expires_in: int = 3600, for_upload: bool = False
    ) -> str:
        """
        Generate presigned URL for file access

        Args:
            object_key: S3 object key (path within bucket)
            expires_in: URL expiration time in seconds (default: 1 hour)
            for_upload: If True, generate URL for upload (PUT), else download (GET)

        Returns:
            Presigned URL string

        Raises:
            RuntimeError: If S3 is not configured
        """
        if not self.is_configured:
            raise RuntimeError("S3 storage not configured")

        try:
            client_method = "put_object" if for_upload else "get_object"
            url = self.s3_client.generate_presigned_url(
                client_method,
                Params={"Bucket": self.bucket_name, "Key": object_key},
                ExpiresIn=expires_in,
            )
            logger.debug(f"Generated presigned URL for {object_key}")
            return url

        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise RuntimeError(f"Presigned URL generation failed: {e}")

    def file_exists(self, object_key: str) -> bool:
        """
        Check if file exists in S3 bucket

        Args:
            object_key: S3 object key (path within bucket)

        Returns:
            True if file exists, False otherwise
        """
        if not self.is_configured:
            return False

        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=object_key)
            return True
        except ClientError:
            return False

    def get_file_metadata(self, object_key: str) -> Optional[dict]:
        """
        Get file metadata from S3

        Args:
            object_key: S3 object key (path within bucket)

        Returns:
            Dictionary with file metadata or None if not found
        """
        if not self.is_configured:
            return None

        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name, Key=object_key
            )
            return {
                "content_type": response.get("ContentType"),
                "content_length": response.get("ContentLength"),
                "last_modified": response.get("LastModified"),
                "etag": response.get("ETag"),
            }
        except ClientError:
            return None


# Singleton instance
storage_service = StorageService()
