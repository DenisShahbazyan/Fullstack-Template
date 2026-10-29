from app.domain.errors import ValidationError


class InvalidPhoneError(ValidationError):
    message = 'Укажите мобильный телефон в формате +7 900 000-00-00'
