from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.user import UserRoleEnum


class UserAdminSchema(BaseModel):
    """Пользователь в админской выдаче: с ролью и датой регистрации."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    first_name: str | None
    last_name: str | None
    role: UserRoleEnum
    is_active: bool
    created_at: datetime


class UserRoleUpdateSchema(BaseModel):
    """Смена роли пользователя администратором."""

    role: UserRoleEnum
