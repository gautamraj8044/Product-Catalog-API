from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.dependencies import get_auth_service, get_current_user
from app.api.routes.auth import router as auth_router
from app.core.security import decode_token, hash_password
from app.db.models import User, UserRole
from app.main import app as main_app
from app.schemas.auth import TokenResponse, UserResponse
from app.services.auth import AuthService


class FakeSession:
    def __init__(self) -> None:
        self.committed = False

    async def commit(self) -> None:
        self.committed = True


class FakeUserRepository:
    def __init__(self, existing_user=None) -> None:
        self.session = FakeSession()
        self.existing_user = existing_user
        self.created_user = None

    async def get_by_email(self, email: str):
        if self.existing_user and self.existing_user.email == email:
            return self.existing_user
        return None

    async def create(self, *, email: str, hashed_password: str, role: UserRole):
        self.created_user = SimpleNamespace(
            id=2,
            email=email,
            hashed_password=hashed_password,
            role=role,
        )
        return self.created_user


class FakeLoginUserRepository:
    def __init__(self, user=None) -> None:
        self.user = user

    async def get_by_email(self, email: str):
        if self.user and self.user.email == email:
            return self.user
        return None


@pytest.mark.asyncio
async def test_auth_service_create_user_creates_admin_account():
    repository = FakeUserRepository()
    service = AuthService(repository)

    response = await service.create_user(
        email="second-admin@example.com",
        password="AdminPass456!",
        role=UserRole.ADMIN,
    )

    assert response == UserResponse(id=2, email="second-admin@example.com", role=UserRole.ADMIN)
    assert repository.created_user is not None
    assert repository.created_user.hashed_password != "AdminPass456!"
    assert repository.session.committed is True


@pytest.mark.asyncio
async def test_auth_service_create_user_rejects_duplicate_email():
    existing_user = SimpleNamespace(
        id=1,
        email="existing@example.com",
        hashed_password="hashed",
        role=UserRole.USER,
    )
    repository = FakeUserRepository(existing_user=existing_user)
    service = AuthService(repository)

    with pytest.raises(HTTPException) as exc_info:
        await service.create_user(
            email="existing@example.com",
            password="Password123!",
            role=UserRole.USER,
        )

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_auth_service_login_returns_access_token_for_valid_credentials():
    hashed_password = hash_password("AdminPass123!")
    repository = FakeLoginUserRepository(
        user=SimpleNamespace(
            id=7,
            email="admin@example.com",
            hashed_password=hashed_password,
            role=UserRole.ADMIN,
        )
    )
    service = AuthService(repository)

    response = await service.login(email="admin@example.com", password="AdminPass123!")

    assert isinstance(response, TokenResponse)
    assert response.token_type == "bearer"
    payload = decode_token(response.access_token)
    assert payload["sub"] == "7"
    assert payload["role"] == "admin"


@pytest.mark.asyncio
async def test_auth_service_login_rejects_invalid_password():
    hashed_password = hash_password("AdminPass123!")
    repository = FakeLoginUserRepository(
        user=SimpleNamespace(
            id=7,
            email="admin@example.com",
            hashed_password=hashed_password,
            role=UserRole.ADMIN,
        )
    )
    service = AuthService(repository)

    with pytest.raises(HTTPException) as exc_info:
        await service.login(email="admin@example.com", password="WrongPass123!")

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid email or password."


@pytest.mark.asyncio
async def test_auth_service_login_rejects_unknown_email():
    service = AuthService(FakeLoginUserRepository())

    with pytest.raises(HTTPException) as exc_info:
        await service.login(email="missing@example.com", password="WrongPass123!")

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid email or password."


class StubAuthService:
    def __init__(self) -> None:
        self.calls = []

    async def create_user(self, *, email: str, password: str, role: UserRole) -> UserResponse:
        self.calls.append({"email": email, "password": password, "role": role})
        return UserResponse(id=10, email=email, role=role)


def test_create_user_route_requires_admin_role():
    app = FastAPI()
    app.include_router(auth_router)
    app.dependency_overrides[get_auth_service] = lambda: StubAuthService()
    app.dependency_overrides[get_current_user] = lambda: User(
        email="user@example.com",
        hashed_password="hashed",
        role=UserRole.USER,
    )

    with TestClient(app) as client:
        response = client.post(
            "/auth/users",
            json={
                "email": "new-user@example.com",
                "password": "Password123!",
                "role": "user",
            },
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions for this action."


def test_create_user_route_allows_admin_to_create_another_admin():
    app = FastAPI()
    app.include_router(auth_router)
    stub_auth_service = StubAuthService()
    app.dependency_overrides[get_auth_service] = lambda: stub_auth_service
    app.dependency_overrides[get_current_user] = lambda: User(
        email="admin@example.com",
        hashed_password="hashed",
        role=UserRole.ADMIN,
    )

    with TestClient(app) as client:
        response = client.post(
            "/auth/users",
            json={
                "email": "new-admin@example.com",
                "password": "Password123!",
                "role": "admin",
            },
        )

    assert response.status_code == 201
    assert response.json() == {
        "id": 10,
        "email": "new-admin@example.com",
        "role": "admin",
    }
    assert stub_auth_service.calls == [
        {
            "email": "new-admin@example.com",
            "password": "Password123!",
            "role": UserRole.ADMIN,
        }
    ]


def test_login_and_access_protected_products_route_with_real_bearer_token():
    main_app.openapi_schema = None

    with TestClient(main_app) as client:
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "AdminPass123!"},
        )

        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        products_response = client.get(
            "/api/v1/products",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert products_response.status_code == 200
