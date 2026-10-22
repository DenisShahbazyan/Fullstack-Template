from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute
from fastapi_users.authentication import AuthenticationBackend


def hide_from_schema(router: APIRouter, *paths: str) -> APIRouter:
    """Убирает указанные роуты из схемы swagger, оставляя их рабочими.

    Вызывать **до** `include_router`, пока роутер «плоский». После подключения
    FastAPI прячет роуты во внутренние обёртки, и обход `router.routes` до них
    не доберётся.
    """
    for route in router.routes:
        if isinstance(route, APIRoute) and route.path in paths:
            route.include_in_schema = False
    return router


def mount_oauth2_form_login(app: FastAPI, backend: AuthenticationBackend) -> None:
    """Публикует форменный `/login` от fastapi-users в корне приложения.

    Кнопка "Authorize" в swagger шлёт OAuth2-форму по адресу из
    `BearerTransport(tokenUrl='/login')` — то есть на корневой `/login`, без
    префикса API. Роут нужен именно там, иначе авторизация в swagger отдаёт 405.
    GET `/login` при этом остаётся за страницей входа сайта.

    Из схемы роут скрыт: клиенты логинятся JSON-эндпоинтом `/auth/login`, а этот
    существует только ради кнопки в swagger.
    """
    from app.core.auth.users import fastapi_users

    app.include_router(
        hide_from_schema(
            fastapi_users.get_auth_router(backend),
            '/login',
            '/logout',
        ),
        include_in_schema=False,
    )
