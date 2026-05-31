import io
import json
from minio import Minio
from app.config import get_settings

_client: Minio | None = None


def _get_client() -> Minio:
    global _client
    if _client is None:
        s = get_settings()
        _client = Minio(
            s.minio_endpoint,
            access_key=s.minio_root_user,
            secret_key=s.minio_root_password,
            secure=s.minio_secure,
        )
    return _client


def ensure_bucket() -> None:
    s = get_settings()
    client = _get_client()
    if not client.bucket_exists(s.minio_bucket):
        client.make_bucket(s.minio_bucket)
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{s.minio_bucket}/*"],
                }
            ],
        }
        client.set_bucket_policy(s.minio_bucket, json.dumps(policy))


def upload(data: bytes, object_path: str, content_type: str) -> str:
    s = get_settings()
    client = _get_client()
    client.put_object(
        s.minio_bucket,
        object_path,
        io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    return logo_url_for(object_path)


def logo_url_for(object_path: str) -> str:
    s = get_settings()
    return f"/media/{s.minio_bucket}/{object_path}"
