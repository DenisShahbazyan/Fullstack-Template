---
name: uploads
description: Загрузка, показ и удаление файлов в S3 — store_upload/store_image, превью _thumb.webp, подписанные ссылки signed_urls_by_key, временные загрузки и claim_uploads, discard_files, чистка сирот (пометка колонок file_folder), копия бакета, галерея в браузере (плитки с прогрессом, обложка, порядок перетаскиванием); особенности проекта — project.md рядом. Использовать при любом новом поле с файлом, папке бакета, форме или эндпоинте с загрузкой, галерее фото, показе или удалении фото, переезде ключей, правке core/s3 или domain/uploads.
---

# Загрузки в S3

Этот файл и модули `core/s3/`, `core/images.py`, `domain/uploads/` (кроме `project.py`), `scripts/uploads/`, `docker/uploads-backup/`, `tests/domain/uploads/`, а также галерея — `static/js/gallery-upload.js`, `gallery-draft.js`, `drag-sort.js`, `tailwind/gallery.css`, `templates/public/macros/gallery_upload.html` — **одинаковы во всех проектах на каркасе**. Своё у проекта — `domain/uploads/project.py`, пометки `file_folder` на колонках моделей и **[project.md](project.md)** рядом: ADR проекта, его папки и загрузки сверх общих. Прочитать оба файла.

## Как устроено

- **Бакет приватный и у каждого проекта свой** — в проде и локально. Колонка хранит ключ (`portfolio/<uuid>.webp`), не URL; ссылка подписывается на `S3__PRESIGNED_TTL_SECONDS`.
- **Изображение** (тип — по сигнатуре) уходит в WebP не больше `S3__IMAGE_MAX_SIDE` плюс превью `<ключ>_thumb.webp` (`S3__THUMBNAIL_SIDE`). **Документ** из `DOCUMENT_TYPES` хранится как есть, без превью. Видео и всё, что больше `S3__MAX_UPLOAD_BYTES`, через сервер не идёт — браузер грузит его прямо в S3 частями.
- **Две дороги.** Форма сайта: роут сразу кладёт файл в постоянную папку. API: `POST /api/public/v1/files/upload` кладёт в `tmp/<user_id>/`, запись потом принимает ключ через `claim_uploads`.
- **Ночная чистка сирот** (сервис `uploads_sweep`, 04:30 UTC): удаляет файлы из папок помеченных колонок и `tmp/`, которые старше `S3__ORPHAN_TTL_HOURS` и на которые не ссылаются колонки с пометкой `file_folder`/`file_keys_in_json`. Колонки и папки чистка находит сама в метаданных моделей. Если сирот больше половины (при 100+ файлах), отказывается — `ImplausibleOrphanSweepError` в логе.
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
| Пометка колонок с ключами | `models/file_keys.py`: `file_folder`, `file_keys_in_json`, `folder_of` |
| Ключи, на которые ссылается база | `crud/public/stored_file.py` |
| Настройки | `class S3` в `core/config.py`, ключи `S3__*` |
| Галерея в браузере | макросы `templates/public/macros/gallery_upload.html`, `static/js/gallery-*.js`, `drag-sort.js`, `tailwind/gallery.css` (ADR проекта — в project.md) |

## Новое поле с файлом — чек-лист

1. **Папка** — константа в `project.py`. Документ без перекодирования (PDF) — тип в `DOCUMENT_TYPES`. Узкий набор форматов для поля — аргумент `allowed` у `store_upload` (например, `types.IMAGE_TYPES`).
2. **Колонка** хранит ключ (`str`), не URL, и **помечена**: `mapped_column(info=file_folder(FOLDER), ...)` (`models/file_keys.py`). По пометке чистка обходит папку и сверяет её файлы с колонкой: без пометки папку она не видит, и сироты в ней копятся. JSONB, где среди значений бывают ключи, — `info=file_keys_in_json()`. Модель — в `app/models/__init__.py` (это и так нужно миграциям): иначе её колонок чистка не видит, а файлы в общей с другой колонкой папке удалит. Две колонки в одной папке — помечены обе.
3. **Сохранение из формы** — `stored = await store_upload(await read_upload(file), FOLDER)` в роуте до записи в БД (`stored` несёт ключ, тип и размер). Если запись не удалась — `discard_files(stored.key)` в `except SQLAlchemyError` и снова `raise`; без этого файл всё равно уберёт чистка, но через сутки. Свой `s3_client.save` — только когда превью точно не нужно.
4. **Ключ от клиента** (API) в БД как есть не пишем: только `claim_uploads(user.id, keys, FOLDER, kept=...)`. `kept` — ключи, уже привязанные к этой записи (правка). Чужой ключ — `ForeignUploadError`. Временная загрузка живёт `S3__ORPHAN_TTL_HOURS`; принятая позже — `StoredFileMissingError`.
5. **Замена или удаление** — `discard_files(*old_keys)` **после** commit; превью уходит само, ошибку хранилища функция только пишет в лог. Пока старый файл ещё кто-то видит, не удалять.
6. **Показ** — в роуте один вызов на страницу: `file_urls = await signed_urls_by_key(keys)`, не по ключу в цикле. В шаблоне `file_urls[key | thumbnail]` — сетки и карточки, `file_urls[key]` — на весь экран. PDF (`is_pdf`) — ссылкой, не `<img>`.
7. **Ошибки** — подклассы общих в `domain/errors.py`: `ValidationError` → 422 (формат, размер, чужой ключ), `UpstreamError` → 502 (`FileStorageUnavailableError`). Новая ошибка загрузок — в `domain/uploads/errors.py`, проектная — в `errors.py` субдомена.

## Галерея в браузере

Любая форма с фото — общий компонент, не свой JS. У каждого файла своя плитка в сетке: превью, полоса, проценты, крестик отмены; обложка — звёздочкой, на месте; порядок — перетаскиванием (на телефоне — долгим нажатием); файлы можно бросить на галерею мышью. Фото больше 2560 px или 2 МБ браузер ужимает до отправки. Образцы разметки — в шапке `gallery.html`.

**Запись уже есть** — всё сразу на сервере, ответ каждого роута — partial галереи (корень с `id`, `class="contents"`, `data-drag-sort="<url порядка>"`):

| Роут | Принимает | Отвечает |
| --- | --- | --- |
| `POST …/images` | поле `file` — **один** файл на запрос | partial галереи |
| `POST …/images/order` | `order` — id всех плиток по порядку | partial галереи |
| `POST …/images/{id}/cover` | — | partial галереи, **порядок плиток прежний** |
| `POST …/images/{id}/delete` | — | partial галереи |

Удаление спрашивает подтверждения окном `confirm_dialog` из `templates/public/macros/modal.html` — макрос каркаса, он должен быть в проекте. Роуты — в `actions_router` с `csrf_validate` (токен шлёт заголовком и сам загрузчик). Ошибка — доменное исключение: `web/errors.py` отдаст её тостом, загрузчик покажет текст на плитке. Плитка — `gallery_ui.tile(id, file_urls[key | thumbnail], is_cover=...)` с `cover_form` и `delete_form` внутри.

**Записи ещё нет (черновик)** — обёртка с `data-gallery-draft`, файл — в `tmp/` автора (`store_tmp_upload`), ответ — `gallery_ui.draft_tile(key, url, 'image_keys')`, вставка `beforeend` в контейнер плиток с пустым `data-drag-sort`. Порядок — порядок полей `image_keys`, обложка — `gallery_ui.draft_cover_input('cover_key')`; без выбора обложка — первое фото. Сохранение формы — `claim_uploads(user.id, keys, FOLDER)`. Ошибка ввода в остальной форме — перерисовать черновик из присланных ключей, отфильтровав чужие (`tmp_owner`).

Своя дорога для типа, который формой не отправить (видео частями в S3), — `galleryUpload.register({ accepts, problem, upload })` в проектном скрипте: `upload` сам вставляет файл в галерею и завершается, когда он там.

## Переезд ключей

Переименовать папку, перенести старые ключи — скриптом в `scripts/uploads/`, не миграцией Alembic: миграция в S3 не ходит. Строки — `get_rows_with_key_prefix`, копия с превью — `copy_to_folder`, новый ключ — в колонку, commit. Исходники — `discard_files` после commit: старую папку, у которой не осталось помеченной колонки, чистка не обходит. Скрипт безопасен к повтору: второй запуск ничего не находит.

## Правила

- CPU-тяжёлое (Pillow, рендер PDF) — не в цикле событий: `core/images.py` или свой модуль по его образцу.
- Тип файла — только по содержимому (`types.py`), не по имени и не по `content_type` от браузера. Лимиты: размер — `S3__MAX_UPLOAD_BYTES` (`read_upload`), мегапиксели — `MAX_IMAGE_PIXELS`.
- Ключ строит `new_key` со случайным uuid; имя файла пользователя в ключ не попадает.
- Новая настройка S3 — поле в `class S3` и ключ в `.env.template`, `.env.local`, `.env.docker` **всех трёх проектов**: модуль общий.
- Правка общего модуля — сначала в шаблоне, затем копия как есть в каждый проект, `make test p=tests/domain/uploads/` и `make lint` в каждом. Проектное в общий модуль не вносить — оно идёт в `project.py` или свой модуль проекта.
- В `.env.local` — только dev-бакет своего проекта: чистка, запущенная локально, удалит в нём всё, на что не ссылается локальная база.

## Эксплуатация

Перед первой чисткой на новом бакете и после правки пометок `file_folder` — просмотр без удаления:

```bash
sudo docker compose --env-file .env.docker exec -T web \
    python -m scripts.uploads.sweep_orphans --dry-run < /dev/null > sweep.txt
head -40 sweep.txt
```

`< /dev/null` нужен при `-T`: без него `exec` ждёт ввода с терминала и может не завершиться. Независимая сверка сирот с базой — поиск их uuid в `pg_dump --data-only`. Чистка отказалась удалять — разобрать список, затем `sweep_orphans --force`.

Копия бакета и восстановление — [docs/guide/ops/uploads-backups.md](../../../docs/guide/ops/uploads-backups.md).
