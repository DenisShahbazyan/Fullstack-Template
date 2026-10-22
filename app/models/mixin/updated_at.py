from datetime import datetime
from typing import Any

from sqlalchemy import event, func
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Mapped, Mapper, mapped_column

from app.models.mixin._utils import get_current_dt_utc


class UpdatedAtMixin:
    """Миксин для добавления поля updated_at (время последнего обновления).

    При создании объекта:
    - Если используется ВМЕСТЕ с CreatedAtMixin (рекомендуется):
      * При INSERT через ORM: event listener устанавливает created_at и updated_at
        в одно и то же значение, гарантируя их идентичность (решает проблему разницы
        в миллисекундах, которая возникает при высокой нагрузке на сервере)
      * При прямом SQL INSERT: оба поля устанавливаются через server_default=func.now()

    - Если используется БЕЗ CreatedAtMixin:
      * При INSERT через ORM: updated_at устанавливается через insert_default
      * При прямом SQL INSERT: updated_at устанавливается через
        server_default=func.now()

    При обновлении объекта:
    - При UPDATE через ORM: updated_at обновляется через onupdate=get_current_dt_utc
    - При прямом SQL UPDATE: updated_at обновляется через server_onupdate=func.now()
    """

    updated_at: Mapped[datetime] = mapped_column(
        insert_default=get_current_dt_utc,
        onupdate=get_current_dt_utc,
        server_default=func.now(),
        server_onupdate=func.now(),
    )

    @classmethod
    def __declare_last__(cls) -> None:
        """Настройка event listener после полной инициализации маппера.

        Регистрирует обработчик before_insert, который синхронизирует значения
        created_at и updated_at при создании объекта, если присутствуют оба поля.
        """

        @event.listens_for(cls, 'before_insert', propagate=True)
        def sync_timestamps_on_insert(
            mapper: Mapper[Any],
            connection: Connection,
            target: Any,
        ) -> None:
            if hasattr(target, 'created_at') and hasattr(target, 'updated_at'):
                now = get_current_dt_utc()
                target.created_at = now
                target.updated_at = now
