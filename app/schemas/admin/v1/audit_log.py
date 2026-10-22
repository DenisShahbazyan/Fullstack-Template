from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.audit_log import AuditActionEnum


class AuditLogSchema(BaseModel):
    """Запись журнала админских действий."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    actor_user_id: int
    action: AuditActionEnum
    object_type: str
    object_id: int
    payload: dict[str, Any]
