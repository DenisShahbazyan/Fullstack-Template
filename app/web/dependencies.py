from http import HTTPStatus
from urllib.parse import parse_qsl, urlsplit

from fastapi import Depends, Request
from fastapi.responses import RedirectResponse
from starlette.exceptions import HTTPException

from app.core.auth.users import current_user_optional
from app.models.user import User, UserRoleEnum


async def optional_user(
    user: User | None = Depends(current_user_optional),
) -> User | None:
    return user


async def web_required_user(
    request: Request,
    user: User | None = Depends(current_user_optional),
) -> User:
    if user is None:
        raise HTTPException(
            status_code=HTTPStatus.TEMPORARY_REDIRECT,
            headers={'Location': f'/login?next={request.url.path}'},
        )
    return user


async def web_require_admin(user: User = Depends(web_required_user)) -> User:
    if user.role != UserRoleEnum.ADMIN:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail='Требуются права администратора',
        )
    return user


async def web_require_moder(user: User = Depends(web_required_user)) -> User:
    if user.role not in (UserRoleEnum.ADMIN, UserRoleEnum.MODER):
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail='Требуются права модератора',
        )
    return user


def redirect(path: str) -> RedirectResponse:
    return RedirectResponse(url=path, status_code=HTTPStatus.SEE_OTHER)


def safe_next_url(url: str, fallback: str = '/') -> str:
    """Адрес возврата после входа: только внутри сайта, наружу не уводим."""
    if url.startswith('/') and not url.startswith('//'):
        return url
    return fallback


def current_page_query(request: Request) -> dict[str, str]:
    """Параметры адреса страницы, с которой пришёл HTMX-запрос.

    Перерисованный после сохранения список должен остаться с тем же
    поиском и на той же странице, а их знает только адрес страницы.
    """
    url = request.headers.get('HX-Current-URL', '')
    return dict(parse_qsl(urlsplit(url).query))
