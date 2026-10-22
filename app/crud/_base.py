from datetime import datetime
from http import HTTPStatus
from typing import Any, Generic, Sequence, Type, TypeVar

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import ColumnElement, delete, func, select, update
from sqlalchemy import exists as sql_exists
from sqlalchemy.ext.asyncio import AsyncSession

from app.models._base import Base

PydanticSchema = TypeVar('PydanticSchema', bound=BaseModel)
SQLAlchemyModel = TypeVar('SQLAlchemyModel', bound=Base)


class CRUDBase(Generic[SQLAlchemyModel]):
    """При наследовании от базового класса нужно указывать в квадратных скобках модель
    с которой будет работать новый класс, и которая будет хранится в `self.model`.

    Example:
    ```
    # Наследование будет не таким
    class CRUDUser(CRUDBase):
    # а таким:
    class CRUDUser(CRUDBase[User]):
    ```
    """

    def __init__(self, model: Type[SQLAlchemyModel]) -> None:
        self.model = model

    async def get(
        self,
        async_session: AsyncSession,
        filters: dict[str, Any],
    ) -> SQLAlchemyModel | None:
        """Получает один элемент по заданным полям.

        Args:
            async_session (AsyncSession): Асинхронная сессия
            filters (dict[str, Any]): Словарь для фильтрации в формате
                {"поле": значение}

        Returns:
            SQLAlchemyModel | None: Найденный объект или None, если объект не найден

        Example:
        ```
            # По ID
            user = await crud.get(session, {"id": 1})

            # По email
            user = await crud.get(session, {"email": "test@example.com"})

            # По нескольким полям
            user = await crud.get(
                session, {"email": "test@example.com", "is_active": True}
            )
        ```
        """
        if not filters:
            raise ValueError('Необходимо указать хотя бы одно поле для поиска')

        query = select(self.model).filter_by(**filters)
        result = await async_session.execute(query)
        return result.scalars().first()

    async def get_or_404(
        self,
        async_session: AsyncSession,
        filters: dict[str, Any],
        *,
        _detail: str | None = None,
    ) -> SQLAlchemyModel:
        """Получает один элемент по заданным полям или возвращает 404 ошибку.

        Args:
            async_session (AsyncSession): Асинхронная сессия
            filters (dict[str, Any]): Словарь для фильтрации в формате
                {"поле": значение}
            _detail (str | None): Кастомное сообщение об ошибке

        Returns:
            SQLAlchemyModel: Найденный объект

        Raises:
            HTTPException: 404 если объект не найден

        Example:
        ```
            # По ID
            user = await crud.get_or_404(session, {"id": 1})

            # По email с кастомной ошибкой
            user = await crud.get_or_404(
                session,
                {"email": "test@example.com"},
                _detail="Пользователь не найден",
            )

            # По нескольким полям
            user = await crud.get_or_404(
                session,
                {"email": "test@example.com", "is_active": True},
            )
        ```
        """
        db_obj = await self.get(async_session, filters)

        if not db_obj:
            if _detail:
                error_detail = _detail
            else:
                filter_parts = [f'{k}={v}' for k, v in filters.items()]
                filter_str = ', '.join(filter_parts)
                error_detail = f'{self.model.__name__} with {filter_str} not found'

            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=error_detail,
            )

        return db_obj

    async def get_by_condition(
        self,
        async_session: AsyncSession,
        *conditions: ColumnElement[bool],
    ) -> SQLAlchemyModel | None:
        """Получает один элемент по сложным условиям.

        Args:
            async_session: Асинхронная сессия
            *conditions: Условия для фильтрации

        Example:
        ```
            # OR условие
            user = await crud.get_by_condition(
                session,
                or_(User.email == "test@test.com", User.username == "test")
            )

            # Сложные условия
            user = await crud.get_by_condition(
                session,
                User.age >= 18,
                User.is_active == True,
                or_(User.role == "admin", User.role == "moderator")
            )
        ```
        """
        if not conditions:
            raise ValueError('Необходимо указать хотя бы одно условие')

        query = select(self.model).filter(*conditions)
        result = await async_session.execute(query)
        return result.scalars().first()

    async def get_by_condition_or_404(
        self,
        async_session: AsyncSession,
        *conditions: ColumnElement[bool],
        _detail: str | None = None,
    ) -> SQLAlchemyModel:
        """Получает один элемент по сложным условиям или возвращает 404 ошибку.

        Args:
            async_session: Асинхронная сессия
            *conditions: Условия для фильтрации

        Example:
        ```
            # OR условие
            user = await crud.get_by_condition_or_404(
                session,
                or_(User.email == "test@test.com", User.username == "test")
            )

            # Сложные условия
            user = await crud.get_by_condition_or_404(
                session,
                User.age >= 18,
                User.is_active == True,
                or_(User.role == "admin", User.role == "moderator")
            )
        ```
        """
        db_obj = await self.get_by_condition(async_session, *conditions)

        if not db_obj:
            error_detail = _detail or f'{self.model.__name__} not found'
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=error_detail,
            )
        return db_obj

    async def get_multi(
        self,
        async_session: AsyncSession,
        filters: dict[str, Any] | None = None,
        *,
        order_by: tuple[ColumnElement[Any], ...] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> Sequence[SQLAlchemyModel]:
        """Получает список элементов с простыми условиями.

        Args:
            async_session (AsyncSession): Асинхронная сессия
            filters (dict[str, Any] | None): Словарь для фильтрации
            order_by (tuple[ColumnElement, ...] | None, optional): Кортеж столбцов для
                сортировки. Используйте .asc() для сортировки по возрастанию и .desc()
                для убывания. По умолчанию None.
            limit (int | None): Максимальное количество записей
            offset (int | None): Смещение для пагинации

        Returns:
            Sequence[SQLAlchemyModel]: Список найденных объектов или [], если объекты не
                найдены

        Example:
        ```
            # Все записи
            users = await crud.get_multi(session)

            # С фильтрацией
            active_users = await crud.get_multi(session, {"is_active": True})

            # Сортировка по одному полю по возрастанию
            users = await crud.get_multi(
                session,
                order_by=(User.created_at.asc(),)
            )

            # Сортировка по нескольким полям с фильтрацией
            users = await crud.get_multi(
                session,
                {"is_active": True, "role": "admin"},
                order_by=(User.role.asc(), User.created_at.desc()),
            )

            # С пагинацией
            users = await crud.get_multi(
                session,
                {"is_active": True},
                limit=10,
                offset=20,
            )
        ```
        """
        query = select(self.model).filter_by(**(filters or {}))

        if order_by:
            query = query.order_by(*order_by)

        if offset is not None:
            query = query.offset(offset)

        if limit is not None:
            query = query.limit(limit)

        db_objs = await async_session.execute(query)
        return db_objs.scalars().unique().all()

    async def get_multi_or_404(
        self,
        async_session: AsyncSession,
        filters: dict[str, Any] | None = None,
        *,
        order_by: tuple[ColumnElement[Any], ...] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        _detail: str | None = None,
    ) -> Sequence[SQLAlchemyModel]:
        """Получает список элементов с простыми условиями или возвращает 404 ошибку.

        Args:
            async_session (AsyncSession): Асинхронная сессия
            filters (dict[str, Any] | None): Словарь для фильтрации
            order_by (tuple[ColumnElement, ...] | None, optional): Кортеж столбцов для
                сортировки
            limit (int | None): Максимальное количество записей
            offset (int | None): Смещение для пагинации
            _detail (str | None): Кастомное сообщение об ошибке

        Returns:
            Sequence[SQLAlchemyModel]: Список найденных объектов (не пустой)

        Raises:
            HTTPException: 404 если объекты не найдены

        Example:
        ```
            # Получить всех админов (ошибка если нет ни одного)
            admins = await crud.get_multi_or_404(session, {"role": "admin"})

            # С кастомной ошибкой
            active_users = await crud.get_multi_or_404(
                session,
                {"is_active": True},
                _detail="Нет активных пользователей",
            )

            # С сортировкой и лимитом
            recent_posts = await crud.get_multi_or_404(
                session,
                {"published": True},
                order_by=(Post.created_at.desc(),),
                limit=5,
            )
        ```
        """
        db_objs = await self.get_multi(
            async_session, filters, order_by=order_by, limit=limit, offset=offset
        )

        if not db_objs:
            if _detail:
                error_detail = _detail
            else:
                if filters:
                    filter_parts = [f'{k}={v}' for k, v in filters.items()]
                    filter_str = ', '.join(filter_parts)
                    error_detail = f'No {self.model.__name__} found with {filter_str}'
                else:
                    error_detail = f'No {self.model.__name__} found'

            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=error_detail,
            )

        return db_objs

    async def get_multi_by_condition(
        self,
        async_session: AsyncSession,
        *conditions: ColumnElement[bool],
        order_by: tuple[ColumnElement[Any], ...] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> Sequence[SQLAlchemyModel]:
        """Получает список элементов по сложным условиям.

        Args:
            async_session: Асинхронная сессия
            *conditions: Условия для фильтрации
            order_by: Кортеж столбцов для сортировки
            limit: Максимальное количество записей
            offset: Смещение для пагинации

        Returns:
            Sequence[SQLAlchemyModel]: Список найденных объектов

        Example:
        ```
            # OR условие
            users = await crud.get_multi_by_condition(
                session,
                or_(User.role == "admin", User.role == "moderator")
            )

            # Сложные условия с сортировкой
            users = await crud.get_multi_by_condition(
                session,
                User.age >= 18,
                User.is_active == True,
                or_(User.role == "admin", User.role == "moderator"),
                order_by=(User.created_at.desc(),)
            )

            # С пагинацией
            users = await crud.get_multi_by_condition(
                session,
                User.is_active == True,
                User.age.between(18, 65),
                order_by=(User.username.asc(),),
                limit=20,
                offset=0
            )

            # Поиск по подстроке
            users = await crud.get_multi_by_condition(
                session,
                User.email.ilike("%@gmail.com"),
                User.is_active == True
            )
        ```
        """
        if not conditions:
            raise ValueError('Необходимо указать хотя бы одно условие')

        query = select(self.model)

        if conditions:
            query = query.filter(*conditions)

        if order_by:
            query = query.order_by(*order_by)

        if offset is not None:
            query = query.offset(offset)

        if limit is not None:
            query = query.limit(limit)

        result = await async_session.execute(query)
        return result.scalars().unique().all()

    async def get_multi_by_condition_or_404(
        self,
        async_session: AsyncSession,
        *conditions: ColumnElement[bool],
        order_by: tuple[ColumnElement[Any], ...] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        _detail: str | None = None,
    ) -> Sequence[SQLAlchemyModel]:
        """Получает список элементов по сложным условиям или возвращает 404 ошибку.

        Args:
            async_session: Асинхронная сессия
            *conditions: Условия для фильтрации
            order_by: Кортеж столбцов для сортировки
            limit: Максимальное количество записей
            offset: Смещение для пагинации
            _detail: Кастомное сообщение об ошибке

        Returns:
            Sequence[SQLAlchemyModel]: Список найденных объектов (не пустой)

        Raises:
            HTTPException: 404 если объекты не найдены

        Example:
        ```
            # OR условие (ошибка если никого не найдено)
            moderators = await crud.get_multi_by_condition_or_404(
                session,
                or_(User.role == "admin", User.role == "moderator")
            )

            # Сложные условия с кастомной ошибкой
            adult_users = await crud.get_multi_by_condition_or_404(
                session,
                User.age >= 18,
                User.is_active == True,
                User.email.ilike("%@gmail.com"),
                _detail="Нет взрослых пользователей с Gmail",
                order_by=(User.username.asc(),)
            )

            # Поиск с пагинацией (ошибка если страница пустая)
            search_results = await crud.get_multi_by_condition_or_404(
                session,
                User.username.ilike(f"%{search_term}%"),
                User.is_active == True,
                order_by=(User.created_at.desc(),),
                limit=10,
                offset=page_offset,
                _detail=f"Пользователи с '{search_term}' не найдены"
            )
        ```
        """
        db_objs = await self.get_multi_by_condition(
            async_session, *conditions, order_by=order_by, limit=limit, offset=offset
        )

        if not db_objs:
            error_detail = (
                _detail or f'No {self.model.__name__} found matching conditions'
            )
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=error_detail,
            )

        return db_objs

    async def count(
        self,
        async_session: AsyncSession,
        filters: dict[str, Any] | None = None,
    ) -> int:
        """Подсчитывает количество записей с простыми условиями.

        Args:
            async_session: Асинхронная сессия
            filters (dict[str, Any] | None): Словарь для фильтрации

        Returns:
            int: Количество записей

        Example:
        ```
            # Общее количество
            total = await crud.count(session)

            # С фильтрацией
            active_count = await crud.count(session, {"is_active": True})
            admin_count = await crud.count(
                session, {"role": "admin", "is_active": True}
            )
        ```
        """
        query = select(func.count(self.model.id)).filter_by(**(filters or {}))
        result = await async_session.execute(query)
        return result.scalar() or 0

    async def count_by_condition(
        self,
        async_session: AsyncSession,
        *conditions: ColumnElement[bool],
    ) -> int:
        """Подсчитывает количество записей по сложным условиям.

        Args:
            async_session: Асинхронная сессия
            *conditions: Условия для фильтрации

        Returns:
            int: Количество записей

        Example:
        ```
            # OR условие
            count = await crud.count_by_condition(
                session,
                or_(User.role == "admin", User.role == "moderator")
            )

            # Сложные условия
            count = await crud.count_by_condition(
                session,
                User.age >= 18,
                User.is_active == True,
                User.email.ilike("%@gmail.com")
            )
        ```
        """
        query = select(func.count(self.model.id))

        if conditions:
            query = query.filter(*conditions)

        result = await async_session.execute(query)
        return result.scalar() or 0

    async def exists(
        self,
        async_session: AsyncSession,
        filters: dict[str, Any],
    ) -> bool:
        """Проверяет существование записи с простыми условиями.

        Args:
            async_session: Асинхронная сессия
            filters (dict[str, Any]): Словарь для фильтрации

        Returns:
            bool: True если запись существует

        Example:
        ```
            # Проверка существования
            exists = await crud.exists(session, {"email": "test@test.com"})
            exists = await crud.exists(
                session, {"username": "admin", "is_active": True}
            )
        ```
        """
        if not filters:
            raise ValueError('Необходимо указать хотя бы одно поле для поиска')

        query = select(sql_exists(select(self.model.id).filter_by(**filters)))
        result = await async_session.execute(query)
        return result.scalar() or False

    async def exists_or_404(
        self,
        async_session: AsyncSession,
        filters: dict[str, Any],
        *,
        _detail: str | None = None,
    ) -> bool:
        """Проверяет существование записи по простым условиям или возвращает 404.

        Args:
            async_session: Асинхронная сессия
            filters (dict[str, Any]): Словарь для фильтрации
            _detail: Кастомное сообщение об ошибке

        Returns:
            bool: True если запись существует

        Raises:
            HTTPException: 404 если запись не найдена
        """
        exists_result = await self.exists(async_session, filters)

        if not exists_result:
            if _detail:
                error_detail = _detail
            else:
                filter_parts = [f'{k}={v}' for k, v in filters.items()]
                filter_str = ', '.join(filter_parts)
                error_detail = f'{self.model.__name__} with {filter_str} not found'

            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=error_detail,
            )

        return True

    async def exists_by_condition(
        self,
        async_session: AsyncSession,
        *conditions: ColumnElement[bool],
    ) -> bool:
        """Проверяет существование записи по сложным условиям.

        Args:
            async_session: Асинхронная сессия
            *conditions: Условия для фильтрации

        Returns:
            bool: True если запись существует

        Example:
        ```
            # OR условие
            exists = await crud.exists_by_condition(
                session,
                or_(User.email == "test@test.com", User.username == "test")
            )

            # Сложные условия
            exists = await crud.exists_by_condition(
                session,
                User.age >= 18,
                User.is_active == True
            )
        ```
        """
        subquery = select(self.model.id)
        if conditions:
            subquery = subquery.filter(*conditions)

        query = select(sql_exists(subquery))
        result = await async_session.execute(query)
        return result.scalar() or False

    async def exists_by_condition_or_404(
        self,
        async_session: AsyncSession,
        *conditions: ColumnElement[bool],
        _detail: str | None = None,
    ) -> bool:
        """Проверяет существование записи по сложным условиям или возвращает 404.

        Args:
            async_session: Асинхронная сессия
            *conditions: SQLAlchemy условия
            _detail: Кастомное сообщение об ошибке

        Returns:
            bool: True если запись существует

        Raises:
            HTTPException: 404 если запись не найдена
        """
        exists_result = await self.exists_by_condition(async_session, *conditions)

        if not exists_result:
            if _detail:
                error_detail = _detail
            else:
                error_detail = f'No {self.model.__name__} found matching conditions'

            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=error_detail,
            )

        return True

    async def not_exists_or_409(
        self,
        async_session: AsyncSession,
        filters: dict[str, Any],
        *,
        _detail: str | None = None,
    ) -> bool:
        """Проверяет отсутствие записи по простым условиям или возвращает 409 Conflict.

        Args:
            async_session: Асинхронная сессия
            filters (dict[str, Any]): Словарь для фильтрации
            _detail: Кастомное сообщение об ошибке

        Returns:
            bool: True если запись не существует

        Raises:
            HTTPException: 409 если запись уже существует

        Example:
        ```
            # Проверка что email свободен перед регистрацией
            await crud.not_exists_or_409(session, {"email": "test@test.com"})

            # С кастомной ошибкой
            await crud.not_exists_or_409(
                session,
                {"email": "test@test.com"},
                _detail="Пользователь с таким email уже зарегистрирован",
            )

            # Проверка нескольких полей
            await crud.not_exists_or_409(
                session,
                {"username": "admin", "email": "admin@test.com"},
            )
        ```
        """
        exists_result = await self.exists(async_session, filters)

        if exists_result:
            if _detail:
                error_detail = _detail
            else:
                filter_parts = [f'{k}={v}' for k, v in filters.items()]
                filter_str = ', '.join(filter_parts)
                error_detail = f'{self.model.__name__} with {filter_str} already exists'

            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail=error_detail,
            )

        return True

    async def not_exists_by_condition_or_409(
        self,
        async_session: AsyncSession,
        *conditions: ColumnElement[bool],
        _detail: str | None = None,
    ) -> bool:
        """Проверяет отсутствие записи по сложным условиям или возвращает 409 Conflict.

        Args:
            async_session: Асинхронная сессия
            *conditions: SQLAlchemy условия
            _detail: Кастомное сообщение об ошибке

        Returns:
            bool: True если запись не существует

        Raises:
            HTTPException: 409 если запись уже существует

        Example:
        ```
            from sqlalchemy import or_

            # Проверка что email или username свободны
            await crud.not_exists_by_condition_or_409(
                session,
                or_(User.email == "test@test.com", User.username == "testuser")
            )

            # С кастомной ошибкой
            await crud.not_exists_by_condition_or_409(
                session,
                or_(User.email == email, User.username == username),
                _detail="Пользователь с таким email или username уже существует"
            )
        ```
        """
        exists_result = await self.exists_by_condition(async_session, *conditions)

        if exists_result:
            error_detail = (
                _detail
                or f'{self.model.__name__} matching specified conditions already exists'
            )

            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail=error_detail,
            )

        return True

    async def get_or_create(
        self,
        async_session: AsyncSession,
        filters: dict[str, Any],
        defaults: dict[str, Any] | None = None,
    ) -> tuple[SQLAlchemyModel, bool]:
        """Получает объект или создает его, если не существует.

        Args:
            async_session (AsyncSession): Асинхронная сессия
            filters (dict[str, Any]): Поля для поиска существующего объекта
            defaults (dict[str, Any] | None): Дополнительные поля для создания объекта

        Returns:
            tuple[SQLAlchemyModel, bool]: Кортеж (объект, создан_ли_новый)
                - объект: найденный или созданный объект
                - создан_ли_новый: True если объект был создан, False если найден

        Example:
        ```
            # Простой случай - получить или создать пользователя по email
            user, created = await crud.get_or_create(
                session,
                {"email": "test@example.com"},
            )
            if created:
                print("Создан новый пользователь")
            else:
                print("Пользователь уже существует")

            # С дополнительными полями для создания
            user, created = await crud.get_or_create(
                session,
                {"email": "john@example.com"},
                defaults={
                    "username": "john_doe",
                    "first_name": "John",
                    "last_name": "Doe",
                    "is_active": True,
                },
            )

            # Сложный пример - категория с slug
            category, created = await crud.get_or_create(
                session,
                {"slug": "technology"},
                defaults={
                    "name": "Technology",
                    "description": "Tech articles",
                },
            )

            # Получить или создать настройки пользователя
            settings, created = await crud.get_or_create(
                session,
                {"user_id": user_id},
                defaults={
                    "theme": "dark",
                    "notifications": True,
                    "language": "en",
                },
            )
        ```
        """
        if not filters:
            raise ValueError('Необходимо указать хотя бы одно поле для поиска')

        db_obj = await self.get(async_session, filters)

        if db_obj:
            return db_obj, False

        try:
            create_data = filters.copy()
            if defaults:
                create_data.update(defaults)

            db_obj = self.model(**create_data)
            async_session.add(db_obj)
            await async_session.flush()
            await async_session.refresh(db_obj)

            return db_obj, True

        except Exception as e:
            await async_session.rollback()

            db_obj = await self.get(async_session, filters)
            if db_obj:
                return db_obj, False

            raise e

    async def get_or_create_with_pydantic(
        self,
        async_session: AsyncSession,
        obj_in: PydanticSchema,
        search_fields: list[str],
        user_id: int | None = None,
    ) -> tuple[SQLAlchemyModel, bool]:
        """Получает объект или создает его используя Pydantic модель.

        Args:
            async_session (AsyncSession): Асинхронная сессия
            obj_in (PydanticSchema): Pydantic объект с данными
            search_fields (list[str]): Список полей для поиска существующего объекта
            user_id (int | None): ИД пользователя для привязки (опционально)

        Returns:
            tuple[SQLAlchemyModel, bool]: Кортеж (объект, создан_ли_новый)

        Example:
        ```
            # Создаем Pydantic объект
            user_data = UserCreate(
                username="john_doe",
                email="john@example.com",
                first_name="John",
                last_name="Doe"
            )

            # Ищем по email, если не найден - создаем со всеми данными
            user, created = await crud.get_or_create_with_pydantic(
                session,
                user_data,
                search_fields=["email"]
            )

            # Поиск по нескольким полям
            post_data = PostCreate(
                title="My Post",
                slug="my-post",
                content="Content here",
                category_id=1
            )

            post, created = await crud.get_or_create_with_pydantic(
                session,
                post_data,
                search_fields=["slug", "category_id"],
                user_id=current_user.id
            )
        ```
        """
        if not search_fields:
            raise ValueError('Необходимо указать хотя бы одно поле для поиска')

        obj_data = obj_in.model_dump()

        search_criteria = {}
        for field in search_fields:
            if field in obj_data:
                search_criteria[field] = obj_data[field]
            else:
                raise ValueError(f"Поле '{field}' не найдено в данных объекта")

        db_obj = await self.get(async_session, search_criteria)

        if db_obj:
            return db_obj, False

        try:
            if user_id is not None:
                obj_data['user_id'] = user_id

            db_obj = self.model(**obj_data)
            async_session.add(db_obj)
            await async_session.flush()
            await async_session.refresh(db_obj)

            return db_obj, True

        except Exception as e:
            await async_session.rollback()

            db_obj = await self.get(async_session, search_criteria)
            if db_obj:
                return db_obj, False

            raise e

    async def get_or_create_by_condition(
        self,
        async_session: AsyncSession,
        *conditions: ColumnElement[bool],
        defaults: dict[str, Any] | None = None,
        create_data: dict[str, Any] | None = None,
    ) -> tuple[SQLAlchemyModel, bool]:
        """Получает объект по сложным условиям или создает его, если не существует.

        Args:
            async_session (AsyncSession): Асинхронная сессия
            *conditions: Условия для поиска существующего объекта
            defaults (dict[str, Any] | None): Дополнительные поля только для создания
                объекта
            create_data (dict[str, Any] | None): Обязательные поля для создания объекта
                (используется если объект не найден)

        Returns:
            tuple[SQLAlchemyModel, bool]: Кортеж (объект, создан_ли_новый)
                - объект: найденный или созданный объект
                - создан_ли_новый: True если объект был создан, False если найден

        Raises:
            ValueError: Если не указаны условия или create_data для создания

        Example:
        ```
            from sqlalchemy import and_, or_

            # Найти пользователя по email ИЛИ username, создать если не найден
            user, created = await crud.get_or_create_by_condition(
                session,
                or_(User.email == "john@example.com", User.username == "john_doe"),
                create_data={
                    "email": "john@example.com",
                    "username": "john_doe",
                    "first_name": "John"
                },
                defaults={
                    "is_active": True,
                    "created_at": datetime.now()
                }
            )

            # Найти настройки пользователя по сложным условиям
            settings, created = await crud.get_or_create_by_condition(
                session,
                and_(
                    UserSettings.user_id == user_id,
                    UserSettings.app_version >= "2.0"
                ),
                create_data={
                    "user_id": user_id,
                    "app_version": "2.1"
                },
                defaults={
                    "theme": "dark",
                    "notifications": True
                }
            )

            # Создать уникальную сессию пользователя
            session_obj, created = await crud.get_or_create_by_condition(
                session,
                and_(
                    UserSession.user_id == user_id,
                    UserSession.ip_address == ip_address,
                    UserSession.is_active == True
                ),
                create_data={
                    "user_id": user_id,
                    "ip_address": ip_address,
                    "session_token": generate_token()
                }
            )
        ```
        """
        if not conditions:
            raise ValueError('Необходимо указать хотя бы одно условие для поиска')

        db_obj = await self.get_by_condition(async_session, *conditions)

        if db_obj:
            return db_obj, False

        if not create_data:
            raise ValueError(
                'Необходимо указать create_data для создания объекта '
                'когда он не найден по условиям'
            )

        try:
            final_create_data = create_data.copy()
            if defaults:
                for key, value in defaults.items():
                    if key not in final_create_data:
                        final_create_data[key] = value

            db_obj = self.model(**final_create_data)
            async_session.add(db_obj)
            await async_session.flush()
            await async_session.refresh(db_obj)

            return db_obj, True

        except Exception as e:
            await async_session.rollback()

            db_obj = await self.get_by_condition(async_session, *conditions)
            if db_obj:
                return db_obj, False

            raise e

    async def create(
        self,
        async_session: AsyncSession,
        obj_in: PydanticSchema,
        **extra_fields: Any,
    ) -> SQLAlchemyModel:
        """Создает новый объект.

        Args:
            async_session (AsyncSession): Асинхронная сессия
            obj_in (PydanticSchema): Pydantic объект, который будет создан.
            **extra_fields (Any): Дополнительные поля для привязки
                (user_id, owner_id и т.д.)

        Returns:
            SQLAlchemyModel: Созданный объект

        Example:
        ```
            # Простое создание
            user = await crud.create(session, user_data)

            # С дополнительными полями
            document = await crud.create(
                session,
                document_data,
                owner_id=owner.id
            )

            # С несколькими дополнительными полями
            post = await crud.create(
                session,
                post_data,
                user_id=user.id,
                category_id=category.id
            )
        ```
        """
        obj_in_data = obj_in.model_dump()
        obj_in_data.update(extra_fields)
        db_obj = self.model(**obj_in_data)
        async_session.add(db_obj)
        await async_session.flush()
        await async_session.refresh(db_obj)
        return db_obj

    async def bulk_create(
        self,
        async_session: AsyncSession,
        objects_in: list[PydanticSchema],
        **extra_fields: Any,
    ) -> list[SQLAlchemyModel]:
        """Создает несколько объектов за один раз.

        Args:
            async_session (AsyncSession): Асинхронная сессия
            objects_in (list[PydanticSchema]): Список Pydantic объектов для создания
            **extra_fields (Any): Дополнительные поля для привязки
                (user_id, owner_id и т.д.)

        Returns:
            list[SQLAlchemyModel]: Список созданных объектов

        Example:
        ```
            # Массовое создание с общими полями
            certificates = await crud.bulk_create(
                session,
                [cert1_data, cert2_data, cert3_data],
                owner_id=owner.id
            )

            # С несколькими дополнительными полями
            posts = await crud.bulk_create(
                session,
                posts_data,
                user_id=user.id,
                status="draft"
            )
        ```
        """
        db_objects = []
        for obj_in in objects_in:
            obj_in_data = obj_in.model_dump()
            obj_in_data.update(extra_fields)
            db_obj = self.model(**obj_in_data)
            db_objects.append(db_obj)

        async_session.add_all(db_objects)
        await async_session.flush()

        for db_obj in db_objects:
            await async_session.refresh(db_obj)

        return db_objects

    async def update(
        self,
        async_session: AsyncSession,
        db_obj: SQLAlchemyModel,
        obj_in: PydanticSchema,
    ) -> SQLAlchemyModel:
        """Обновляет объект по экземпляру объекта.

        Args:
            async_session (AsyncSession): Асинхронная сессия
            db_obj (SQLAlchemyModel): Объект из БД, который будет обновлен
            obj_in (PydanticSchema): Pydantic объект с данными для обновления

        Returns:
            SQLAlchemyModel: Обновленный объект

        Example:
        ```
            # Получаем объект и обновляем его
            user = await crud.get(session, {"id": 1})
            if user:
                update_data = UserUpdate(username="new_username", email="new@email.com")
                updated_user = await crud.update(session, user, update_data)
        ```
        """
        update_data = obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        async_session.add(db_obj)
        await async_session.flush()
        return db_obj

    async def update_or_404(
        self,
        async_session: AsyncSession,
        obj_in: PydanticSchema,
        filters: dict[str, Any],
    ) -> SQLAlchemyModel:
        """Находит один объект и обновляет его, или возвращает 404 ошибку.

        Args:
            async_session (AsyncSession): Асинхронная сессия
            obj_in (PydanticSchema): Pydantic объект с данными для обновления
            filters (dict[str, Any]): Словарь для поиска объекта

        Returns:
            SQLAlchemyModel: Обновленный объект

        Raises:
            HTTPException: 404 если объект не найден

        Example:
        ```
            # Найти и обновить пользователя
            update_data = UserUpdate(username="new_username", email="new@email.com")
            updated_user = await crud.update_or_404(
                session,
                update_data,
                {"id": 1},
            )

            # Найти и обновить пост по slug
            post_update = PostUpdate(title="New Title", content="New content")
            updated_post = await crud.update_or_404(
                session,
                post_update,
                {"slug": "my-post-slug"},
            )
        ```
        """
        db_obj = await self.get_or_404(async_session, filters)
        return await self.update(async_session, db_obj, obj_in)

    async def update_by_fields(
        self,
        async_session: AsyncSession,
        update_data: dict[str, Any],
        filters: dict[str, Any],
    ) -> int:
        """Обновляет объекты по простым условиям.

        Args:
            async_session (AsyncSession): Асинхронная сессия
            update_data (dict[str, Any]): Словарь с данными для обновления
            filters (dict[str, Any]): Словарь для фильтрации

        Returns:
            int: Количество обновленных объектов

        Example:
        ```
            # Обновить email пользователя
            updated_count = await crud.update_by_fields(
                session,
                {"email": "new@email.com", "is_verified": True},
                {"id": 1},
            )

            # Деактивировать всех пользователей определенной роли
            updated_count = await crud.update_by_fields(
                session,
                {"is_active": False},
                {"role": "guest"},
            )

            # Обновить статус всех постов пользователя
            updated_count = await crud.update_by_fields(
                session,
                {"status": "archived"},
                {"user_id": user_id, "published": False},
            )
        ```
        """
        if not filters:
            raise ValueError('Необходимо указать хотя бы одно поле для фильтрации')

        if not update_data:
            raise ValueError('Необходимо указать данные для обновления')

        stmt = update(self.model).filter_by(**filters).values(**update_data)
        result = await async_session.execute(stmt)
        await async_session.flush()
        return result.rowcount or 0

    async def update_by_fields_or_404(
        self,
        async_session: AsyncSession,
        update_data: dict[str, Any],
        filters: dict[str, Any],
        *,
        _detail: str | None = None,
    ) -> int:
        """Обновляет объекты по простым условиям или возвращает 404 ошибку.

        Args:
            async_session (AsyncSession): Асинхронная сессия
            update_data (dict[str, Any]): Словарь с данными для обновления
            filters (dict[str, Any]): Словарь для фильтрации
            _detail (str | None): Кастомное сообщение об ошибке

        Returns:
            int: Количество обновленных объектов (больше 0)

        Raises:
            HTTPException: 404 если объекты не найдены

        Example:
        ```
            # Обновить пользователя по email (ошибка если не найден)
            updated_count = await crud.update_by_fields_or_404(
                session,
                {"username": "new_username"},
                {"email": "test@example.com"},
            )

            # С кастомной ошибкой
            updated_count = await crud.update_by_fields_or_404(
                session,
                {"status": "completed"},
                {"id": task_id},
                _detail="Задача для обновления не найдена",
            )
        ```
        """
        updated_count = await self.update_by_fields(async_session, update_data, filters)

        if updated_count == 0:
            if _detail:
                error_detail = _detail
            else:
                filter_parts = [f'{k}={v}' for k, v in filters.items()]
                filter_str = ', '.join(filter_parts)
                error_detail = (
                    f'No {self.model.__name__} found to update with {filter_str}'
                )

            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=error_detail,
            )

        return updated_count

    async def update_by_condition(
        self,
        async_session: AsyncSession,
        update_data: dict[str, Any],
        *conditions: ColumnElement[bool],
    ) -> int:
        """Обновляет объекты по сложным условиям.

        Args:
            async_session: Асинхронная сессия
            update_data (dict[str, Any]): Словарь с данными для обновления
            *conditions: Условия для фильтрации

        Returns:
            int: Количество обновленных объектов

        Example:
        ```
            # Обновить всех пользователей старше 18 или с подтвержденным email
            from sqlalchemy import or_

            updated_count = await crud.update_by_condition(
                session,
                {"can_vote": True},
                or_(User.age >= 18, User.email_verified == True)
            )

            # Архивировать старые посты
            from datetime import datetime, timedelta

            updated_count = await crud.update_by_condition(
                session,
                {"status": "archived", "archived_at": datetime.now()},
                Post.created_at < datetime.now() - timedelta(days=365),
                Post.status == "published"
            )

            # Обновить временные файлы
            updated_count = await crud.update_by_condition(
                session,
                {"is_permanent": True, "expires_at": None},
                File.is_temporary == True,
                File.download_count > 10
            )
        ```
        """
        if not conditions:
            raise ValueError('Необходимо указать хотя бы одно условие для обновления')

        if not update_data:
            raise ValueError('Необходимо указать данные для обновления')

        stmt = update(self.model).filter(*conditions).values(**update_data)
        result = await async_session.execute(stmt)
        await async_session.flush()
        return result.rowcount or 0

    async def update_by_condition_or_404(
        self,
        async_session: AsyncSession,
        update_data: dict[str, Any],
        *conditions: ColumnElement[bool],
        _detail: str | None = None,
    ) -> int:
        """Обновляет объекты по сложным условиям или возвращает 404 ошибку.

        Args:
            async_session: Асинхронная сессия
            update_data (dict[str, Any]): Словарь с данными для обновления
            *conditions: Условия для фильтрации
            _detail: Кастомное сообщение об ошибке

        Returns:
            int: Количество обновленных объектов (больше 0)

        Raises:
            HTTPException: 404 если объекты не найдены

        Example:
        ```
            # Обновить активных пользователей (ошибка если таких нет)
            updated_count = await crud.update_by_condition_or_404(
                session,
                {"last_notification_sent": datetime.now()},
                User.is_active == True,
                User.notifications_enabled == True
            )

            # С кастомной ошибкой
            updated_count = await crud.update_by_condition_or_404(
                session,
                {"status": "reviewed"},
                Post.status == "pending",
                Post.created_at < datetime.now() - timedelta(hours=24),
                _detail="Нет постов ожидающих проверку"
            )
        ```
        """
        updated_count = await self.update_by_condition(
            async_session, update_data, *conditions
        )

        if updated_count == 0:
            error_detail = (
                _detail
                or f'No {self.model.__name__} found to update matching conditions'
            )
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=error_detail,
            )

        return updated_count

    async def update_with_pydantic_by_fields(
        self,
        async_session: AsyncSession,
        obj_in: PydanticSchema,
        filters: dict[str, Any],
    ) -> int:
        """Обновляет объекты используя Pydantic модель по простым условиям.

        Args:
            async_session (AsyncSession): Асинхронная сессия
            obj_in (PydanticSchema): Pydantic объект с данными для обновления
            filters (dict[str, Any]): Словарь для фильтрации

        Returns:
            int: Количество обновленных объектов

        Example:
        ```
            # Обновить пользователя используя Pydantic модель
            update_data = UserUpdate(username="new_username", email="new@email.com")
            updated_count = await crud.update_with_pydantic_by_fields(
                session,
                update_data,
                {"id": 1},
            )

            # Обновить настройки всех пользователей
            settings_update = UserSettingsUpdate(theme="dark", notifications=False)
            updated_count = await crud.update_with_pydantic_by_fields(
                session,
                settings_update,
                {"role": "user"},
            )
        ```
        """
        update_data = obj_in.model_dump(exclude_unset=True)
        return await self.update_by_fields(async_session, update_data, filters)

    async def update_with_pydantic_by_fields_or_404(
        self,
        async_session: AsyncSession,
        obj_in: PydanticSchema,
        filters: dict[str, Any],
        *,
        _detail: str | None = None,
    ) -> int:
        """Обновляет объекты используя Pydantic модель по простым условиям или
        возвращает 404.

        Args:
            async_session (AsyncSession): Асинхронная сессия
            obj_in (PydanticSchema): Pydantic объект с данными для обновления
            filters (dict[str, Any]): Словарь для фильтрации
            _detail (str | None): Кастомное сообщение об ошибке

        Returns:
            int: Количество обновленных объектов (больше 0)

        Raises:
            HTTPException: 404 если объекты не найдены

        Example:
        ```
            # Обновить пользователя (ошибка если не найден)
            update_data = UserUpdate(username="new_username")
            updated_count = await crud.update_with_pydantic_by_fields_or_404(
                session,
                update_data,
                {"email": "test@example.com"},
            )
        ```
        """
        update_data = obj_in.model_dump(exclude_unset=True)
        return await self.update_by_fields_or_404(
            async_session, update_data, filters, _detail=_detail
        )

    async def bulk_update_by_ids(
        self,
        async_session: AsyncSession,
        obj_ids: list[int],
        update_data: dict[str, Any],
    ) -> int:
        """Обновляет несколько объектов по списку ID.

        Args:
            async_session (AsyncSession): Асинхронная сессия
            obj_ids (list[int]): Список ID объектов для обновления
            update_data (dict[str, Any]): Словарь с данными для обновления

        Returns:
            int: Количество обновленных объектов

        Example:
        ```
            # Обновить несколько пользователей
            user_ids = [1, 2, 3, 4, 5]
            updated_count = await crud.bulk_update_by_ids(
                session,
                user_ids,
                {"is_active": False, "deactivated_at": datetime.now()}
            )
            print(f"Обновлено {updated_count} пользователей")

            # Обновить выбранные посты
            post_ids = [10, 15, 20]
            updated_count = await crud.bulk_update_by_ids(
                session,
                post_ids,
                {"status": "featured", "featured_at": datetime.now()}
            )
        ```
        """
        if not obj_ids:
            return 0

        if not update_data:
            raise ValueError('Необходимо указать данные для обновления')

        stmt = (
            update(self.model).where(self.model.id.in_(obj_ids)).values(**update_data)
        )
        result = await async_session.execute(stmt)
        await async_session.flush()
        return result.rowcount or 0

    async def bulk_update_by_field_values(
        self,
        async_session: AsyncSession,
        field_name: str,
        field_values: list[Any],
        update_data: dict[str, Any],
    ) -> int:
        """Обновляет объекты по списку значений для определенного поля.

        Args:
            async_session (AsyncSession): Асинхронная сессия
            field_name (str): Имя поля для фильтрации
            field_values (list[Any]): Список значений для обновления
            update_data (dict[str, Any]): Словарь с данными для обновления

        Returns:
            int: Количество обновленных объектов

        Example:
        ```
            # Обновить пользователей по списку email'ов
            emails = ["user1@test.com", "user2@test.com", "user3@test.com"]
            updated_count = await crud.bulk_update_by_field_values(
                session,
                "email",
                emails,
                {"email_verified": True, "verified_at": datetime.now()}
            )

            # Обновить посты по slug'ам
            slugs = ["post-1", "post-2", "important-article"]
            updated_count = await crud.bulk_update_by_field_values(
                session,
                "slug",
                slugs,
                {"is_featured": True}
            )

            # Обновить файлы по именам
            filenames = ["file1.txt", "file2.txt", "document.pdf"]
            updated_count = await crud.bulk_update_by_field_values(
                session,
                "filename",
                filenames,
                {"is_processed": True, "processed_at": datetime.now()}
            )
        ```
        """
        if not field_values:
            return 0

        if not update_data:
            raise ValueError('Необходимо указать данные для обновления')

        if not hasattr(self.model, field_name):
            raise AttributeError(
                f"Поле '{field_name}' не существует в модели {self.model.__name__}"
            )

        field = getattr(self.model, field_name)
        stmt = update(self.model).where(field.in_(field_values)).values(**update_data)
        result = await async_session.execute(stmt)
        await async_session.flush()
        return result.rowcount or 0

    async def bulk_update_all_by_fields(
        self,
        async_session: AsyncSession,
        update_data: dict[str, Any],
        filters: dict[str, Any],
        batch_size: int = 1000,
    ) -> int:
        """Обновляет все объекты по условиям порциями (для больших таблиц).

        Args:
            async_session (AsyncSession): Асинхронная сессия
            update_data (dict[str, Any]): Словарь с данными для обновления
            filters (dict[str, Any]): Словарь для фильтрации
            batch_size (int): Размер порции для обновления

        Returns:
            int: Общее количество обновленных объектов

        Example:
        ```
            # Обновить всех неактивных пользователей порциями
            total_updated = await crud.bulk_update_all_by_fields(
                session,
                {"status": "archived", "archived_at": datetime.now()},
                {"is_active": False},
                batch_size=500,
            )
            print(f"Обновлено {total_updated} неактивных пользователей")

            # Обновить все непрочитанные уведомления
            total_updated = await crud.bulk_update_all_by_fields(
                session,
                {"expires_at": datetime.now() + timedelta(days=30)},
                {"is_read": False, "type": "notification"},
                batch_size=2000,
            )
        ```
        """
        if not filters:
            raise ValueError('Необходимо указать условия для обновления')

        if not update_data:
            raise ValueError('Необходимо указать данные для обновления')

        total_updated = 0
        last_id = 0

        while True:
            ids_query = (
                select(self.model.id)
                .filter_by(**filters)
                .where(self.model.id > last_id)
                .order_by(self.model.id)
                .limit(batch_size)
            )
            ids_result = await async_session.execute(ids_query)
            ids_to_update = [row[0] for row in ids_result.fetchall()]

            if not ids_to_update:
                break

            stmt = (
                update(self.model)
                .where(self.model.id.in_(ids_to_update))
                .values(**update_data)
            )
            result = await async_session.execute(stmt)
            await async_session.flush()

            total_updated += result.rowcount or 0
            last_id = ids_to_update[-1]

            if len(ids_to_update) < batch_size:
                break

        return total_updated

    async def upsert(  # noqa: C901
        self,
        async_session: AsyncSession,
        obj_in: PydanticSchema,
        unique_fields: list[str],
        update_fields: list[str] | None = None,
        user_id: int | None = None,
    ) -> tuple[SQLAlchemyModel, bool]:
        """Создает новый объект или обновляет существующий (UPDATE или INSERT).

        Args:
            async_session (AsyncSession): Асинхронная сессия
            obj_in (PydanticSchema): Pydantic объект с данными
            unique_fields (list[str]): Поля для поиска существующего объекта
            update_fields (list[str] | None): Поля для обновления. Если None -
                обновляет все поля
            user_id (int | None): ИД пользователя для привязки (опционально)

        Returns:
            tuple[SQLAlchemyModel, bool]: Кортеж (объект, создан_ли_новый)
                - объект: найденный/обновленный или созданный объект
                - создан_ли_новый: True если объект был создан, False если обновлен

        Raises:
            ValueError: Если не указаны unique_fields или поле не найдено в данных

        Example:
        ```
            # Простой upsert по email
            user_data = UserUpsert(
                email="john@example.com",
                username="john_doe",
                first_name="John",
                last_name="Doe",
                is_active=True
            )

            user, created = await crud.upsert(
                session,
                user_data,
                unique_fields=["email"]  # Ищем по email
            )
            # Если email существует - обновит все поля
            # Если не существует - создаст нового пользователя

            # Upsert с ограниченным обновлением
            user, created = await crud.upsert(
                session,
                user_data,
                unique_fields=["email"],
                update_fields=["first_name", "last_name"]  # Обновит только имя
            )

            # Upsert по нескольким полям
            settings_data = UserSettingsUpsert(
                user_id=1,
                app_version="2.1",
                theme="dark",
                notifications=True
            )

            settings, created = await crud.upsert(
                session,
                settings_data,
                unique_fields=["user_id", "app_version"]  # Ищем по комбинации
            )

            # Upsert продукта в корзине
            cart_item_data = CartItemUpsert(
                user_id=1,
                product_id=123,
                quantity=2,
                price=99.99
            )

            cart_item, created = await crud.upsert(
                session,
                cart_item_data,
                unique_fields=["user_id", "product_id"],
                update_fields=["quantity", "price"]  # Только количество и цену
            )

            # Upsert статистики (создать или накопить)
            stats_data = UserStatsUpsert(
                user_id=1,
                date=date.today(),
                page_views=5,
                clicks=2
            )

            # Можно реализовать накопление через логику в update_fields
            stats, created = await crud.upsert(
                session,
                stats_data,
                unique_fields=["user_id", "date"]
            )
        ```
        """
        if not unique_fields:
            raise ValueError(
                'Необходимо указать хотя бы одно поле для поиска (unique_fields)'
            )

        obj_data = obj_in.model_dump()

        if user_id is not None:
            obj_data['user_id'] = user_id

        search_criteria = {}
        for field in unique_fields:
            if field in obj_data:
                search_criteria[field] = obj_data[field]
            else:
                raise ValueError(f"Поле '{field}' не найдено в данных объекта")

        existing_obj = await self.get(async_session, search_criteria)

        if existing_obj:
            try:
                if update_fields is not None:
                    update_data = {
                        field: obj_data[field]
                        for field in update_fields
                        if field in obj_data
                    }
                else:
                    update_data = {
                        field: value
                        for field, value in obj_data.items()
                        if field not in unique_fields
                    }

                if update_data:
                    for field, value in update_data.items():
                        if hasattr(existing_obj, field):
                            setattr(existing_obj, field, value)

                    async_session.add(existing_obj)
                    await async_session.flush()

                return existing_obj, False

            except Exception as e:
                await async_session.rollback()
                raise e

        else:
            try:
                db_obj = self.model(**obj_data)
                async_session.add(db_obj)
                await async_session.flush()

                return db_obj, True

            except Exception as e:
                await async_session.rollback()

                existing_obj = await self.get(async_session, search_criteria)
                if existing_obj:
                    return existing_obj, False

                raise e

    async def bulk_upsert(
        self,
        async_session: AsyncSession,
        objects_in: list[PydanticSchema],
        unique_fields: list[str],
        update_fields: list[str] | None = None,
        user_id: int | None = None,
    ) -> tuple[list[SQLAlchemyModel], int, int]:
        """Массовый upsert для списка объектов.

        Args:
            async_session (AsyncSession): Асинхронная сессия
            objects_in (list[PydanticSchema]): Список Pydantic объектов
            unique_fields (list[str]): Поля для поиска существующих объектов
            update_fields (list[str] | None): Поля для обновления
            user_id (int | None): ИД пользователя для привязки

        Returns:
            tuple[list[SQLAlchemyModel], int, int]: Кортеж (объекты, создано, обновлено)

        Example:
        ```
            users_data = [
                UserUpsert(email="user1@example.com", name="User 1"),
                UserUpsert(email="user2@example.com", name="User 2"),
                UserUpsert(email="user3@example.com", name="User 3"),
            ]

            users, created_count, updated_count = await crud.bulk_upsert(
                session,
                users_data,
                unique_fields=["email"]
            )

            print(f"Создано: {created_count}, Обновлено: {updated_count}")
        ```
        """
        if not objects_in:
            return [], 0, 0

        results = []
        created_count = 0
        updated_count = 0

        for obj_in in objects_in:
            obj, created = await self.upsert(
                async_session, obj_in, unique_fields, update_fields, user_id
            )
            results.append(obj)

            if created:
                created_count += 1
            else:
                updated_count += 1

        return results, created_count, updated_count

    async def delete(
        self,
        async_session: AsyncSession,
        db_obj: SQLAlchemyModel,
    ) -> None:
        """Удаляет объект по экземпляру объекта.

        Args:
            async_session (AsyncSession): Асинхронная сессия
            db_obj (SQLAlchemyModel): Объект из БД, который будет удален

        Example:
        ```
            # Получаем объект и удаляем его
            user = await crud.get(session, {"id": 1})
            if user:
                await crud.delete(session, user)
        ```
        """
        await async_session.delete(db_obj)
        await async_session.flush()

    async def delete_by_fields(
        self,
        async_session: AsyncSession,
        filters: dict[str, Any],
    ) -> int:
        """Удаляет объекты по простым условиям.

        Args:
            async_session (AsyncSession): Асинхронная сессия
            filters (dict[str, Any]): Словарь для фильтрации

        Returns:
            int: Количество удаленных объектов

        Example:
        ```
            # Удалить пользователя по email
            deleted_count = await crud.delete_by_fields(
                session,
                {"email": "test@example.com"},
            )

            # Удалить всех неактивных пользователей определенной роли
            deleted_count = await crud.delete_by_fields(
                session,
                {"is_active": False, "role": "guest"},
            )

            # Удалить все посты пользователя
            deleted_count = await crud.delete_by_fields(
                session, {"user_id": user_id}
            )
        ```
        """
        if not filters:
            raise ValueError('Необходимо указать хотя бы одно поле для удаления')

        stmt = delete(self.model).filter_by(**filters)
        result = await async_session.execute(stmt)
        await async_session.flush()
        return result.rowcount or 0

    async def delete_by_fields_or_404(
        self,
        async_session: AsyncSession,
        filters: dict[str, Any],
        *,
        _detail: str | None = None,
    ) -> int:
        """Удаляет объекты по простым условиям или возвращает 404 ошибку.

        Args:
            async_session (AsyncSession): Асинхронная сессия
            filters (dict[str, Any]): Словарь для фильтрации
            _detail (str | None): Кастомное сообщение об ошибке

        Returns:
            int: Количество удаленных объектов (больше 0)

        Raises:
            HTTPException: 404 если объекты не найдены

        Example:
        ```
            # Удалить пользователя по email (ошибка если не найден)
            deleted_count = await crud.delete_by_fields_or_404(
                session,
                {"email": "test@example.com"},
            )

            # С кастомной ошибкой
            deleted_count = await crud.delete_by_fields_or_404(
                session,
                {"email": "test@example.com"},
                _detail="Пользователь для удаления не найден",
            )
        ```
        """
        deleted_count = await self.delete_by_fields(async_session, filters)

        if deleted_count == 0:
            if _detail:
                error_detail = _detail
            else:
                filter_parts = [f'{k}={v}' for k, v in filters.items()]
                filter_str = ', '.join(filter_parts)
                error_detail = (
                    f'No {self.model.__name__} found to delete with {filter_str}'
                )

            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=error_detail,
            )

        return deleted_count

    async def delete_by_condition(
        self,
        async_session: AsyncSession,
        *conditions: ColumnElement[bool],
    ) -> int:
        """Удаляет объекты по сложным условиям.

        Args:
            async_session: Асинхронная сессия
            *conditions: Условия для фильтрации

        Returns:
            int: Количество удаленных объектов

        Example:
        ```
            # Удалить пользователей старше 65 или неактивных
            from sqlalchemy import or_

            deleted_count = await crud.delete_by_condition(
                session,
                or_(User.age > 65, User.is_active == False)
            )

            # Удалить старые посты
            from datetime import datetime, timedelta

            deleted_count = await crud.delete_by_condition(
                session,
                Post.created_at < datetime.now() - timedelta(days=365),
                Post.published == False
            )

            # Удалить временные файлы
            deleted_count = await crud.delete_by_condition(
                session,
                File.is_temporary == True,
                File.created_at < datetime.now() - timedelta(hours=1)
            )
        ```
        """
        if not conditions:
            raise ValueError('Необходимо указать хотя бы одно условие для удаления')

        stmt = delete(self.model).filter(*conditions)
        result = await async_session.execute(stmt)
        await async_session.flush()
        return result.rowcount or 0

    async def delete_by_condition_or_404(
        self,
        async_session: AsyncSession,
        *conditions: ColumnElement[bool],
        _detail: str | None = None,
    ) -> int:
        """Удаляет объекты по сложным условиям или возвращает 404 ошибку.

        Args:
            async_session: Асинхронная сессия
            *conditions: Условия для фильтрации
            _detail: Кастомное сообщение об ошибке

        Returns:
            int: Количество удаленных объектов (больше 0)

        Raises:
            HTTPException: 404 если объекты не найдены

        Example:
        ```
            # Удалить неактивных пользователей (ошибка если таких нет)
            deleted_count = await crud.delete_by_condition_or_404(
                session,
                User.is_active == False,
                User.last_login < datetime.now() - timedelta(days=30)
            )

            # С кастомной ошибкой
            deleted_count = await crud.delete_by_condition_or_404(
                session,
                Post.status == "draft",
                Post.created_at < datetime.now() - timedelta(days=7),
                _detail="Нет черновиков для удаления"
            )
        ```
        """
        deleted_count = await self.delete_by_condition(async_session, *conditions)

        if deleted_count == 0:
            error_detail = (
                _detail
                or f'No {self.model.__name__} found to delete matching conditions'
            )
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=error_detail,
            )

        return deleted_count

    async def bulk_delete_by_ids(
        self,
        async_session: AsyncSession,
        obj_ids: list[int],
    ) -> int:
        """Удаляет несколько объектов по списку ID.

        Args:
            async_session (AsyncSession): Асинхронная сессия
            obj_ids (list[int]): Список ID объектов для удаления

        Returns:
            int: Количество удаленных объектов

        Example:
        ```
            # Удалить несколько пользователей
            user_ids = [1, 2, 3, 4, 5]
            deleted_count = await crud.bulk_delete_by_ids(session, user_ids)
            print(f"Удалено {deleted_count} пользователей")

            # Удалить выбранные посты
            post_ids = [10, 15, 20]
            deleted_count = await crud.bulk_delete_by_ids(session, post_ids)
        ```
        """
        if not obj_ids:
            return 0

        stmt = delete(self.model).where(self.model.id.in_(obj_ids))
        result = await async_session.execute(stmt)
        await async_session.flush()
        return result.rowcount or 0

    async def bulk_delete_by_field_values(
        self,
        async_session: AsyncSession,
        field_name: str,
        field_values: list[Any],
    ) -> int:
        """Удаляет объекты по списку значений для определенного поля.

        Args:
            async_session (AsyncSession): Асинхронная сессия
            field_name (str): Имя поля для фильтрации
            field_values (list[Any]): Список значений для удаления

        Returns:
            int: Количество удаленных объектов

        Example:
        ```
            # Удалить пользователей по списку email'ов
            emails = ["user1@test.com", "user2@test.com", "user3@test.com"]
            deleted_count = await crud.bulk_delete_by_field_values(
                session,
                "email",
                emails
            )

            # Удалить посты по slug'ам
            slugs = ["old-post-1", "old-post-2", "outdated-article"]
            deleted_count = await crud.bulk_delete_by_field_values(
                session,
                "slug",
                slugs
            )

            # Удалить файлы по именам
            filenames = ["temp1.txt", "temp2.txt", "cache.dat"]
            deleted_count = await crud.bulk_delete_by_field_values(
                session,
                "filename",
                filenames
            )
        ```
        """
        if not field_values:
            return 0

        if not hasattr(self.model, field_name):
            raise AttributeError(
                f"Поле '{field_name}' не существует в модели {self.model.__name__}"
            )

        field = getattr(self.model, field_name)
        stmt = delete(self.model).where(field.in_(field_values))
        result = await async_session.execute(stmt)
        await async_session.flush()
        return result.rowcount or 0

    async def bulk_delete_all_by_fields(
        self,
        async_session: AsyncSession,
        filters: dict[str, Any],
        batch_size: int = 1000,
    ) -> int:
        """Удаляет все объекты по условиям порциями (для больших таблиц).

        Args:
            async_session (AsyncSession): Асинхронная сессия
            filters (dict[str, Any]): Словарь для фильтрации
            batch_size (int): Размер порции для удаления

        Returns:
            int: Общее количество удаленных объектов

        Example:
        ```
            # Удалить всех неактивных пользователей порциями
            total_deleted = await crud.bulk_delete_all_by_fields(
                session,
                {"is_active": False},
                batch_size=500,
            )
            print(f"Удалено {total_deleted} неактивных пользователей")

            # Удалить все старые логи порциями
            total_deleted = await crud.bulk_delete_all_by_fields(
                session,
                {"log_type": "debug"},
                batch_size=1000,
            )
        ```
        """
        if not filters:
            raise ValueError('Необходимо указать условия для удаления')

        total_deleted = 0

        while True:
            ids_query = select(self.model.id).filter_by(**filters).limit(batch_size)
            ids_result = await async_session.execute(ids_query)
            ids_to_delete = [row[0] for row in ids_result.fetchall()]

            if not ids_to_delete:
                break

            stmt = delete(self.model).where(self.model.id.in_(ids_to_delete))
            result = await async_session.execute(stmt)
            await async_session.flush()

            deleted_in_batch = result.rowcount or 0
            total_deleted += deleted_in_batch

            if len(ids_to_delete) < batch_size:
                break

        return total_deleted

    async def bulk_delete_all_by_condition(
        self,
        async_session: AsyncSession,
        *conditions: ColumnElement[bool],
        batch_size: int = 1000,
    ) -> int:
        """Удаляет все объекты по сложным условиям порциями.

        Args:
            async_session: Асинхронная сессия
            *conditions: Условия для фильтрации
            batch_size: Размер порции для удаления

        Returns:
            int: Общее количество удаленных объектов

        Example:
        ```
            # Удалить старые записи порциями
            from datetime import datetime, timedelta

            total_deleted = await crud.bulk_delete_all_by_condition(
                session,
                Log.created_at < datetime.now() - timedelta(days=30),
                Log.level == "DEBUG",
                batch_size=2000
            )

            # Удалить неактивных пользователей с дополнительными условиями
            total_deleted = await crud.bulk_delete_all_by_condition(
                session,
                User.is_active == False,
                User.last_login < datetime.now() - timedelta(days=90),
                or_(User.email.ilike("%temp%"), User.username.ilike("%test%")),
                batch_size=500
            )
        ```
        """
        if not conditions:
            raise ValueError('Необходимо указать условия для удаления')

        total_deleted = 0

        while True:
            ids_query = select(self.model.id).filter(*conditions).limit(batch_size)
            ids_result = await async_session.execute(ids_query)
            ids_to_delete = [row[0] for row in ids_result.fetchall()]

            if not ids_to_delete:
                break

            stmt = delete(self.model).where(self.model.id.in_(ids_to_delete))
            result = await async_session.execute(stmt)
            await async_session.flush()

            deleted_in_batch = result.rowcount or 0
            total_deleted += deleted_in_batch

            if len(ids_to_delete) < batch_size:
                break

        return total_deleted

    def _assert_field_exists(self, field_name: str) -> None:
        """Проверяет, что поле есть в модели. Иначе — AttributeError."""
        if not hasattr(self.model, field_name):
            raise AttributeError(
                f"Поле '{field_name}' не существует в модели {self.model.__name__}"
            )

    def _build_soft_delete_data(
        self,
        delete_field: str,
        delete_value: Any,
        deleted_at_field: str | None,
        deleted_by_field: str | None,
        user_id: int | None,
    ) -> dict[str, Any]:
        """Собирает словарь полей для отметки объекта удалённым."""
        self._assert_field_exists(delete_field)
        update_data: dict[str, Any] = {delete_field: delete_value}

        if deleted_at_field:
            self._assert_field_exists(deleted_at_field)
            update_data[deleted_at_field] = datetime.now()

        if deleted_by_field and user_id:
            self._assert_field_exists(deleted_by_field)
            update_data[deleted_by_field] = user_id

        return update_data

    async def soft_delete(
        self,
        async_session: AsyncSession,
        db_obj: SQLAlchemyModel,
        *,
        delete_field: str = 'is_deleted',
        delete_value: Any = True,
        deleted_at_field: str | None = 'deleted_at',
        deleted_by_field: str | None = None,
        user_id: int | None = None,
    ) -> SQLAlchemyModel:
        """Мягкое удаление объекта (устанавливает флаг вместо физического удаления).

        Args:
            async_session (AsyncSession): Асинхронная сессия
            db_obj (SQLAlchemyModel): Объект для мягкого удаления
            delete_field (str): Поле для отметки удаления. По умолчанию 'is_deleted'
            delete_value (Any): Значение для поля удаления. По умолчанию True
            deleted_at_field (str | None): Поле для времени удаления.
                По умолчанию 'deleted_at'
            deleted_by_field (str | None): Поле для пользователя удалившего.
                По умолчанию None
            user_id (int | None): ID пользователя, совершившего удаление

        Returns:
            SQLAlchemyModel: Мягко удаленный объект

        Raises:
            AttributeError: Если указанное поле не существует в модели

        Example:
        ```
            # Простое мягкое удаление
            user = await crud.get(session, {'id': 1})
            deleted_user = await crud.soft_delete(session, user)
            # Устанавливает is_deleted=True, deleted_at=now()

            # С кастомными полями
            post = await crud.get(session, {'id': 1})
            deleted_post = await crud.soft_delete(
                session,
                post,
                delete_field='status',
                delete_value='deleted',
                deleted_at_field='deleted_timestamp',
                deleted_by_field='deleted_by_user_id',
                user_id=current_user.id,
            )

            # Только флаг без времени
            comment = await crud.get(session, {'id': 1})
            deleted_comment = await crud.soft_delete(
                session,
                comment,
                deleted_at_field=None,  # Не устанавливать время
            )
        ```
        """
        update_data = self._build_soft_delete_data(
            delete_field,
            delete_value,
            deleted_at_field,
            deleted_by_field,
            user_id,
        )

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        async_session.add(db_obj)
        await async_session.flush()
        await async_session.refresh(db_obj)
        return db_obj

    async def soft_delete_by_fields(
        self,
        async_session: AsyncSession,
        filters: dict[str, Any],
        *,
        delete_field: str = 'is_deleted',
        delete_value: Any = True,
        deleted_at_field: str | None = 'deleted_at',
        deleted_by_field: str | None = None,
        user_id: int | None = None,
    ) -> int:
        """Мягкое удаление объектов по простым условиям.

        Args:
            async_session (AsyncSession): Асинхронная сессия
            filters (dict[str, Any]): Словарь для фильтрации в формате
                {"поле": значение}
            delete_field (str): Поле для отметки удаления
            delete_value (Any): Значение для поля удаления
            deleted_at_field (str | None): Поле для времени удаления
            deleted_by_field (str | None): Поле для пользователя удалившего
            user_id (int | None): ID пользователя, совершившего удаление

        Returns:
            int: Количество мягко удаленных объектов

        Raises:
            ValueError: Если не указаны фильтры
            AttributeError: Если указанное поле не существует в модели

        Example:
        ```
            # Мягко удалить всех неактивных пользователей
            deleted_count = await crud.soft_delete_by_fields(
                session,
                {'is_active': False},
                user_id=admin_user.id,
            )

            # С кастомными полями
            deleted_count = await crud.soft_delete_by_fields(
                session,
                {'category': 'old'},
                delete_field='status',
                delete_value='archived',
                deleted_at_field='archived_at',
            )
        ```
        """
        if not filters:
            raise ValueError('Необходимо указать хотя бы одно поле для фильтрации')

        update_data = self._build_soft_delete_data(
            delete_field,
            delete_value,
            deleted_at_field,
            deleted_by_field,
            user_id,
        )
        return await self.update_by_fields(async_session, update_data, filters)

    async def soft_delete_by_condition(
        self,
        async_session: AsyncSession,
        *conditions: ColumnElement[bool],
        delete_field: str = 'is_deleted',
        delete_value: Any = True,
        deleted_at_field: str | None = 'deleted_at',
        deleted_by_field: str | None = None,
        user_id: int | None = None,
    ) -> int:
        """Мягкое удаление объектов по сложным условиям.

        Args:
            async_session: Асинхронная сессия
            *conditions: Условия для фильтрации
            delete_field (str): Поле для отметки удаления
            delete_value (Any): Значение для поля удаления
            deleted_at_field (str | None): Поле для времени удаления
            deleted_by_field (str | None): Поле для пользователя удалившего
            user_id (int | None): ID пользователя, совершившего удаление

        Returns:
            int: Количество мягко удаленных объектов

        Raises:
            ValueError: Если не указаны условия
            AttributeError: Если указанное поле не существует в модели

        Example:
        ```
            from datetime import datetime, timedelta

            from sqlalchemy import and_, or_

            # Мягко удалить старые неактивные посты
            deleted_count = await crud.soft_delete_by_condition(
                session,
                and_(
                    Post.is_active == False,
                    Post.created_at < datetime.now() - timedelta(days=30),
                ),
                user_id=admin_user.id,
            )

            # Архивировать посты определенных категорий
            deleted_count = await crud.soft_delete_by_condition(
                session,
                or_(Post.category == 'temp', Post.category == 'draft'),
                delete_field='status',
                delete_value='archived',
            )
        ```
        """
        if not conditions:
            raise ValueError('Необходимо указать хотя бы одно условие для удаления')

        update_data = self._build_soft_delete_data(
            delete_field,
            delete_value,
            deleted_at_field,
            deleted_by_field,
            user_id,
        )
        return await self.update_by_condition(async_session, update_data, *conditions)

    async def restore(
        self,
        async_session: AsyncSession,
        db_obj: SQLAlchemyModel,
        *,
        delete_field: str = 'is_deleted',
        restore_value: Any = False,
        deleted_at_field: str | None = 'deleted_at',
        deleted_by_field: str | None = None,
    ) -> SQLAlchemyModel:
        """Восстанавливает мягко удаленный объект.

        Args:
            async_session (AsyncSession): Асинхронная сессия
            db_obj (SQLAlchemyModel): Объект для восстановления
            delete_field (str): Поле удаления для сброса
            restore_value (Any): Значение для восстановления. По умолчанию False
            deleted_at_field (str | None): Поле времени удаления для сброса
            deleted_by_field (str | None): Поле пользователя удалившего для сброса

        Returns:
            SQLAlchemyModel: Восстановленный объект

        Raises:
            AttributeError: Если поле удаления не существует в модели

        Example:
        ```
            # Найти мягко удаленного пользователя и восстановить
            deleted_user = await crud.get_with_deleted(
                session, {'id': 1, 'is_deleted': True}
            )
            if deleted_user:
                restored_user = await crud.restore(session, deleted_user)
                # Устанавливает is_deleted=False, deleted_at=None
        ```
        """
        self._assert_field_exists(delete_field)
        setattr(db_obj, delete_field, restore_value)

        if deleted_at_field and hasattr(db_obj, deleted_at_field):
            setattr(db_obj, deleted_at_field, None)

        if deleted_by_field and hasattr(db_obj, deleted_by_field):
            setattr(db_obj, deleted_by_field, None)

        async_session.add(db_obj)
        await async_session.flush()
        await async_session.refresh(db_obj)
        return db_obj

    async def get_with_deleted(
        self,
        async_session: AsyncSession,
        filters: dict[str, Any],
    ) -> SQLAlchemyModel | None:
        """Получает объект включая мягко удаленные.

        В отличие от `get()`, не подразумевает никакой фильтрации по флагу удаления —
        ищет строго по переданным полям.

        Args:
            async_session (AsyncSession): Асинхронная сессия
            filters (dict[str, Any]): Словарь для фильтрации в формате
                {"поле": значение}

        Returns:
            SQLAlchemyModel | None: Найденный объект или None

        Raises:
            ValueError: Если не указаны фильтры

        Example:
        ```
            # Найти пользователя даже если он мягко удален
            user = await crud.get_with_deleted(session, {'id': 1})

            # Найти именно удаленного пользователя
            deleted_user = await crud.get_with_deleted(
                session, {'id': 1, 'is_deleted': True}
            )
        ```
        """
        if not filters:
            raise ValueError('Необходимо указать хотя бы одно поле для поиска')

        query = select(self.model).filter_by(**filters)
        result = await async_session.execute(query)
        return result.scalars().first()
