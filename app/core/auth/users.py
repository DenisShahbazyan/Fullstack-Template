from fastapi_users import FastAPIUsers

from app.core.auth.backend import auth_backend, cookie_auth_backend
from app.core.auth.dependencies.manager import get_user_manager
from app.models.user import User

fastapi_users = FastAPIUsers[User, int](
    get_user_manager,
    [auth_backend, cookie_auth_backend],
)

current_user = fastapi_users.current_user(active=True)
current_user_optional = fastapi_users.current_user(active=True, optional=True)
