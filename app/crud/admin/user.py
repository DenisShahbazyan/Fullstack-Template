from typing import Any, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud._base import CRUDBase
from app.models.user import User, UserRoleEnum

SelectT = TypeVar('SelectT', bound=Select[Any])


class CRUDAdminUser(CRUDBase[User]):
    """Список пользователей и их срезы — операции, которых нет в публичной стороне."""

    def _filtered(
        self,
        query: SelectT,
        role: UserRoleEnum | None,
        search: str | None,
    ) -> SelectT:
        if role is not None:
            query = query.where(self.model.role == role)
        if search:
            pattern = f'%{search.lower()}%'
            query = query.where(
                func.lower(self.model.email).like(pattern)
                | func.lower(self.model.last_name).like(pattern)
                | func.lower(self.model.first_name).like(pattern),
            )
        return query

    async def get_for_admin(
        self,
        async_session: AsyncSession,
        role: UserRoleEnum | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[User]:
        """Пользователи для админского списка, от новых к старым."""
        query = self._filtered(select(self.model), role, search)
        query = query.order_by(self.model.created_at.desc()).limit(limit).offset(offset)
        result = await async_session.execute(query)
        return list(result.scalars().all())

    async def count_for_admin(
        self,
        async_session: AsyncSession,
        role: UserRoleEnum | None = None,
        search: str | None = None,
    ) -> int:
        """Число пользователей под теми же фильтрами, что и `get_for_admin`."""
        query = self._filtered(select(func.count(self.model.id)), role, search)
        result = await async_session.execute(query)
        return int(result.scalar_one())


admin_user_crud = CRUDAdminUser(User)
