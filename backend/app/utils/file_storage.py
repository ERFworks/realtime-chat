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

def ensure_bucket_exists() -> None:
    try:
        s3_client.head_bucket(Bucket = settings.MINIO_BUCKET_NAME)
    except ClientError:
        s3_client.create_bucket(Bucket = settings.MINIO_BUCKET_NAME)


async def save_profile_picture(file: UploadFile, user_guid: uuid.UUID) -> str:
    if file.content_type not in settings.ALLOWD_IMAGE_TYPES:
        raise HTTPException(
            status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail = "Invalid file format(only JPEG, PNG, WEBP allowed)"
        )
    
    contents = await file.read()
    if len(contents) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code = status.HTTP_413_CONTENT_TOO_LARGE,
            detail = "File too large" 
        )
    
    ext = file.content_type.split("/")[-1]
    key = f"profile_pics/{user_guid}/{uuid.uuid4()}.{ext}"

    await run_in_threadpool(
        s3_client.put_object,
        Bucket = settings.MINIO_BUCKET_NAME,
        Key = key,
        Body = contents,
        ContentType = file.content_type
    )

    return key


def delete_profile_picture(key: str) -> None:
    s3_client.delete_object(Bucket = settings.MINIO_BUCKET_NAME, Key = key)


def get_profile_picture_url(key: str | None) -> str | None:
    if key is None:
        return None
    
    return s3_client.generate_presigned_url(
        "get_object",
        Params = {"Bucket": settings.MINIO_BUCKET_NAME, "Key": key},
        ExpiersIn = 3600
    )