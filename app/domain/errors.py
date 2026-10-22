class DomainError(Exception):
    """Базовая ошибка доменного слоя."""

    message = 'Ошибка бизнес-логики'

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)
        self.message = message or self.message


class NotFoundError(DomainError):
    """Запрашиваемый объект не найден."""

    message = 'Объект не найден'


class ConflictError(DomainError):
    """Действие конфликтует с текущим состоянием данных."""

    message = 'Конфликт данных'


class PermissionDeniedError(DomainError):
    """Недостаточно прав на действие."""

    message = 'Недостаточно прав'


class RateLimitedError(DomainError):
    """Действие слишком частое. Данные верны, повторить можно позже."""

    message = 'Слишком часто. Попробуйте позже'


class UpstreamError(DomainError):
    """Внешний сервис не ответил или отказал. Наша сторона исправна."""

    message = 'Внешний сервис недоступен'


class ValidationError(DomainError):
    """Данные не удовлетворяют бизнес-правилу."""

    message = 'Некорректные данные'
