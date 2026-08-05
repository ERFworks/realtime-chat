import uuid
import pytest
from fastapi import HTTPException
from app.models.profile import Profile
from app.services.profile import get_my_profile, update_bio, set_profile_picture
from tests.unit.fakes import FakeProfileRepository, FakeFileStorage, FakeUpload, FakeUnitOfWork
from app.core.config import settings


def get_profile(profile_id: int = 1, user_id: int = 1, biography: str = "salam", profile_pic: str = None) -> Profile:
    return Profile(
            profile_id = profile_id,
            user_id = user_id,
            biography = biography,
            profile_pic = profile_pic
        )


async def test_get_my_profile_returns_profile():
    uow = FakeUnitOfWork()
    uow.profiles = FakeProfileRepository({1: get_profile()})
    result = await get_my_profile(uow, FakeFileStorage(), user_id=1)
    assert result.user_id == 1
    assert result.biography == "salam"
    assert result.profile_pic is None


async def test_get_my_profile_missing_raises_404():
    uow = FakeUnitOfWork()
    with pytest.raises(HTTPException) as exc:
        await get_my_profile(uow, FakeFileStorage(),user_id=5)

    assert exc.value.status_code == 404


async def test_update_bio_updates_profile():
    profile = get_profile()
    uow = FakeUnitOfWork()
    uow.profiles = FakeProfileRepository({1: profile})
    result = await update_bio(uow, FakeFileStorage(),user_id=1, biography="hello")

    assert result.biography == "hello"
    assert profile.biography == "hello"
    assert uow.committed is True


async def test_set_profile_picture_replace_old():
    profile = get_profile(profile_pic="old/key.png")
    uow = FakeUnitOfWork()
    uow.profiles = FakeProfileRepository({1: profile})
    storage = FakeFileStorage()
    guid = uuid.uuid4()
    result = await set_profile_picture(
        uow, storage,user_id=1, user_guid=guid, 
        file=FakeUpload(content=b"data", content_type="image/png")
    )

    assert profile.profile_pic.startswith(f"profile_pics/{guid}/")
    assert profile.profile_pic.endswith(f".png")
    assert storage.deleted == ["old/key.png"]
    assert result.profile_pic == storage.url_for(profile.profile_pic)
    assert uow.committed is True


async def test_set_profile_picture_rejects_wrong_type():
    uow = FakeUnitOfWork()
    uow.profiles = FakeProfileRepository({1: get_profile()})
    with pytest.raises(HTTPException) as exc:
        await set_profile_picture(
            uow, FakeFileStorage(), user_id=1, user_guid=uuid.uuid4(),
            file=FakeUpload(content_type="application/pdf")
        )

    assert exc.value.status_code == 415
    assert uow.committed is False


async def test_set_profile_picture_rejects_too_large(monkeypatch):
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE", 3)
    uow = FakeUnitOfWork()
    uow.profiles = FakeProfileRepository({1: get_profile()})
    with pytest.raises(HTTPException) as exc:
        await set_profile_picture(
            uow, FakeFileStorage(), user_id=1, user_guid=uuid.uuid4(),
            file=FakeUpload(content=b"toolong", content_type="image/png")
        )

    assert exc.value.status_code == 413
    assert uow.committed is False