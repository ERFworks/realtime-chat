from typing import Protocol

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from fastapi.concurrency import run_in_threadpool

from app.core.config import settings

class AbstractFileStorage(Protocol):
    async def put(self, key: str, content: bytes, content_type: str) -> None: ...
    async def delete(self, key: str) -> None: ...
    def url_for(self, key: str | None) -> str | None: ...


def _make_client(endpoint: str):
    return boto3.client(
        "s3",
        endpoint_url=f"http{'s' if settings.MINIO_USE_SSL else ''}://{endpoint}",
        aws_access_key_id = settings.MINIO_ACCESS_KEY,
        aws_secret_access_key = settings.MINIO_SECRET_KEY,
        config = Config(signature_version = "s3v4"),
        region_name = "us-east-1"
    )

class MinioFileStorage:
    def __init__(self):
        self._client = _make_client(settings.MINIO_ENDPOINT)
        public_endpoint = settings.MINIO_PUBLIC_ENDPOINT or settings.MINIO_ENDPOINT
        self._public_client = _make_client(public_endpoint)


    async def put(self, key: str, content: bytes, content_type: str) -> None:
        await run_in_threadpool(
            self._client.put_object, 
            Bucket = settings.MINIO_BUCKET_NAME,
            Key=key, 
            Body=content, 
            ContentType=content_type
        )


    async def delete(self, key: str) -> None:
        await run_in_threadpool(
            self._client.delete_object, 
            Bucket=settings.MINIO_BUCKET_NAME,
            Key=key
        )


    def url_for(self, key: str | None) -> str | None:
        if key is None:
            return None

        return self._public_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.MINIO_BUCKET_NAME, "Key": key},
            ExpiresIn=3600,
        )


def ensure_bucket_exists() -> None:
    client = _make_client(settings.MINIO_ENDPOINT)
    try:
        client.head_bucket(Bucket = settings.MINIO_BUCKET_NAME)
    except ClientError:
        client.create_bucket(Bucket = settings.MINIO_BUCKET_NAME)