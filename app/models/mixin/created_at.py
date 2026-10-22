from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixin._utils import get_current_dt_utc


class CreatedAtMixin:
    """Миксин для добавления поля created_at (время создания объекта).

    Поведение зависит от того, используется ли одновременно UpdatedAtMixin:

    1. Если используется ТОЛЬКО CreatedAtMixin:
        - При INSERT через ORM: created_at устанавливается из
            insert_default=get_current_dt_utc
        - При прямом SQL INSERT: created_at устанавливается из
            server_default=func.now()

    2. Если используется ВМЕСТЕ с UpdatedAtMixin:
        - При INSERT через ORM: оба поля (created_at и updated_at) устанавливаются
            одновременно через event listener, гарантируя абсолютно идентичные значения
        - При прямом SQL INSERT: оба поля устанавливаются через
            server_default=func.now()
    """

    created_at: Mapped[datetime] = mapped_column(
        insert_default=get_current_dt_utc,
        server_default=func.now(),
    )
