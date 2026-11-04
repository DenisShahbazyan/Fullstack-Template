import asyncio

from fastapi import Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_users import (
    BaseUserManager,
    IntegerIDMixin,
    InvalidPasswordException,
    exceptions,
    schemas,
)

from app.domain.auth.password import MIN_PASSWORD_LENGTH
from app.models.user import User


class UserManager(IntegerIDMixin, BaseUserManager[User, int]):
    """Логин по email — штатное поведение fastapi-users, но хеш пароля — в потоке.

    Базовый менеджер считает Argon2 прямо в цикле событий: десятки миллисекунд
    на каждый вход, и все запросы процесса ждут. argon2-cffi отпускает GIL,
    поэтому в потоке хеш считается параллельно. Ещё синхронно хешируют базовые
    `update` с паролем и сброс пароля по ссылке — понадобятся, переопределить.
    """

    async def validate_password(
        self,
        password: str,
        user: schemas.BaseUserCreate | User,
    ) -> None:
        if len(password) < MIN_PASSWORD_LENGTH:
            raise InvalidPasswordException(
                reason=f'Пароль должен быть не короче {MIN_PASSWORD_LENGTH} символов',
            )

    async def hash_password(self, password: str) -> str:
        return await asyncio.to_thread(self.password_helper.hash, password)

    async def authenticate(
        self,
        credentials: OAuth2PasswordRequestForm,
    ) -> User | None:
        try:
            user = await self.get_by_email(credentials.username)
        except exceptions.UserNotExists:
            # Хешируем впустую, чтобы время ответа не выдавало существование
            # пользователя — так же, как это делает базовый менеджер.
            await self.hash_password(credentials.password)
            return None
        verified, updated_hash = await asyncio.to_thread(
            self.password_helper.verify_and_update,
            credentials.password,
            user.hashed_password,
        )
        if not verified:
            return None
        if updated_hash is not None:
            await self.user_db.update(user, {'hashed_password': updated_hash})
        return user

    async def create(
        self,
        user_create: schemas.UC,
        safe: bool = False,
        request: Request | None = None,
    ) -> User:
        await self.validate_password(user_create.password, user_create)
        if await self.user_db.get_by_email(user_create.email) is not None:
            raise exceptions.UserAlreadyExists()
        user_dict = (
            user_create.create_update_dict()
            if safe
            else user_create.create_update_dict_superuser()
        )
        user_dict['hashed_password'] = await self.hash_password(
            user_dict.pop('password')
        )
        user = await self.user_db.create(user_dict)
        await self.on_after_register(user, request)
        return user
