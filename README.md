# Fullstack-Template

Шаблон fullstack-проекта на одном FastAPI-процессе: JSON API и SSR-сайт (Jinja2 + HTMX + Alpine.js + Tailwind CSS v4), встроенная админка, PostgreSQL с бэкапами в S3, деплой пушем в `main`. Собран из проектов SENO и comparo.

Правила написания кода — [CLAUDE.md](CLAUDE.md). Документация — [docs/](docs/README.md).

## Что внутри

- **Пользователи:** регистрация и вход по email (fastapi-users), JWT в HttpOnly-cookie для сайта и Bearer для API, скользящая сессия, роли `USER` / `MODER` / `ADMIN`.
- **Сайт:** главная, вход, регистрация, страница ошибок, тосты, CSRF на всех формах.
- **Админка** `/admin`: панель, пользователи со сменой роли, журнал аудита. То же в API: `/api/admin/v1/...`.
- **Загрузки:** приватный бакет S3 со своими ключами, фото в WebP с превью, подписанные ссылки, временные загрузки для API, ночная чистка сирот, ежедневная копия бакета к другому провайдеру ([ADR 0002](docs/DECISIONS/0002-s3-uploads.md)).
- **Инфраструктура:** базовый CRUD с тестами, доменные ошибки → HTTP-коды, JSON-логи с request id, Swagger на `/docs`, `/health`.
- **Прод:** Docker-образ, granian за Caddy (TLS и лимиты запросов), CI/CD через Docker Hub, Postgres + pgBackRest (WAL и ежедневный бэкап в S3, еженедельная проверка восстановления).

Сознательно **нет** Redis, очереди задач и поиска — добавляются, когда понадобятся (правила для них уже в CLAUDE.md).

## Новый проект из шаблона

1. Скопировать папку и завести репозиторий:

   ```sh
   cp -R Fullstack-Template ~/dev/MY/newproject && cd ~/dev/MY/newproject
   rm -rf .venv && git init
   ```

2. Заменить имя проекта. Плейсхолдеры — `myproject` (технические имена) и `MyProject` (то, что видит человек):

   ```sh
   grep -rn -i 'myproject' --exclude-dir=.venv --exclude-dir=.git .
   ```

   | Где | Что |
   | --- | --- |
   | `pyproject.toml` | `name` |
   | `.env.template`, `.env.local` | `SITE__NAME`, `DB__NAME` |
   | `.env.docker` | `DOCKER_IMAGE_NAME`, `SITE__NAME`, `POSTGRES_DB`, `DB__NAME` |
   | `CLAUDE.md`, `docs/` | название в заголовках |

   После правки `pyproject.toml` — `uv lock`.

3. Заполнить `.env.docker`: `DOCKER_USERNAME`, `DOMAIN`, все `change-me` (пароли и секреты — `openssl rand -base64 48`), `POSTGRES_USER`/`POSTGRES_PASSWORD` совпадают с `DB__USERNAME`/`DB__PASSWORD`. Раздел `BACKUPS` — по [docs/guide/ops/backups.md](docs/guide/ops/backups.md), `UPLOADS BACKUP` — по [uploads-backups.md](docs/guide/ops/uploads-backups.md). `S3__*` — **свой бакет проекта** и ключ только к нему. Файл коммитится вместе с секретами — **репозиторий должен быть приватным**.
4. В `.env.local` сгенерировать свои `JWT__SECRET` и `CSRF__SECRET` (`openssl rand -hex 32`) и вписать `S3__*` — отдельный dev-бакет проекта, не продовый и не от другого проекта.
5. Заполнить §0 и §2 (предметная часть) в `CLAUDE.md`, `docs/spec/v01.md`, `docs/plan/mvp.md`; `.claude/skills/backups/project.md`; когда у проекта появятся файлы — ещё `.claude/skills/uploads/project.md`.
6. Палитру сайта — токены `@theme` в `tailwind/input.css`.
7. Первая миграция `alembic/versions/…_first_migration.py` уже есть. Новые модели — `make revision m="..."`.

## Локальный запуск

Нужны [uv](https://docs.astral.sh/uv/) и Postgres на `localhost:5432` (параметры — в `.env.local`).

```sh
uv sync
createdb -h localhost -U postgres myproject_db
make migrate
make admin e=admin@example.com p=adminpass123   # без p пароль сгенерируется
make dev                                         # скачает Tailwind, соберёт CSS, запустит на :8000
```

- Сайт — http://localhost:8000, админка — `/admin`, Swagger — `/docs`.
- При правке шаблонов держите во втором терминале `make css-watch`: Tailwind собирает только классы, которые видит в файлах.

### Команды

| Команда | Что делает |
| --- | --- |
| `make dev` | CSS + granian с перезагрузкой |
| `make css` / `make css-watch` | собрать `static/css/app.css` |
| `make migrate` | применить миграции |
| `make revision m="add item"` | автогенерировать миграцию из моделей (прочитать её глазами!) |
| `make lint` | ruff (линт + формат) и ty |
| `make test p=tests/domain/` | pytest по пути; без `p` — всё |
| `make admin e=… p=…` | создать администратора |
| `make docker-up` / `make docker-down` | прод-образ локально (`docker-compose-dev.yml`, Postgres на `127.0.0.1:15432`) |

### Тесты

Нужна отдельная база из `.env.test` (по умолчанию `pytest_db`): таблицы создаются и удаляются на каждый тест.

```sh
createdb -h localhost -U postgres pytest_db
make test
```

## Деплой

Пуш в `main` → GitHub Actions ([.github/workflows/main.yml](.github/workflows/main.yml)): ruff и ty → сборка образов приложения и Postgres в Docker Hub → копирование `docker-compose.yml`, `Caddyfile`, `.env.docker` на сервер в `/home/<SERVER_USER>/<DOCKER_IMAGE_NAME>/` → `docker compose up -d`. Миграции применяет сервис `migrate` до старта `web`.

**Секреты репозитория** (Settings → Secrets and variables → Actions):

| Секрет | Что |
| --- | --- |
| `DOCKER_USERNAME`, `DOCKER_PASSWORD` | логин и токен Docker Hub |
| `SERVER_HOST`, `SERVER_USER` | адрес сервера и SSH-пользователь |
| `SSH_PRIVATE_KEY`, `SSH_PASSPHRASE` | ключ для входа на сервер |

**Сервер:** Docker с compose-плагином, открыты 22, 80, 443. A-запись `DOMAIN` указывает на сервер — Caddy сам получит TLS-сертификат.

После первого деплоя:

```sh
sudo docker compose --env-file .env.docker exec web \
    python -m scripts.users.create_user admin@example.com --role admin
sudo docker logs postgres_backup     # бэкапы: в конце «Восстановление прошло успешно.»
```

## Структура

```
app/            приложение (слои — CLAUDE.md §3)
alembic/        миграции
docker/postgres/ образ Postgres + pgBackRest и скрипты бэкапа
docker/uploads-backup/ образ rclone и расписание копии бакета загрузок
docs/           спека, план, ADR, эксплуатация
scripts/        start.sh, migrate.sh, консольные утилиты
static/         css (собранный), js (htmx, alpine), swagger
tailwind/       input.css — токены и компоненты
tests/          pytest
```
