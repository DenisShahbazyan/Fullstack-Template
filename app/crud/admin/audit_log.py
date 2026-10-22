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


admin_audit_log_crud = CRUDAdminAuditLog(AuditLog)
