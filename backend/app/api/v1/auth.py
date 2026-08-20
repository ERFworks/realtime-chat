from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import (
    get_current_user,
    get_token_store,
    get_uow,
    oauth2_scheme,
    rate_limit,
)
from app.models.user import User
from app.schemas.auth import LogoutIn, RefreshIn, RegisterIn, TokenOut, UserOut
from app.services import auth as auth_service
from app.services.token_store import AbstractTokenStore
from app.services.unit_of_work import AbstractUnitOfWork

router = APIRouter(tags=["authentication"])


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(
            rate_limit(
                "register",
                3,
                3600,
                detail="Too many registration attempts. Please try again later.",
            )
        )
    ],
)
async def register(
    user: RegisterIn,
    uow: AbstractUnitOfWork = Depends(get_uow),
):
    return await auth_service.register_user(
        uow,
        username=user.username,
        password=user.password,
        first_name=user.first_name,
        last_name=user.last_name,
    )


@router.post(
    "/login",
    response_model=TokenOut,
    dependencies=[
        Depends(
            rate_limit(
                "login",
                5,
                60,
                detail="Too many login attempts. Please try again in a minute.",
            )
        )
    ],
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    uow: AbstractUnitOfWork = Depends(get_uow),
    token_store: AbstractTokenStore = Depends(get_token_store),
):
    return await auth_service.authenticate_user(
        uow, token_store, form_data.username, form_data.password
    )


@router.post("/refresh", response_model=TokenOut)
async def refresh_access_token(
    payload_in: RefreshIn,
    uow: AbstractUnitOfWork = Depends(get_uow),
    token_store: AbstractTokenStore = Depends(get_token_store),
):
    return await auth_service.refresh_tokens(uow, token_store, payload_in.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload_in: LogoutIn,
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user),
    token_store: AbstractTokenStore = Depends(get_token_store),
):
    await auth_service.logout(
        token_store, current_user.user_id, token, payload_in.refresh_token
    )


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
