from fastapi import APIRouter, Depends, File, UploadFile

from app.adapters.file_storage import AbstractFileStorage
from app.api.deps import get_current_user, get_file_storage, get_uow
from app.models.user import User
from app.schemas.profile import ProfileOut, ProfileUpdate
from app.services import profile as profile_service
from app.services.unit_of_work import AbstractUnitOfWork

router = APIRouter(tags=["profiles"])


@router.get("/me", response_model=ProfileOut)
async def get_my_profile(
    uow: AbstractUnitOfWork = Depends(get_uow),
    storage: AbstractFileStorage = Depends(get_file_storage),
    current_user: User = Depends(get_current_user)
):
    return await profile_service.get_my_profile(uow, storage, current_user.user_id)


@router.patch("/me", response_model=ProfileOut)
async def update_profile(
    payload: ProfileUpdate,
    uow: AbstractUnitOfWork = Depends(get_uow),
    storage: AbstractFileStorage = Depends(get_file_storage),
    current_user: User = Depends(get_current_user),
):
    return await profile_service.update_bio(uow, storage, current_user.user_id, payload.biography)


@router.post("/me/picture", response_model=ProfileOut)
async def upload_profile_pic(
    file: UploadFile = File(...),
    uow: AbstractUnitOfWork = Depends(get_uow),
    storage: AbstractFileStorage = Depends(get_file_storage),
    current_user: User = Depends(get_current_user)
):
    return await profile_service.set_profile_picture(uow, storage, current_user.user_id, current_user.guid ,file)