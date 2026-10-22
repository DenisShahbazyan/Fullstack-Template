"""Access-лог granian в том же JSON, что и остальные логи.

granian зовёт `access_logger.info(fmt, atoms)`, где `atoms` — словарь полей
запроса (`status`, `path`, `dt_ms`, ...). Штатный `JsonFormatter` кладёт
`args` в список пропускаемых атрибутов, поэтому без этой прослойки от запроса
осталась бы одна собранная строка: по ней не отфильтровать пятисотки и не
посчитать перцентиль времени ответа.
"""

import logging
from typing import Any

from pythonjsonlogger.json import JsonFormatter

from app.core.config import settings
from app.core.logs.request_id import current_request_id

# Атомы, которые в JSON не идут. `query_string` — потому что granian отдаёт
# его сырыми байтами (в логе выходит base64), а в параметрах запроса могут
# ехать персональные данные: их логировать нельзя. Остальные постоянны для
# всего лога и места не стоят.
_SKIPPED_ATOMS = frozenset({'query_string', 'scheme', 'protocol', 'time'})


class AccessJsonFormatter(JsonFormatter):
    """Раскладывает атомы запроса в поля JSON вместо собранной строки."""

    def add_fields(
        self,
        log_data: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        super().add_fields(log_data, record, message_dict)
        if not isinstance(record.args, dict):
            return

        log_data.update(
            {
                key: value
                for key, value in record.args.items()
                if key not in _SKIPPED_ATOMS and not key.startswith('_')
            }
        )
        # Время ответа в поле с долей миллисекунды до десятого знака читается
        # хуже, чем помогает: округляем до микросекунд.
        if 'dt_ms' in log_data:
            log_data['dt_ms'] = round(log_data['dt_ms'], 3)

        request_id = current_request_id()
        if request_id:
            log_data['request_id'] = request_id


class SkipStaticFilter(logging.Filter):
    """Отсеивает из access-лога запросы за статикой.

    Caddy проксирует на приложение всё, включая `/static`, поэтому на каждую
    страницу приходится несколько строк про css и js. О работе приложения они
    не говорят ничего, а осмысленные запросы в них тонут.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if not isinstance(record.args, dict):
            return True
        path = record.args.get('path', '')
        return not (isinstance(path, str) and path.startswith(settings.static.URL))
