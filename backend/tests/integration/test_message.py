import pytest
from httpx2 import AsyncClient

from tests.conftest import (
    get_auth_headers,
    get_conversation_headers,
    register_user,
)


@pytest.mark.asyncio
async def test_send_successful_message(client: AsyncClient):

    conversation = await get_conversation_headers(client)
    

    response_message = await client.post(
        "/api/v1/conversations/1/messages",
        json={"body": "Hi"},
        headers = conversation
    )

    assert response_message.status_code == 201
    data = response_message.json()
    assert data["body"] == "Hi"
    assert data["sender_id"] is not None



@pytest.mark.asyncio
async def test_reject_outsider(client: AsyncClient):

    await register_user(client)
    await register_user(client, username="mmd")
    headers_a = await get_auth_headers(client)
    await client.post(
        "/api/v1/conversations",
        json={"other_user_id": 2},
        headers=headers_a
    )

    await register_user(client, username="ali")
    headers_c = await get_auth_headers(client, username="ali")


    response = await client.post(
        "/api/v1/conversations/1/messages",
        json={"body": "Hi"},
        headers = headers_c
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_successful_messages(client: AsyncClient):

    headers = await get_conversation_headers(client)

    await client.post(
        "/api/v1/conversations/1/messages",
        json={"body": "Hi"},
        headers = headers
    )

    response_get = await client.get(
        "/api/v1/conversations/1/messages",
        headers=headers
    )

    assert response_get.status_code == 200
    data = response_get.json()
    assert len(data) == 1
    assert data[0]["body"] == "Hi"


