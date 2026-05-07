from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_auth_service, require_role
from app.db.models import User, UserRole
from app.schemas.auth import CreateUserRequest, LoginRequest, TokenResponse, UserResponse
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate a user and return a JWT token",
    description=(
        "Submit bootstrap-admin or registered user credentials to receive a Bearer token. "
        "Use the token with the `Authorize` button in Swagger UI."
    ),
)
async def login(payload: LoginRequest, auth_service: AuthService = Depends(get_auth_service)) -> TokenResponse:
    return await auth_service.login(email=payload.email, password=payload.password)


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user account",
    description="Admin-only endpoint to create a user or another admin account.",
)
async def create_user(
    payload: CreateUserRequest,
    auth_service: AuthService = Depends(get_auth_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> UserResponse:
    return await auth_service.create_user(
        email=payload.email,
        password=payload.password,
        role=payload.role,
    )
