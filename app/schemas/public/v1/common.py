"""Типы полей, общие для схем API и форм админки."""

from typing import Annotated

from pydantic import AfterValidator

from app.domain.contacts.errors import InvalidPhoneError
from app.domain.contacts.phone import normalize_phone


def _normalize_phone(value: str) -> str:
    try:
        return normalize_phone(value)
    except InvalidPhoneError as error:
        raise ValueError(error.message) from error


Phone = Annotated[str, AfterValidator(_normalize_phone)]
"""Мобильный телефон: приходит в любом виде, дальше — только +79XXXXXXXXX."""
