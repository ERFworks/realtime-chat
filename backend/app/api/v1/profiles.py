from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.deps import get_current_user, get_profile_repo, get_user_repo
from app.schemas.profile import ProfileOut, ProfileUpdate
from app.models.user import User
from app.services import profile as profile_service
from app.repositories.user import AbstractUserRepository
from app.repositories.profile import AbstractProfileRepository



router = APIRouter(tags=["profiles"])


@router.get("/me", response_model=ProfileOut)
async def get_my_profile(
    profile_repo: AbstractProfileRepository = Depends(get_profile_repo),
    current_user: User = Depends(get_current_user)
):
    return await profile_service.get_my_profile(profile_repo, current_user.user_id)

@router.patch("/me", response_model=ProfileOut)
async def update_profile(
    payload: ProfileUpdate,
    db: AsyncSession = Depends(get_db), 
    profile_repo: AbstractProfileRepository = Depends(get_profile_repo),
    current_user: User = Depends(get_current_user),
):
    return await profile_service.update_bio(db, profile_repo,current_user.user_id, payload.biography)

@router.post("/me/picture", response_model=ProfileOut)
async def upload_profile_pic(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    profile_repo: AbstractProfileRepository = Depends(get_profile_repo),
    user_repo: AbstractUserRepository = Depends(get_user_repo),
    current_user: User = Depends(get_current_user)
):
    return await profile_service.set_profile_picture(db, profile_repo, user_repo, current_user.user_id, file)