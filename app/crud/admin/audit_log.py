from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud._base import CRUDBase
from app.models.audit_log import AuditLog


class CRUDAdminAuditLog(CRUDBase[AuditLog]):
    async def get_recent(
        self,
        async_session: AsyncSession,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditLog]:
        """Записи журнала от новых к старым, с автором действия."""
        query = (
            select(self.model)
            .options(selectinload(self.model.actor_user))
            .order_by(self.model.created_at.desc(), self.model.id.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await async_session.execute(query)
        return list(result.scalars().all())

    async def get_for_object(
        self, async_session: AsyncSession, object_type: str, object_id: int
    ) -> list[AuditLog]:
        """История действий с одним объектом, от старых к новым, с автором."""
        query = (
            select(self.model)
            .where(
                self.model.object_type == object_type,
                self.model.object_id == object_id,
            )
            .options(selectinload(self.model.actor_user))
            .order_by(self.model.created_at, self.model.id)
        )
        return list((await async_session.scalars(query)).all())


admin_audit_log_crud = CRUDAdminAuditLog(AuditLog)
