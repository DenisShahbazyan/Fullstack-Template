import logging.config

from app.core.logs.config import LOGGING_CONFIG


def setup_logging() -> None:
    logging.config.dictConfig(LOGGING_CONFIG)
