"""Журнал действий администрации."""

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_async_session
from app.crud.admin.audit_log import admin_audit_log_crud
from app.web.admin.context import AdminContext, admin_context
from app.web.dependencies import web_require_admin
from app.web.pagination import PAGE_SIZE, build_pagination
from app.web.templates import render

router = APIRouter(prefix='/admin', dependencies=[Depends(web_require_admin)])


@router.get('/audit', response_class=HTMLResponse)
async def audit_list(
    request: Request,
    page: int = Query(1, ge=1),
    context: AdminContext = Depends(admin_context),
    session: AsyncSession = Depends(get_async_session),
):
    records = await admin_audit_log_crud.get_recent(
        session, limit=PAGE_SIZE, offset=(page - 1) * PAGE_SIZE
    )
    total = await admin_audit_log_crud.count(session)
    return render(
        request,
        'admin/pages/audit.html',
        {
            **context.as_template_context('audit'),
            'records': records,
            'page_data': build_pagination('/admin/audit', page, total),
        },
    )
