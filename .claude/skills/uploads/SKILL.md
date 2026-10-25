---
name: uploads
description: Загрузка, показ и удаление файлов в S3 — store_upload/store_image, превью _thumb.webp, подписанные ссылки signed_urls_by_key, временные загрузки и claim_uploads, discard_files, чистка сирот (KEY_COLUMNS, SITE_FOLDERS), копия бакета. Использовать при любом новом поле с файлом, папке бакета, форме или эндпоинте с загрузкой, показе фото.
---

# Загрузки в S3

Решение и причины — [ADR 0002 шаблона](../../../docs/DECISIONS/0002-s3-uploads.md). Модули в `core/s3/`, `core/images.py`, `domain/uploads/` (кроме `project.py`), `scripts/uploads/`, `docker/uploads-backup/` **одинаковы во всех проектах на каркасе**: правятся в шаблоне и переносятся как есть. Своё у проекта — только `domain/uploads/project.py` и `crud/public/stored_file.py`.

## Где что

| Что | Где |
| --- | --- |
| Клиент S3 (ошибки — доменные) | `core/s3/client.py`, `s3_client` |
| Приём файла формы, WebP + превью | `core/s3/store.py`: `read_upload`, `store_upload`, `store_image` |
| Временные загрузки API | `core/s3/claim.py`, `POST /api/public/v1/files/upload` |
| Ссылки | `core/s3/links.py`: `signed_url`, `signed_urls_by_key` |
| Удаление | `core/s3/discard.py`: `discard_files` |
| Чистка сирот | `core/s3/sweep.py`, сервис `uploads_sweep`, руками — `scripts/uploads/sweep_orphans.py` |
| Форматы по сигнатуре | `domain/uploads/types.py` |
| Папки и документы проекта | `domain/uploads/project.py` |
| Колонки с ключами | `crud/public/stored_file.py` |

## Новое поле с файлом — чек-лист

1. **Папка** — константа и строка в `SITE_FOLDERS` (`project.py`). Документы без перекодирования (PDF) — тип в `DOCUMENT_TYPES`.
2. **Колонка** хранит ключ (`str`), не URL. **Строка в `KEY_COLUMNS`** (`stored_file.py`); ключи внутри JSONB — колонка в `JSON_KEY_COLUMNS`. Без этого ночная чистка удалит файлы как сироты.
3. **Сохранение из формы** — `(await store_upload(await read_upload(file), FOLDER)).key` в роуте до записи в БД (`StoredUpload` несёт ещё тип и размер сохранённого). Свой `s3_client.save` — только если превью точно не нужно.
4. **Ключ от клиента** (API) в БД как есть не пишем: только `claim_uploads(user.id, keys, FOLDER, kept=...)`. `kept` — ключи, уже привязанные к этой записи (правка). Чужой ключ — `ForeignUploadError`.
5. **Замена или удаление** — `discard_files(*old_keys)` **после** commit; превью уходит само. Если файл ещё виден (правка ушла на модерацию) — не удалять.
6. **Показ** — в роуте `file_urls = await signed_urls_by_key(keys)`, в шаблоне `file_urls[key | thumbnail]` для сеток и карточек, `file_urls[key]` — на весь экран.

## Правила

- CPU-тяжёлое (Pillow, рендер PDF) — не в цикле событий: `core/images.py` или свой модуль по его образцу.
- Тип файла — только по содержимому (`types.py`), не по имени и не по `content_type` от браузера.
- Бакет у проекта свой и локально. В `.env.local` — dev-бакет проекта: чистка, запущенная локально, удалит в нём всё, на что не ссылается локальная база.
- Лимит размера — `S3__MAX_UPLOAD_BYTES` (`read_upload`). Мегапиксели — `MAX_IMAGE_PIXELS`.

## Эксплуатация

Копия бакета и восстановление — [docs/guide/ops/uploads-backups.md](../../../docs/guide/ops/uploads-backups.md). Перед первой ночной чисткой на новом бакете: `python -m scripts.uploads.sweep_orphans --dry-run`.
