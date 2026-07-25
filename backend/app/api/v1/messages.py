from fastapi import APIRouter, status, Depends
from app.schemas.message import MessageOut, MessageCreate
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services import message as msg_service

router = APIRouter(tags=["messages"])

@router.post(
    "/{conversation_id}/messages", 
    response_model=MessageOut, 
    status_code=status.HTTP_201_CREATED)

async def send_message(
    conversation_id: int, 
    payload: MessageCreate, 
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    return await msg_service.send_message(
        db, 
        conversation_id=conversation_id, 
        sender_id=current_user.user_id, 
        body=payload.body
    )

@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
async def get_message(
    conversation_id: int, 
    before_id: int | None = None, 
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await msg_service.get_messages(
        db,
        conversation_id=conversation_id,
        user_id=current_user.user_id,
        before_id=before_id,
        limit=limit
    )
    