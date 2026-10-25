# rclone + curl для алерта. Образ нужен как свой, а не готовый rclone/rclone:
# на сервер копируется только docker-compose.yml, скрипту расписания там лежать негде.
FROM rclone/rclone:1.75.2

RUN apk add --no-cache curl

COPY bin/ /usr/local/bin/
RUN chmod 755 /usr/local/bin/uploads-*

ENTRYPOINT []
