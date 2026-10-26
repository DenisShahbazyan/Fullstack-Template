"""Проектная часть загрузок: папки бакета и документы, которые принимаем как есть.

Единственный файл раздела `uploads`, который у каждого проекта свой. Остальные
модули загрузок одинаковы во всех проектах на каркасе — правятся в шаблоне.

Папка — константа здесь; в чистку сирот она попадает через пометку колонки
`info=file_folder(FOLDER)` (`app/models/file_keys.py`), а не через список.
"""

from app.domain.uploads import types

# Типы, которые хранятся без перекодирования (например, types.PDF). Изображения
# из types.IMAGE_TYPES принимаются всегда и уходят в WebP с превью.
DOCUMENT_TYPES: frozenset[str] = frozenset()

UPLOAD_TYPES = types.IMAGE_TYPES | DOCUMENT_TYPES
