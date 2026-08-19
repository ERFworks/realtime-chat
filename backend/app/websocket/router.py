import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, status
from pydantic import ValidationError

from app.api.deps import get_rate_limiter
from app.schemas.message import MessageCreate
from app.services import message as msg_service
from app.websocket.manager import manager
from app.websocket.auth import authenticate_websocket_token
from app.services.unit_of_work import SqlAlchemyUnitOfWork
from app.db.session import AsyncSessionLocal


router = APIRouter()

@router.websocket("/ws")
async def websocket_endpont(websocket: WebSocket, token: str | None = None):
    rate_limiter = get_rate_limiter()
    client_host = websocket.client.host if websocket.client else "unknown"
    if await rate_limiter.is_rate_limited(
        f"rate_limit:ws_connect:{client_host}", limit=10, window_seconds=60
    ):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = authenticate_websocket_token(token)
    if user_id is None:
        await websocket.close(code = status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(user_id, websocket)

    try: 
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=20
                )
            except asyncio.TimeoutError:
                try:
                    await websocket.send_json({"type": "ping"})
                    data = await asyncio.wait_for(
                        websocket.receive_json(), timeout=10
                    )
                except Exception:
                    break
                if isinstance(data, dict) and data.get("type") == "pong":
                    continue
            except (ValueError, TypeError):
                await websocket.send_json({"type": "error", "detail": "Invalid JSON"})
                continue

            await _handle_incoming(websocket, user_id, data)
    
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(user_id, websocket)


async def _handle_incoming(websocket: WebSocket, user_id: int, data: dict) -> None:
    rate_limiter = get_rate_limiter()
    if await rate_limiter.is_rate_limited(
        f"rate_limit:ws_message:{user_id}", limit=30, window_seconds=60
    ):
        await websocket.send_json(
            {"type": "error", "detail": "Too many messages. Please slow down."}
        )
        return

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
        async with AsyncSessionLocal() as session:
            uow = SqlAlchemyUnitOfWork(session)
            message = await msg_service.send_message(
                uow,
                conversation_id=conversation_id,
                sender_id=user_id,
                body=validated.body
            )
            async with uow:
                participants = await uow.conversations.get_participants(conversation_id)
                participant_ids = [p.user_id for p in participants]
            
    except HTTPException as exc:
        await websocket.send_json({"type": "error", "detail": exc.detail})
        return

    payload = {
        "type": "message",
        "data": message.model_dump(mode="json")
    }
    for pid in participant_ids:
        await manager.send_to_user(pid, payload)
        