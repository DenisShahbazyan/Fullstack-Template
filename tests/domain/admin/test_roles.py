import pytest

from app.domain.admin.errors import AdminRoleAssignmentError, SelfRoleChangeError
from app.domain.admin.roles import ensure_role_change_allowed
from app.models.user import UserRoleEnum


def test_admin_can_grant_moder_role() -> None:
    ensure_role_change_allowed(1, UserRoleEnum.ADMIN, 2, UserRoleEnum.MODER)


def test_role_change_of_self_is_rejected() -> None:
    with pytest.raises(SelfRoleChangeError):
        ensure_role_change_allowed(1, UserRoleEnum.ADMIN, 1, UserRoleEnum.USER)


@pytest.mark.parametrize('new_role', [UserRoleEnum.ADMIN, UserRoleEnum.MODER])
def test_moder_cannot_grant_staff_roles(new_role: UserRoleEnum) -> None:
    with pytest.raises(AdminRoleAssignmentError):
        ensure_role_change_allowed(1, UserRoleEnum.MODER, 2, new_role)
