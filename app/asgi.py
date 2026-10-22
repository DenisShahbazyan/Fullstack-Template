"""Точка входа granian в проде: приложение стоит за Caddy.

granian не разбирает X-Forwarded-* сам (флага для этого нет), и без обёртки
приложение видит схему http и адрес Caddy: canonical и sitemap уходят с
http://, а лимит запросов считается один на всех клиентов. Порт приложения
наружу не опубликован (expose в docker-compose), поэтому доверяем только
частным сетям — там живёт Caddy.
"""

from granian.utils.proxies import wrap_asgi_with_proxy_headers

from app.main import app as fastapi_app

PRIVATE_NETWORKS = ['10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16']

app = wrap_asgi_with_proxy_headers(fastapi_app, trusted_hosts=PRIVATE_NETWORKS)
