from http import HTTPStatus

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud._base import CRUDBase
from tests.utils.crud.base import (
    ModelForBaseCRUD,
    ModelForBaseCRUDCreateSchema,
    ModelForBaseCRUDUpdateSchema,
)


class TestCRUDGet:
    """Тесты для метода get."""

    async def test_get_by_id_success(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест успешного получения объекта по ID."""
        test_obj = created_objects[0]
        result = await crud.get(async_session, {'id': test_obj.id})

        assert result is not None
        assert result.id == test_obj.id
        assert result.name == test_obj.name
        assert result.email == test_obj.email

    async def test_get_by_single_field_success(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест успешного получения объекта по одному полю."""
        test_obj = created_objects[0]
        result = await crud.get(async_session, {'email': test_obj.email})

        assert result is not None
        assert result.email == test_obj.email

    async def test_get_by_multiple_fields_success(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест получения объекта по нескольким полям."""
        test_obj = created_objects[0]
        result = await crud.get(
            async_session,
            {'email': test_obj.email, 'is_active': test_obj.is_active},
        )

        assert result is not None
        assert result.email == test_obj.email
        assert result.is_active == test_obj.is_active

    async def test_get_not_found(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест получения несуществующего объекта возвращает None."""
        result = await crud.get(async_session, {'id': 999})
        assert result is None

    async def test_get_without_filters_raises_error(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест что метод get требует хотя бы один фильтр."""
        with pytest.raises(
            ValueError, match='Необходимо указать хотя бы одно поле для поиска'
        ):
            await crud.get(async_session, {})


class TestCRUDGetOr404:
    """Тесты для метода get_or_404."""

    async def test_get_or_404_success(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест успешного получения объекта через get_or_404."""
        test_obj = created_objects[0]
        result = await crud.get_or_404(async_session, {'id': test_obj.id})

        assert result.id == test_obj.id
        assert result.name == test_obj.name

    async def test_get_or_404_not_found_raises_404(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест 404 ошибки при получении несуществующего объекта."""
        with pytest.raises(HTTPException) as exc_info:
            await crud.get_or_404(async_session, {'id': 999})

        assert exc_info.value.status_code == HTTPStatus.NOT_FOUND
        assert 'ModelForBaseCRUD with id=999 not found' in exc_info.value.detail

    async def test_get_or_404_custom_detail_message(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест кастомного сообщения об ошибке."""
        custom_detail = 'Пользователь не найден'

        with pytest.raises(HTTPException) as exc_info:
            await crud.get_or_404(
                async_session,
                {'id': 999},
                _detail=custom_detail,
            )

        assert exc_info.value.status_code == HTTPStatus.NOT_FOUND
        assert exc_info.value.detail == custom_detail


class TestCRUDGetByCondition:
    """Тесты для метода get_by_condition."""

    async def test_get_by_condition_success(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест получения объекта по сложным условиям."""
        from sqlalchemy import or_

        result = await crud.get_by_condition(
            async_session,
            or_(
                ModelForBaseCRUD.email == 'test1@example.com',
                ModelForBaseCRUD.email == 'test2@example.com',
            ),
        )

        assert result is not None
        assert result.email in ['test1@example.com', 'test2@example.com']

    async def test_get_by_condition_not_found(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест получения несуществующего объекта по условиям возвращает None."""
        from sqlalchemy import and_

        result = await crud.get_by_condition(
            async_session,
            and_(
                ModelForBaseCRUD.email == 'nonexistent@example.com',
                ModelForBaseCRUD.is_active.is_(True),
            ),
        )

        assert result is None

    async def test_get_by_condition_without_conditions_raises_error(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест что метод требует хотя бы одно условие."""
        with pytest.raises(ValueError, match='Необходимо указать хотя бы одно условие'):
            await crud.get_by_condition(async_session)


class TestCRUDGetByConditionOr404:
    """Тесты для метода get_by_condition_or_404."""

    async def test_get_by_condition_or_404_success(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест успешного получения объекта через get_by_condition_or_404."""
        from sqlalchemy import or_

        result = await crud.get_by_condition_or_404(
            async_session,
            or_(
                ModelForBaseCRUD.email == 'test1@example.com',
                ModelForBaseCRUD.email == 'test2@example.com',
            ),
        )

        assert result is not None
        assert result.email in ['test1@example.com', 'test2@example.com']

    async def test_get_by_condition_or_404_not_found_raises_404(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест 404 ошибки при получении несуществующего объекта."""
        from sqlalchemy import and_

        with pytest.raises(HTTPException) as exc_info:
            await crud.get_by_condition_or_404(
                async_session,
                and_(
                    ModelForBaseCRUD.email == 'nonexistent@example.com',
                    ModelForBaseCRUD.is_active.is_(True),
                ),
            )

        assert exc_info.value.status_code == HTTPStatus.NOT_FOUND
        assert 'ModelForBaseCRUD not found' in exc_info.value.detail

    async def test_get_by_condition_or_404_custom_detail(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест кастомного сообщения об ошибке."""
        from sqlalchemy import and_

        custom_detail = 'Пользователь с указанными условиями не найден'

        with pytest.raises(HTTPException) as exc_info:
            await crud.get_by_condition_or_404(
                async_session,
                and_(
                    ModelForBaseCRUD.email == 'nonexistent@example.com',
                    ModelForBaseCRUD.is_active.is_(True),
                ),
                _detail=custom_detail,
            )

        assert exc_info.value.status_code == HTTPStatus.NOT_FOUND
        assert exc_info.value.detail == custom_detail


class TestCRUDGetMulti:
    """Тесты для метода get_multi."""

    async def test_get_multi_all(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест получения всех объектов."""
        results = await crud.get_multi(async_session)

        assert len(results) == len(created_objects)
        assert all(isinstance(obj, ModelForBaseCRUD) for obj in results)

    async def test_get_multi_with_filter(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест получения объектов с фильтром."""
        results = await crud.get_multi(async_session, {'is_active': True})

        assert len(results) == 2
        assert all(obj.is_active for obj in results)

    async def test_get_multi_with_order_by(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест получения объектов с сортировкой."""
        results = await crud.get_multi(
            async_session, order_by=(ModelForBaseCRUD.name.asc(),)
        )

        assert len(results) == 3
        names = [obj.name for obj in results]
        assert names == sorted(names)

    async def test_get_multi_with_limit_offset(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест получения объектов с пагинацией."""
        results = await crud.get_multi(async_session, limit=2, offset=1)

        assert len(results) == 2


class TestCRUDGetMultiOr404:
    """Тесты для метода get_multi_or_404."""

    async def test_get_multi_or_404_success(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест успешного получения объектов через get_multi_or_404."""
        results = await crud.get_multi_or_404(async_session, {'is_active': True})

        assert len(results) == 2
        assert all(obj.is_active for obj in results)

    async def test_get_multi_or_404_not_found_raises_404(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест 404 ошибки при получении пустого списка."""
        with pytest.raises(HTTPException) as exc_info:
            await crud.get_multi_or_404(
                async_session, {'email': 'nonexistent@example.com'}
            )

        assert exc_info.value.status_code == HTTPStatus.NOT_FOUND
        assert (
            'No ModelForBaseCRUD found with email=nonexistent@example.com'
            in exc_info.value.detail
        )

    async def test_get_multi_or_404_custom_detail(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест кастомного сообщения об ошибке."""
        custom_detail = 'Нет активных пользователей'

        with pytest.raises(HTTPException) as exc_info:
            await crud.get_multi_or_404(
                async_session, {'is_active': True}, _detail=custom_detail
            )

        assert exc_info.value.status_code == HTTPStatus.NOT_FOUND
        assert exc_info.value.detail == custom_detail


class TestCRUDGetMultiByCondition:
    """Тесты для метода get_multi_by_condition."""

    async def test_get_multi_by_condition_success(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест успешного получения объектов через get_multi_by_condition."""
        from sqlalchemy import and_

        results = await crud.get_multi_by_condition(
            async_session,
            and_(
                ModelForBaseCRUD.is_active.is_(True),
                ModelForBaseCRUD.user_id == 1,
            ),
        )

        assert len(results) == 2
        assert all(obj.is_active for obj in results)
        assert all(obj.user_id == 1 for obj in results)

    async def test_get_multi_by_condition_empty_result(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест получения пустого списка через get_multi_by_condition."""
        from sqlalchemy import and_

        results = await crud.get_multi_by_condition(
            async_session,
            and_(
                ModelForBaseCRUD.email == 'nonexistent@example.com',
                ModelForBaseCRUD.is_active.is_(True),
            ),
        )

        assert len(results) == 0

    async def test_get_multi_by_condition_with_order_by(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест get_multi_by_condition с сортировкой."""
        from sqlalchemy import and_

        results = await crud.get_multi_by_condition(
            async_session,
            and_(
                ModelForBaseCRUD.is_active.is_(True),
                ModelForBaseCRUD.user_id == 1,
            ),
            order_by=(ModelForBaseCRUD.name.asc(),),
        )

        assert len(results) == 2
        names = [obj.name for obj in results]
        assert names == sorted(names)

    async def test_get_multi_by_condition_with_limit_offset(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест get_multi_by_condition с пагинацией."""
        from sqlalchemy import and_

        results = await crud.get_multi_by_condition(
            async_session,
            and_(
                ModelForBaseCRUD.is_active.is_(True),
                ModelForBaseCRUD.user_id == 1,
            ),
            limit=1,
            offset=0,
        )

        assert len(results) == 1
        assert all(obj.is_active for obj in results)
        assert all(obj.user_id == 1 for obj in results)

    async def test_get_multi_by_condition_without_conditions_raises_error(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест что метод get_multi_by_condition требует хотя бы одно условие."""
        with pytest.raises(ValueError, match='Необходимо указать хотя бы одно условие'):
            await crud.get_multi_by_condition(async_session)


class TestCRUDGetMultiByConditionOr404:
    """Тесты для метода get_multi_by_condition_or_404."""

    async def test_get_multi_by_condition_or_404_success(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест успешного получения объектов через get_multi_by_condition_or_404."""
        from sqlalchemy import and_

        results = await crud.get_multi_by_condition_or_404(
            async_session,
            and_(
                ModelForBaseCRUD.is_active.is_(True),
                ModelForBaseCRUD.user_id == 1,
            ),
        )

        assert len(results) == 2
        assert all(obj.is_active for obj in results)
        assert all(obj.user_id == 1 for obj in results)

    async def test_get_multi_by_condition_or_404_not_found_raises_404(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест 404 ошибки при получении пустого списка."""
        from sqlalchemy import and_

        with pytest.raises(HTTPException) as exc_info:
            await crud.get_multi_by_condition_or_404(
                async_session,
                and_(
                    ModelForBaseCRUD.email == 'nonexistent@example.com',
                    ModelForBaseCRUD.is_active.is_(True),
                ),
            )

        assert exc_info.value.status_code == HTTPStatus.NOT_FOUND
        assert 'No ModelForBaseCRUD found matching conditions' in exc_info.value.detail

    async def test_get_multi_by_condition_or_404_custom_detail(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест кастомного сообщения об ошибке."""
        from sqlalchemy import and_

        custom_detail = 'Пользователи с указанными условиями не найдены'

        with pytest.raises(HTTPException) as exc_info:
            await crud.get_multi_by_condition_or_404(
                async_session,
                and_(
                    ModelForBaseCRUD.email == 'nonexistent@example.com',
                    ModelForBaseCRUD.is_active.is_(True),
                ),
                _detail=custom_detail,
            )

        assert exc_info.value.status_code == HTTPStatus.NOT_FOUND
        assert exc_info.value.detail == custom_detail


class TestCRUDCount:
    """Тесты для метода count."""

    async def test_count_all(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест подсчета всех объектов."""
        count = await crud.count(async_session)
        assert count == 3

    async def test_count_with_filter(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест подсчета объектов с фильтром."""
        active_count = await crud.count(async_session, {'is_active': True})
        assert active_count == 2

        inactive_count = await crud.count(async_session, {'is_active': False})
        assert inactive_count == 1

    async def test_count_empty_result(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест подсчета когда объекты не найдены."""
        count = await crud.count(async_session, {'email': 'nonexistent@example.com'})
        assert count == 0


class TestCRUDCountByCondition:
    """Тесты для метода count_by_condition."""

    async def test_count_by_condition_success(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест подсчета объектов по условиям."""
        from sqlalchemy import and_

        count = await crud.count_by_condition(
            async_session,
            and_(
                ModelForBaseCRUD.user_id == 1,
                ModelForBaseCRUD.is_active.is_(True),
            ),
        )

        assert count == 2

    async def test_count_by_condition_empty_result(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест подсчета когда объекты не найдены."""
        from sqlalchemy import and_

        count = await crud.count_by_condition(
            async_session,
            and_(
                ModelForBaseCRUD.email == 'nonexistent@example.com',
                ModelForBaseCRUD.is_active.is_(True),
            ),
        )

        assert count == 0


class TestCRUDExists:
    """Тесты для метода exists."""

    async def test_exists_true(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест проверки существования существующего объекта."""
        test_obj = created_objects[0]

        exists = await crud.exists(async_session, {'email': test_obj.email})
        assert exists is True

    async def test_exists_false(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест проверки существования несуществующего объекта."""
        exists = await crud.exists(async_session, {'email': 'nonexistent@example.com'})
        assert exists is False

    async def test_exists_without_filters_raises_error(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест что метод exists требует хотя бы один фильтр."""
        with pytest.raises(
            ValueError, match='Необходимо указать хотя бы одно поле для поиска'
        ):
            await crud.exists(async_session, {})


class TestCRUDExistsOr404:
    """Тесты для метода exists_or_404."""

    async def test_exists_or_404_true(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест успешной проверки существования."""
        test_obj = created_objects[0]

        result = await crud.exists_or_404(async_session, {'email': test_obj.email})
        assert result is True

    async def test_exists_or_404_not_found_raises(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест 404 ошибки когда объект не найден."""
        with pytest.raises(HTTPException) as exc_info:
            await crud.exists_or_404(
                async_session, {'email': 'nonexistent@example.com'}
            )

        assert exc_info.value.status_code == HTTPStatus.NOT_FOUND
        assert (
            'ModelForBaseCRUD with email=nonexistent@example.com not found'
            in exc_info.value.detail
        )

    async def test_exists_or_404_custom_detail(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест кастомного сообщения об ошибке."""
        custom_detail = 'Пользователь не найден'

        with pytest.raises(HTTPException) as exc_info:
            await crud.exists_or_404(
                async_session,
                {'email': 'nonexistent@example.com'},
                _detail=custom_detail,
            )

        assert exc_info.value.status_code == HTTPStatus.NOT_FOUND
        assert exc_info.value.detail == custom_detail


class TestCRUDExistsByCondition:
    """Тесты для метода exists_by_condition."""

    async def test_exists_by_condition_true(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест проверки существования по условиям."""
        from sqlalchemy import and_

        exists = await crud.exists_by_condition(
            async_session,
            and_(
                ModelForBaseCRUD.is_active.is_(True),
                ModelForBaseCRUD.user_id == 1,
            ),
        )

        assert exists is True

    async def test_exists_by_condition_false(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест проверки несуществования по условиям."""
        from sqlalchemy import and_

        exists = await crud.exists_by_condition(
            async_session,
            and_(
                ModelForBaseCRUD.email == 'nonexistent@example.com',
                ModelForBaseCRUD.is_active.is_(True),
            ),
        )

        assert exists is False


class TestCRUDExistsByConditionOr404:
    """Тесты для метода exists_by_condition_or_404."""

    async def test_exists_by_condition_or_404_true(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест успешной проверки по условиям."""
        from sqlalchemy import and_

        result = await crud.exists_by_condition_or_404(
            async_session,
            and_(
                ModelForBaseCRUD.is_active.is_(True),
                ModelForBaseCRUD.user_id == 1,
            ),
        )

        assert result is True

    async def test_exists_by_condition_or_404_not_found_raises(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест 404 ошибки когда объект не найден по условиям."""
        from sqlalchemy import and_

        with pytest.raises(HTTPException) as exc_info:
            await crud.exists_by_condition_or_404(
                async_session,
                and_(
                    ModelForBaseCRUD.email == 'nonexistent@example.com',
                    ModelForBaseCRUD.is_active.is_(True),
                ),
            )

        assert exc_info.value.status_code == HTTPStatus.NOT_FOUND
        assert 'No ModelForBaseCRUD found matching conditions' in exc_info.value.detail

    async def test_exists_by_condition_or_404_custom_detail(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест кастомного сообщения об ошибке."""
        from sqlalchemy import and_

        custom_detail = 'Объект не найден по условиям'

        with pytest.raises(HTTPException) as exc_info:
            await crud.exists_by_condition_or_404(
                async_session,
                and_(
                    ModelForBaseCRUD.email == 'nonexistent@example.com',
                    ModelForBaseCRUD.is_active.is_(True),
                ),
                _detail=custom_detail,
            )

        assert exc_info.value.status_code == HTTPStatus.NOT_FOUND
        assert exc_info.value.detail == custom_detail


class TestCRUDNotExistsOr409:
    """Тесты для метода not_exists_or_409."""

    async def test_not_exists_or_409_true(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест успешной проверки отсутствия объекта."""
        result = await crud.not_exists_or_409(
            async_session, {'email': 'new_unique@example.com'}
        )
        assert result is True

    async def test_not_exists_or_409_conflict_raises(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест 409 ошибки когда объект уже существует."""
        test_obj = created_objects[0]

        with pytest.raises(HTTPException) as exc_info:
            await crud.not_exists_or_409(async_session, {'email': test_obj.email})

        assert exc_info.value.status_code == HTTPStatus.CONFLICT
        assert 'already exists' in exc_info.value.detail

    async def test_not_exists_or_409_custom_detail(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест кастомного сообщения об ошибке."""
        test_obj = created_objects[0]
        custom_detail = 'Пользователь с таким email уже зарегистрирован'

        with pytest.raises(HTTPException) as exc_info:
            await crud.not_exists_or_409(
                async_session, {'email': test_obj.email}, _detail=custom_detail
            )

        assert exc_info.value.status_code == HTTPStatus.CONFLICT
        assert exc_info.value.detail == custom_detail

    async def test_not_exists_or_409_multiple_fields(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест проверки нескольких полей одновременно."""
        test_obj = created_objects[0]

        with pytest.raises(HTTPException) as exc_info:
            await crud.not_exists_or_409(
                async_session,
                {'email': test_obj.email, 'user_id': test_obj.user_id},
            )

        assert exc_info.value.status_code == HTTPStatus.CONFLICT
        assert f'email={test_obj.email}' in exc_info.value.detail
        assert f'user_id={test_obj.user_id}' in exc_info.value.detail


class TestCRUDNotExistsByConditionOr409:
    """Тесты для метода not_exists_by_condition_or_409."""

    async def test_not_exists_by_condition_or_409_true(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест успешной проверки отсутствия по условиям."""
        from sqlalchemy import and_

        result = await crud.not_exists_by_condition_or_409(
            async_session,
            and_(
                ModelForBaseCRUD.email == 'nonexistent@example.com',
                ModelForBaseCRUD.is_active.is_(True),
            ),
        )

        assert result is True

    async def test_not_exists_by_condition_or_409_conflict_raises(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест 409 ошибки когда объект существует по условиям."""
        from sqlalchemy import and_

        with pytest.raises(HTTPException) as exc_info:
            await crud.not_exists_by_condition_or_409(
                async_session,
                and_(
                    ModelForBaseCRUD.is_active.is_(True),
                    ModelForBaseCRUD.user_id == 1,
                ),
            )

        assert exc_info.value.status_code == HTTPStatus.CONFLICT
        assert 'already exists' in exc_info.value.detail

    async def test_not_exists_by_condition_or_409_custom_detail(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест кастомного сообщения об ошибке."""
        from sqlalchemy import or_

        test_obj = created_objects[0]
        custom_detail = 'Объект с таким email или user_id уже существует'

        with pytest.raises(HTTPException) as exc_info:
            await crud.not_exists_by_condition_or_409(
                async_session,
                or_(
                    ModelForBaseCRUD.email == test_obj.email,
                    ModelForBaseCRUD.user_id == test_obj.user_id,
                ),
                _detail=custom_detail,
            )

        assert exc_info.value.status_code == HTTPStatus.CONFLICT
        assert exc_info.value.detail == custom_detail


class TestCRUDGetOrCreate:
    """Тесты для метода get_or_create."""

    async def test_get_or_create_existing(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест получения существующего объекта."""
        existing_obj = created_objects[0]

        result, created = await crud.get_or_create(
            async_session, {'email': existing_obj.email}
        )

        assert not created  # Объект не был создан
        assert result.id == existing_obj.id
        assert result.email == existing_obj.email

    async def test_get_or_create_new(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест создания нового объекта."""
        result, created = await crud.get_or_create(
            async_session,
            {'email': 'newcreated@example.com'},
            defaults={
                'name': 'New Created User',
                'description': 'Created via get_or_create',
                'is_active': True,
            },
        )

        assert created  # Объект был создан
        assert result.email == 'newcreated@example.com'
        assert result.name == 'New Created User'
        assert result.id is not None  # Объект получил ID после flush()

    async def test_get_or_create_without_filters_raises_error(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест что метод требует хотя бы один фильтр."""
        with pytest.raises(
            ValueError, match='Необходимо указать хотя бы одно поле для поиска'
        ):
            await crud.get_or_create(async_session, {})


class TestCRUDGetOrCreateWithPydantic:
    """Тесты для метода get_or_create_with_pydantic."""

    async def test_get_or_create_with_pydantic_existing(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест получения существующего объекта через Pydantic."""
        existing_obj = created_objects[0]
        create_data = ModelForBaseCRUDCreateSchema(
            name='New Name',
            email=existing_obj.email,  # Используем существующий email
            description='New description',
        )

        result, created = await crud.get_or_create_with_pydantic(
            async_session, create_data, search_fields=['email']
        )

        assert not created  # Объект не был создан
        assert result.id == existing_obj.id
        assert result.email == existing_obj.email

    async def test_get_or_create_with_pydantic_new(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест создания нового объекта через Pydantic."""
        create_data = ModelForBaseCRUDCreateSchema(
            name='Pydantic User',
            email='pydantic@example.com',
            description='Created via pydantic',
        )

        result, created = await crud.get_or_create_with_pydantic(
            async_session, create_data, search_fields=['email']
        )

        assert created  # Объект был создан
        assert result.email == 'pydantic@example.com'
        assert result.name == 'Pydantic User'
        assert result.id is not None  # Объект получил ID после flush()

    async def test_get_or_create_with_pydantic_missing_field(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест ошибки при отсутствующем поле в search_fields."""
        create_data = ModelForBaseCRUDCreateSchema(
            name='Test User', email='test@example.com'
        )

        with pytest.raises(
            ValueError, match="Поле 'nonexistent' не найдено в данных объекта"
        ):
            await crud.get_or_create_with_pydantic(
                async_session, create_data, search_fields=['nonexistent']
            )


class TestCRUDGetOrCreateByCondition:
    """Тесты для метода get_or_create_by_condition."""

    async def test_get_or_create_by_condition_existing(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест получения существующего объекта по условиям."""
        from sqlalchemy import or_

        existing_obj = created_objects[0]

        result, created = await crud.get_or_create_by_condition(
            async_session,
            or_(
                ModelForBaseCRUD.email == existing_obj.email,
                ModelForBaseCRUD.name == existing_obj.name,
            ),
            create_data={'email': 'new@example.com', 'name': 'New Name'},
        )

        assert not created  # Объект не был создан
        assert result.id == existing_obj.id
        assert result.email == existing_obj.email

    async def test_get_or_create_by_condition_new(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест создания нового объекта по условиям."""
        from sqlalchemy import and_

        result, created = await crud.get_or_create_by_condition(
            async_session,
            and_(
                ModelForBaseCRUD.email == 'newcondition@example.com',
                ModelForBaseCRUD.is_active.is_(True),
            ),
            create_data={
                'email': 'newcondition@example.com',
                'name': 'New Condition User',
                'is_active': True,
            },
            defaults={'description': 'Created via condition', 'user_id': 999},
        )

        assert created  # Объект был создан
        assert result.email == 'newcondition@example.com'
        assert result.name == 'New Condition User'
        assert result.description == 'Created via condition'
        assert result.user_id == 999
        assert result.id is not None  # Объект получил ID после flush()

    async def test_get_or_create_by_condition_without_conditions_raises_error(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест что метод требует хотя бы одно условие."""
        with pytest.raises(
            ValueError, match='Необходимо указать хотя бы одно условие для поиска'
        ):
            await crud.get_or_create_by_condition(
                async_session, create_data={'email': 'test@example.com'}
            )

    async def test_get_or_create_by_condition_without_create_data_raises_error(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест что метод требует create_data для создания объекта."""
        with pytest.raises(
            ValueError, match='Необходимо указать create_data для создания объекта'
        ):
            await crud.get_or_create_by_condition(
                async_session, ModelForBaseCRUD.email == 'nonexistent@example.com'
            )


class TestCRUDCreate:
    """Тесты для метода create."""

    async def test_create_success(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест успешного создания объекта."""
        create_data = ModelForBaseCRUDCreateSchema(
            name='New User',
            email='new@example.com',
            description='New test user',
            is_active=True,
            user_id=1,
        )

        result = await crud.create(async_session, create_data)

        assert result.id is not None  # Объект получил ID после flush()
        assert result.name == 'New User'
        assert result.email == 'new@example.com'
        assert result.user_id == 1

    async def test_create_with_user_id(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест создания объекта с user_id."""
        create_data = ModelForBaseCRUDCreateSchema(
            name='User With ID',
            email='userid@example.com',
            description='User with user_id',
        )

        result = await crud.create(async_session, create_data, user_id=123)

        assert result.user_id == 123
        assert result.id is not None  # Объект получил ID после flush()


class TestCRUDBulkCreate:
    """Тесты для метода bulk_create."""

    async def test_bulk_create_success(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест массового создания объектов."""
        create_data = [
            ModelForBaseCRUDCreateSchema(
                name='Bulk User 1',
                email='bulk1@example.com',
                is_active=True,
            ),
            ModelForBaseCRUDCreateSchema(
                name='Bulk User 2',
                email='bulk2@example.com',
                is_active=False,
            ),
        ]

        results = await crud.bulk_create(async_session, create_data, user_id=999)

        assert len(results) == 2
        assert all(obj.user_id == 999 for obj in results)
        assert all(
            obj.id is not None for obj in results
        )  # Все объекты получили ID после flush()
        assert results[0].name == 'Bulk User 1'
        assert results[1].name == 'Bulk User 2'

    async def test_bulk_create_empty_list(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест массового создания с пустым списком."""
        results = await crud.bulk_create(async_session, [])

        assert len(results) == 0


class TestCRUDUpdate:
    """Тесты для метода update."""

    async def test_update_success(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест успешного обновления объекта."""
        test_obj = created_objects[0]
        original_id = test_obj.id

        update_data = ModelForBaseCRUDUpdateSchema(
            name='Updated Name', email='updated@example.com'
        )

        result = await crud.update(async_session, test_obj, update_data)

        assert result.name == 'Updated Name'
        assert result.email == 'updated@example.com'
        assert result.id == original_id  # ID не изменился
        assert result is test_obj  # Тот же объект в памяти

    async def test_update_partial(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест частичного обновления объекта."""
        test_obj = created_objects[0]
        original_email = test_obj.email

        update_data = ModelForBaseCRUDUpdateSchema(name='Partially Updated')

        result = await crud.update(async_session, test_obj, update_data)

        assert result.name == 'Partially Updated'
        assert result.email == original_email  # Email не изменился


class TestCRUDUpdateOr404:
    """Тесты для метода update_or_404."""

    async def test_update_or_404_success(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест успешного обновления через update_or_404."""
        test_obj = created_objects[0]
        update_data = ModelForBaseCRUDUpdateSchema(name='Updated via 404')

        result = await crud.update_or_404(
            async_session, update_data, {'id': test_obj.id}
        )

        assert result.name == 'Updated via 404'
        assert result.id == test_obj.id

    async def test_update_or_404_not_found_raises_404(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест 404 ошибки при обновлении несуществующего объекта."""
        update_data = ModelForBaseCRUDUpdateSchema(name='Updated Name')

        with pytest.raises(HTTPException) as exc_info:
            await crud.update_or_404(async_session, update_data, {'id': 999})

        assert exc_info.value.status_code == HTTPStatus.NOT_FOUND


class TestCRUDUpdateByFields:
    """Тесты для метода update_by_fields."""

    async def test_update_by_fields_success(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест обновления объектов по полям."""
        test_obj = created_objects[0]

        updated_count = await crud.update_by_fields(
            async_session,
            {
                'name': 'Bulk Updated',
                'is_active': False,
            },
            {'id': test_obj.id},
        )

        assert updated_count == 1

        # Проверяем что объект действительно обновился
        updated_obj = await crud.get(async_session, {'id': test_obj.id})
        assert updated_obj.name == 'Bulk Updated'
        assert updated_obj.is_active is False

    async def test_update_by_fields_multiple_objects(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест обновления нескольких объектов."""
        updated_count = await crud.update_by_fields(
            async_session,
            {'description': 'Bulk updated description'},
            {'is_active': True},
        )

        assert updated_count == 2  # Два активных пользователя

        # Проверяем что объекты действительно обновились
        active_objects = await crud.get_multi(async_session, {'is_active': True})
        assert all(
            obj.description == 'Bulk updated description' for obj in active_objects
        )

    async def test_update_by_fields_no_objects_found(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест обновления когда объекты не найдены."""
        updated_count = await crud.update_by_fields(
            async_session,
            {'name': 'Updated Name'},
            {'email': 'nonexistent@example.com'},
        )

        assert updated_count == 0

    async def test_update_by_fields_without_filters_raises_error(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест ошибки при отсутствии фильтров."""
        with pytest.raises(
            ValueError, match='Необходимо указать хотя бы одно поле для фильтрации'
        ):
            await crud.update_by_fields(async_session, {'name': 'Updated'}, {})


class TestCRUDUpdateByFieldsOr404:
    """Тесты для метода update_by_fields_or_404."""

    async def test_update_by_fields_or_404_success(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест успешного обновления через update_by_fields_or_404."""
        test_obj = created_objects[0]

        updated_count = await crud.update_by_fields_or_404(
            async_session,
            {
                'name': 'Updated via 404',
                'is_active': False,
            },
            {'id': test_obj.id},
        )

        assert updated_count == 1

        # Проверяем что объект действительно обновился
        updated_obj = await crud.get(async_session, {'id': test_obj.id})
        assert updated_obj.name == 'Updated via 404'
        assert updated_obj.is_active is False

    async def test_update_by_fields_or_404_not_found_raises_404(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест 404 ошибки при обновлении несуществующего объекта."""
        with pytest.raises(HTTPException) as exc_info:
            await crud.update_by_fields_or_404(
                async_session,
                {'name': 'Updated Name'},
                {'id': 999},
            )

        assert exc_info.value.status_code == HTTPStatus.NOT_FOUND
        assert (
            'No ModelForBaseCRUD found to update with id=999' in exc_info.value.detail
        )

    async def test_update_by_fields_or_404_custom_detail(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест кастомного сообщения об ошибке."""
        custom_detail = 'Пользователь для обновления не найден'

        with pytest.raises(HTTPException) as exc_info:
            await crud.update_by_fields_or_404(
                async_session,
                {'name': 'Updated Name'},
                {'id': 999},
                _detail=custom_detail,
            )

        assert exc_info.value.status_code == HTTPStatus.NOT_FOUND
        assert exc_info.value.detail == custom_detail


class TestCRUDUpdateByCondition:
    """Тесты для метода update_by_condition."""

    async def test_update_by_condition_success(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест обновления объектов по условиям."""
        from sqlalchemy import and_

        updated_count = await crud.update_by_condition(
            async_session,
            {'description': 'Updated by condition'},
            and_(
                ModelForBaseCRUD.is_active.is_(True),
                ModelForBaseCRUD.user_id == 1,
            ),
        )

        assert updated_count == 2  # Два активных пользователя с user_id=1

        # Проверяем что объекты действительно обновились
        updated_objects = await crud.get_multi(
            async_session, {'is_active': True, 'user_id': 1}
        )
        assert all(obj.description == 'Updated by condition' for obj in updated_objects)

    async def test_update_by_condition_no_objects_found(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест обновления когда объекты не найдены."""
        from sqlalchemy import and_

        updated_count = await crud.update_by_condition(
            async_session,
            {'description': 'Updated description'},
            and_(
                ModelForBaseCRUD.email == 'nonexistent@example.com',
                ModelForBaseCRUD.is_active.is_(True),
            ),
        )

        assert updated_count == 0

    async def test_update_by_condition_without_conditions_raises_error(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест ошибки при отсутствии условий."""
        with pytest.raises(
            ValueError, match='Необходимо указать хотя бы одно условие для обновления'
        ):
            await crud.update_by_condition(async_session, {'description': 'Updated'})


class TestCRUDUpdateByConditionOr404:
    """Тесты для метода update_by_condition_or_404."""

    async def test_update_by_condition_or_404_success(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест успешного обновления через update_by_condition_or_404."""
        from sqlalchemy import and_

        updated_count = await crud.update_by_condition_or_404(
            async_session,
            {'description': 'Updated by condition or 404'},
            and_(
                ModelForBaseCRUD.is_active.is_(True),
                ModelForBaseCRUD.user_id == 1,
            ),
        )

        assert updated_count == 2  # Два активных пользователя с user_id=1

        # Проверяем что объекты действительно обновились
        updated_objects = await crud.get_multi(
            async_session, {'is_active': True, 'user_id': 1}
        )
        assert all(
            obj.description == 'Updated by condition or 404' for obj in updated_objects
        )

    async def test_update_by_condition_or_404_not_found_raises_404(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест 404 ошибки при обновлении несуществующих объектов."""
        from sqlalchemy import and_

        with pytest.raises(HTTPException) as exc_info:
            await crud.update_by_condition_or_404(
                async_session,
                {'description': 'Updated description'},
                and_(
                    ModelForBaseCRUD.email == 'nonexistent@example.com',
                    ModelForBaseCRUD.is_active.is_(True),
                ),
            )

        assert exc_info.value.status_code == HTTPStatus.NOT_FOUND
        assert (
            'No ModelForBaseCRUD found to update matching conditions'
            in exc_info.value.detail
        )

    async def test_update_by_condition_or_404_custom_detail(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест кастомного сообщения об ошибке."""
        from sqlalchemy import and_

        custom_detail = 'Пользователи для обновления не найдены'

        with pytest.raises(HTTPException) as exc_info:
            await crud.update_by_condition_or_404(
                async_session,
                {'description': 'Updated description'},
                and_(
                    ModelForBaseCRUD.email == 'nonexistent@example.com',
                    ModelForBaseCRUD.is_active.is_(True),
                ),
                _detail=custom_detail,
            )

        assert exc_info.value.status_code == HTTPStatus.NOT_FOUND
        assert exc_info.value.detail == custom_detail


class TestCRUDUpdateWithPydanticByFields:
    """Тесты для метода update_with_pydantic_by_fields."""

    async def test_update_with_pydantic_by_fields_success(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест успешного обновления через update_with_pydantic_by_fields."""
        test_obj = created_objects[0]
        update_data = ModelForBaseCRUDUpdateSchema(
            name='Updated via Pydantic',
            description='Updated description via Pydantic',
        )

        updated_count = await crud.update_with_pydantic_by_fields(
            async_session, update_data, {'id': test_obj.id}
        )

        assert updated_count == 1

        # Проверяем что объект действительно обновился
        updated_obj = await crud.get(async_session, {'id': test_obj.id})
        assert updated_obj.name == 'Updated via Pydantic'
        assert updated_obj.description == 'Updated description via Pydantic'

    async def test_update_with_pydantic_by_fields_partial_update(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест частичного обновления через update_with_pydantic_by_fields."""
        test_obj = created_objects[0]
        original_name = test_obj.name

        # Обновляем только email
        update_data = ModelForBaseCRUDUpdateSchema(email='partial@example.com')

        updated_count = await crud.update_with_pydantic_by_fields(
            async_session, update_data, {'id': test_obj.id}
        )

        assert updated_count == 1

        # Проверяем что обновился только email, а name остался прежним
        updated_obj = await crud.get(async_session, {'id': test_obj.id})
        assert updated_obj.email == 'partial@example.com'
        assert updated_obj.name == original_name  # Не изменился

    async def test_update_with_pydantic_by_fields_no_objects_found(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест обновления когда объекты не найдены."""
        update_data = ModelForBaseCRUDUpdateSchema(name='Updated Name')

        updated_count = await crud.update_with_pydantic_by_fields(
            async_session, update_data, {'email': 'nonexistent@example.com'}
        )

        assert updated_count == 0


class TestCRUDUpdateWithPydanticByFieldsOr404:
    """Тесты для метода update_with_pydantic_by_fields_or_404."""

    async def test_update_with_pydantic_by_fields_or_404_success(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест успешного обновления через update_with_pydantic_by_fields_or_404."""
        test_obj = created_objects[0]
        update_data = ModelForBaseCRUDUpdateSchema(
            name='Updated via Pydantic 404',
            description='Updated via Pydantic 404',
        )

        updated_count = await crud.update_with_pydantic_by_fields_or_404(
            async_session, update_data, {'id': test_obj.id}
        )

        assert updated_count == 1

        # Проверяем что объект действительно обновился
        updated_obj = await crud.get(async_session, {'id': test_obj.id})
        assert updated_obj.name == 'Updated via Pydantic 404'
        assert updated_obj.description == 'Updated via Pydantic 404'

    async def test_update_with_pydantic_by_fields_or_404_not_found_raises_404(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест 404 ошибки при обновлении несуществующего объекта."""
        update_data = ModelForBaseCRUDUpdateSchema(name='Updated Name')

        with pytest.raises(HTTPException) as exc_info:
            await crud.update_with_pydantic_by_fields_or_404(
                async_session, update_data, {'id': 999}
            )

        assert exc_info.value.status_code == HTTPStatus.NOT_FOUND
        assert (
            'No ModelForBaseCRUD found to update with id=999' in exc_info.value.detail
        )

    async def test_update_with_pydantic_by_fields_or_404_custom_detail(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест кастомного сообщения об ошибке."""
        update_data = ModelForBaseCRUDUpdateSchema(name='Updated Name')
        custom_detail = 'Пользователь для обновления не найден'

        with pytest.raises(HTTPException) as exc_info:
            await crud.update_with_pydantic_by_fields_or_404(
                async_session, update_data, {'id': 999}, _detail=custom_detail
            )

        assert exc_info.value.status_code == HTTPStatus.NOT_FOUND
        assert exc_info.value.detail == custom_detail


class TestCRUDBulkUpdateByIds:
    """Тесты для метода bulk_update_by_ids."""

    async def test_bulk_update_by_ids_success(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест массового обновления по ID."""
        obj_ids = [obj.id for obj in created_objects[:2]]

        updated_count = await crud.bulk_update_by_ids(
            async_session, obj_ids, {'description': 'Bulk updated'}
        )

        assert updated_count == 2

        # Проверяем что объекты обновились
        for obj_id in obj_ids:
            obj = await crud.get(async_session, {'id': obj_id})
            assert obj.description == 'Bulk updated'

    async def test_bulk_update_by_ids_empty_list(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест массового обновления с пустым списком ID."""
        updated_count = await crud.bulk_update_by_ids(
            async_session, [], {'description': 'Updated'}
        )

        assert updated_count == 0

    async def test_bulk_update_by_ids_nonexistent_ids(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест обновления несуществующих ID."""
        updated_count = await crud.bulk_update_by_ids(
            async_session, [999, 1000], {'description': 'Updated'}
        )

        assert updated_count == 0


class TestCRUDBulkUpdateByFieldValues:
    """Тесты для метода bulk_update_by_field_values."""

    async def test_bulk_update_by_field_values_success(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест массового обновления по значениям поля."""
        emails = [obj.email for obj in created_objects[:2]]

        updated_count = await crud.bulk_update_by_field_values(
            async_session,
            'email',
            emails,
            {'is_active': False},
        )

        assert updated_count == 2

        # Проверяем что объекты обновились
        for email in emails:
            obj = await crud.get(async_session, {'email': email})
            assert obj.is_active is False

    async def test_bulk_update_by_field_values_empty_list(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест массового обновления с пустым списком значений."""
        updated_count = await crud.bulk_update_by_field_values(
            async_session, 'email', [], {'is_active': False}
        )

        assert updated_count == 0

    async def test_bulk_update_by_field_values_nonexistent_field(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест ошибки при несуществующем поле."""
        with pytest.raises(
            AttributeError,
            match="Поле 'nonexistent' не существует в модели ModelForBaseCRUD",
        ):
            await crud.bulk_update_by_field_values(
                async_session, 'nonexistent', ['value1', 'value2'], {'name': 'Updated'}
            )


class TestCRUDBulkUpdateAllByFields:
    """Тесты для метода bulk_update_all_by_fields."""

    async def test_bulk_update_all_by_fields_success(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест массового обновления всех объектов по полям."""
        total_updated = await crud.bulk_update_all_by_fields(
            async_session,
            {'description': 'Bulk updated all active'},
            {'is_active': True},
            batch_size=2,
        )

        assert total_updated == 2  # Два активных пользователя

        # Проверяем что объекты обновились
        updated_objects = await crud.get_multi(async_session, {'is_active': True})
        assert all(
            obj.description == 'Bulk updated all active' for obj in updated_objects
        )

    async def test_bulk_update_all_by_fields_no_objects_found(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест обновления когда объекты не найдены."""
        total_updated = await crud.bulk_update_all_by_fields(
            async_session,
            {'description': 'Updated'},
            {'email': 'nonexistent@example.com'},
            batch_size=2,
        )

        assert total_updated == 0

    async def test_bulk_update_all_by_fields_without_filters_raises_error(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест ошибки при обновлении без фильтров."""
        with pytest.raises(
            ValueError, match='Необходимо указать условия для обновления'
        ):
            await crud.bulk_update_all_by_fields(
                async_session, {'description': 'Updated'}, {}, batch_size=2
            )


class TestCRUDUpsert:
    """Тесты для метода upsert."""

    async def test_upsert_create_new(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест создания нового объекта через upsert."""
        upsert_data = ModelForBaseCRUDCreateSchema(
            name='Upsert User',
            email='upsert@example.com',
            description='Created via upsert',
            is_active=True,
        )

        result, created = await crud.upsert(
            async_session, upsert_data, unique_fields=['email']
        )

        assert created  # Объект был создан
        assert result.email == 'upsert@example.com'
        assert result.name == 'Upsert User'
        assert result.id is not None

    async def test_upsert_update_existing(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест обновления существующего объекта через upsert."""
        existing_obj = created_objects[0]

        upsert_data = ModelForBaseCRUDCreateSchema(
            name='Updated Name',
            email=existing_obj.email,  # Используем существующий email
            description='Updated via upsert',
            is_active=False,
        )

        result, created = await crud.upsert(
            async_session, upsert_data, unique_fields=['email']
        )

        assert not created  # Объект не был создан
        assert result.id == existing_obj.id  # Тот же объект
        assert result.name == 'Updated Name'  # Обновленные данные
        assert result.description == 'Updated via upsert'
        assert result.is_active is False

    async def test_upsert_update_specific_fields_only(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест обновления только указанных полей через upsert."""
        existing_obj = created_objects[0]
        original_description = existing_obj.description

        upsert_data = ModelForBaseCRUDCreateSchema(
            name='Updated Name Only',
            email=existing_obj.email,
            description='This should not update',
            is_active=False,
        )

        result, created = await crud.upsert(
            async_session,
            upsert_data,
            unique_fields=['email'],
            update_fields=['name'],  # Обновляем только name
        )

        assert not created
        assert result.id == existing_obj.id
        assert result.name == 'Updated Name Only'  # Обновилось
        assert result.description == original_description  # НЕ изменилось
        assert result.is_active == existing_obj.is_active  # НЕ изменилось

    async def test_upsert_multiple_unique_fields(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест upsert по нескольким уникальным полям."""
        existing_obj = created_objects[0]

        # Пытаемся найти по email И user_id
        upsert_data = ModelForBaseCRUDCreateSchema(
            name='Multi Field Update',
            email=existing_obj.email,
            user_id=existing_obj.user_id,
            description='Updated by multiple fields',
        )

        result, created = await crud.upsert(
            async_session, upsert_data, unique_fields=['email', 'user_id']
        )

        assert not created
        assert result.id == existing_obj.id
        assert result.name == 'Multi Field Update'

    async def test_upsert_without_unique_fields_raises_error(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест что upsert требует unique_fields."""
        upsert_data = ModelForBaseCRUDCreateSchema(
            name='Test', email='test@example.com'
        )

        with pytest.raises(
            ValueError, match='Необходимо указать хотя бы одно поле для поиска'
        ):
            await crud.upsert(async_session, upsert_data, unique_fields=[])

    async def test_upsert_missing_unique_field_raises_error(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест ошибки при отсутствии unique_field в данных."""
        upsert_data = ModelForBaseCRUDCreateSchema(
            name='Test', email='test@example.com'
        )

        with pytest.raises(
            ValueError, match="Поле 'nonexistent' не найдено в данных объекта"
        ):
            await crud.upsert(async_session, upsert_data, unique_fields=['nonexistent'])


class TestCRUDBulkUpsert:
    """Тесты для метода bulk_upsert."""

    async def test_bulk_upsert_mixed_operations(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест массового upsert с созданием и обновлением."""
        existing_obj = created_objects[0]

        upsert_data = [
            # Обновить существующий
            ModelForBaseCRUDCreateSchema(
                name='Updated Existing', email=existing_obj.email, description='Updated'
            ),
            # Создать новый
            ModelForBaseCRUDCreateSchema(
                name='New User 1', email='new1@example.com', description='New'
            ),
            # Создать еще один новый
            ModelForBaseCRUDCreateSchema(
                name='New User 2', email='new2@example.com', description='New'
            ),
        ]

        results, created_count, updated_count = await crud.bulk_upsert(
            async_session, upsert_data, unique_fields=['email']
        )

        assert len(results) == 3
        assert created_count == 2  # Два новых
        assert updated_count == 1  # Один обновлен

        # Проверяем обновленный объект
        updated_obj = next(r for r in results if r.id == existing_obj.id)
        assert updated_obj.name == 'Updated Existing'

    async def test_bulk_upsert_empty_list(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест bulk_upsert с пустым списком."""
        results, created, updated = await crud.bulk_upsert(
            async_session, [], unique_fields=['email']
        )

        assert results == []
        assert created == 0
        assert updated == 0


class TestCRUDDelete:
    """Тесты для метода delete."""

    async def test_delete_success(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест успешного удаления объекта."""
        test_obj = created_objects[0]
        object_id = test_obj.id

        await crud.delete(async_session, test_obj)

        # Проверяем что объект удален
        deleted_obj = await crud.get(async_session, {'id': object_id})
        assert deleted_obj is None


class TestCRUDDeleteByFields:
    """Тесты для метода delete_by_fields."""

    async def test_delete_by_fields_success(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест удаления объектов по полям."""
        deleted_count = await crud.delete_by_fields(async_session, {'is_active': False})

        assert deleted_count == 1  # Один неактивный пользователь

        # Проверяем что неактивные пользователи удалены
        inactive_users = await crud.get_multi(async_session, {'is_active': False})
        assert len(inactive_users) == 0

    async def test_delete_by_fields_multiple_objects(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест удаления нескольких объектов."""
        deleted_count = await crud.delete_by_fields(async_session, {'user_id': 1})

        assert deleted_count == 2  # Два пользователя с user_id=1

        # Проверяем что пользователи с user_id=1 удалены
        users_with_id_1 = await crud.get_multi(async_session, {'user_id': 1})
        assert len(users_with_id_1) == 0

    async def test_delete_by_fields_no_objects_found(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест удаления когда объекты не найдены."""
        deleted_count = await crud.delete_by_fields(
            async_session, {'email': 'nonexistent@example.com'}
        )

        assert deleted_count == 0

    async def test_delete_by_fields_without_filters_raises_error(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест ошибки при удалении без фильтров."""
        with pytest.raises(
            ValueError, match='Необходимо указать хотя бы одно поле для удаления'
        ):
            await crud.delete_by_fields(async_session, {})


class TestCRUDDeleteByFieldsOr404:
    """Тесты для метода delete_by_fields_or_404."""

    async def test_delete_by_fields_or_404_success(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест успешного удаления через delete_by_fields_or_404."""
        test_obj = created_objects[0]

        deleted_count = await crud.delete_by_fields_or_404(
            async_session, {'id': test_obj.id}
        )

        assert deleted_count == 1

        # Проверяем что объект удален
        deleted_obj = await crud.get(async_session, {'id': test_obj.id})
        assert deleted_obj is None

    async def test_delete_by_fields_or_404_not_found_raises_404(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест 404 ошибки при удалении несуществующего объекта."""
        with pytest.raises(HTTPException) as exc_info:
            await crud.delete_by_fields_or_404(async_session, {'id': 999})

        assert exc_info.value.status_code == HTTPStatus.NOT_FOUND
        assert (
            'No ModelForBaseCRUD found to delete with id=999' in exc_info.value.detail
        )

    async def test_delete_by_fields_or_404_custom_detail(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест кастомного сообщения об ошибке."""
        custom_detail = 'Пользователь для удаления не найден'

        with pytest.raises(HTTPException) as exc_info:
            await crud.delete_by_fields_or_404(
                async_session, {'id': 999}, _detail=custom_detail
            )

        assert exc_info.value.status_code == HTTPStatus.NOT_FOUND
        assert exc_info.value.detail == custom_detail


class TestCRUDDeleteByCondition:
    """Тесты для метода delete_by_condition."""

    async def test_delete_by_condition_success(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест удаления объектов по условиям."""
        from sqlalchemy import and_

        deleted_count = await crud.delete_by_condition(
            async_session,
            and_(
                ModelForBaseCRUD.user_id == 1,
                ModelForBaseCRUD.is_active.is_(True),
            ),
        )

        assert deleted_count == 2  # Два активных пользователя с user_id=1

        # Проверяем что объекты удалены
        remaining_users = await crud.get_multi(
            async_session, {'user_id': 1, 'is_active': True}
        )
        assert len(remaining_users) == 0

    async def test_delete_by_condition_no_objects_found(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест удаления когда объекты не найдены."""
        from sqlalchemy import and_

        deleted_count = await crud.delete_by_condition(
            async_session,
            and_(
                ModelForBaseCRUD.email == 'nonexistent@example.com',
                ModelForBaseCRUD.is_active.is_(True),
            ),
        )

        assert deleted_count == 0

    async def test_delete_by_condition_without_conditions_raises_error(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест ошибки при удалении без условий."""
        with pytest.raises(
            ValueError, match='Необходимо указать хотя бы одно условие для удаления'
        ):
            await crud.delete_by_condition(async_session)


class TestCRUDDeleteByConditionOr404:
    """Тесты для метода delete_by_condition_or_404."""

    async def test_delete_by_condition_or_404_success(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест успешного удаления через delete_by_condition_or_404."""
        from sqlalchemy import and_

        deleted_count = await crud.delete_by_condition_or_404(
            async_session,
            and_(
                ModelForBaseCRUD.user_id == 1,
                ModelForBaseCRUD.is_active.is_(True),
            ),
        )

        assert deleted_count == 2  # Два активных пользователя с user_id=1

        # Проверяем что объекты удалены
        remaining_users = await crud.get_multi(
            async_session, {'user_id': 1, 'is_active': True}
        )
        assert len(remaining_users) == 0

    async def test_delete_by_condition_or_404_not_found_raises_404(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест 404 ошибки при удалении несуществующих объектов."""
        from sqlalchemy import and_

        with pytest.raises(HTTPException) as exc_info:
            await crud.delete_by_condition_or_404(
                async_session,
                and_(
                    ModelForBaseCRUD.email == 'nonexistent@example.com',
                    ModelForBaseCRUD.is_active.is_(True),
                ),
            )

        assert exc_info.value.status_code == HTTPStatus.NOT_FOUND
        assert (
            'No ModelForBaseCRUD found to delete matching conditions'
            in exc_info.value.detail
        )

    async def test_delete_by_condition_or_404_custom_detail(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест кастомного сообщения об ошибке."""
        from sqlalchemy import and_

        custom_detail = 'Пользователи для удаления не найдены'

        with pytest.raises(HTTPException) as exc_info:
            await crud.delete_by_condition_or_404(
                async_session,
                and_(
                    ModelForBaseCRUD.email == 'nonexistent@example.com',
                    ModelForBaseCRUD.is_active.is_(True),
                ),
                _detail=custom_detail,
            )

        assert exc_info.value.status_code == HTTPStatus.NOT_FOUND
        assert exc_info.value.detail == custom_detail


class TestCRUDBulkDeleteByIds:
    """Тесты для метода bulk_delete_by_ids."""

    async def test_bulk_delete_by_ids_success(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест массового удаления по ID."""
        obj_ids = [obj.id for obj in created_objects[:2]]

        deleted_count = await crud.bulk_delete_by_ids(async_session, obj_ids)

        assert deleted_count == 2

        # Проверяем что объекты удалены
        for obj_id in obj_ids:
            obj = await crud.get(async_session, {'id': obj_id})
            assert obj is None

    async def test_bulk_delete_by_ids_empty_list(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест массового удаления с пустым списком ID."""
        deleted_count = await crud.bulk_delete_by_ids(async_session, [])

        assert deleted_count == 0

    async def test_bulk_delete_by_ids_nonexistent_ids(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест удаления несуществующих ID."""
        deleted_count = await crud.bulk_delete_by_ids(async_session, [999, 1000])

        assert deleted_count == 0


class TestCRUDBulkDeleteByFieldValues:
    """Тесты для метода bulk_delete_by_field_values."""

    async def test_bulk_delete_by_field_values_success(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест массового удаления по значениям поля."""
        emails = [obj.email for obj in created_objects[:2]]

        deleted_count = await crud.bulk_delete_by_field_values(
            async_session, 'email', emails
        )

        assert deleted_count == 2

        # Проверяем что объекты удалены
        for email in emails:
            obj = await crud.get(async_session, {'email': email})
            assert obj is None

    async def test_bulk_delete_by_field_values_empty_list(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест массового удаления с пустым списком значений."""
        deleted_count = await crud.bulk_delete_by_field_values(
            async_session, 'email', []
        )

        assert deleted_count == 0

    async def test_bulk_delete_by_field_values_nonexistent_field(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест ошибки при несуществующем поле."""
        with pytest.raises(
            AttributeError,
            match="Поле 'nonexistent' не существует в модели ModelForBaseCRUD",
        ):
            await crud.bulk_delete_by_field_values(
                async_session, 'nonexistent', ['value1', 'value2']
            )


class TestCRUDBulkDeleteAllByFields:
    """Тесты для метода bulk_delete_all_by_fields."""

    async def test_bulk_delete_all_by_fields_success(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест массового удаления всех объектов по полям."""
        total_deleted = await crud.bulk_delete_all_by_fields(
            async_session, {'is_active': False}, batch_size=1
        )

        assert total_deleted == 1  # Один неактивный пользователь

        # Проверяем что объекты удалены
        remaining_users = await crud.get_multi(async_session, {'is_active': False})
        assert len(remaining_users) == 0

    async def test_bulk_delete_all_by_fields_no_objects_found(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест удаления когда объекты не найдены."""
        total_deleted = await crud.bulk_delete_all_by_fields(
            async_session, {'email': 'nonexistent@example.com'}, batch_size=1
        )

        assert total_deleted == 0

    async def test_bulk_delete_all_by_fields_without_filters_raises_error(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест ошибки при удалении без фильтров."""
        with pytest.raises(ValueError, match='Необходимо указать условия для удаления'):
            await crud.bulk_delete_all_by_fields(async_session, {}, batch_size=1)


class TestCRUDBulkDeleteAllByCondition:
    """Тесты для метода bulk_delete_all_by_condition."""

    async def test_bulk_delete_all_by_condition_success(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест массового удаления всех объектов по условиям."""
        from sqlalchemy import and_

        total_deleted = await crud.bulk_delete_all_by_condition(
            async_session,
            and_(
                ModelForBaseCRUD.user_id == 1,
                ModelForBaseCRUD.is_active.is_(True),
            ),
            batch_size=1,
        )

        assert total_deleted == 2  # Два активных пользователя с user_id=1

        # Проверяем что объекты удалены
        remaining_users = await crud.get_multi(
            async_session, {'user_id': 1, 'is_active': True}
        )
        assert len(remaining_users) == 0

    async def test_bulk_delete_all_by_condition_no_objects_found(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест удаления когда объекты не найдены."""
        from sqlalchemy import and_

        total_deleted = await crud.bulk_delete_all_by_condition(
            async_session,
            and_(
                ModelForBaseCRUD.email == 'nonexistent@example.com',
                ModelForBaseCRUD.is_active.is_(True),
            ),
            batch_size=1,
        )

        assert total_deleted == 0

    async def test_bulk_delete_all_by_condition_without_conditions_raises_error(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест ошибки при удалении без условий."""
        with pytest.raises(ValueError, match='Необходимо указать условия для удаления'):
            await crud.bulk_delete_all_by_condition(async_session, batch_size=1)


class TestCRUDSoftDelete:
    """Тесты для метода soft_delete."""

    async def test_soft_delete_success(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест успешного мягкого удаления объекта."""
        test_obj = created_objects[0]

        result = await crud.soft_delete(async_session, test_obj)

        assert result.is_deleted is True
        assert result.deleted_at is not None
        assert result.id == test_obj.id

    async def test_soft_delete_keeps_object_in_db(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест что мягко удаленный объект остается в БД."""
        test_obj = created_objects[0]

        await crud.soft_delete(async_session, test_obj)

        found = await crud.get(async_session, {'id': test_obj.id})
        assert found is not None
        assert found.is_deleted is True

    async def test_soft_delete_with_custom_fields(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест мягкого удаления с кастомными полями."""
        test_obj = created_objects[0]

        result = await crud.soft_delete(
            async_session,
            test_obj,
            delete_field='status',
            delete_value='deleted',
            deleted_at_field='archived_at',
            deleted_by_field='archived_by',
            user_id=999,
        )

        assert result.status == 'deleted'
        assert result.archived_at is not None
        assert result.archived_by == 999
        assert result.is_deleted is False

    async def test_soft_delete_without_deleted_at_field(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест мягкого удаления без установки времени удаления."""
        test_obj = created_objects[0]

        result = await crud.soft_delete(
            async_session,
            test_obj,
            deleted_at_field=None,
        )

        assert result.is_deleted is True
        assert result.deleted_at is None

    async def test_soft_delete_deleted_by_ignored_without_user_id(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест что deleted_by_field игнорируется без user_id."""
        test_obj = created_objects[0]

        result = await crud.soft_delete(
            async_session,
            test_obj,
            deleted_by_field='archived_by',
        )

        assert result.is_deleted is True
        assert result.archived_by is None

    async def test_soft_delete_nonexistent_field_raises_error(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест ошибки при несуществующем поле удаления."""
        test_obj = created_objects[0]

        with pytest.raises(
            AttributeError, match="Поле 'nonexistent' не существует в модели"
        ):
            await crud.soft_delete(async_session, test_obj, delete_field='nonexistent')

    async def test_soft_delete_nonexistent_deleted_at_field_raises_error(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест ошибки при несуществующем поле времени удаления."""
        test_obj = created_objects[0]

        with pytest.raises(
            AttributeError, match="Поле 'nonexistent' не существует в модели"
        ):
            await crud.soft_delete(
                async_session,
                test_obj,
                deleted_at_field='nonexistent',
            )


class TestCRUDSoftDeleteByFields:
    """Тесты для метода soft_delete_by_fields."""

    async def test_soft_delete_by_fields_success(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест мягкого удаления по простым условиям."""
        deleted_count = await crud.soft_delete_by_fields(
            async_session,
            {'is_active': True},
        )

        assert deleted_count == 2

        deleted_objects = await crud.get_multi(async_session, {'is_deleted': True})
        assert len(deleted_objects) == 2
        for obj in deleted_objects:
            assert obj.deleted_at is not None

    async def test_soft_delete_by_fields_with_user_id(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест мягкого удаления с указанием пользователя."""
        deleted_count = await crud.soft_delete_by_fields(
            async_session,
            {'email': created_objects[0].email},
            deleted_by_field='archived_by',
            user_id=777,
        )

        assert deleted_count == 1

        obj = await crud.get(async_session, {'id': created_objects[0].id})
        assert obj is not None
        assert obj.archived_by == 777

    async def test_soft_delete_by_fields_no_matches(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест мягкого удаления когда объекты не найдены."""
        deleted_count = await crud.soft_delete_by_fields(
            async_session,
            {'email': 'nonexistent@example.com'},
        )

        assert deleted_count == 0

    async def test_soft_delete_by_fields_without_filters_raises_error(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест ошибки при мягком удалении без фильтров."""
        with pytest.raises(
            ValueError, match='Необходимо указать хотя бы одно поле для фильтрации'
        ):
            await crud.soft_delete_by_fields(async_session, {})

    async def test_soft_delete_by_fields_nonexistent_field_raises_error(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест ошибки при несуществующем поле удаления."""
        with pytest.raises(
            AttributeError, match="Поле 'nonexistent' не существует в модели"
        ):
            await crud.soft_delete_by_fields(
                async_session,
                {'is_active': True},
                delete_field='nonexistent',
            )


class TestCRUDSoftDeleteByCondition:
    """Тесты для метода soft_delete_by_condition."""

    async def test_soft_delete_by_condition_success(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест мягкого удаления по сложным условиям."""
        from sqlalchemy import or_

        deleted_count = await crud.soft_delete_by_condition(
            async_session,
            or_(
                ModelForBaseCRUD.email == created_objects[0].email,
                ModelForBaseCRUD.email == created_objects[1].email,
            ),
        )

        assert deleted_count == 2

        deleted_objects = await crud.get_multi(async_session, {'is_deleted': True})
        assert len(deleted_objects) == 2

    async def test_soft_delete_by_condition_with_custom_fields(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест мягкого удаления по условиям с кастомными полями."""
        deleted_count = await crud.soft_delete_by_condition(
            async_session,
            ModelForBaseCRUD.is_active.is_(False),
            delete_field='status',
            delete_value='archived',
            deleted_at_field='archived_at',
        )

        assert deleted_count == 1

        obj = await crud.get(async_session, {'status': 'archived'})
        assert obj is not None
        assert obj.archived_at is not None
        assert obj.is_deleted is False

    async def test_soft_delete_by_condition_without_conditions_raises_error(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест ошибки при мягком удалении без условий."""
        with pytest.raises(
            ValueError, match='Необходимо указать хотя бы одно условие для удаления'
        ):
            await crud.soft_delete_by_condition(async_session)


class TestCRUDRestore:
    """Тесты для метода restore."""

    async def test_restore_success(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест успешного восстановления мягко удаленного объекта."""
        test_obj = created_objects[0]
        await crud.soft_delete(async_session, test_obj)

        result = await crud.restore(async_session, test_obj)

        assert result.is_deleted is False
        assert result.deleted_at is None
        assert result.id == test_obj.id

    async def test_restore_with_custom_fields(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест восстановления с кастомными полями."""
        test_obj = created_objects[0]
        await crud.soft_delete(
            async_session,
            test_obj,
            delete_field='status',
            delete_value='deleted',
            deleted_at_field='archived_at',
            deleted_by_field='archived_by',
            user_id=999,
        )

        result = await crud.restore(
            async_session,
            test_obj,
            delete_field='status',
            restore_value='active',
            deleted_at_field='archived_at',
            deleted_by_field='archived_by',
        )

        assert result.status == 'active'
        assert result.archived_at is None
        assert result.archived_by is None

    async def test_restore_nonexistent_field_raises_error(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест ошибки при несуществующем поле удаления."""
        test_obj = created_objects[0]

        with pytest.raises(
            AttributeError, match="Поле 'nonexistent' не существует в модели"
        ):
            await crud.restore(async_session, test_obj, delete_field='nonexistent')


class TestCRUDGetWithDeleted:
    """Тесты для метода get_with_deleted."""

    async def test_get_with_deleted_success(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест получения мягко удаленного объекта."""
        test_obj = created_objects[0]
        await crud.soft_delete(async_session, test_obj)

        result = await crud.get_with_deleted(async_session, {'id': test_obj.id})

        assert result is not None
        assert result.id == test_obj.id
        assert result.is_deleted is True

    async def test_get_with_deleted_filters_by_deleted_flag(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
        created_objects: list[ModelForBaseCRUD],
    ) -> None:
        """Тест поиска именно удаленного объекта по флагу."""
        test_obj = created_objects[0]
        await crud.soft_delete(async_session, test_obj)

        result = await crud.get_with_deleted(
            async_session,
            {'id': test_obj.id, 'is_deleted': True},
        )
        assert result is not None

        not_deleted = await crud.get_with_deleted(
            async_session,
            {'id': created_objects[1].id, 'is_deleted': True},
        )
        assert not_deleted is None

    async def test_get_with_deleted_not_found(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест получения несуществующего объекта."""
        result = await crud.get_with_deleted(async_session, {'id': 999})

        assert result is None

    async def test_get_with_deleted_without_filters_raises_error(
        self,
        async_session: AsyncSession,
        crud: CRUDBase[ModelForBaseCRUD],
    ) -> None:
        """Тест ошибки при поиске без фильтров."""
        with pytest.raises(
            ValueError, match='Необходимо указать хотя бы одно поле для поиска'
        ):
            await crud.get_with_deleted(async_session, {})
