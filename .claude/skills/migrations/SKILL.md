---
name: migrations
description: Изменение схемы БД проекта — стиль моделей SQLAlchemy 2.0 (Mapped, back_populates, TYPE_CHECKING), индексы и констрейнты в модели, регистрация новой модели, make revision (--autogenerate), что автоген не умеет (новое значение enum, в т.ч. AuditActionEnum), проверка перед сквошем. Использовать при любой правке app/models/, новом индексе, enum или миграции.
---

# Схема БД: модели и миграции

**Источник истины о схеме — `app/models/`. Миграция — производная, её пишет `--autogenerate`.** Никаких `Base.metadata.create_all()` в рантайме (кроме тестов).

## Почему так

Автоген сравнивает БД с `Base.metadata`. Объект, созданный в миграции мимо модели, для него не существует и при сквоше молча исчезнет — без ошибки и без падения тестов. В прошлом проекте так терялись индексы, созданные `op.create_index`. Запросы не ломаются, а уходят в seq scan — видно только на проде под нагрузкой. Так же беззвучно при сквоше пропадают расширения (`pg_trgm` и т.п.), созданные `op.execute`.

## Стиль моделей

Только SQLAlchemy 2.0 declarative: `Mapped[...]` + `mapped_column(...)`. `Column(...)` и `declarative_base()` запрещены.

- В начале файла `from __future__ import annotations`.
- Импорты моделей только для аннотаций — под `if TYPE_CHECKING:`.
- `Mapped[...]` у каждого атрибута. Nullable из типа: `Mapped[int]` — NOT NULL, `Mapped[int | None]` — nullable. Коллекции — `Mapped[list[Child]]`.
- Все `relationship` двусторонние через `back_populates`; `backref` не использовать.
- FK-колонка и `relationship` рядом: сначала `*_id`, потом связь.
- `__tablename__` выводится автоматически в `app/models/_base.py`: CamelCase → snake_case, **в единственном числе** (`ItemImage → item_image`). Вручную — только для исключений (`User` от fastapi-users — `user`).
- Имена индексов и констрейнтов — из `naming_convention` в `_base.py`, руками не задаются.
- Колонкам — `comment='...'` по-русски (видно в DBeaver).
- Enum — в файле модели; используется в ≥ 2 моделях — в `app/models/enums.py`.
- Общие колонки — миксины `app/models/mixin/`: `IntIdPkMixin`, `CreatedAtMixin`, `UpdatedAtMixin`.
- **Новая модель — импорт в `app/models/__init__.py` и `app/core/base.py`**, иначе автоген её не увидит.
- Бизнес-логики в моделях нет.

```python
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models._base import Base
from app.models.mixin.int_id_pk import IntIdPkMixin

if TYPE_CHECKING:
    from app.models.category import Category


class Item(Base, IntIdPkMixin):
    category_id: Mapped[int] = mapped_column(
        ForeignKey('category.id'), comment='Категория'
    )
    category: Mapped[Category] = relationship(back_populates='items')
```

## Что объявляется в модели

Всё, что попадает в схему: колонки, типы, `nullable`, `server_default`, `UNIQUE`, `CHECK`, **индексы** (`index=True` для одноколоночных, `Index(...)` в `__table_args__` для составных и частичных), `ondelete`/`onupdate` у FK, значения enum. Уникальность — индексом в БД, не проверкой в коде.

## Порядок работы

1. Правим модель в `app/models/`.
2. `make revision m="..."` (= `alembic revision --autogenerate -m "..."`).
3. **Читаем сгенерированный файл глазами.** Автоген пропускает переименования (видит drop + create с потерей данных), смену типа с несовместимым `USING`, изменения `CHECK` и частичных индексов.
4. Правим миграцию данными и порядком операций, а не добавлением объектов схемы мимо моделей.
5. `make migrate`, затем `uv run alembic check` — расхождений быть не должно.

## Что автоген не умеет

| Случай | Решение |
|---|---|
| Новое значение enum (`ALTER TYPE … ADD VALUE`), в т.ч. `AuditActionEnum` | добавить в enum в модели; в миграции — `op.execute("ALTER TYPE <имя> ADD VALUE IF NOT EXISTS '...'")` внутри `op.get_context().autocommit_block()` (в транзакции нельзя), `downgrade` пустой |
| Миграция данных (UPDATE, backfill, перенос) | только руками в миграции |
| Переименование колонки/таблицы | заменить `drop_column` + `add_column` на `op.alter_column(new_column_name=...)` |
| Backfill перед `NOT NULL` | колонка nullable → `UPDATE` → `alter_column(nullable=False)` |
| Расширения, триггеры, функции, materialized view | `op.execute` + **обязательно ADR**, иначе исчезнут при сквоше |

## Перед сквошем миграций

Собрать две базы — прогоном всей цепочки и автогеном из моделей — и сравнить схемы (колонки, индексы, констрейнты, enum, расширения). Разница = что-то живёт только в миграциях. Разный порядок значений enum допустим.

Если объект не выражается в метаданных и автоген его теряет — **остановиться и обсудить** с автором, а не оставлять расхождение молча.

## На проде

Миграции применяет при деплое сервис `migrate`, `web` стартует только после их успеха. Поэтому миграция проверяется `make migrate` на локальной базе с данными, а не только на пустой. Деструктивные шаги (drop, смена типа, `NOT NULL` без backfill) — только обсудив с автором.
