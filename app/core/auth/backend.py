from fastapi import Response
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    CookieTransport,
    JWTStrategy,
)

from app.core.config import settings
from app.models.user import User

bearer_transport = BearerTransport(tokenUrl='/login')

cookie_transport = CookieTransport(
    cookie_name='access_token',
    cookie_max_age=settings.jwt.ACCESS_TOKEN_LIFETIME_SECONDS,
    cookie_httponly=True,
    cookie_secure=settings.jwt.COOKIE_SECURE,
    cookie_samesite='lax',
)


def get_access_jwt_strategy() -> JWTStrategy[User, int]:
    return JWTStrategy(
        secret=settings.jwt.SECRET,
        lifetime_seconds=settings.jwt.ACCESS_TOKEN_LIFETIME_SECONDS,
        token_audience=['fastapi-users:auth'],
    )


def get_refresh_jwt_strategy() -> JWTStrategy[User, int]:
    return JWTStrategy(
        secret=settings.jwt.SECRET,
        lifetime_seconds=settings.jwt.REFRESH_TOKEN_LIFETIME_SECONDS,
        token_audience=['fastapi-users:refresh'],
    )


auth_backend = AuthenticationBackend(
    name='jwt',
    transport=bearer_transport,
    get_strategy=get_access_jwt_strategy,
)

cookie_auth_backend = AuthenticationBackend(
    name='jwt-cookie',
    transport=cookie_transport,
    get_strategy=get_access_jwt_strategy,
)


def set_access_cookie(response: Response, token: str) -> None:
    """Ставит cookie сессии теми же параметрами, что и `cookie_transport`."""
    response.set_cookie(
        cookie_transport.cookie_name,
        token,
        max_age=settings.jwt.ACCESS_TOKEN_LIFETIME_SECONDS,
        httponly=True,
        secure=settings.jwt.COOKIE_SECURE,
        samesite='lax',
    )


def set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        'refresh_token',
        token,
        max_age=settings.jwt.REFRESH_TOKEN_LIFETIME_SECONDS,
        httponly=True,
        secure=settings.jwt.COOKIE_SECURE,
        samesite='lax',
    )
