import uuid

from fastapi import HTTPException, status, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.profile import Profile
from app.schemas.profile import ProfileOut
from app.repositories.profile import AbstractProfileRepository
from app.adapters.file_storage import AbstractFileStorage


def _to_profile_out(profile: Profile, storage: AbstractFileStorage) -> ProfileOut:
    return ProfileOut(
        profile_id= profile.profile_id,
        user_id=profile.user_id,
        biography=profile.biography,
        profile_pic=storage.url_for(profile.profile_pic)
    )

async def _get_profile_or_404(
    profile_repo: AbstractProfileRepository, 
    user_id: int
) -> Profile:
    profile = await profile_repo.get_profile_by_user_id(user_id)

    if profile is None:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail = "Profile not found"
        )
    return profile


async def get_my_profile(
    profile_repo: AbstractProfileRepository,
    storage: AbstractFileStorage,
    user_id: int
) -> ProfileOut:
    profile = await _get_profile_or_404(profile_repo, user_id)
    return _to_profile_out(profile, storage)


async def update_bio(
    db: AsyncSession, 
    profile_repo: AbstractProfileRepository,
    storage: AbstractFileStorage,
    user_id: int, 
    biography: str | None
) -> ProfileOut:
    profile = await _get_profile_or_404(profile_repo ,user_id)
    profile.biography = biography
    await db.commit()
    await db.refresh(profile)

    return _to_profile_out(profile, storage)


def _build_picture_key(user_guid: uuid.UUID, content_type: str) -> str:
    ext = content_type.split("/")[-1]
    return f"profile_pics/{user_guid}/{uuid.uuid4()}.{ext}"

async def set_profile_picture(
    db: AsyncSession,
    profile_repo: AbstractProfileRepository,
    storage: AbstractFileStorage,
    user_id: int,
    user_guid: uuid.UUID,
    file: UploadFile
) -> ProfileOut:
    profile = await _get_profile_or_404(profile_repo, user_id)
    if file.content_type not in settings.ALLOWD_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Invalid file format (Only JPEG, PNG, WEBP allowed)"
        )

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="File too large"
        )

    new_key = _build_picture_key(user_guid, file.content_type)
    await storage.put(new_key, content, file.content_type)
    old_key = profile.profile_pic
    profile.profile_pic = new_key

    await db.commit()
    await db.refresh(profile)

    if old_key is not None:
        await storage.delete(old_key)

    return _to_profile_out(profile, storage) 