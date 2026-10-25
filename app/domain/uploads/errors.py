from app.domain.errors import DomainError, UpstreamError, ValidationError


class UnsupportedFileTypeError(ValidationError):
    message = 'Этот формат файла не подходит'


class FileTooLargeError(ValidationError):
    message = 'Файл слишком большой'


class ImageProcessingError(ValidationError):
    message = 'Не удалось обработать изображение. Попробуйте другой файл'


class ImageTooLargeError(ValidationError):
    message = 'Фото слишком большое. Загрузите снимок до 60 мегапикселей'


class ForeignUploadError(ValidationError):
    message = 'Файл не найден среди ваших загрузок. Загрузите его заново'


class StoredFileMissingError(ValidationError):
    message = 'Файл не найден в хранилище. Загрузите его заново'


class FileStorageUnavailableError(UpstreamError):
    message = 'Хранилище файлов временно недоступно. Попробуйте позже'


class ImplausibleOrphanSweepError(DomainError):
    """Сирот подозрительно много: скорее всего, не та база или пустой ответ."""

    message = 'Чистка загрузок остановлена: под удаление попало слишком много файлов'
