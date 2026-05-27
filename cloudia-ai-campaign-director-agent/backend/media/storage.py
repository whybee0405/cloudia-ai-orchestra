"""MinIO client wrapper — all object storage operations go through here."""
import io
import logging
from datetime import timedelta
from typing import Optional
from minio import Minio
from minio.error import S3Error

from backend.config import get_settings

logger = logging.getLogger(__name__)
_client: Optional[Minio] = None


def get_client() -> Minio:
    global _client
    if _client is None:
        s = get_settings()
        _client = Minio(
            endpoint=s.minio_endpoint,
            access_key=s.minio_root_user,
            secret_key=s.minio_root_password,
            secure=s.minio_secure,
        )
    return _client


def ensure_bucket(bucket: Optional[str] = None) -> None:
    """Create the media bucket if it does not exist. Called at API startup."""
    s = get_settings()
    bucket = bucket or s.minio_bucket
    client = get_client()
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
        logger.info("Created MinIO bucket: %s", bucket)


def upload(
    data: bytes,
    object_path: str,
    content_type: str = "application/octet-stream",
    bucket: Optional[str] = None,
) -> str:
    """Upload bytes to MinIO. Returns the object path."""
    s = get_settings()
    bucket = bucket or s.minio_bucket
    client = get_client()
    client.put_object(
        bucket_name=bucket,
        object_name=object_path,
        data=io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    logger.debug("Uploaded %s (%d bytes) to bucket %s", object_path, len(data), bucket)
    return object_path


def download(object_path: str, bucket: Optional[str] = None) -> bytes:
    """Download object from MinIO and return raw bytes."""
    s = get_settings()
    bucket = bucket or s.minio_bucket
    client = get_client()
    response = client.get_object(bucket_name=bucket, object_name=object_path)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def signed_url(
    object_path: str,
    bucket: Optional[str] = None,
    expires: timedelta = timedelta(hours=1),
    client_id_prefix: Optional[str] = None,
) -> str:
    """
    Generate a presigned GET URL. Validates that the path starts with client_id_prefix
    when provided — prevents cross-client URL guessing.
    """
    if client_id_prefix and not object_path.startswith(f"{client_id_prefix}/"):
        raise PermissionError(f"Path {object_path!r} does not belong to client {client_id_prefix!r}")
    s = get_settings()
    bucket = bucket or s.minio_bucket
    client = get_client()
    return client.presigned_get_object(bucket_name=bucket, object_name=object_path, expires=expires)


def object_path(client_id: int, campaign_id: int, stage: str, subdir: str, filename: str) -> str:
    """Build a canonical MinIO path: {client_id}/campaigns/{campaign_id}/{stage}/{subdir}/{filename}"""
    return f"{client_id}/campaigns/{campaign_id}/{stage}/{subdir}/{filename}"
