from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, UserRole


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, *, email: str, hashed_password: str, role: UserRole) -> User:
        user = User(email=email, hashed_password=hashed_password, role=role)
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user
