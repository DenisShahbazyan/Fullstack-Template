from typing import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud._base import CRUDBase
from tests.utils.crud.base import ModelForBaseCRUD


@pytest.fixture
def crud() -> CRUDBase:
    """Фикстура для CRUD класса."""
    return CRUDBase(ModelForBaseCRUD)


TEST_DATA = [
    {
        'name': 'Test User 1',
        'email': 'test1@example.com',
        'description': 'First test user',
        'is_active': True,
        'user_id': 1,
    },
    {
        'name': 'Test User 2',
        'email': 'test2@example.com',
        'description': 'Second test user',
        'is_active': False,
        'user_id': 2,
    },
    {
        'name': 'Test User 3',
        'email': 'test3@example.com',
        'description': 'Third test user',
        'is_active': True,
        'user_id': 1,
    },
]


@pytest.fixture
async def created_objects(
    async_session: AsyncSession,
    crud: CRUDBase[ModelForBaseCRUD],
) -> AsyncGenerator[list[ModelForBaseCRUD], None]:
    """
    Создает тестовые объекты в БД.
    Возвращает список созданных объектов.
    Очищает БД после тестов.
    """
    objects = []
    for data in TEST_DATA:
        obj = ModelForBaseCRUD(**data)
        async_session.add(obj)
        objects.append(obj)

    await async_session.commit()

    for obj in objects:
        await async_session.refresh(obj)

    yield objects

    for obj in objects:
        await async_session.delete(obj)
    await async_session.commit()
