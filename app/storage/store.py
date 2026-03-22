"""Unified storage abstraction: DigitalOcean Spaces (S3) with local filesystem fallback.

All paths are relative keys like 'data/users.json' or 'users/{uid}/problems/{pid}.SCN'.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError

from app.config import settings
from app.storage.config import get_storage_backend

logger = logging.getLogger(__name__)

LOCAL_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "local_data"


class StorageBackend:
    """Abstract interface for read/write/delete/list of JSON objects by key."""

    async def initialize(self) -> None:
        """Run any setup needed at app startup."""
        pass

    async def read_json(self, key: str) -> Any | None:
        """Read and parse a JSON file. Returns None if not found."""
        raise NotImplementedError

    async def write_json(self, key: str, data: Any) -> None:
        """Write data as JSON to the given key."""
        raise NotImplementedError

    async def delete(self, key: str) -> bool:
        """Delete a key. Returns True if it existed."""
        raise NotImplementedError

    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        raise NotImplementedError

    async def list_keys(self, prefix: str) -> list[str]:
        """List all keys under a prefix."""
        raise NotImplementedError

    async def read_raw(self, key: str) -> bytes | None:
        """Read raw bytes. Returns None if not found."""
        raise NotImplementedError

    async def write_raw(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        """Write raw bytes."""
        raise NotImplementedError


class LocalStorage(StorageBackend):
    """Local filesystem storage for development."""

    async def initialize(self) -> None:
        LOCAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
        logger.info("Local storage initialized at %s", LOCAL_DATA_DIR)

    def _path(self, key: str) -> Path:
        # Sanitize: prevent path traversal
        clean = Path(key)
        if ".." in clean.parts:
            raise ValueError("Invalid key")
        return LOCAL_DATA_DIR / clean

    async def read_json(self, key: str) -> Any | None:
        p = self._path(key)
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    async def write_json(self, key: str, data: Any) -> None:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    async def delete(self, key: str) -> bool:
        p = self._path(key)
        if p.exists():
            p.unlink()
            return True
        return False

    async def exists(self, key: str) -> bool:
        return self._path(key).exists()

    async def list_keys(self, prefix: str) -> list[str]:
        base = self._path(prefix)
        if not base.exists():
            return []
        results = []
        for p in base.rglob("*"):
            if p.is_file():
                results.append(str(p.relative_to(LOCAL_DATA_DIR)))
        return results

    async def read_raw(self, key: str) -> bytes | None:
        p = self._path(key)
        if not p.exists():
            return None
        return p.read_bytes()

    async def write_raw(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)


class SpacesStorage(StorageBackend):
    """DigitalOcean Spaces (S3-compatible) storage for production."""

    def __init__(self):
        self._client = None

    async def initialize(self) -> None:
        self._client = boto3.client(
            "s3",
            region_name=settings.SPACES_REGION,
            endpoint_url=settings.SPACES_ENDPOINT,
            aws_access_key_id=settings.SPACES_KEY,
            aws_secret_access_key=settings.SPACES_SECRET,
        )
        logger.info("Spaces storage initialized: %s/%s", settings.SPACES_ENDPOINT, settings.SPACES_BUCKET)

    @property
    def bucket(self):
        return settings.SPACES_BUCKET

    async def read_json(self, key: str) -> Any | None:
        try:
            resp = self._client.get_object(Bucket=self.bucket, Key=key)
            return json.loads(resp["Body"].read().decode("utf-8"))
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return None
            raise

    async def write_json(self, key: str, data: Any) -> None:
        body = json.dumps(data, indent=2, default=str).encode("utf-8")
        self._client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=body,
            ContentType="application/json",
        )

    async def delete(self, key: str) -> bool:
        try:
            self._client.delete_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False

    async def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False

    async def list_keys(self, prefix: str) -> list[str]:
        results = []
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                results.append(obj["Key"])
        return results

    async def read_raw(self, key: str) -> bytes | None:
        try:
            resp = self._client.get_object(Bucket=self.bucket, Key=key)
            return resp["Body"].read()
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return None
            raise

    async def write_raw(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        self._client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )


def _create_storage() -> StorageBackend:
    backend = get_storage_backend()
    if backend == "spaces":
        return SpacesStorage()
    return LocalStorage()


storage = _create_storage()
