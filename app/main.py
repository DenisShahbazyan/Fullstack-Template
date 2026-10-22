from fastapi import FastAPI

from app.api.routers import main_router
from app.api.utils.user import mount_oauth2_form_login
from app.core.auth.backend import auth_backend
from app.core.config import mount_static, settings
from app.core.csrf import register_csrf_exception_handler
from app.core.docs.docs import get_custom_docs
from app.core.exception_handlers import add_exception_handlers
from app.core.logs import setup_logging
from app.core.middleware.request_id import add_request_id_middleware
from app.core.middleware.session import add_session_middleware
from app.web.errors import HtmlErrorRenderer
from app.web.routers import web_router

setup_logging()

app = FastAPI(
    title=settings.site.NAME,
    docs_url=None,
    redoc_url=None,
)

add_session_middleware(app)
add_exception_handlers(app, HtmlErrorRenderer())
register_csrf_exception_handler(app)
add_request_id_middleware(app)
mount_static(app)
app.include_router(main_router)
app.include_router(web_router)
mount_oauth2_form_login(app, auth_backend)
get_custom_docs(
    app,
    docs_url='/docs',
    swagger_js_url=settings.static.DOCS_JS,
    swagger_css_url=settings.static.DOCS_CSS,
    redoc_url=None,
)
