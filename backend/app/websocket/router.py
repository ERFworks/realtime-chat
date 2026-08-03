from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, status
from pydantic import ValidationError

from app.db.session import AsyncSessionLocal
from app.schemas.message import MessageCreate
from app.services import message as msg_service
from app.repositories.message import SqlAlchemyMessageRepository
from app.repositories.conversation import SqlAlchemyConversationRepository
from app.websocket.manager import manager
from app.websocket.auth import authenticate_websocket_token

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpont(websocket: WebSocket, token: str | None = None):
    user_id = authenticate_websocket_token(token)
    if user_id is None:
        await websocket.close(code = status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(user_id, websocket)

    try: 
        while True:
            try:
                data = await websocket.receive_json()
            except (ValueError, TypeError):
                await websocket.send_json(
                    {"type": "error", "detail": "Invalid JSON"}
                )
                continue
            await _handle_incoming(websocket, user_id, data)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(user_id, websocket)

async def _handle_incoming(websocket: WebSocket, user_id: int, data: dict) -> None:
    conversation_id = data.get("conversation_id")
    body = data.get("body")

    if not isinstance(conversation_id, int):
        await websocket.send_json(
            {"type": "error", "detail": "conversation_id must be an integer"}
        )
        return

    try:
        validated = MessageCreate(body=body)
    except ValidationError:
        await websocket.send_json(
            {"type": "error", "detail": "Invalid message body"}
        )
        return

    try:
        async with AsyncSessionLocal() as db:
            msg_repo = SqlAlchemyMessageRepository(db)
            conv_repo = SqlAlchemyConversationRepository(db)

            message = await msg_service.send_message(
                db,
                msg_repo,
                conv_repo,
                conversation_id=conversation_id,
                sender_id=user_id,
                body=validated.body
            )
            participants = await conv_repo.get_participants(conversation_id)
    except HTTPException as exc:
        await websocket.send_json({"type": "error", "detail": exc.detail})
        return

    payload = {
        "type": "message",
        "data": message.model_dump(mode="json")
    }
    for participant in participants:
        await manager.send_to_user(participant.user_id, payload)
        