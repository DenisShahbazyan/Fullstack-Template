from app.domain.errors import ConflictError, NotFoundError, PermissionDeniedError


class SelfRoleChangeError(ConflictError):
    message = 'Нельзя менять собственную роль'


class AdminRoleAssignmentError(PermissionDeniedError):
    message = 'Назначать роли модератора и администратора может только администратор'


class UserNotFoundError(NotFoundError):
    message = 'Пользователь не найден'


class StaleOrderError(ConflictError):
    message = 'Список изменился в другой вкладке — порядок не сохранён'
