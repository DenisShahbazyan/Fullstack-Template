from fastapi_users import schemas
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.domain.auth.password import MIN_PASSWORD_LENGTH
from app.models.user import UserRoleEnum


class LoginRequestSchema(BaseModel):
    email: EmailStr
    password: str


class LoginResponseSchema(BaseModel):
    access_token: str
    token_type: str


class UserNameSchema(BaseModel):
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)

    @field_validator('first_name', 'last_name', mode='before')
    @classmethod
    def _empty_to_none(cls, value: object) -> object:
        """HTML-форма шлёт незаполненное поле как '', а не опускает его."""
        if isinstance(value, str):
            return value.strip() or None
        return value


class UserReadSchema(schemas.BaseUser[int], UserNameSchema):
    role: UserRoleEnum


class UserCreateSchema(schemas.BaseUserCreate, UserNameSchema):
    password: str = Field(min_length=MIN_PASSWORD_LENGTH)

    @field_validator('email', mode='before')
    @classmethod
    def _normalize_email(cls, value: object) -> object:
        """Два адреса, отличающихся только регистром, уникальный индекс пропустил бы."""
        return value.strip().lower() if isinstance(value, str) else value


class UserUpdateSchema(schemas.BaseUserUpdate, UserNameSchema):
    pass
