"""Всплывающие сообщения для страниц сайта.

Ответ HTMX несёт сообщение заголовком HX-Trigger — фронт показывает его,
не перезагружая страницу. Обычный переход по редиректу заголовка донести
не может, поэтому там сообщение едет параметром и всплывает после отрисовки.
"""

import json
from urllib.parse import quote

from fastapi import Request
from fastapi.responses import RedirectResponse, Response

from app.web.dependencies import redirect
from app.web.toast_params import TOAST_KIND_PARAM, TOAST_PARAM

_EVENT = 'app:toast'


def is_htmx(request: Request) -> bool:
    return request.headers.get('HX-Request') == 'true'


def attach_toast(response: Response, message: str, kind: str = 'error') -> Response:
    """Просит фронт показать сообщение поверх текущей страницы.

    Заголовок HTTP держит только latin-1, а сообщения русские, поэтому
    кириллица уезжает \\uXXXX-последовательностями — JSON.parse на той
    стороне вернёт её обратно.
    """
    response.headers['HX-Trigger'] = json.dumps(
        {_EVENT: {'message': message, 'kind': kind}},
    )
    return response


def add_htmx_event(response: Response, event: str) -> None:
    """Добавляет событие в HX-Trigger, не затирая уже лежащие там (тост)."""
    current = response.headers.get('HX-Trigger')
    events: dict[str, object] = json.loads(current) if current else {}
    events[event] = True
    response.headers['HX-Trigger'] = json.dumps(events)


def toast_context(message: str, kind: str = 'error') -> dict[str, str]:
    """Сообщение для страницы, которую роут отвечает сам, без редиректа.

    Форму с ошибкой нельзя заменить редиректом: он стёр бы уже введённое.
    Базовый шаблон печатает это в `data-toast`, откуда скрипт и забирает —
    тот же путь, что и у сообщения из `?toast=`.
    """
    return {'toast': message, 'toast_kind': kind}


def redirect_with_toast(
    path: str,
    message: str,
    kind: str = 'error',
) -> RedirectResponse:
    """Редирект, после которого на новой странице всплывёт сообщение.

    Параметр вставляется перед якорем: за «#» начинается фрагмент, и
    дописанный туда query до сервера бы просто не доехал.
    """
    base, _, fragment = path.partition('#')
    separator = '&' if '?' in base else '?'
    query = f'{TOAST_PARAM}={quote(message)}'
    if kind != 'error':
        query += f'&{TOAST_KIND_PARAM}={quote(kind)}'
    target = f'{base}{separator}{query}'
    return redirect(f'{target}#{fragment}' if fragment else target)
