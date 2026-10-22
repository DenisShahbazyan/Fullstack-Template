from http import HTTPStatus
from typing import Callable

from fastapi import Depends, HTTPException

from app.core.auth.users import current_user
from app.models.user import User, UserRoleEnum


def require_role(*allowed_roles: UserRoleEnum) -> Callable[..., User]:
    """Строит зависимость, пропускающую только пользователей с одной из ролей."""

    def dependency(user: User = Depends(current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail='Недостаточно прав',
            )
        return user

    return dependency


require_admin = require_role(UserRoleEnum.ADMIN)
require_moder_or_higher = require_role(UserRoleEnum.ADMIN, UserRoleEnum.MODER)
