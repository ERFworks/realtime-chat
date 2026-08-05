from fastapi import APIRouter, Depends, status

from app.schemas.auth import RegisterIn, TokenOut, UserOut, RefreshIn
from app.models.user import User
from app.api.deps import get_current_user, get_uow
from fastapi.security import OAuth2PasswordRequestForm
from app.services import auth as auth_service
from app.services.unit_of_work import AbstractUnitOfWork



router = APIRouter(tags=["authentication"])

@router.post("/register", response_model=UserOut, status_code = status.HTTP_201_CREATED)
async def register (
    user: RegisterIn, 
    uow: AbstractUnitOfWork = Depends(get_uow)
    
):
    result = await auth_service.register_user(
        uow,
        username=user.username,
        password=user.password,
        first_name=user.first_name,
        last_name=user.last_name
    )
    return result


@router.post("/login", response_model=TokenOut)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    uow: AbstractUnitOfWork = Depends(get_uow)
):
    return await auth_service.authenticate_user(uow, form_data.username, form_data.password)
    

@router.post("/refresh", response_model=TokenOut)
async def refresh_access_token(payload_in: RefreshIn, uow: AbstractUnitOfWork = Depends(get_uow)):

   return await auth_service.refresh_tokens(uow, payload_in.refresh_token)


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return current_user