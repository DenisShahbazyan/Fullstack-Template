#!/bin/sh

granian \
    --interface asgi \
    --host 0.0.0.0 \
    --port 8000 \
    --loop uvloop \
    --no-ws \
    --respawn-failed-workers \
    --access-log \
    --access-log-fmt '%(method)s %(path)s %(status)d' \
    app.asgi:app
