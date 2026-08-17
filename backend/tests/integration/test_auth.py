import pytest
from httpx import AsyncClient

from tests.conftest import register_user, login_user


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    response = await register_user(client)

    assert response.status_code == 201

    data = response.json()

    assert data["username"] == "erf"
    assert data["first_name"] == "erfan"
    assert data["last_name"] is None
    assert "user_id" in data

    assert "password" not in data
    assert "password_hash" not in data



@pytest.mark.asyncio
async def test_register_rejects_short_password(client: AsyncClient):
    response = await register_user(client, password = "123")

    assert response.status_code == 422



@pytest.mark.asyncio
async def test_register_rejects_short_username(client : AsyncClient):
    response = await register_user(client,username="er")

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_rejects_duplicate_username(client: AsyncClient):
        
        first_response = await register_user(client)
        second_response = await register_user(client)

        assert first_response.status_code == 201
        assert second_response.status_code == 409
        assert second_response.json()["detail"] == "Username already exists"

        
        
@pytest.mark.asyncio
async def test_login_successful(client: AsyncClient):

    register_response = await register_user(client)

    assert register_response.status_code == 201

    login_response = await login_user(client)

    assert login_response.status_code == 200

    data = login_response.json()

    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str)
    assert isinstance(data["refresh_token"], str)
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["access_token"] != data["refresh_token"]



@pytest.mark.asyncio
async def test_login_rejects_wrong_password(client: AsyncClient):

    response_register = await register_user(client)
    assert response_register.status_code == 201

    response_login = await login_user(client, password="wrong-password")
    assert response_login.status_code == 401
    assert response_login.json()["detail"] == "Invalid username or password"


@pytest.mark.asyncio
async def test_login_rejects_unknown_user(client: AsyncClient):

    response_login = await login_user(client)

    assert response_login.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_current_user(client: AsyncClient):
    await register_user(client)

    login_response = await login_user(client)

    access_token = login_response.json()["access_token"]

    response = await client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": f"Bearer {access_token}",
        }
    )

    assert response.status_code == 200
    data = response.json()

    assert data["username"] == "erf"
    assert data["first_name"] == "erfan"



@pytest.mark.asyncio
async def test_me_rejects_missing_token(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401



@pytest.mark.asyncio
async def test_me_rejects_invalid_token(client: AsyncClient):
    response = await client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization" : "Bearer invalid-token"
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


@pytest.mark.asyncio
async def test_me_rejects_refresh_token(client: AsyncClient):
    await register_user(client)

    login_response = await login_user(client)

    refresh_token = login_response.json()["refresh_token"]

    response = await client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": f"Bearer {refresh_token}",
        }
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


from app.core.security import create_access_token

@pytest.mark.asyncio
async def test_me_rejects_non_numberic_token_subject(
    client: AsyncClient
):
    token = create_access_token(
        {
            "sub" : "Not a number"
        }
    )

    response = await client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": f"Bearer {token}",
        }
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"



@pytest.mark.asyncio
async def test_register_normalizes_username(client: AsyncClient):
    response = await register_user(client, username="   ERfan  ")

    assert response.status_code == 201
    assert response.json()["username"] == "erfan"


@pytest.mark.asyncio
async def test_username_is_case_insensitive(client: AsyncClient):
    first_response = await register_user(client, username="   ERfan  ")
    second_response = await register_user(client, username="  erFAn")

    assert first_response.status_code == 201
    assert second_response.status_code == 409


@pytest.mark.asyncio
async def test_login_is_case_insensitive(client: AsyncClient):
    await register_user(client, username="ERfan")
    response = await login_user(client, username="  ERfan  ")
    assert response.status_code == 200



async def _login_tokens(client: AsyncClient) -> dict:
    await register_user(client)
    login_response = await login_user(client)
    assert login_response.status_code == 200
    return login_response.json()


@pytest.mark.asyncio
async def test_refresh_rotates_token(client: AsyncClient):
    tokens = await _login_tokens(client)

    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh_response.status_code == 200

    new_tokens = refresh_response.json()
    assert new_tokens["refresh_token"] != tokens["refresh_token"]
    assert new_tokens["access_token"]

    # the old refresh token was invalidated by the rotation
    replay_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert replay_response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_reuse_detection_revokes_family(client: AsyncClient):
    tokens = await _login_tokens(client)

    first = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert first.status_code == 200
    newest_refresh = first.json()["refresh_token"]

    # replaying the rotated-out token is reuse -> whole family revoked
    replay = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert replay.status_code == 401

    # even the newest token of the family is now dead
    newest = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": newest_refresh},
    )
    assert newest.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_refresh_and_access_tokens(client: AsyncClient):
    tokens = await _login_tokens(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    logout_response = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers=headers,
    )
    assert logout_response.status_code == 204

    # refresh with the logged-out token fails
    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh_response.status_code == 401

    # the access token was denylisted too
    me_response = await client.get("/api/v1/auth/me", headers=headers)
    assert me_response.status_code == 401


@pytest.mark.asyncio
async def test_logout_requires_authentication(client: AsyncClient):
    await register_user(client)
    login_response = await login_user(client)
    tokens = login_response.json()

    response = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert response.status_code == 401