from __future__ import annotations

from enum import StrEnum, auto
from typing import TYPE_CHECKING

from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTable
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models._base import Base
from app.models.mixin.created_at import CreatedAtMixin
from app.models.mixin.int_id_pk import IntIdPkMixin
from app.models.mixin.updated_at import UpdatedAtMixin

if TYPE_CHECKING:
    from app.models.audit_log import AuditLog


class UserRoleEnum(StrEnum):
    USER = auto()
    MODER = auto()
    ADMIN = auto()


class User(
    SQLAlchemyBaseUserTable[int],
    Base,
    IntIdPkMixin,
    CreatedAtMixin,
    UpdatedAtMixin,
):
    """Пользователь. Логин — email, права — роль."""

    first_name: Mapped[str | None] = mapped_column(comment='Имя')
    last_name: Mapped[str | None] = mapped_column(comment='Фамилия')
    role: Mapped[UserRoleEnum] = mapped_column(
        default=UserRoleEnum.USER,
        server_default=UserRoleEnum.USER.name,
        comment='Роль',
    )

    audit_logs: Mapped[list[AuditLog]] = relationship(back_populates='actor_user')
