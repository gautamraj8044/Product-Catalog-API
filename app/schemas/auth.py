from pydantic import BaseModel, EmailStr, Field

from app.db.models import UserRole


class LoginRequest(BaseModel):
    email: EmailStr = Field(examples=["admin@example.com"])
    password: str = Field(min_length=8, examples=["AdminPass123!"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.example",
                "token_type": "bearer",
            }
        }
    }


class CreateUserRequest(BaseModel):
    email: EmailStr = Field(examples=["new-admin@example.com"])
    password: str = Field(min_length=8, examples=["StrongPass123!"])
    role: UserRole = Field(default=UserRole.USER, examples=[UserRole.ADMIN])


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    role: UserRole

    model_config = {"from_attributes": True}
