from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.deps import get_current_user, get_profile_repo, get_file_storage
from app.schemas.profile import ProfileOut, ProfileUpdate
from app.models.user import User
from app.services import profile as profile_service
from app.repositories.profile import AbstractProfileRepository
from app.adapters.file_storage import AbstractFileStorage



router = APIRouter(tags=["profiles"])


@router.get("/me", response_model=ProfileOut)
async def get_my_profile(
    profile_repo: AbstractProfileRepository = Depends(get_profile_repo),
    storage: AbstractFileStorage = Depends(get_file_storage),
    current_user: User = Depends(get_current_user)
):
    return await profile_service.get_my_profile(profile_repo, storage, current_user.user_id)

@router.patch("/me", response_model=ProfileOut)
async def update_profile(
    payload: ProfileUpdate,
    db: AsyncSession = Depends(get_db), 
    profile_repo: AbstractProfileRepository = Depends(get_profile_repo),
    storage: AbstractFileStorage = Depends(get_file_storage),
    current_user: User = Depends(get_current_user),
):
    return await profile_service.update_bio(db, profile_repo, storage, current_user.user_id, payload.biography)

@router.post("/me/picture", response_model=ProfileOut)
async def upload_profile_pic(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    profile_repo: AbstractProfileRepository = Depends(get_profile_repo),
    storage: AbstractFileStorage = Depends(get_file_storage),
    current_user: User = Depends(get_current_user)
):
    return await profile_service.set_profile_picture(db, profile_repo, storage, current_user.user_id, current_user.guid ,file)