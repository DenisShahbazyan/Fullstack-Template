"""Правила паролей."""

import secrets

MIN_PASSWORD_LENGTH = 8
GENERATED_PASSWORD_LENGTH = 14

# Без символов, которые путаются при переписывании и диктовке: O/0, I/l/1.
_ALPHABET = 'ABCDEFGHJKMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789'


def generate_password(length: int = GENERATED_PASSWORD_LENGTH) -> str:
    """Случайный пароль для учётной записи, которую заводит не сам её владелец."""
    return ''.join(secrets.choice(_ALPHABET) for _ in range(length))
