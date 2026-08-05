from fastapi import APIRouter, Depends, status

from app.db.session import get_db
from app.api.deps import get_current_user,get_uow
from app.models.user import User
from app.schemas.conversation import ConversationCreate, ConversationOut
from app.services import conversation as conv_service
from app.services.unit_of_work import AbstractUnitOfWork


router = APIRouter(tags=["conversations"])


@router.post("", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreate,
    current_user: User = Depends(get_current_user),
    uow: AbstractUnitOfWork = Depends(get_uow)
):
    return await conv_service.get_or_create_private_conversation(current_user.user_id, payload.other_user_id, uow)


@router.get("", response_model=list[ConversationOut])
async def list_my_conversations(
    current_user: User = Depends(get_current_user),
    uow: AbstractUnitOfWork = Depends(get_uow)
):
    return await conv_service.list_conversations(current_user.user_id, uow)


