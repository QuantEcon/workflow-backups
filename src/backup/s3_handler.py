"""S3 handler for uploading repository backups to AWS S3."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class S3Handler:
    """Handles uploading and managing backups in AWS S3."""

    def __init__(
        self,
        bucket_name: str,
        region: str = "us-east-1",
        prefix: str = "backups/",
    ) -> None:
        """
        Initialize the S3 handler.

        Args:
            bucket_name: Name of the S3 bucket
            region: AWS region for the bucket
            prefix: Prefix for all backup objects in the bucket
        """
        self.bucket_name = bucket_name
        self.region = region
        # Handle empty prefix (no leading slash)
        self.prefix = (prefix.rstrip("/") + "/") if prefix else ""
        self.s3_client = boto3.client("s3", region_name=region)
        logger.info(f"Initialized S3Handler for bucket '{bucket_name}' in region '{region}'")

    def upload_file(
        self,
        file_path: Path,
        object_key: str,
        metadata: dict[str, str] | None = None,
    ) -> bool:
        """
        Upload a file to S3 with verification.

        Args:
            file_path: Path to the local file to upload
            object_key: S3 object key (without prefix, will be added automatically)
            metadata: Optional metadata to attach to the object

        Returns:
            True if upload was successful and verified, False otherwise
        """
        full_key = f"{self.prefix}{object_key}"

        try:
            # Prepare upload arguments
            extra_args: dict[str, Any] = {}
            if metadata:
                extra_args["Metadata"] = metadata

            # Use SHA256 checksum for verification (supported by upload_file)
            extra_args["ChecksumAlgorithm"] = "SHA256"

            logger.info(f"Uploading {file_path} to s3://{self.bucket_name}/{full_key}")

            # Upload file
            self.s3_client.upload_file(
                str(file_path),
                self.bucket_name,
                full_key,
                ExtraArgs=extra_args,
            )

            # Verify upload
            if self._verify_upload(full_key, file_path):
                logger.info(f"Successfully uploaded and verified: {full_key}")
                return True
            else:
                logger.error(f"Upload verification failed for: {full_key}")
                return False

        except ClientError as e:
            logger.error(f"Failed to upload {file_path} to S3: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during upload: {e}")
            return False

    def _calculate_md5(self, file_path: Path) -> str:
        """Calculate base64-encoded MD5 hash of a file."""
        import base64

        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return base64.b64encode(hash_md5.digest()).decode("utf-8")

    def _verify_upload(self, object_key: str, local_file: Path) -> bool:
        """
        Verify that uploaded file matches local file.

        Args:
            object_key: S3 object key to verify
            local_file: Local file to compare against

        Returns:
            True if sizes match, False otherwise
        """
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=object_key)
            s3_size = response["ContentLength"]
            local_size = local_file.stat().st_size

            if s3_size == local_size:
                logger.debug(f"Verification passed: sizes match ({s3_size} bytes)")
                return True
            else:
                logger.error(f"Size mismatch: S3={s3_size} bytes, local={local_size} bytes")
                return False
        except ClientError as e:
            logger.error(f"Failed to verify upload: {e}")
            return False

    def backup_exists(self, object_key: str) -> bool:
        """
        Check if a backup already exists in S3.

        Args:
            object_key: S3 object key to check

        Returns:
            True if object exists, False otherwise
        """
        full_key = f"{self.prefix}{object_key}"
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=full_key)
            return True
        except ClientError:
            return False

    def list_backups(self, repo_name: str) -> list[dict[str, Any]]:
        """
        List all backups for a specific repository.

        Args:
            repo_name: Name of the repository

        Returns:
            List of backup metadata dictionaries
        """
        prefix = f"{self.prefix}{repo_name}/"
        backups = []

        try:
            paginator = self.s3_client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                if "Contents" in page:
                    for obj in page["Contents"]:
                        backups.append(
                            {
                                "key": obj["Key"],
                                "size": obj["Size"],
                                "last_modified": obj["LastModified"],
                            }
                        )
            logger.info(f"Found {len(backups)} backups for repository: {repo_name}")
            return backups
        except ClientError as e:
            logger.error(f"Failed to list backups for {repo_name}: {e}")
            return []
