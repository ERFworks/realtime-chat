from fastapi import HTTPException, status, UploadFile

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import Profile
from app.schemas.profile import ProfileOut
from app.repositories import profile as profile_repo
from app.repositories import user as user_repo
from app.utils.file_storage import save_profile_picture, delete_profile_picture, get_profile_picture_url


def _to_profile_out(profile: Profile) -> ProfileOut:
    return ProfileOut(
        profile_id= profile.profile_id,
        user_id=profile.user_id,
        biography=profile.biography,
        profile_pic=get_profile_picture_url(profile.profile_pic)
    )

async def _get_profile_or_404(db: AsyncSession, user_id: int) -> Profile:
    profile = await profile_repo.get_profile_by_user_id(db, user_id)

    if profile is None:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail = "User not found"
        )
    return profile


async def get_my_profile(db: AsyncSession, user_id: int) -> ProfileOut:
    profile = await _get_profile_or_404(db, user_id)
    return _to_profile_out(profile)


async def update_bio(db: AsyncSession, user_id, biography:str) -> ProfileOut:
    profile = await _get_profile_or_404(db, user_id)
    profile.biography = biography
    await db.commit()
    await db.refresh(profile)

    return _to_profile_out(profile)


async def set_profile_picture(db: AsyncSession, user_id: int, file: UploadFile) -> ProfileOut:
    profile = await _get_profile_or_404(db, user_id)
    user = await user_repo.get_user_by_id(db, user_id)
    new_key = await save_profile_picture(file, user.guid)

    old_key = profile.profile_pic

    profile.profile_pic = new_key
    await db.commit()
    await db.refresh(profile)

    if old_key is not None:
       delete_profile_picture(old_key)

    return _to_profile_out(profile)