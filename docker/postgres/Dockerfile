# Официальный Postgres + pgBackRest. Утилита нужна именно в контейнере базы:
# archive_command запускает сам Postgres, и pgBackRest должен лежать рядом.
FROM postgres:18.0-alpine

RUN apk add --no-cache "pgbackrest~2.55" curl jq

COPY pgbackrest.conf /etc/pgbackrest/pgbackrest.conf
COPY bin/ /usr/local/bin/
RUN chmod 755 /usr/local/bin/pg-*
