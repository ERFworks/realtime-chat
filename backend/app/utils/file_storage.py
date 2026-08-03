import uuid
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from fastapi import UploadFile, HTTPException, status
from fastapi.concurrency import run_in_threadpool

from app.core.config import settings

s3_client = boto3.client(
    "s3",
    endpoint_url = f"http{'s' if settings.MINIO_USE_SSL else ''}://{settings.MINIO_ENDPOINT}",
    aws_access_key_id = settings.MINIO_ACCESS_KEY,
    aws_secret_access_key = settings.MINIO_SECRET_KEY,
    config = Config(signature_version = "s3v4"),
    region_name = "us-east-1"
)

_public_endpoint = settings.MINIO_PUBLIC_ENDPOINT or settings.MINIO_ENDPOINT
s3_public_client = boto3.client(
    "s3",
    endpoint_url=f"http{'s' if settings.MINIO_USE_SSL else ''}://{_public_endpoint}",
    aws_access_key_id=settings.MINIO_ACCESS_KEY,
    aws_secret_access_key=settings.MINIO_SECRET_KEY,
    config=Config(signature_version="s3v4"),
    region_name="us-east-1",
)

def presigned_url(key: str | None) -> str | None:
    if key is None:
        return None
    return s3_public_client.generate_presigned_url(  
        "get_object",
        Params={"Bucket": settings.MINIO_BUCKET_NAME, "Key": key},
        ExpiresIn=3600,
    )

def ensure_bucket_exists() -> None:
    try:
        s3_client.head_bucket(Bucket = settings.MINIO_BUCKET_NAME)
    except ClientError:
        s3_client.create_bucket(Bucket = settings.MINIO_BUCKET_NAME)


def put_object(key: str, content: bytes, content_type: str) -> None:
    s3_client.put_object(
        Bucket=settings.MINIO_BUCKET_NAME,
        Key=key,
        Body=content,
        ContentType=content_type,
    )


def delete_object(key: str) -> None:
    s3_client.delete_object(Bucket = settings.MINIO_BUCKET_NAME, Key = key)
