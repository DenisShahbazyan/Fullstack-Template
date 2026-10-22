"""Заведение пользователя из консоли: первый администратор, тестовые аккаунты.

    uv run python -m scripts.users.create_user admin@example.com --role admin
    uv run python -m scripts.users.create_user user@example.com --password secret12345

На сервере:

    sudo docker compose --env-file .env.docker exec web \\
        python -m scripts.users.create_user admin@example.com --role admin

Пароль, если не задан, генерируется и печатается в конце.
"""

from __future__ import annotations

import argparse
import asyncio

from fastapi_users.exceptions import InvalidPasswordException, UserAlreadyExists
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from pydantic import ValidationError

from app.core.auth.manager import UserManager
from app.core.db import AsyncSessionLocal
from app.core.logs import setup_logging
from app.domain.auth.password import MIN_PASSWORD_LENGTH, generate_password
from app.models.user import User, UserRoleEnum
from app.schemas.public.v1.user import UserCreateSchema


async def create_user(
    email: str,
    password: str,
    first_name: str | None,
    role: UserRoleEnum,
) -> User:
    """Заводит пользователя тем же путём, что и сайт.

    Создание идёт через `UserManager`, а не прямым INSERT: так работают те же
    хеширование пароля, правила пароля и проверка уникальности.
    """
    async with AsyncSessionLocal() as session:
        manager = UserManager(SQLAlchemyUserDatabase(session, User))
        payload = UserCreateSchema(
            email=email, password=password, first_name=first_name
        )
        user = await manager.create(payload, safe=True)
        if role is not UserRoleEnum.USER:
            user.role = role
            await session.commit()
        return user


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Создать пользователя.')
    parser.add_argument('email', help='email — он же логин')
    parser.add_argument(
        '--password',
        help=f'пароль от {MIN_PASSWORD_LENGTH} символов; по умолчанию случайный',
    )
    parser.add_argument('--name', help='имя')
    parser.add_argument(
        '--role',
        choices=[item.value for item in UserRoleEnum],
        default=UserRoleEnum.USER.value,
        help='роль',
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    setup_logging()
    password = args.password or generate_password()

    try:
        user = asyncio.run(
            create_user(
                email=args.email,
                password=password,
                first_name=args.name,
                role=UserRoleEnum(args.role),
            ),
        )
    except (ValidationError, InvalidPasswordException) as error:
        raise SystemExit(
            f'Ошибка: проверьте email и пароль (от {MIN_PASSWORD_LENGTH} символов)'
        ) from error
    except UserAlreadyExists as error:
        raise SystemExit('Ошибка: этот email уже зарегистрирован') from error

    print(f'Создан пользователь #{user.id} ({user.role.value})')
    print(f'Вход: {user.email} / {password}')


if __name__ == '__main__':
    main()
