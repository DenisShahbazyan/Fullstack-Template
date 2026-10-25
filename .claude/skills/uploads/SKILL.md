---
name: uploads
description: Загрузка, показ и удаление файлов в S3 — store_upload/store_image, превью _thumb.webp, подписанные ссылки signed_urls_by_key, временные загрузки и claim_uploads, discard_files, чистка сирот (KEY_COLUMNS, SITE_FOLDERS), копия бакета; особенности проекта — project.md рядом. Использовать при любом новом поле с файлом, папке бакета, форме или эндпоинте с загрузкой, показе или удалении фото, переезде ключей, правке core/s3 или domain/uploads.
---

# Загрузки в S3

Этот файл и модули `core/s3/`, `core/images.py`, `domain/uploads/` (кроме `project.py`), `scripts/uploads/`, `docker/uploads-backup/`, `tests/domain/uploads/` **одинаковы во всех проектах на каркасе**. Своё у проекта — `domain/uploads/project.py`, `crud/public/stored_file.py` и **[project.md](project.md)** рядом: ADR проекта, его папки и загрузки сверх общих. Прочитать оба файла.

## Как устроено

- **Бакет приватный и у каждого проекта свой** — в проде и локально. Колонка хранит ключ (`portfolio/<uuid>.webp`), не URL; ссылка подписывается на `S3__PRESIGNED_TTL_SECONDS`.
- **Изображение** (тип — по сигнатуре) уходит в WebP не больше `S3__IMAGE_MAX_SIDE` плюс превью `<ключ>_thumb.webp` (`S3__THUMBNAIL_SIDE`). **Документ** из `DOCUMENT_TYPES` хранится как есть, без превью. Видео и всё, что больше `S3__MAX_UPLOAD_BYTES`, через сервер не идёт — браузер грузит его прямо в S3 частями.
- **Две дороги.** Форма сайта: роут сразу кладёт файл в постоянную папку. API: `POST /api/public/v1/files/upload` кладёт в `tmp/<user_id>/`, запись потом принимает ключ через `claim_uploads`.
- **Ночная чистка сирот** (сервис `uploads_sweep`, 04:30 UTC): удаляет файлы из `SITE_FOLDERS` и `tmp/`, которые старше `S3__ORPHAN_TTL_HOURS` и на которые не ссылаются `KEY_COLUMNS`/`JSON_KEY_COLUMNS`. Если сирот больше половины (при 100+ файлах), отказывается — `ImplausibleOrphanSweepError` в логе.
- **Копия бакета** — сервис `uploads_backup`, rclone к другому провайдеру, всё кроме `tmp/`. Новая папка попадает в копию сама.

## Где что

| Что | Где |
| --- | --- |
| Клиент S3 (ошибки — доменные) | `core/s3/client.py`, `s3_client` |
| Приём файла формы, WebP + превью | `core/s3/store.py`: `read_upload`, `store_upload`, `store_image` |
| Временные загрузки API | `core/s3/claim.py`: `store_tmp_upload`, `claim_uploads`, `copy_to_folder` |
| Ссылки | `core/s3/links.py`: `signed_url`, `signed_urls_by_key` |
| Удаление | `core/s3/discard.py`: `discard_files` |
| Чистка сирот | `core/s3/sweep.py`, сервис `uploads_sweep`, руками — `scripts/uploads/sweep_orphans.py` |
| Pillow вне цикла событий | `core/images.py` |
| Форматы по сигнатуре | `domain/uploads/types.py` |
| Ключи, превью, `is_pdf` | `domain/uploads/urls.py`, фильтр Jinja `thumbnail` |
| Ошибки | `domain/uploads/errors.py` |
| Папки и документы проекта | `domain/uploads/project.py` |
| Колонки с ключами | `crud/public/stored_file.py` |
| Настройки | `class S3` в `core/config.py`, ключи `S3__*` |

## Новое поле с файлом — чек-лист

1. **Папка** — константа и строка в `SITE_FOLDERS` (`project.py`). Без строки чистка папку не видит, и сироты в ней копятся навсегда. Документ без перекодирования (PDF) — тип в `DOCUMENT_TYPES`. Узкий набор форматов для поля — аргумент `allowed` у `store_upload` (например, `types.IMAGE_TYPES`).
2. **Колонка** хранит ключ (`str`), не URL. **Строка в `KEY_COLUMNS`** (`stored_file.py`); ключи внутри JSONB — колонка в `JSON_KEY_COLUMNS`. Без этого чистка удалит файлы поля через сутки.
3. **Сохранение из формы** — `stored = await store_upload(await read_upload(file), FOLDER)` в роуте до записи в БД (`stored` несёт ключ, тип и размер). Если запись не удалась — `discard_files(stored.key)` в `except SQLAlchemyError` и снова `raise`; без этого файл всё равно уберёт чистка, но через сутки. Свой `s3_client.save` — только когда превью точно не нужно.
4. **Ключ от клиента** (API) в БД как есть не пишем: только `claim_uploads(user.id, keys, FOLDER, kept=...)`. `kept` — ключи, уже привязанные к этой записи (правка). Чужой ключ — `ForeignUploadError`. Временная загрузка живёт `S3__ORPHAN_TTL_HOURS`; принятая позже — `StoredFileMissingError`.
5. **Замена или удаление** — `discard_files(*old_keys)` **после** commit; превью уходит само, ошибку хранилища функция только пишет в лог. Пока старый файл ещё кто-то видит, не удалять.
6. **Показ** — в роуте один вызов на страницу: `file_urls = await signed_urls_by_key(keys)`, не по ключу в цикле. В шаблоне `file_urls[key | thumbnail]` — сетки и карточки, `file_urls[key]` — на весь экран. PDF (`is_pdf`) — ссылкой, не `<img>`.
7. **Ошибки** — подклассы общих в `domain/errors.py`: `ValidationError` → 422 (формат, размер, чужой ключ), `UpstreamError` → 502 (`FileStorageUnavailableError`). Новая ошибка загрузок — в `domain/uploads/errors.py`, проектная — в `errors.py` субдомена.

## Переезд ключей

Переименовать папку, перенести старые ключи — скриптом в `scripts/uploads/`, не миграцией Alembic: миграция в S3 не ходит. Строки — `get_rows_with_key_prefix`, копия с превью — `copy_to_folder`, новый ключ — в колонку, commit. Исходники уберёт чистка или `discard_files` после commit. Скрипт безопасен к повтору: второй запуск ничего не находит.

## Правила

- CPU-тяжёлое (Pillow, рендер PDF) — не в цикле событий: `core/images.py` или свой модуль по его образцу.
- Тип файла — только по содержимому (`types.py`), не по имени и не по `content_type` от браузера. Лимиты: размер — `S3__MAX_UPLOAD_BYTES` (`read_upload`), мегапиксели — `MAX_IMAGE_PIXELS`.
- Ключ строит `new_key` со случайным uuid; имя файла пользователя в ключ не попадает.
- Новая настройка S3 — поле в `class S3` и ключ в `.env.template`, `.env.local`, `.env.docker` **всех трёх проектов**: модуль общий.
- Правка общего модуля — сначала в шаблоне, затем копия как есть в каждый проект, `make test p=tests/domain/uploads/` и `make lint` в каждом. Проектное в общий модуль не вносить — оно идёт в `project.py` или свой модуль проекта.
- В `.env.local` — только dev-бакет своего проекта: чистка, запущенная локально, удалит в нём всё, на что не ссылается локальная база.

## Эксплуатация

Перед первой чисткой на новом бакете и после правки `KEY_COLUMNS` — просмотр без удаления:

```bash
sudo docker compose --env-file .env.docker exec -T web \
    python -m scripts.uploads.sweep_orphans --dry-run < /dev/null > sweep.txt
head -40 sweep.txt
```

`< /dev/null` нужен при `-T`: без него `exec` ждёт ввода с терминала и может не завершиться. Независимая сверка сирот с базой — поиск их uuid в `pg_dump --data-only`. Чистка отказалась удалять — разобрать список, затем `sweep_orphans --force`.

Копия бакета и восстановление — [docs/guide/ops/uploads-backups.md](../../../docs/guide/ops/uploads-backups.md).
