"""Правила смены роли пользователя администрацией."""

from app.domain.admin.errors import AdminRoleAssignmentError, SelfRoleChangeError
from app.models.user import UserRoleEnum

_STAFF_ROLES = frozenset({UserRoleEnum.ADMIN, UserRoleEnum.MODER})


def ensure_role_change_allowed(
    actor_user_id: int,
    actor_role: UserRoleEnum,
    target_user_id: int,
    new_role: UserRoleEnum,
) -> None:
    """Проверяет право сменить роль: не себе и не выше собственных полномочий.

    Raises:
        SelfRoleChangeError: если пользователь меняет роль сам себе.
        AdminRoleAssignmentError: если не-администратор выдаёт роль персонала.
    """
    if actor_user_id == target_user_id:
        raise SelfRoleChangeError()
    if actor_role is not UserRoleEnum.ADMIN and new_role in _STAFF_ROLES:
        raise AdminRoleAssignmentError()
