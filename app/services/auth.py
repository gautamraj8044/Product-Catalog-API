from fastapi import HTTPException, status

from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import UserRole
from app.repositories.user import UserRepository
from app.schemas.auth import TokenResponse, UserResponse


class AuthService:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def login(self, *, email: str, password: str) -> TokenResponse:
        user = await self.user_repository.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        token = create_access_token(subject=str(user.id), role=user.role.value)
        return TokenResponse(access_token=token)

    async def create_user(self, *, email: str, password: str, role: UserRole) -> UserResponse:
        existing_user = await self.user_repository.get_by_email(email)
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists.",
            )

        user = await self.user_repository.create(
            email=email,
            hashed_password=hash_password(password),
            role=role,
        )
        await self.user_repository.session.commit()
        return UserResponse.model_validate(user)
