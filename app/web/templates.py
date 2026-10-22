from fastapi import Request
from fastapi.templating import Jinja2Templates
from fastapi_csrf_protect import CsrfProtect
from itsdangerous import BadData, URLSafeTimedSerializer

from app.core.config import APP_DIR, settings
from app.core.csrf import CSRF_SALT
from app.web.toast_params import TOAST_KIND_PARAM, TOAST_PARAM

templates = Jinja2Templates(directory=str(APP_DIR / 'templates'))
# Необязательные поля (фамилия, email) приходят как None, а Jinja печатает его
# строкой «None». Пустое значение на странице — это пусто, а не слово.
templates.env.finalize = lambda value: '' if value is None else value


def _ru_plural(count: int, forms: str) -> str:
    """`forms` — три формы через `|`: «запись|записи|записей»."""
    one, few, many = forms.split('|')
    n = abs(count) % 100
    if 11 <= n <= 14:
        return many
    rem = n % 10
    if rem == 1:
        return one
    if 2 <= rem <= 4:
        return few
    return many


def _static_version(path: str) -> str:
    """Новая версия файла меняет URL, чтобы браузер не взял его из кэша.

    Скрипт со старым кэшем ломает свежую разметку: Alpine ищет в нём то, что
    добавила новая версия шаблона, и форма перестаёт работать.
    Несобранный файл (app.css до `make css` — в тестах и свежем клоне) не роняет
    страницу: версия просто нулевая.
    """
    file = settings.static.DIR / path
    return str(file.stat().st_mtime_ns) if file.exists() else '0'


def _full_name(user: object) -> str:
    """Имя пользователя для показа: без лишних пробелов, email — если имени нет."""
    parts = (getattr(user, 'first_name', None), getattr(user, 'last_name', None))
    return ' '.join(part for part in parts if part) or getattr(user, 'email', '')


def _canonical_for(request: Request, path: str) -> str:
    """Абсолютный URL для canonical: scheme + host + path."""
    return f'{request.url.scheme}://{request.url.netloc}{path}'


templates.env.filters['ru_plural'] = _ru_plural
templates.env.filters['full_name'] = _full_name
templates.env.globals['static_version'] = _static_version  # ty: ignore[invalid-assignment]
templates.env.globals['canonical_for'] = _canonical_for  # ty: ignore[invalid-assignment]
templates.env.globals['site_name'] = settings.site.NAME  # ty: ignore[invalid-assignment]


def _reuse_csrf_token(request: Request, csrf: CsrfProtect) -> tuple[str, str] | None:
    signed = request.cookies.get(csrf._cookie_key)
    if not signed:
        return None
    serializer = URLSafeTimedSerializer(csrf._secret_key, salt=CSRF_SALT)
    try:
        token = serializer.loads(signed, max_age=csrf._max_age)
    except BadData:
        return None
    return token, signed


def render(
    request: Request,
    name: str,
    context: dict | None = None,
    *,
    status_code: int = 200,
):
    csrf = CsrfProtect()
    reused = _reuse_csrf_token(request, csrf)
    if reused is None:
        csrf_token, signed_token = csrf.generate_csrf_tokens()
    else:
        csrf_token, signed_token = reused
    ctx = {
        'request': request,
        'csrf_token': csrf_token,
        # Сообщение из ?toast= показывается на любой странице: редирект не
        # может донести заголовок, а ставить проверку в каждый роут — не дело.
        'toast': request.query_params.get(TOAST_PARAM),
        'toast_kind': request.query_params.get(TOAST_KIND_PARAM, 'error'),
        **(context or {}),
    }
    response = templates.TemplateResponse(request, name, ctx, status_code=status_code)
    if reused is None:
        csrf.set_csrf_cookie(signed_token, response)
    return response
