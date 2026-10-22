FROM python:3.14.3-slim

ENV PYTHONUNBUFFERED=1
ARG TAILWIND_VERSION=v4.2.2

# postgresql-client — pg_isready для scripts/migrate.sh, curl — скачать Tailwind.
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client curl ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Установка uv
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh
ENV PATH="/root/.local/bin/:$PATH"

# Сначала зависимости — слой кешируется пока lock-файл не меняется
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY . .

# Tailwind-бинарь под архитектуру контейнера и сборка CSS
RUN ARCH="$(dpkg --print-architecture)" \
    && case "$ARCH" in \
         amd64) TW_ASSET=tailwindcss-linux-x64 ;; \
         arm64) TW_ASSET=tailwindcss-linux-arm64 ;; \
         *) echo "Unsupported arch: $ARCH" && exit 1 ;; \
       esac \
    && curl -fsSL -o tailwind/tailwindcss \
         "https://github.com/tailwindlabs/tailwindcss/releases/download/${TAILWIND_VERSION}/${TW_ASSET}" \
    && chmod +x tailwind/tailwindcss \
    && tailwind/tailwindcss -i tailwind/input.css -o static/css/app.css --minify

EXPOSE 8000

RUN chmod +x /app/scripts/migrate.sh /app/scripts/start.sh

# Создаём непривилегированного пользователя
RUN groupadd --system appgroup \
    && useradd --system --gid appgroup --no-create-home appuser \
    && chown -R appuser:appgroup /app

# Помещаем скрипты в PATH, чтобы их можно было запускать без uv run
ENV PATH="/app/.venv/bin:$PATH"

USER appuser:appgroup
