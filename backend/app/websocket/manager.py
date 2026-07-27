from fastapi import WebSocket

class ConnectionManager:

    def __init__(self):
        self.activate_connections : dict[int, set[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self.activate_connections.setdefault(user_id, set()).add(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        connections = self.activate_connections.get(user_id)
        if connections is None:
            return

        connections.discard(websocket)
        if not connections:
            self.activate_connections.pop(user_id, None)

    async def send_to_user(self, user_id: int, message: dict) -> None:
        connections = self.activate_connections.get(user_id)
        if not connections:
            return

        dead_connections: list[WebSocket] = []
        for websocket in set(connections):
            try:
                await websocket.send_json(message)
            except Exception:
                dead_connections.append(websocket)

        for websocket in dead_connections:
            self.disconnect(user_id, websocket)

manager = ConnectionManager()
        