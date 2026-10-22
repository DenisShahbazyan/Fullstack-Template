from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin.audit import OBJECT_USER, record_action
from app.core.admin.permissions import require_admin
from app.core.constants import ADMIN_ONLY
from app.core.db import get_async_session
from app.crud.admin.user import admin_user_crud
from app.domain.admin.errors import UserNotFoundError
from app.domain.admin.roles import ensure_role_change_allowed
from app.models.audit_log import AuditActionEnum
from app.models.user import User, UserRoleEnum
from app.schemas.admin.v1.user import UserAdminSchema, UserRoleUpdateSchema

router = APIRouter(prefix='/users', tags=['admin:user'])


@router.get('', summary=ADMIN_ONLY + 'Список пользователей')
async def get_users(
    role: UserRoleEnum | None = Query(None),
    search: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    async_session: AsyncSession = Depends(get_async_session),
) -> list[UserAdminSchema]:
    users = await admin_user_crud.get_for_admin(
        async_session, role=role, search=search, limit=limit, offset=offset
    )
    return [UserAdminSchema.model_validate(user) for user in users]


@router.patch('/{user_id}/role', summary=ADMIN_ONLY + 'Смена роли пользователя')
async def change_user_role(
    user_id: int,
    body: UserRoleUpdateSchema,
    actor: User = Depends(require_admin),
    async_session: AsyncSession = Depends(get_async_session),
) -> UserAdminSchema:
    user = await admin_user_crud.get(async_session, {'id': user_id})
    if user is None:
        raise UserNotFoundError()
    ensure_role_change_allowed(actor.id, actor.role, user.id, body.role)
    record_action(
        async_session,
        actor.id,
        AuditActionEnum.USER_ROLE_CHANGE,
        OBJECT_USER,
        user.id,
        {'from': user.role.value, 'to': body.role.value},
    )
    user.role = body.role
    await async_session.commit()
    return UserAdminSchema.model_validate(user)
