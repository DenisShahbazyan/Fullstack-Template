"""Импорты класса Base и всех моделей для Alembic."""

from app.models._base import Base  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.user import User  # noqa: F401
