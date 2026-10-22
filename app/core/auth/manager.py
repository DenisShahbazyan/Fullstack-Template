from fastapi_users import (
    BaseUserManager,
    IntegerIDMixin,
    InvalidPasswordException,
    schemas,
)

from app.domain.auth.password import MIN_PASSWORD_LENGTH
from app.models.user import User


class UserManager(IntegerIDMixin, BaseUserManager[User, int]):
    """Логин по email — штатное поведение fastapi-users."""

    async def validate_password(
        self,
        password: str,
        user: schemas.BaseUserCreate | User,
    ) -> None:
        if len(password) < MIN_PASSWORD_LENGTH:
            raise InvalidPasswordException(
                reason=f'Пароль должен быть не короче {MIN_PASSWORD_LENGTH} символов',
            )
