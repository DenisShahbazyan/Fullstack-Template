"""Пользователи: список с фильтром по роли и поиском, смена роли."""

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin.audit import OBJECT_USER, record_action
from app.core.csrf import csrf_validate
from app.core.db import get_async_session
from app.crud.admin.user import admin_user_crud
from app.domain.admin.errors import UserNotFoundError
from app.domain.admin.roles import ensure_role_change_allowed
from app.models.audit_log import AuditActionEnum
from app.models.user import User, UserRoleEnum
from app.web.admin.context import AdminContext, admin_context
from app.web.dependencies import web_require_admin
from app.web.pagination import PAGE_SIZE, build_pagination
from app.web.templates import render
from app.web.toasts import redirect_with_toast

router = APIRouter(prefix='/admin', dependencies=[Depends(web_require_admin)])
actions_router = APIRouter(dependencies=[Depends(csrf_validate)])


def _list_url(role: UserRoleEnum | None, search: str | None) -> str:
    params = []
    if role is not None:
        params.append(f'role={role.value}')
    if search:
        params.append(f'search={search}')
    return '/admin/users' + ('?' + '&'.join(params) if params else '')


@router.get('/users', response_class=HTMLResponse)
async def users_list(
    request: Request,
    role: UserRoleEnum | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    context: AdminContext = Depends(admin_context),
    session: AsyncSession = Depends(get_async_session),
):
    users = await admin_user_crud.get_for_admin(
        session,
        role=role,
        search=search,
        limit=PAGE_SIZE,
        offset=(page - 1) * PAGE_SIZE,
    )
    total = await admin_user_crud.count_for_admin(session, role=role, search=search)
    return render(
        request,
        'admin/pages/users.html',
        {
            **context.as_template_context('users'),
            'users': users,
            'roles': list(UserRoleEnum),
            'selected_role': role,
            'search': search or '',
            'page_data': build_pagination(_list_url(role, search), page, total),
        },
    )


@actions_router.post('/users/{user_id}/role')
async def change_user_role(
    user_id: int,
    role: UserRoleEnum = Form(...),
    actor: User = Depends(web_require_admin),
    session: AsyncSession = Depends(get_async_session),
) -> RedirectResponse:
    user = await admin_user_crud.get(session, {'id': user_id})
    if user is None:
        raise UserNotFoundError()
    ensure_role_change_allowed(actor.id, actor.role, user.id, role)
    record_action(
        session,
        actor.id,
        AuditActionEnum.USER_ROLE_CHANGE,
        OBJECT_USER,
        user.id,
        {'from': user.role.value, 'to': role.value},
    )
    user.role = role
    await session.commit()
    return redirect_with_toast('/admin/users', 'Роль изменена', kind='success')


router.include_router(actions_router)
