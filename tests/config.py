from pathlib import Path
from typing import Self

from pydantic import BaseModel, PostgresDsn, ValidationInfo, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

API_PUBLIC_V1 = '/api/public/v1'
API_ADMIN_V1 = '/api/admin/v1'


class DB(BaseModel):
    host: str = 'localhost'
    port: int = 5432
    username: str = 'postgres'
    password: str = 'postgres'
    name: str = 'test_db'
    url: str = 'postgresql+asyncpg://postgres:postgres@localhost:5432/test_db'

    @model_validator(mode='after')
    def assemble_dsn(self, validation_info: ValidationInfo) -> Self:
        self.url = str(
            PostgresDsn.build(
                scheme='postgresql+asyncpg',
                username=self.username,
                password=self.password,
                host=self.host,
                port=int(self.port),
                path=self.name,
            )
        )
        return self


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            BASE_DIR / '.env.template',
            BASE_DIR / '.env.test',
        ),
        case_sensitive=False,
        env_nested_delimiter='__',
        extra='allow',
    )

    test_db: DB = DB()


settings = Settings()
