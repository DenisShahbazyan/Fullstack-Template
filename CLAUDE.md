# CLAUDE.md — MyProject

Ядро правил: то, что действует в любой задаче. Пошаговые процедуры для отдельных задач — в скиллах (`.claude/skills/`). Полная спека — `docs/spec/v01.md`, решения — `docs/DECISIONS/`.

> **Шаблон.** Разделы §5 и §7 (предметная часть) заполняются под конкретный проект при копировании (чек-лист — в [README.md](README.md)). Остальное — общие правила для всех проектов на этом каркасе; меняются осознанно и с ADR. Рецепт под задачу, нужный не в каждой работе, — новый скилл с триггером в §7, а не новый раздел здесь.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:

- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:

- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:

```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

## 5. Профиль

_TODO: одной строкой, что это за продукт._ Основная сущность — _TODO: `<Entity>`_.

Python 3.14 · FastAPI · SQLAlchemy 2.0 + Alembic · PostgreSQL 18 (бэкапы pgBackRest в S3) · S3 для загрузок (свой приватный бакет у проекта, копия — rclone к другому провайдеру) · granian за Caddy · SSR: Jinja2 + HTMX + Alpine.js + Tailwind v4 · тайпчекер `ty` · Ruff. Очереди, Redis и поиска нет; понадобятся — ARQ + Redis, Meilisearch.

Сущности:

- `User` — пользователь, логин — email. Роли: `USER`, `MODER`, `ADMIN`.
- `AuditLog` — журнал изменяющих действий администрации.
- _TODO: сущности предметной области._

Субдомены `app/domain/`: `auth/` (пароли), `admin/` (правила смены ролей, ручной порядок списков), `contacts/` (телефон), `stats/` (периоды статистики), _TODO: субдомены предметной области_.

## 6. Язык

- С пользователем — по-русски. Коммиты — по-английски.
- Идентификаторы — по-английски. Docstrings и исключения для пользователя интерфейса — по-русски, технические docstrings — по-английски.

## 7. Инварианты и триггеры

Нарушение этих правил не падает, а молча считает неверно или открывает закрытое. Пункт со стрелкой — сигнал загрузить скилл до начала работы.

- _TODO: правила, нарушение которых не видно глазами (производные величины, видимость, деньги). Каждый — с единственным местом, где он обеспечивается, и чек-листом «добавил X — тронь Y и Z»._
- **Изменяющее действие администрации пишется в аудит**: новое значение `AuditActionEnum` + `record_action(...)` (`core/admin/audit.py`) в той же сессии и том же коммите.
- Меняешь **схему БД** (модель, индекс, enum, миграция) → скилл `migrations`. Схему описывают модели, а не миграции.
- Шаблон, форма, HTMX-роут, вёрстка, JS → скилл `frontend`.
- Поле телефона в форме, валидация, хранение, поиск или показ номера → скилл `phone-input`. Номер хранится только как `+79XXXXXXXXX` (тип `Phone`): по нему ищут человека и держат уникальность.
- Страница статистики или отчёт в админке → скилл `admin-stats`.
- **«Сегодня» и время для человека — по местным часам**: `local_now()`/`local_today()` из `core/clock.py` (`SITE__TIMEZONE`), `created_at` на странице — фильтром `local_dt`. `date.today()` и `datetime.now()` сервер считает в UTC: вечером «сегодня» уже завтра.
- Файл в S3 (новое поле, папка, загрузка, галерея фото, показ, удаление) → скилл `uploads`. **Колонка с ключом файла — `mapped_column(info=file_folder(FOLDER))`** (`models/file_keys.py`); без пометки чистка не видит колонку, а в общей папке удалит её файлы.
- Тронул `docker/postgres/`, `docker/uploads-backup/`, сервисы `db`/`backup`/`uploads_backup`, версию Postgres, имя базы или завёл новое хранилище данных; рискованная миграция на проде → скилл `backups`. Бэкапы ломаются молча: алерт придёт через сутки, а то и при восстановлении.

## 8. Структура и слои

Одно FastAPI-приложение в `app/`. Админка — не отдельное приложение, а симметричная ветка `public/` ↔ `admin/` в каждом слое, где это имеет смысл.

```
app/
├── main.py, asgi.py                       # FastAPI; точка входа granian (X-Forwarded-* от Caddy)
├── api/{public,admin}/v1/endpoints/       # JSON API
├── web/{public,admin}/{pages,partials}/   # SSR + HTMX-фрагменты; templates.py (render, фильтры), formatting.py, toasts.py, errors.py
├── templates/{public,admin}/{macros,pages,partials}/   # у каждой стороны свой base.html
├── schemas/{public,admin}/v1/             # Pydantic
├── crud/{public,admin}/                   # доступ к БД; _base.py — общий CRUD
├── domain/<субдомен>/                     # бизнес-логика, общая для public и admin
├── models/                                # SQLAlchemy, одни на обе стороны
└── core/                                  # config, db, csrf, clock, auth/, admin/, logs/, middleware/, docs/, s3/ (загрузки)
static/ (css, js, img), tailwind/input.css, docker/postgres/, alembic/, tests/, scripts/, docs/
```

URL: `/`, `/login`, `/register`, … — публичное; `/admin`, `/admin/users`, `/admin/audit` — админка; `/api/public/v1/...`, `/api/admin/v1/...`, `/docs`, `/health`. URL совпадает с раскладкой: `web/admin/pages/users.py` ↔ `/admin/users`. Модули создаются по мере надобности, не заранее. Пакеты — с `__init__.py`, пустые директории — `.gitkeep`.

Зависимости (ломать — только с ADR):

- **`api/`, `web/`** — транспорт: зависимости → `domain`/`crud` → ответ. Бизнес-логики нет. Роут ≤ 15 строк. Будущий `workers/` — такой же транспорт.
- **`domain/`** — не импортирует `app.crud`, FastAPI, Jinja, сессии. `app.models` — можно для плоских моделей; если функция трогает ленивые связи — на границе Pydantic-DTO. Данные — аргументом или callable-зависимостью; часы и rng инжектятся. Не открывает сессий, не коммитит, не знает HTTP. Ошибки — доменные исключения.
- **`crud/`** — единственный доступ к БД. В `crud/admin/` — только то, чего нет в `crud/public/` (bulk, soft-delete, восстановление, админские фильтры); чтение не дублируется.
- **`models/`** — без бизнес-логики. **`schemas/`** — общая схема живёт в `public/`, admin её импортирует.
- **`templates/`** — только `{% if %}`/`{% for %}` и макросы; вычисления (форматирование цены, даты, флаги) — в Python.
- **Параллельность транспортов:** всё, что сделано для `web/public/`, должно быть реализуемо в `api/public/` без правок `domain/` и `crud/`. Логика в роуте или шаблоне — блокер.
- HTML — через `render()` из `web/templates.py` (CSRF-токен и тост); HTMX-фрагменты — отдельные роуты в `web/<side>/partials/`.
- Внешний провайдер (оплата, доставка, парсер) — `Protocol` в `domain/`, реализация-адаптер снаружи. Новый провайдер — новый адаптер, домен не меняется.
- Маппинг доменных исключений в HTTP — `core/exception_handlers.py`: сайт получает страницу ошибки (HTMX — тост), `/api/` — JSON.

## 9. БД — общие правила

- Только через `app/crud/`. Один CRUD-модуль — одна агрегатная сущность.
- **Фильтры — словарём вторым аргументом:** `crud.get(session, {'id': 1})`. Именованные — только `order_by`, `limit`, `offset`, `_detail`, `defaults`. Список методов — `app/crud/crud_methods_description.md`. Сложные условия (OR, LIKE, диапазоны) — `*_by_condition`.
- Мягкое удаление (`soft_delete*`, `restore`, `get_with_deleted`): обычные `get*` флаг не учитывают — фильтр `{'is_deleted': False}` явно; для публичной выдачи — в CRUD-подклассе, не в роутах.
- Транзакции — в роуте/задаче, не в CRUD. **Сессия — только через `Depends(get_async_session)`**. После записи читаем с мастера или возвращаем данные из самой записи.
- Уникальность — `UNIQUE INDEX`, ловим `IntegrityError` → доменная ошибка. Не `SELECT → INSERT`.
- JSONB — через Pydantic-схемы, не сырой `dict`.

## 10. Код

- SOLID, KISS, YAGNI (никаких флагов фич и шимов «про запас»), композиция вместо наследования (глубина ≤ 2). Абстракция — со второй реализации, устранение дублирования — с третьего повтора и только для одной бизнес-концепции. Fail fast на границе (Pydantic), внутри доверяем типам.
- Ориентиры: функция ≤ 20 строк, класс ≤ 200, аргументов ≤ 4 (больше — dataclass/Pydantic), вложенность ≤ 3.
- Функция — один глагол. CQS: либо меняет, либо возвращает. Флаг `do_save: bool` — это два метода.
- Имена: функции — глагол, булевы — `is_/has_/can_`, классы — существительное, протоколы без `I`, полные слова, приватное — `_`.
- Исключения — свои классы в `app/domain/<субдомен>/errors.py`, база `DomainError` и общие (`NotFoundError`, `ConflictError`, `PermissionDeniedError`, `ValidationError`, …) — `app/domain/errors.py`; HTTP-код выводится из базового класса. Не ловим `Exception` широко, не используем для потока управления.
- Pydantic: API-DTO — суффикс `Schema` (`ItemCreateSchema`), формы админки — `Form`; ORM и enum — без суффикса, кроме унаследованных `*Enum` ролей и статусов (`UserRoleEnum`).
- Типизация: строгая для `domain/` и `crud/`; публичные функции аннотированы полностью; `Any` и `# type: ignore[...]` — только с правилом и причиной; `Optional` — только когда `None` осмысленно; доменные id — `NewType`.
- Комментарии — только «почему», ссылка на ADR/issue или `TODO(имя, дата)`. Docstring — 1–2 строки, для публичного `domain/`, нетривиальных алгоритмов, сервисов. Не повторять сигнатуру, не ссылаться на текущую задачу.
- Логи: `logger = logging.getLogger(__name__)`, JSON (`core/logs/config.py`) в stdout; у запроса есть `request_id` (заголовок `x-request-id`, access-лог, запись об ошибке). Логирование уровня запроса — `core/middleware/`; в `domain/` без инфраструктуры; без паролей, токенов, платёжных данных и ПД. Ошибки, требующие алерта, — в Sentry, когда подключим.

Красные флаги: копипаста «чтобы не трогать рабочее», `utils.py`/`helpers.py` без темы, классы-менеджеры на 500 строк, глобальные изменяемые переменные, `import *`, `# noqa`/`# type: ignore` без правила и причины, закомментированный код, запросы к БД из роутов/шаблонов.

## 11. Stateless и конкурентность

Приложение должно работать в N инстансах:

- Никакого состояния в памяти процесса, кроме неизменяемых кэшей при старте. Кэш данных — только Redis; `lru_cache` — только для чистых функций без I/O.
- Сессии пользователей — JWT в HttpOnly-cookie со скользящим продлением (`core/middleware/session.py`). Файлы пользователя — сразу в S3, не на диск.
- Критические секции — `SELECT … FOR UPDATE` или Redis-lock, не `asyncio.Lock`. Фоновые задачи идемпотентны (ключ идемпотентности, `ON CONFLICT DO NOTHING`).
- Не закладываем заранее: реплики (появятся — `get_write_session`/`get_read_session`, код на DI не меняется), шардирование, 2PC/Saga, свои брокеры, event sourcing.

## 12. Безопасность и админка

- Права — на уровне роутера: `APIRouter(dependencies=[Depends(require_admin)])` (или `require_moder_or_higher`) и в `api/admin/`, и в `web/admin/`; уровень действия — `Depends(require_role(...))` из `core/admin/permissions.py`. Никаких `if user.role == ...` в роутах. Вход один — `core/auth/` (API) и `web/dependencies.py` (сайт).
- **Изменяющие web-роуты — с `dependencies=[Depends(csrf_validate)]` на роутере** (отдельный `actions_router` / `forms_router` рядом с роутером страниц). HTMX шлёт `X-CSRF-Token` сам (`static/js/csrf.js`), обычная форма — скрытое поле `token_key`.
- Форма админки — `*Form` в `schemas/admin/v1/`, только валидация ввода; сохранение — через `domain`/`crud`, в обход доменных правил в БД не пишем. Готовые админки (SQLAdmin и т.п.) и свой «AdminBaseView» не заводим.
- Bulk-операции, импорты, экспорты — через очередь, не синхронно в роуте: роут ставит задачу и сразу отвечает, прогресс — HTMX-роутом из `web/admin/partials/`.
- Лимит запросов — в `Caddyfile`, не в приложении (своего хранилища счётчиков нет). Появится Redis — лимиты отдельных действий переедут в приложение.
- Настройки — `app/core/config.py`, вложенные через `__` (`DB__HOST` → `settings.db.host`). База — `.env.template`, поверх — `.env.local` или `.env.docker`. Новая настройка — раздел в `config.py`, ключ во всех трёх файлах с комментарием. `.env.docker` с продовыми секретами лежит в git намеренно (репозиторий приватный).

## 13. Персональные данные (152-ФЗ)

Email, имена, адреса, телефоны пользователей — ПД. Не логировать, не отдавать в публичный API сверх нужного.

## 14. Тесты, линт, проверки

- **На MVP новые тесты не пишем.** Исключение — деньги, права и видимость: ошибка там молча открывает закрытое или считает неверно. Тесты там чистые, без БД (образец — `tests/domain/admin/test_roles.py`). _TODO: перечислить такие места проекта._ Существующие тесты не удаляем.
- Не гонять весь `pytest` без нужды: только покрывающее затронутое (`make test p=tests/domain/`). Шаблоны, документация, конфиги, новые эндпоинты — без тестов. Полный прогон — по просьбе или перед релизом.
- `make lint` (Ruff + `ty`) — запускать всегда. Строка ≤ 88, кавычки одинарные (docstrings — двойные). Системные диалоги браузера ловит pre-commit-хук.
- Проверка UI-правок — в браузере.
- После MVP: unit-тесты `domain/` без БД и сети (crud мокается через DI), интеграционные — с реальным Postgres (`.env.test`); один тест — один сценарий, имя описывает поведение.

## 15. Git и прод

- Коммиты по-английски, повелительно: «add category fixture». Один коммит — одна логическая правка, рефакторинг отдельно от фичи.
- Коммитим в `main`, ветки — только для долгого рискованного рефакторинга или эксперимента. **`main` не оставляем сломанным:** каждый коммит проходит `make lint` и приложение поднимается.
- **Push в `main` = деплой на прод**: CI линт не гоняет (это `make lint` и pre-commit локально), собирает образы, копирует `docker-compose.yml`, `Caddyfile`, `.env.docker` на сервер, сервис `migrate` применяет миграции до старта `web`. Без явной просьбы не пушить.
- **Нужен рефакторинг или смена структуры за пределами фичи, чтобы обойтись без костыля, — остановись и спроси:** что тронуть, почему иначе костыль, какова цена. Решает автор: рефакторинг отдельным шагом или осознанный костыль с `TODO(имя, дата)`. Локальных мелочей внутри фичи это не касается.
- `docker/postgres/` — это бэкапы прода (pgBackRest, [docs/guide/ops/backups.md](docs/guide/ops/backups.md), [ADR 0001](docs/DECISIONS/0001-postgres-backups.md)); ломать его — ломать базу. Порт Postgres на сервере — только `127.0.0.1`, доступ — SSH-туннелем ([docs/guide/ops/dbeaver-prod.md](docs/guide/ops/dbeaver-prod.md)).
- Новый сервис в compose (Redis, Meili, воркер) — с `logging: *default-logging` и `expose`, не `ports`.

## 16. Когда сомневаешься

Неочевидное решение — ADR в `docs/DECISIONS/` (образец `0000-template.md`). Документацию библиотек (FastAPI, fastapi-users, SQLAlchemy 2.0, Pydantic v2, Alembic, HTMX, Alpine, Tailwind v4, granian, pgBackRest) смотрим через Context7 MCP (`resolve-library-id` → `query-docs`), а не по памяти.
