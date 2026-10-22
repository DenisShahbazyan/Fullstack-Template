import os
from pathlib import Path
from typing import Self

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, PostgresDsn, ValidationInfo, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
APP_DIR: Path = PROJECT_DIR / 'app'
STATIC_DIR: Path = PROJECT_DIR / 'static'


class DB(BaseModel):
    host: str = 'localhost'
    port: int = 5432
    username: str = 'postgres'
    password: str = 'postgres'
    name: str = 'app_db'
    url: str = 'postgresql+asyncpg://postgres:postgres@localhost:5432/app_db'

    POOL_SIZE: int = 20
    MAX_OVERFLOW: int = 10
    POOL_TIMEOUT: int = 30
    POOL_RECYCLE: int = 1800
    ECHO: bool = False

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


class JWT(BaseModel):
    SECRET: str = 'change-me'
    # Сессия скользящая (см. core/middleware/session.py): срок отсчитывается
    # от последнего запроса, поэтому это лимит простоя, а не времени работы.
    ACCESS_TOKEN_LIFETIME_SECONDS: int = 60 * 60 * 24 * 7  # 7 days
    REFRESH_TOKEN_LIFETIME_SECONDS: int = 60 * 60 * 24 * 7  # 7 days
    COOKIE_SECURE: bool = True


class Csrf(BaseModel):
    SECRET: str = 'change-me'
    COOKIE_KEY: str = 'csrftoken'
    COOKIE_SAMESITE: str = 'lax'
    COOKIE_SECURE: bool = True
    MAX_AGE: int = 60 * 60 * 24  # 1 day


class Static(BaseModel):
    DIR: Path = STATIC_DIR
    URL: str = '/static'
    DOCS_JS: str = '/static/docs/swagger-ui-bundle.js'
    DOCS_CSS: str = '/static/docs/swagger-ui.css'


class Site(BaseModel):
    """То, что видит посетитель: название в заголовках и шапке."""

    NAME: str = 'MyProject'


def get_env_file(environment: str | None) -> Path:
    match environment:
        case 'docker':
            return PROJECT_DIR / '.env.docker'
        case _:
            return PROJECT_DIR / '.env.local'


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            PROJECT_DIR / '.env.template',
            get_env_file(os.getenv('ENVIRONMENT')),
        ),
        case_sensitive=False,
        env_nested_delimiter='__',
        # В окружении есть переменные для инфраструктуры, а не для приложения:
        # DOCKER_USERNAME, DOMAIN, POSTGRES_* нужны docker compose и Caddy.
        # Без ignore Settings падает на них с extra_forbidden.
        extra='ignore',
    )

    db: DB = DB()
    jwt: JWT = JWT()
    csrf: Csrf = Csrf()
    static: Static = Static()
    site: Site = Site()


settings = Settings()


def mount_static(app: FastAPI) -> None:
    settings.static.DIR.mkdir(parents=True, exist_ok=True)
    app.mount(
        settings.static.URL,
        StaticFiles(directory=settings.static.DIR),
        name='static',
    )
