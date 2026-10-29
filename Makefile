TAILWIND_VERSION := v4.2.2
TAILWIND_BIN := tailwind/tailwindcss

UNAME_S := $(shell uname -s)
UNAME_M := $(shell uname -m)

ifeq ($(UNAME_S),Darwin)
    ifeq ($(UNAME_M),arm64)
        TAILWIND_ASSET := tailwindcss-macos-arm64
    else
        TAILWIND_ASSET := tailwindcss-macos-x64
    endif
else
    ifeq ($(UNAME_M),aarch64)
        TAILWIND_ASSET := tailwindcss-linux-arm64
    else
        TAILWIND_ASSET := tailwindcss-linux-x64
    endif
endif

TAILWIND_URL := https://github.com/tailwindlabs/tailwindcss/releases/download/$(TAILWIND_VERSION)/$(TAILWIND_ASSET)

.PHONY: help tailwind css css-watch build dev migrate revision lint test admin docker-up docker-down clean

help:
	@echo "Доступные команды:"
	@echo "  make tailwind      — скачать tailwind-бинарь для текущей платформы"
	@echo "  make css           — собрать static/css/app.css"
	@echo "  make css-watch     — собирать CSS в watch-режиме"
	@echo "  make build         — собрать CSS (всё, что нужно перед запуском)"
	@echo "  make dev           — пересобрать всё и запустить granian с reload (локально)"
	@echo "  make migrate       — применить миграции"
	@echo "  make revision m=…  — автогенерировать миграцию из моделей"
	@echo "  make lint          — ruff (линт + формат) и ty"
	@echo "  make test p=…      — pytest по пути (по умолчанию весь tests/)"
	@echo "  make admin e=… p=… — создать администратора"
	@echo "  make docker-up     — поднять прод-сборку локально (docker-compose-dev.yml)"
	@echo "  make docker-down   — остановить её"
	@echo "  make clean         — удалить билд-артефакты"

$(TAILWIND_BIN):
	@echo "Скачиваю $(TAILWIND_ASSET) ($(TAILWIND_VERSION))..."
	curl -fsSL -o $(TAILWIND_BIN) $(TAILWIND_URL)
	chmod +x $(TAILWIND_BIN)

# Скачать tailwind-бинарь. Если файл уже есть, make пропустит правило.
tailwind: $(TAILWIND_BIN)

css: $(TAILWIND_BIN)
	$(TAILWIND_BIN) -i tailwind/input.css -o static/css/app.css --minify
	@# Tailwind не ставит перевод строки в конце, а pre-commit его требует.
	@printf '\n' >> static/css/app.css

css-watch: $(TAILWIND_BIN)
	$(TAILWIND_BIN) -i tailwind/input.css -o static/css/app.css --watch

build: css

dev: build
	uv run granian --interface asgi --reload --access-log app.main:app

migrate:
	uv run alembic upgrade head

revision:
	@test -n "$(m)" || (echo 'Укажите описание: make revision m="add item"' && exit 1)
	uv run alembic revision --autogenerate -m "$(m)"

lint:
	uv run ruff check app tests scripts
	uv run ruff format --check app tests scripts
	uv run ty check app

test:
	uv run pytest $(p)

admin:
	uv run python -m scripts.users.create_user "$(e)" --role admin $(if $(p),--password "$(p)")

# --env-file нужен для подстановки ${...} в самом compose-файле: env_file
# отдаёт переменные только внутрь контейнеров.
docker-up:
	docker compose --env-file .env.docker -f docker-compose-dev.yml up -d --build

docker-down:
	docker compose --env-file .env.docker -f docker-compose-dev.yml down

clean:
	rm -f static/css/app.css
