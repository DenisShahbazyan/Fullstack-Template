"""Единая точка превращения исключений в ответ.

Как выглядит ответ, решает не `core`: HTML-страницу умеет рисовать только
транспортный слой. Рендерер передаётся снаружи и лежит в `app.state`, откуда
его берут и обработчики соседних модулей (CSRF, ограничение частоты).
"""

import logging
from http import HTTPStatus
from typing import Protocol

from fastapi import FastAPI, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.core.logs.request_id import current_request_id
from app.domain.errors import (
    ConflictError,
    DomainError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitedError,
    UpstreamError,
    ValidationError,
)

logger = logging.getLogger(__name__)

_STATUS_BY_ERROR: dict[type[DomainError], HTTPStatus] = {
    NotFoundError: HTTPStatus.NOT_FOUND,
    ConflictError: HTTPStatus.CONFLICT,
    PermissionDeniedError: HTTPStatus.FORBIDDEN,
    ValidationError: HTTPStatus.UNPROCESSABLE_ENTITY,
    RateLimitedError: HTTPStatus.TOO_MANY_REQUESTS,
    UpstreamError: HTTPStatus.BAD_GATEWAY,
}


class ErrorRenderer(Protocol):
    """Тот, кто знает, как показать ошибку человеку, а не клиенту API."""

    def accepts(self, request: Request) -> bool:
        """Стоит ли отвечать этому запросу страницей вместо JSON."""

    def render(
        self, request: Request, status_code: int, detail: str | None
    ) -> Response:
        """Страница ошибки. `detail` — текст исключения, если он для пользователя."""

    def detail_for(self, status_code: int) -> str:
        """Человеческое описание статуса для исключений без своего текста."""


def _resolve_status(error: DomainError) -> HTTPStatus:
    for error_type, status in _STATUS_BY_ERROR.items():
        if isinstance(error, error_type):
            return status
    return HTTPStatus.BAD_REQUEST


def error_response(
    request: Request,
    status_code: int,
    detail: str | None = None,
) -> Response:
    """Ответ об ошибке в форме, которую ждёт вызвавшая сторона."""
    renderer: ErrorRenderer = request.app.state.error_renderer
    if renderer.accepts(request):
        return renderer.render(request, status_code, detail)
    return JSONResponse(
        status_code=status_code,
        content={'detail': detail or renderer.detail_for(status_code)},
    )


def add_exception_handlers(app: FastAPI, renderer: ErrorRenderer) -> None:
    app.state.error_renderer = renderer

    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError) -> Response:
        return error_response(request, _resolve_status(exc), exc.message)

    @app.exception_handler(HTTPException)
    async def handle_http_exception(request: Request, exc: HTTPException) -> Response:
        # Переход на /login живёт в зависимостях как HTTPException с Location:
        # отдать вместо него страницу ошибки значило бы сломать вход.
        if exc.headers and 'Location' in exc.headers:
            return Response(status_code=exc.status_code, headers=exc.headers)
        detail = exc.detail if isinstance(exc.detail, str) else None
        return error_response(request, exc.status_code, detail)

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> Response:
        # Разбор ошибок Pydantic с `loc` и `type` рассчитан на клиента API;
        # посетителю сайта показывается общий текст статуса.
        renderer: ErrorRenderer = request.app.state.error_renderer
        if renderer.accepts(request):
            return renderer.render(request, HTTPStatus.UNPROCESSABLE_ENTITY, None)
        return JSONResponse(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            # В `ctx` валидатор кладёт само исключение, а оно не сериализуется
            # json.dumps — без кодировщика ответ 422 падал бы в 500.
            content=jsonable_encoder({'detail': exc.errors()}),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> Response:
        logger.exception(
            'unhandled error on %s',
            request.url.path,
            exc_info=exc,
            extra={'request_id': current_request_id()},
        )
        return error_response(request, HTTPStatus.INTERNAL_SERVER_ERROR)
