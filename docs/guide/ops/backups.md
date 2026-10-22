# Бэкапы Postgres

Бэкапы делает [pgBackRest](https://pgbackrest.org/), хранятся они в S3. Каждые сутки снимается полный бэкап, а между бэкапами непрерывно архивируются WAL-журналы. Поэтому базу можно вернуть не только на 03:00, но и на любой момент последних 7 дней: например, на минуту до случайного `DELETE`. Почему выбран такой вариант, описано в [ADR 0001](../../DECISIONS/0001-postgres-backups.md).

## Как устроено

| Что | Где |
| --- | --- |
| Образ Postgres с pgBackRest | [docker/postgres/Dockerfile](../../../docker/postgres/Dockerfile), собирается в CI, на сервер приходит как `<DOCKER_USERNAME>/<DOCKER_IMAGE_NAME>-postgres:latest` |
| Общие настройки pgBackRest | [docker/postgres/pgbackrest.conf](../../../docker/postgres/pgbackrest.conf), вшиты в образ |
| Ключи S3 и пароль шифрования | раздел `BACKUPS` в [.env.docker](../../../.env.docker) |
| Архивация WAL | `command` сервиса `db` в [docker-compose.yml](../../../docker-compose.yml) |
| Расписание бэкапов и проверок | сервис `backup` (контейнер `postgres_backup`), скрипт `pg-backup-scheduler` |

Что происходит:

- **Postgres** отправляет WAL в S3 сам, через `archive_command`, по мере заполнения сегментов и не реже раза в 5 минут (`archive_timeout`). Это и задаёт худший случай потери данных: около 5 минут.
- **Раз в сутки**, вскоре после 00:00 UTC (03:00 МСК), `backup` снимает полный бэкап и запускает `pgbackrest check`. `check` убеждается, что WAL реально доезжает до S3. pgBackRest хранит 7 последних полных бэкапов и сам удаляет более старые вместе с их WAL.
- **По воскресеньям и после самого первого бэкапа** `backup` восстанавливает свежий бэкап во временный каталог и проверяет, что база стартует. Рабочую базу он не трогает.

Отметку «сегодня бэкап уже был» сервис берёт из самого репозитория. Поэтому перезапуск при деплое бэкап не повторяет, а пропущенный (сервер был выключен) бэкап снимется сразу после старта.

Бэкапы шифруются (AES-256) до отправки, поэтому провайдер S3 видит только шифрованные файлы.

Бэкапится только Postgres. Если в проекте появятся Meilisearch или Redis — их не бэкапим: индекс пересобирается из БД, а очередь задач и кэш восстанавливать незачем.

## Включение

На сервере ничего делать не нужно.

1. У S3-провайдера (Timeweb Cloud, Yandex Object Storage и т.п.) создайте **отдельный приватный бакет** для бэкапов и **отдельный ключ доступа** к нему. Ключ от бакета загрузок не подходит: если он утечёт, он не должен давать доступ к бэкапам.
2. Заполните раздел `BACKUPS` в `.env.docker`. Пароль шифрования сгенерируйте командой `openssl rand -base64 48` и **сохраните в менеджер паролей**: без него бэкап не расшифровать.
3. Для алертов заведите heartbeat в [Better Stack](https://betterstack.com) (Uptime → Heartbeats) с периодом 1 день и запасом 2 часа и впишите его адрес в `BACKUP_PING_URL`. Подойдёт любой сервис, где запрос на адрес означает «успех», а на `адрес/fail` — «сбой». Если бэкап или проверка восстановления упадёт либо вовсе не запустится, придёт письмо.
4. Запушьте в `main`. Сразу после деплоя `backup` создаст репозиторий в бакете, снимет первый бэкап и проверит восстановление.

Убедиться, что всё заработало:

```sh
sudo docker logs postgres_backup     # в конце: «Восстановление прошло успешно.»
```

Пока раздел `BACKUPS` пустой, `backup` пишет в лог «бэкапы выключены» и ничего не делает. Но архивация WAL в `db` всё равно включена и будет падать, а WAL — копиться на диске. Поэтому не оставляйте раздел пустым надолго.

## Повседневное

```sh
# Список бэкапов и диапазон WAL в архиве
sudo docker exec postgres_backup pgbackrest --stanza=main info

# Бэкап или проверка восстановления вне расписания
sudo docker exec postgres_backup pg-backup
sudo docker exec postgres_backup pg-restore-check

# Доезжает ли WAL: failed_count не должен расти, last_archived_time — свежий
sudo docker exec postgres sh -c 'psql -U "$POSTGRES_USER" -d postgres -c "SELECT archived_count, last_archived_time, failed_count, last_failed_wal, last_failed_time FROM pg_stat_archiver;"'

# Размер pg_wal: если S3 недоступен, WAL копится здесь
sudo docker exec postgres sh -c 'du -sh "$PGDATA/pg_wal"'
```

**Если архивация сломалась** (ключ отозван, бакет удалён, S3 недоступен), Postgres не теряет WAL, а копит его в `pg_wal`, пока не доставит. База продолжает работать, но диск постепенно заполняется. Ночной `check` упадёт, и придёт алерт. Причину ищите в `docker logs postgres` по строкам `archive command failed`.

**Проверка восстановления** временно занимает на диске ещё столько же, сколько весит база: копия разворачивается внутри контейнера `postgres_backup` и удаляется после проверки.

## Восстановление продакшена

Сценарий: в 20:07 случайно удалили данные, нужно вернуть состояние на 20:04.

Время указывайте **с часовым поясом**: в контейнерах UTC, и без пояса `20:04` поймётся как UTC.

```sh
cd /home/<SERVER_USER>/<DOCKER_IMAGE_NAME>
IMAGE=$(sudo docker inspect -f '{{.Config.Image}}' postgres)
VOLUME=$(sudo docker inspect -f '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql"}}{{.Name}}{{end}}{{end}}' postgres)
TARGET="2026-10-17 20:04:00+03"
```

**1. Проверьте момент на копии.** Это безопасно: копия разворачивается во временном каталоге, рабочую базу команда не трогает. В выводе есть строка `recovery stopping before ...`: в ней видно, перед какой транзакцией остановится восстановление.

```sh
sudo docker exec postgres_backup pg-restore-check "$TARGET"
```

**2. Остановите запись в базу**, а затем саму базу:

```sh
sudo docker compose --env-file .env.docker stop web backup
sudo docker compose --env-file .env.docker stop db
```

**3. Сохраните текущее состояние volume.** Если ошиблись с моментом, к нему можно будет вернуться:

```sh
sudo docker run --rm --entrypoint cp -v "$VOLUME":/from -v "${VOLUME}_before_restore":/to "$IMAGE" -a /from/. /to/
```

**4. Восстановите.** Флаг `--delta` перезаписывает только отличающиеся файлы:

```sh
sudo docker run --rm -u postgres --env-file .env.docker \
    -v "$VOLUME":/var/lib/postgresql "$IMAGE" \
    pgbackrest --stanza=main --delta --type=time --target="$TARGET" --target-action=promote restore
```

**5. Запустите базу и проверьте данные** (через DBeaver или `psql`):

```sh
sudo docker compose --env-file .env.docker start db
sudo docker logs -f postgres     # ждём "database system is ready to accept connections"
```

**6. Верните сайт.** Если в проекте есть поисковый индекс (Meili) — пересоберите его: в нём остались документы новее восстановленной базы.

```sh
sudo docker compose --env-file .env.docker start web backup
```

**7. Сразу снимите новый бэкап.** После восстановления база живёт на новом timeline, и прежние бэкапы для неё — история. Сам `backup` этого не сделает: бэкап за сегодня в репозитории уже есть.

```sh
sudo docker exec postgres_backup pg-backup
```

Через несколько дней, убедившись, что всё в порядке, удалите `${VOLUME}_before_restore`.

**Восстановление на последний момент**, например когда умер сам сервер, — те же шаги, но без `--type`, `--target` и `--target-action`. На новом сервере шаг 3 не нужен, а `--delta` ничего не меняет.

## Разное

- **`WARN: unknown group 'root' in backup manifest`** при восстановлении безопасен: у части файлов каталога данных группа root, и pgBackRest сообщает, что заменил её группой postgres.
- **Сжатие — `lz4`, а не `zst`**: в Alpine-сборку pgBackRest `zst` не включён, и бэкап с ним падает.
- **Сколько хранить** задаёт `repo1-retention-full` в `pgbackrest.conf`. После изменения нужен деплой.
- **Обновление Postgres до новой major-версии** (18 → 19) меняет каталог данных и требует `pgbackrest stanza-upgrade`. Это отдельная работа, а не просто смена `FROM`.
