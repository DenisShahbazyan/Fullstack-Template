import time

import jwt
from fastapi import FastAPI
from fastapi_users.jwt import decode_jwt, generate_jwt
from starlette.datastructures import Headers, MutableHeaders
from starlette.requests import cookie_parser
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.auth.backend import cookie_transport, set_access_cookie
from app.core.config import settings

ACCESS_AUDIENCE = ['fastapi-users:auth']

# Порог продления: пока израсходовано меньше половины срока, cookie не трогаем.
# Иначе каждый HTMX-запрос слал бы новый Set-Cookie ради нескольких секунд.
RENEW_AFTER_FRACTION = 0.5


def _renewed_token(token: str) -> str | None:
    """Перевыпускает access-токен, если истёк больше половины его срока."""
    try:
        payload = decode_jwt(token, settings.jwt.SECRET, ACCESS_AUDIENCE)
    except jwt.PyJWTError:
        return None

    subject = payload.get('sub')
    expires_at = payload.get('exp')
    if subject is None or expires_at is None:
        return None

    lifetime = settings.jwt.ACCESS_TOKEN_LIFETIME_SECONDS
    if expires_at - time.time() > lifetime * RENEW_AFTER_FRACTION:
        return None

    return generate_jwt(
        {'sub': subject, 'aud': ACCESS_AUDIENCE},
        settings.jwt.SECRET,
        lifetime,
    )


def _access_cookie_header(token: str) -> str:
    """Собирает готовый Set-Cookie теми же параметрами, что и логин."""
    carrier = Response()
    set_access_cookie(carrier, token)
    return carrier.headers['set-cookie']


class SlidingSessionMiddleware:
    """Продлевает cookie-сессию, пока пользователь активен.

    SSR-фронт не умеет обновлять токен сам, поэтому срок жизни отсчитывается
    от последнего запроса, а не от момента входа.

    Реализовано на «голом» ASGI, а не на BaseHTTPMiddleware: тот на каждый
    запрос оборачивает приложение в отдельную задачу, а здесь достаточно
    дописать заголовок в http.response.start.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        cookies = cookie_parser(Headers(scope=scope).get('cookie', ''))
        token = cookies.get(cookie_transport.cookie_name)
        renewed = _renewed_token(token) if token else None
        if renewed is None:
            await self.app(scope, receive, send)
            return

        async def send_with_renewed_cookie(message: Message) -> None:
            if message['type'] == 'http.response.start':
                headers = MutableHeaders(scope=message)
                # Логин и выход сами распоряжаются cookie: их заголовок должен
                # остаться последним, иначе выход воскресит сессию.
                if not _handles_access_cookie(headers):
                    headers.append('set-cookie', _access_cookie_header(renewed))
            await send(message)

        await self.app(scope, receive, send_with_renewed_cookie)


def _handles_access_cookie(headers: MutableHeaders) -> bool:
    prefix = f'{cookie_transport.cookie_name}='
    return any(value.startswith(prefix) for value in headers.getlist('set-cookie'))


def add_session_middleware(app: FastAPI) -> None:
    app.add_middleware(SlidingSessionMiddleware)
