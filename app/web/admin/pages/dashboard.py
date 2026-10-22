"""Панель администратора: сводные числа."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_async_session
from app.crud.admin.user import admin_user_crud
from app.web.admin.context import AdminContext, admin_context
from app.web.dependencies import web_require_moder
from app.web.templates import render

router = APIRouter(prefix='/admin', dependencies=[Depends(web_require_moder)])


@router.get('', response_class=HTMLResponse)
async def dashboard(
    request: Request,
    context: AdminContext = Depends(admin_context),
    session: AsyncSession = Depends(get_async_session),
):
    return render(
        request,
        'admin/pages/dashboard.html',
        {
            **context.as_template_context('dashboard'),
            'users_total': await admin_user_crud.count(session),
        },
    )
