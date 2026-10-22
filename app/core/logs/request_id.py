"""Сквозной идентификатор запроса: связывает access-строку с traceback'ом.

Access-лог пишет granian, а исключение — обработчик приложения, и это две
несвязанные строки: по «упало в 19:55» среди сотни одновременных запросов
не найти, какой именно. Общий идентификатор в обеих строках и в заголовке
ответа превращает жалобу со скриншотом в точку в логе.

Хранится в `contextvars`: у каждой задачи asyncio своя копия, поэтому
соседние запросы не видят чужой идентификатор.
"""

from contextvars import ContextVar
from uuid import uuid4

REQUEST_ID_HEADER = 'x-request-id'

_request_id: ContextVar[str] = ContextVar('request_id', default='')


def current_request_id() -> str:
    """Идентификатор обрабатываемого запроса; пустая строка вне запроса."""
    return _request_id.get()


def set_request_id(value: str) -> None:
    _request_id.set(value)


def new_request_id() -> str:
    return uuid4().hex
