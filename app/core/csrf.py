from fastapi import Depends, FastAPI, Request, Response
from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import (
    CsrfProtectError,
    MissingTokenError,
    TokenValidationError,
)
from itsdangerous import BadData, SignatureExpired, URLSafeTimedSerializer
from pydantic import BaseModel

from app.core.config import settings
from app.core.exception_handlers import error_response

CSRF_SALT = 'fastapi-csrf-token'


class _CsrfConfig(BaseModel):
    secret_key: str = settings.csrf.SECRET
    cookie_key: str = settings.csrf.COOKIE_KEY
    cookie_samesite: str = settings.csrf.COOKIE_SAMESITE
    cookie_secure: bool = settings.csrf.COOKIE_SECURE
    max_age: int = settings.csrf.MAX_AGE
    token_key: str = 'token_key'


@CsrfProtect.load_config
def _load_csrf_config():
    return _CsrfConfig()


async def _read_submitted_token(request: Request, csrf: CsrfProtect) -> str:
    header_token = request.headers.get(csrf._header_name)
    if header_token:
        return header_token
    form = await request.form()
    token = form.get(csrf._token_key)
    if isinstance(token, str) and token:
        return token
    raise MissingTokenError(
        f'CSRF token не найден ни в заголовке `{csrf._header_name}`, '
        f'ни в поле формы `{csrf._token_key}`',
    )


async def csrf_validate(
    request: Request,
    csrf_protect: CsrfProtect = Depends(),
) -> None:
    signed = request.cookies.get(csrf_protect._cookie_key)
    if signed is None:
        raise MissingTokenError(f'Missing Cookie: `{csrf_protect._cookie_key}`.')
    submitted = await _read_submitted_token(request, csrf_protect)
    serializer = URLSafeTimedSerializer(csrf_protect._secret_key, salt=CSRF_SALT)
    try:
        original = serializer.loads(signed, max_age=csrf_protect._max_age)
    except SignatureExpired as exc:
        raise TokenValidationError('CSRF-токен просрочен') from exc
    except BadData as exc:
        raise TokenValidationError('CSRF-токен недействителен') from exc
    if submitted != original:
        raise TokenValidationError('CSRF-токены не совпадают')


async def _csrf_error_handler(request: Request, exc: Exception) -> Response:
    assert isinstance(exc, CsrfProtectError)
    return error_response(request, exc.status_code, exc.message)


def register_csrf_exception_handler(app: FastAPI) -> None:
    app.add_exception_handler(CsrfProtectError, _csrf_error_handler)
