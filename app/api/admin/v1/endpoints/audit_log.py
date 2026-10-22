from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ADMIN_ONLY
from app.core.db import get_async_session
from app.crud.admin.audit_log import admin_audit_log_crud
from app.schemas.admin.v1.audit_log import AuditLogSchema

router = APIRouter(prefix='/audit-log', tags=['admin:audit'])


@router.get('', summary=ADMIN_ONLY + 'Журнал действий администрации')
async def get_audit_log(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    async_session: AsyncSession = Depends(get_async_session),
) -> list[AuditLogSchema]:
    records = await admin_audit_log_crud.get_recent(
        async_session, limit=limit, offset=offset
    )
    return [AuditLogSchema.model_validate(record) for record in records]
