import pytest
from starlette.websockets import WebSocketDisconnect


def _register_and_login(sync_client, username: str) -> str:
    sync_client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "password123", "first_name": username},
    )
    return sync_client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": "password123"},
    ).json()["access_token"]


def test_ws_rejects_invalid_token(sync_client):
    with (
        pytest.raises(WebSocketDisconnect) as exc,
        sync_client.websocket_connect("/api/v1/ws") as ws,
    ):
        ws.receive_json()

    assert exc.value.code == 1008


def test_ws_broadcast_message_to_other_user(sync_client):
    token_a = _register_and_login(sync_client, "ali")
    token_b = _register_and_login(sync_client, "mmd")

    conv_id = sync_client.post(
        "/api/v1/conversations",
        json={"other_user_id": 2},
        headers={"Authorization": f"Bearer {token_a}"},
    ).json()["conversation_id"]

    with (
        sync_client.websocket_connect(f"/api/v1/ws?token={token_b}") as ws_b,
        sync_client.websocket_connect(f"/api/v1/ws?token={token_a}") as ws_a,
    ):
        ws_a.send_json({"conversation_id": conv_id, "body": "Hi!"})

        for _ in range(5):
            message = ws_b.receive_json()
            if message.get("type") == "message":
                assert message["data"]["body"] == "Hi!"
                assert message["data"]["sender_id"] == 1
                break
        else:
            pytest.fail("Expected a message broadcast, got nothing")


def test_ws_rejects_message_from_non_participant(sync_client):
    token_a = _register_and_login(sync_client, "ali")
    _register_and_login(sync_client, "mmd")
    token_c = _register_and_login(sync_client, "erf")

    conv_id = sync_client.post(
        "/api/v1/conversations",
        json={"other_user_id": 2},
        headers={"Authorization": f"Bearer {token_a}"},
    ).json()["conversation_id"]

    with sync_client.websocket_connect(f"/api/v1/ws?token={token_c}") as ws_c:
        ws_c.send_json({"conversation_id": conv_id, "body": "Hi!"})

        for _ in range(5):
            message = ws_c.receive_json()
            if message.get("type") == "error":
                assert message["detail"] == "Not a participant"
                break
        else:
            pytest.fail("Expected an error frame, got nothing")


def test_ws_connect_rate_limit(sync_client):
    token = _register_and_login(sync_client, "ali")

    for _ in range(10):
        with sync_client.websocket_connect(f"/api/v1/ws?token={token}") as ws:
            ws.send_text("ping")

    with (
        pytest.raises(WebSocketDisconnect) as exc,
        sync_client.websocket_connect(f"/api/v1/ws?token={token}") as ws,
    ):
        ws.receive_json()

    assert exc.value.code == 1008


def test_ws_message_rate_limit(sync_client):
    token = _register_and_login(sync_client, "ali")

    with sync_client.websocket_connect(f"/api/v1/ws?token={token}") as ws:

        for _ in range(30):
            ws.send_json({"conversation_id": "not-an-int", "body": "x"})
            message = ws.receive_json()
            assert message["type"] == "error"

        ws.send_json({"conversation_id": "not-an-int", "body": "x"})
        message = ws.receive_json()
        assert message["type"] == "error"
        assert message["detail"] == "Too many messages. Please slow down."


def test_ws_invalid_json_gets_error(sync_client):
    token = _register_and_login(sync_client, "ali")

    with sync_client.websocket_connect(f"/api/v1/ws?token={token}") as ws:
        ws.send_text("{not valid json")
        message = ws.receive_json()
        assert message["type"] == "error"
        assert message["detail"] == "Invalid JSON"


def test_ws_rejects_non_integer_conversation_id(sync_client):
    token = _register_and_login(sync_client, "ali")

    with sync_client.websocket_connect(f"/api/v1/ws?token={token}") as ws:
        ws.send_json({"conversation_id": "abc", "body": "hi"})
        message = ws.receive_json()
        assert message["type"] == "error"
        assert message["detail"] == "conversation_id must be an integer"


def test_ws_rejects_invalid_message_body(sync_client):
    token = _register_and_login(sync_client, "ali")

    with sync_client.websocket_connect(f"/api/v1/ws?token={token}") as ws:
        ws.send_json({"conversation_id": 1, "body": ""})
        message = ws.receive_json()
        assert message["type"] == "error"
        assert message["detail"] == "Invalid message body"
