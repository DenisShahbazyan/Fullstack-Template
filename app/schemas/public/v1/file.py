from pydantic import BaseModel


class FileUploadSchema(BaseModel):
    """Временная загрузка: `key` — для записи, `url` — чтобы сразу показать."""

    key: str
    url: str
