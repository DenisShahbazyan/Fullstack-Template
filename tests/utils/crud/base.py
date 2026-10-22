from datetime import datetime

from pydantic import BaseModel, Field
from sqlalchemy.orm import Mapped, mapped_column

from app.models._base import Base
from app.models.mixin.int_id_pk import IntIdPkMixin


class ModelForBaseCRUD(Base, IntIdPkMixin):
    """Тестовая модель для тестирования базовых CRUD операций."""

    name: Mapped[str]
    email: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str | None]
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    user_id: Mapped[int | None]
    is_deleted: Mapped[bool] = mapped_column(default=False)
    deleted_at: Mapped[datetime | None]

    # Альтернативные поля мягкого удаления — для тестов с кастомными именами
    status: Mapped[str] = mapped_column(default='active')
    archived_at: Mapped[datetime | None]
    archived_by: Mapped[int | None]


# Pydantic схемы для тестирования
class ModelForBaseCRUDCreateSchema(BaseModel):
    """Схема для тестирования базовых CRUD операций. Для создания объекта."""

    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., max_length=255)
    description: str | None = None
    is_active: bool = True
    user_id: int | None = None


class ModelForBaseCRUDUpdateSchema(BaseModel):
    """Схема для тестирования базовых CRUD операций. Для обновления объекта."""

    name: str | None = Field(None, min_length=1, max_length=100)
    email: str | None = Field(None, max_length=255)
    description: str | None = None
    is_active: bool | None = None
