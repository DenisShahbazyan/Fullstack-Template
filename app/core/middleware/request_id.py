"""Заводит идентификатор запроса и возвращает его в заголовке ответа.

На «голом» ASGI, а не на BaseHTTPMiddleware: тот на каждый запрос оборачивает
приложение в отдельную задачу, а здесь достаточно положить значение в
contextvar и дописать заголовок в http.response.start.
"""

from fastapi import FastAPI
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logs.request_id import (
    REQUEST_ID_HEADER,
    new_request_id,
    set_request_id,
)


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        # Свой заголовок клиента принимаем: он позволяет связать наш лог с
        # логом того, кто нас позвал. Длину режем — идентификатор попадает в
        # каждую строку лога, и чужой мегабайт там не нужен.
        incoming = Headers(scope=scope).get(REQUEST_ID_HEADER, '')
        request_id = incoming[:64] or new_request_id()
        set_request_id(request_id)

        async def send_with_request_id(message: Message) -> None:
            if message['type'] == 'http.response.start':
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        await self.app(scope, receive, send_with_request_id)


def add_request_id_middleware(app: FastAPI) -> None:
    app.add_middleware(RequestIdMiddleware)
