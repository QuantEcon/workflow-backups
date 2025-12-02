"""Unit tests for S3Handler."""

from datetime import datetime
from unittest.mock import Mock, patch

from botocore.exceptions import ClientError

from src.backup.s3_handler import S3Handler


class TestS3HandlerInit:
    """Test S3Handler initialization."""

    @patch("src.backup.s3_handler.boto3")
    def test_init_with_defaults(self, mock_boto3):
        """Test initialization with default parameters."""
        handler = S3Handler(bucket_name="test-bucket")

        assert handler.bucket_name == "test-bucket"
        assert handler.region == "us-east-1"
        assert handler.prefix == "backups/"
        mock_boto3.client.assert_called_once_with("s3", region_name="us-east-1")

    @patch("src.backup.s3_handler.boto3")
    def test_init_with_custom_params(self, mock_boto3):
        """Test initialization with custom parameters."""
        handler = S3Handler(bucket_name="my-bucket", region="eu-west-1", prefix="custom-prefix")

        assert handler.bucket_name == "my-bucket"
        assert handler.region == "eu-west-1"
        assert handler.prefix == "custom-prefix/"
        mock_boto3.client.assert_called_once_with("s3", region_name="eu-west-1")

    @patch("src.backup.s3_handler.boto3")
    def test_prefix_normalization(self, mock_boto3):
        """Test that prefix is normalized with trailing slash."""
        handler1 = S3Handler(bucket_name="bucket", prefix="no-slash")
        handler2 = S3Handler(bucket_name="bucket", prefix="with-slash/")

        assert handler1.prefix == "no-slash/"
        assert handler2.prefix == "with-slash/"


class TestS3HandlerUpload:
    """Test S3Handler upload functionality."""

    @patch("src.backup.s3_handler.boto3")
    def test_upload_file_success(self, mock_boto3, tmp_path):
        """Test successful file upload."""
        # Create test file
        test_file = tmp_path / "test.tar.gz"
        test_file.write_bytes(b"test content here")

        # Setup mock
        mock_client = Mock()
        mock_client.head_object.return_value = {"ContentLength": len(b"test content here")}
        mock_boto3.client.return_value = mock_client

        handler = S3Handler(bucket_name="test-bucket")
        result = handler.upload_file(
            test_file, "repo/repo-20251127.tar.gz", metadata={"repository": "org/repo"}
        )

        assert result is True
        mock_client.upload_file.assert_called_once()

    @patch("src.backup.s3_handler.boto3")
    def test_upload_file_with_metadata(self, mock_boto3, tmp_path):
        """Test upload includes metadata."""
        test_file = tmp_path / "test.tar.gz"
        test_file.write_bytes(b"test content")

        mock_client = Mock()
        mock_client.head_object.return_value = {"ContentLength": 12}
        mock_boto3.client.return_value = mock_client

        handler = S3Handler(bucket_name="test-bucket")
        metadata = {
            "repository": "quantecon/lecture-python",
            "backup_date": "2025-11-27T00:00:00",
            "default_branch": "main",
        }
        handler.upload_file(test_file, "key", metadata=metadata)

        # Check that metadata was passed in ExtraArgs
        call_args = mock_client.upload_file.call_args
        assert "Metadata" in call_args.kwargs.get("ExtraArgs", {})

    @patch("src.backup.s3_handler.boto3")
    def test_upload_file_client_error(self, mock_boto3, tmp_path):
        """Test handling of S3 client errors."""
        test_file = tmp_path / "test.tar.gz"
        test_file.write_bytes(b"test content")

        mock_client = Mock()
        mock_client.upload_file.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}}, "PutObject"
        )
        mock_boto3.client.return_value = mock_client

        handler = S3Handler(bucket_name="test-bucket")
        result = handler.upload_file(test_file, "key")

        assert result is False

    @patch("src.backup.s3_handler.boto3")
    def test_upload_verification_failure(self, mock_boto3, tmp_path):
        """Test upload fails if verification fails."""
        test_file = tmp_path / "test.tar.gz"
        test_file.write_bytes(b"test content")  # 12 bytes

        mock_client = Mock()
        # Return different size to simulate verification failure
        mock_client.head_object.return_value = {"ContentLength": 999}
        mock_boto3.client.return_value = mock_client

        handler = S3Handler(bucket_name="test-bucket")
        result = handler.upload_file(test_file, "key")

        assert result is False


class TestS3HandlerBackupExists:
    """Test S3Handler backup existence checks."""

    @patch("src.backup.s3_handler.boto3")
    def test_backup_exists_true(self, mock_boto3):
        """Test backup exists returns True when object exists."""
        mock_client = Mock()
        mock_client.head_object.return_value = {"ContentLength": 1024}
        mock_boto3.client.return_value = mock_client

        handler = S3Handler(bucket_name="test-bucket")
        result = handler.backup_exists("repo/repo-20251127.tar.gz")

        assert result is True
        mock_client.head_object.assert_called_once_with(
            Bucket="test-bucket", Key="backups/repo/repo-20251127.tar.gz"
        )

    @patch("src.backup.s3_handler.boto3")
    def test_backup_exists_false(self, mock_boto3):
        """Test backup exists returns False when object doesn't exist."""
        mock_client = Mock()
        mock_client.head_object.side_effect = ClientError(
            {"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject"
        )
        mock_boto3.client.return_value = mock_client

        handler = S3Handler(bucket_name="test-bucket")
        result = handler.backup_exists("repo/repo-20251127.tar.gz")

        assert result is False


class TestS3HandlerListBackups:
    """Test S3Handler backup listing."""

    @patch("src.backup.s3_handler.boto3")
    def test_list_backups_returns_all(self, mock_boto3):
        """Test listing backups returns all objects."""
        mock_client = Mock()
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {
                        "Key": "backups/repo/repo-20251127.tar.gz",
                        "Size": 1024,
                        "LastModified": datetime(2025, 11, 27),
                    },
                    {
                        "Key": "backups/repo/repo-20251120.tar.gz",
                        "Size": 1000,
                        "LastModified": datetime(2025, 11, 20),
                    },
                ]
            }
        ]
        mock_client.get_paginator.return_value = mock_paginator
        mock_boto3.client.return_value = mock_client

        handler = S3Handler(bucket_name="test-bucket")
        backups = handler.list_backups("repo")

        assert len(backups) == 2
        assert backups[0]["size"] == 1024
        assert backups[1]["size"] == 1000

    @patch("src.backup.s3_handler.boto3")
    def test_list_backups_empty(self, mock_boto3):
        """Test listing backups when none exist."""
        mock_client = Mock()
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [{}]  # No Contents key
        mock_client.get_paginator.return_value = mock_paginator
        mock_boto3.client.return_value = mock_client

        handler = S3Handler(bucket_name="test-bucket")
        backups = handler.list_backups("repo")

        assert len(backups) == 0

    @patch("src.backup.s3_handler.boto3")
    def test_list_backups_error(self, mock_boto3):
        """Test listing backups handles errors gracefully."""
        mock_client = Mock()
        mock_paginator = Mock()
        mock_paginator.paginate.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}}, "ListObjectsV2"
        )
        mock_client.get_paginator.return_value = mock_paginator
        mock_boto3.client.return_value = mock_client

        handler = S3Handler(bucket_name="test-bucket")
        backups = handler.list_backups("repo")

        assert backups == []


class TestS3HandlerMD5:
    """Test MD5 hash calculation."""

    @patch("src.backup.s3_handler.boto3")
    def test_calculate_md5(self, mock_boto3, tmp_path):
        """Test MD5 calculation produces consistent results."""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"hello world")

        handler = S3Handler(bucket_name="test-bucket")
        md5_hash = handler._calculate_md5(test_file)

        # MD5 of "hello world" in base64
        assert md5_hash == "XrY7u+Ae7tCTyyK7j1rNww=="
