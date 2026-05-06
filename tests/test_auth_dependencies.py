from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api.dependencies import get_current_user, require_role
from app.db.models import UserRole


class FakeSession:
    def __init__(self, user) -> None:
        self.user = user

    async def get(self, model, user_id: int):
        return self.user


@pytest.mark.asyncio
async def test_get_current_user_rejects_missing_credentials():
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=None, session=FakeSession(None))

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Not authenticated."


@pytest.mark.asyncio
async def test_get_current_user_rejects_invalid_auth_scheme():
    credentials = HTTPAuthorizationCredentials(scheme="Basic", credentials="token")

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=credentials, session=FakeSession(None))

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Not authenticated."


@pytest.mark.asyncio
async def test_get_current_user_rejects_missing_subject(monkeypatch):
    monkeypatch.setattr("app.api.dependencies.decode_token", lambda token: {"role": "admin"})
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="jwt-token")

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=credentials, session=FakeSession(None))

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid token payload."


@pytest.mark.asyncio
async def test_get_current_user_rejects_deleted_user(monkeypatch):
    monkeypatch.setattr("app.api.dependencies.decode_token", lambda token: {"sub": "5", "role": "admin"})
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="jwt-token")

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=credentials, session=FakeSession(None))

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "User no longer exists."


@pytest.mark.asyncio
async def test_get_current_user_returns_user_for_valid_token(monkeypatch):
    monkeypatch.setattr("app.api.dependencies.decode_token", lambda token: {"sub": "5", "role": "admin"})
    user = SimpleNamespace(id=5, email="admin@example.com", role=UserRole.ADMIN)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="jwt-token")

    current_user = await get_current_user(credentials=credentials, session=FakeSession(user))

    assert current_user is user


@pytest.mark.asyncio
async def test_require_role_allows_matching_role():
    dependency = require_role(UserRole.ADMIN)
    admin_user = SimpleNamespace(role=UserRole.ADMIN)

    current_user = await dependency(current_user=admin_user)

    assert current_user is admin_user


@pytest.mark.asyncio
async def test_require_role_rejects_non_matching_role():
    dependency = require_role(UserRole.ADMIN)

    with pytest.raises(HTTPException) as exc_info:
        await dependency(current_user=SimpleNamespace(role=UserRole.USER))

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Insufficient permissions for this action."
