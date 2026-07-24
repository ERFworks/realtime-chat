import pytest
from httpx import AsyncClient

from tests.conftest import register_user, login_user, get_auth_headers

@pytest.mark.asyncio
async def test_create_private_chat_successfull(client: AsyncClient):

    await register_user(client)
    await register_user(client, username="mmd")

    headers = await get_auth_headers(client, username="mmd")


    response = await client.post(
        "/api/v1/conversations",
        json={"other_user_id":1},
        headers=headers
    )

    assert response.status_code == 201

    data = response.json()
    assert len(data["participants"]) == 2



@pytest.mark.asyncio
async def test_reject_no_user(client: AsyncClient):
    await register_user(client)
    headers = await get_auth_headers(client)

    response = await client.post(
        "/api/v1/conversations",
        json={"other_user_id":999},
        headers=headers
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_reject_chat_with_yourself(client: AsyncClient):
    await register_user(client)
    headers = await get_auth_headers(client)

    response = await client.post(
        "/api/v1/conversations",
        json={"other_user_id":1},
        headers=headers
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_request_again_already_chat(client: AsyncClient):

    await register_user(client)
    await register_user(client, username="mmd")

    headers = await get_auth_headers(client, username="mmd")

    response_a = await client.post(
        "/api/v1/conversations",
        json={"other_user_id":1},
        headers=headers
    )

    response_b = await client.post(
        "/api/v1/conversations",
        json={"other_user_id":1},
        headers=headers
    )

    assert response_a.json()["conversation_id"] == response_b.json()["conversation_id"]



@pytest.mark.asyncio
async def test_reject_without_token(client: AsyncClient):

    response = await client.post(
        "/api/v1/conversations",
        json={"other_user_id":1},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_each_user_sees_only_own_conversations(client: AsyncClient):

    await register_user(client)                                 
    headers_erf = await get_auth_headers(client)     

    await register_user(client, username="mmd")                  
    headers_mmd = await get_auth_headers(client, username="mmd") 

    await register_user(client, username="ali")                 

    
    conv_x = await client.post(
        "/api/v1/conversations", 
        json={"other_user_id": 2}, 
        headers=headers_erf
    )
    x_id = conv_x.json()["conversation_id"]

    
    conv_y = await client.post(
        "/api/v1/conversations", 
        json={"other_user_id": 3}, 
        headers=headers_mmd
    )
    y_id = conv_y.json()["conversation_id"]

    erf_convs = (await client.get(
        "/api/v1/conversations", 
        headers=headers_erf
    )).json()
    
    mmd_convs = (await client.get(
        "/api/v1/conversations", 
        headers=headers_mmd
        )).json()


    erf_ids = {c["conversation_id"] for c in erf_convs}
    mmd_ids = {c["conversation_id"] for c in mmd_convs}

    assert erf_ids == {x_id}
    assert mmd_ids == {x_id, y_id}