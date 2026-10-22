"""Запись изменяющих админ-действий в журнал аудита."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditActionEnum, AuditLog

OBJECT_USER = 'user'


def record_action(
    async_session: AsyncSession,
    actor_user_id: int,
    action: AuditActionEnum,
    object_type: str,
    object_id: int,
    payload: dict[str, Any] | None = None,
) -> None:
    """Добавляет запись журнала в сессию — коммитит вызывающий вместе с действием."""
    async_session.add(
        AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            object_type=object_type,
            object_id=object_id,
            payload=payload or {},
        ),
    )
