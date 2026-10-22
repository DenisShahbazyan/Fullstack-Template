from typing import Any

LOGGING_CONFIG: dict[str, Any] = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.json.JsonFormatter',
            'format': '%(asctime)s %(name)s %(module)s %(lineno)d %(levelname)s %(message)s',  # noqa: E501
            'datefmt': '%Y-%m-%dT%H:%M:%S',
            'json_ensure_ascii': False,
        },
        'access': {
            '()': 'app.core.logs.access.AccessJsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s',
            'datefmt': '%Y-%m-%dT%H:%M:%S',
            'json_ensure_ascii': False,
        },
    },
    'filters': {
        'skip_static': {'()': 'app.core.logs.access.SkipStaticFilter'},
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
            'stream': 'ext://sys.stdout',
        },
        'access': {
            'class': 'logging.StreamHandler',
            'formatter': 'access',
            'filters': ['skip_static'],
            'stream': 'ext://sys.stdout',
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console'],
    },
    'loggers': {
        # HTTP-клиенты пишут строку на каждый исходящий запрос: о работе
        # приложения это не говорит, а осмысленные записи в этом тонут.
        'httpx': {'level': 'WARNING'},
        'httpcore': {'level': 'WARNING'},
        # granian настраивает свои логгеры сам, до импорта приложения, и
        # вешает на них текстовый handler с `propagate: False`. Не перечислив
        # их здесь, мы оставили бы в одном потоке два формата сразу.
        '_granian': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
        'granian.access': {'handlers': ['access'], 'level': 'INFO', 'propagate': False},
    },
}
