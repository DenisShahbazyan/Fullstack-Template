"""Телефон человека: хранится только как +79XXXXXXXXX (скилл phone-input)."""

from app.domain.contacts.errors import InvalidPhoneError


def normalize_phone(raw: str) -> str:
    """Мобильный в виде +79XXXXXXXXX из «8 (930) …», «+7 930 …» или «930 …».

    Raises:
        InvalidPhoneError: это не полный российский мобильный номер.
    """
    digits = ''.join(char for char in raw if char.isdigit())
    if len(digits) == 10:
        digits = f'7{digits}'
    elif len(digits) == 11 and digits[0] == '8':
        digits = f'7{digits[1:]}'
    if len(digits) != 11 or not digits.startswith('79'):
        raise InvalidPhoneError()
    return f'+{digits}'


def format_phone(phone: str) -> str:
    """+79301112233 → +7 930 111-22-33; чужой формат — как есть."""
    digits = phone.removeprefix('+')
    if len(digits) != 11 or not digits.isdigit():
        return phone
    return f'+{digits[0]} {digits[1:4]} {digits[4:7]}-{digits[7:9]}-{digits[9:]}'


def phone_search_digits(query: str) -> str | None:
    """Цифры для поиска по части телефона; None — запрос не похож на номер.

    «8 900 486» ищет то же, что «+7 900 486»: телефоны хранятся с семёрки.
    """
    digits = ''.join(char for char in query if char.isdigit())
    if len(digits) < 3:
        return None
    if len(digits) == 11 and digits[0] == '8':
        return f'7{digits[1:]}'
    return digits


def tel_href(phone: str) -> str:
    """Ссылка `tel:` из номера как его пишут: «8 910 303-21-70» → `tel:+79103032170`."""
    digits = ''.join(char for char in phone if char.isdigit())
    if len(digits) == 11 and digits.startswith('8'):
        digits = f'7{digits[1:]}'
    return f'tel:+{digits}'
