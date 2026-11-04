#!/bin/sh
# Деплой на сервере без остановки сайта. Запускает CI из каталога проекта
# под sudo, рядом лежат docker-compose.yml, Caddyfile и .env.docker.
#
# web обновляется по очереди: новые экземпляры поднимаются рядом со старыми,
# Caddy находит их по DNS Docker (refresh 5s в Caddyfile), старые гасятся
# после этого. Остальное — обычный up -d: пересоздаётся только изменившееся.
set -eu

# env_file отдаёт значения только внутрь контейнера, а ${...} в самом
# compose-файле берётся из --env-file; sudo вычищает окружение — файл явно.
compose() { docker compose --env-file .env.docker "$@"; }
env_value() { grep -E "^$1=" .env.docker | tail -1 | cut -d= -f2- | tr -d "\"'\r"; }

# Caddy обновляет список экземпляров раз в 5 секунд, берём с запасом.
CADDY_REFRESH_SECONDS=7
WAIT_SECONDS=180

compose pull

# 1. Всё, кроме web и caddy. up сам ждёт migrate (uploads_sweep и воркеры
# от него зависят), поэтому миграции применены до нового кода web.
# Без --wait: migrate завершается, и --wait счёл бы это сбоем.
# shellcheck disable=SC2046 # имена сервисов — отдельные аргументы
compose up -d --remove-orphans $(compose config --services | grep -vxE 'web|caddy')

# 2. web по очереди. Первый деплой — просто поднять.
web_replicas=$(env_value WEB_REPLICAS)
web_replicas=${web_replicas:-1}
old_web=$(compose ps -q web)
old_count=$(echo "$old_web" | grep -c . || true)
compose up -d --no-deps --no-recreate --wait --wait-timeout "$WAIT_SECONDS" \
    --scale "web=$((old_count + web_replicas))" web
if [ -n "$old_web" ]; then
    sleep "$CADDY_REFRESH_SECONDS"
    # SIGTERM: granian дописывает начатые ответы.
    # shellcheck disable=SC2086 # список id — отдельные аргументы
    docker stop $old_web >/dev/null
    # shellcheck disable=SC2086
    docker rm $old_web >/dev/null
fi

# 3. Caddy читает Caddyfile с диска при старте, а CI заменяет файл новым:
# привязанный к контейнеру файл остался бы прежним. Пересоздаём, только
# если файл изменился, — это секунда простоя на смену конфига.
if ! sha256sum --check --status .Caddyfile.sha256 2>/dev/null; then
    compose up -d --no-deps --force-recreate caddy
    sha256sum Caddyfile > .Caddyfile.sha256
else
    compose up -d --no-deps caddy
fi

# Пуш перезаписывает тег :latest, и предыдущий образ остаётся на диске без
# тега. За десяток деплоев это гигабайты. Без -a: чистим только dangling,
# образы с тегами (postgres, caddy и т.п.) нужны.
docker image prune -f
