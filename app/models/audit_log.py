from __future__ import annotations

from enum import StrEnum, auto
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, BigInteger, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models._base import Base
from app.models.mixin.created_at import CreatedAtMixin
from app.models.mixin.int_id_pk import IntIdPkMixin

if TYPE_CHECKING:
    from app.models.user import User


class AuditActionEnum(StrEnum):
    """Изменяющие админ-действия, попадающие в журнал."""

    USER_ROLE_CHANGE = auto()


class AuditLog(Base, IntIdPkMixin, CreatedAtMixin):
    """Журнал изменяющих действий администрации: кто, что, когда, с какими данными."""

    __table_args__ = (Index('ix_audit_log_created_at', 'created_at'),)

    actor_user_id: Mapped[int] = mapped_column(
        ForeignKey('user.id'),
        comment='Кто выполнил действие',
    )
    actor_user: Mapped[User] = relationship(back_populates='audit_logs')

    action: Mapped[AuditActionEnum] = mapped_column(
        index=True,
        comment='Что сделано',
    )
    object_type: Mapped[str] = mapped_column(comment='Тип объекта: user, ...')
    object_id: Mapped[int] = mapped_column(BigInteger, comment='ID объекта')
    payload: Mapped[dict[str, Any]] = mapped_column(
        type_=JSON,
        default=dict,
        server_default='{}',
        comment='Детали действия: прежнее и новое значение',
    )
