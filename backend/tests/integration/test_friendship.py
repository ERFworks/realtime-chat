import pytest
from httpx import AsyncClient
from tests.conftest import login_user, register_user, get_auth_headers, get_conversation_headers

@pytest.mark.asyncio
async def test_request_successful_friendship(client: AsyncClient):
    await register_user(client)
    await register_user(client, username="mmd")

    headers = await get_auth_headers(client, username="erf")

    response = await client.post(
        "/api/v1/friends/requests/2",
        headers = headers
    )

    assert response.status_code == 201

    data = response.json()
    assert data["requester_id"] == 1
    assert data ["addressee_id"] == 2
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_reject_request_to_yourself(client: AsyncClient):

    await register_user(client)
    await login_user(client)

    headers = await get_auth_headers(client, username="erf")

    response = await client.post(
        "/api/v1/friends/requests/1",
        headers = headers
    )

    assert response.status_code == 400

@pytest.mark.asyncio
async def test_reject_duplicate_requests(client: AsyncClient):

    await register_user(client)
    await register_user(client, username="mmd")

    headers = await get_auth_headers(client, username="erf")

    response_a = await client.post(
        "/api/v1/friends/requests/2",
        headers = headers
    )

    response_b = await client.post(
        "/api/v1/friends/requests/2",
        headers = headers
    )
    assert response_b.status_code == 409


@pytest.mark.asyncio
async def test_accept_request(client: AsyncClient):

    await register_user(client)
    await register_user(client, username="mmd")

    headers_a = await get_auth_headers(client, username="erf")
    headers_b = await get_auth_headers(client, username="mmd")

    response_a = await client.post(
        "/api/v1/friends/requests/2",
        headers = headers_a
    )
    assert response_a.status_code == 201

    response_b = await client.post(
        "/api/v1/friends/requests/1/respond",
        params={"accept": True},
        headers=headers_b
    )

    assert response_b.status_code == 200
    assert response_b.json()["status"] == "accepted"


@pytest.mark.asyncio
async def test_reject_respond_by_non_addressee(client: AsyncClient):
    await register_user(client)
    await register_user(client, username="mmd")
    await register_user(client, username="ali")

    headers_a = await get_auth_headers(client, username="erf")
    headers_c = await get_auth_headers(client, username="ali")

    await client.post(
        "/api/v1/friends/requests/2",
        headers = headers_a
    )

    response = await client.post(
        "/api/v1/friends/requests/1/respond",
        params={"accept": True},
        headers=headers_c
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_accepted_friend_appears_for_both(client: AsyncClient):
    await register_user(client)
    await register_user(client, username="mmd")
    headers_a = await get_auth_headers(client, username="erf")
    headers_b = await get_auth_headers(client, username="mmd")

    await client.post("/api/v1/friends/requests/2", headers=headers_a)
    await client.post(
        "/api/v1/friends/requests/1/respond",
        params={"accept": True},
        headers=headers_b,
    )

    erf_friends = (await client.get("/api/v1/friends", headers=headers_a)).json()
    mmd_friends = (await client.get("/api/v1/friends", headers=headers_b)).json()

    assert {f["user_id"] for f in erf_friends} == {2}   
    assert {f["user_id"] for f in mmd_friends} == {1}   

@pytest.mark.asyncio
async def test_reject_reverse_duplicate(client: AsyncClient):
    await register_user(client)
    await register_user(client, username="mmd")
    headers_a = await get_auth_headers(client, username="erf")
    headers_b = await get_auth_headers(client, username="mmd")

    await client.post("/api/v1/friends/requests/2", headers=headers_a)  

    response = await client.post("/api/v1/friends/requests/1", headers=headers_b)
    assert response.status_code == 409