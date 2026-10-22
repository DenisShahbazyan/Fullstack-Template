"""Показ ошибок на сайте: HTML-страница вместо JSON `{"detail": ...}`."""

from http import HTTPStatus

from fastapi import Request, Response

from app.web.templates import render
from app.web.toasts import attach_toast

_TITLES: dict[int, str] = {
    HTTPStatus.BAD_REQUEST: 'Некорректный запрос',
    HTTPStatus.UNAUTHORIZED: 'Нужно войти',
    HTTPStatus.FORBIDDEN: 'Доступ закрыт',
    HTTPStatus.NOT_FOUND: 'Страница не найдена',
    HTTPStatus.METHOD_NOT_ALLOWED: 'Так эта страница не открывается',
    HTTPStatus.CONFLICT: 'Действие невозможно',
    HTTPStatus.REQUEST_ENTITY_TOO_LARGE: 'Файл слишком большой',
    HTTPStatus.UNPROCESSABLE_ENTITY: 'Некорректные данные',
    HTTPStatus.TOO_MANY_REQUESTS: 'Слишком много запросов',
    HTTPStatus.INTERNAL_SERVER_ERROR: 'Что-то пошло не так',
    HTTPStatus.BAD_GATEWAY: 'Внешний сервис не ответил',
    HTTPStatus.SERVICE_UNAVAILABLE: 'Сервис временно недоступен',
}

_DETAILS: dict[int, str] = {
    HTTPStatus.BAD_REQUEST: 'Мы не смогли разобрать запрос. Попробуйте начать заново.',
    HTTPStatus.UNAUTHORIZED: 'Войдите в аккаунт, чтобы продолжить.',
    HTTPStatus.FORBIDDEN: 'У вашего аккаунта нет прав на этот раздел.',
    HTTPStatus.NOT_FOUND: 'Возможно, она была удалена или адрес указан неверно.',
    HTTPStatus.METHOD_NOT_ALLOWED: 'Вернитесь назад и повторите действие со страницы.',
    HTTPStatus.CONFLICT: 'Данные изменились с момента открытия страницы. Обновите её.',
    HTTPStatus.REQUEST_ENTITY_TOO_LARGE: 'Уменьшите размер файла и попробуйте снова.',
    HTTPStatus.UNPROCESSABLE_ENTITY: 'Проверьте заполненные поля и повторите отправку.',
    HTTPStatus.TOO_MANY_REQUESTS: 'Подождите немного и повторите попытку.',
    HTTPStatus.INTERNAL_SERVER_ERROR: 'Мы уже знаем о проблеме. Попробуйте позже.',
    HTTPStatus.BAD_GATEWAY: 'Сервис-партнёр сейчас не отвечает. Попробуйте позже.',
    HTTPStatus.SERVICE_UNAVAILABLE: 'Мы восстанавливаем работу. Зайдите позже.',
}

# Starlette подставляет в HTTPException английскую фразу статуса, когда свой
# текст не задан. Показывать «Not Found» вместо описания страницы незачем.
_HTTP_PHRASES = frozenset(status.phrase for status in HTTPStatus)

_FALLBACK_TITLE = 'Ошибка'
_FALLBACK_DETAIL = 'Не удалось выполнить запрос. Попробуйте ещё раз.'


class HtmlErrorRenderer:
    """Реализация `core.exception_handlers.ErrorRenderer` для сайта."""

    def accepts(self, request: Request) -> bool:
        """Сайт получает страницу, `/api/` — JSON.

        Путь надёжнее заголовка Accept: браузер шлёт `*/*` из fetch и
        `text/html` из адресной строки, а сторона API не должна зависеть от
        того, кто её дёрнул.
        """
        return not request.url.path.startswith('/api/')

    def render(
        self,
        request: Request,
        status_code: int,
        detail: str | None,
    ) -> Response:
        """Страница целиком, а для HTMX — всплывашка вместо содержимого блока.

        Фрагмент с текстом ошибки затирал бы обновляемый блок: неудачное
        добавление строки стирало бы с экрана весь список. Пустое тело
        оставляет блок как был, а сообщение приходит заголовком.

        Ответ со статусом 200 намеренно: htmx по умолчанию не обрабатывает
        ошибочные, и заголовок с сообщением никто бы не прочитал.
        """
        message = self._user_detail(status_code, detail)
        if request.headers.get('HX-Request') == 'true':
            return attach_toast(Response(status_code=HTTPStatus.OK), message)
        return render(
            request,
            'public/pages/error.html',
            {
                'status_code': status_code,
                'title': _TITLES.get(status_code, _FALLBACK_TITLE),
                'detail': message,
            },
            status_code=status_code,
        )

    def detail_for(self, status_code: int) -> str:
        return _DETAILS.get(status_code, _FALLBACK_DETAIL)

    def _user_detail(self, status_code: int, detail: str | None) -> str:
        if detail is None or detail in _HTTP_PHRASES:
            return self.detail_for(status_code)
        return detail
