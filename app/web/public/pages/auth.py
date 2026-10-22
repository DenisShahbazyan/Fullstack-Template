from http import HTTPStatus

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_users.exceptions import InvalidPasswordException, UserAlreadyExists
from pydantic import ValidationError

from app.core.auth.backend import get_access_jwt_strategy, set_access_cookie
from app.core.auth.dependencies.manager import get_user_manager
from app.core.auth.manager import UserManager
from app.core.csrf import csrf_validate
from app.domain.auth.password import MIN_PASSWORD_LENGTH
from app.models.user import User
from app.schemas.public.v1.user import UserCreateSchema
from app.web.dependencies import optional_user, redirect, safe_next_url
from app.web.templates import render
from app.web.toasts import toast_context

router = APIRouter()
# Формы входа и регистрации меняют состояние сессии, поэтому защищены CSRF.
# Страницы (GET) остаются без проверки: токен в них ещё только выдаётся.
forms_router = APIRouter(dependencies=[Depends(csrf_validate)])

_REGISTER_ERROR = (
    f'Проверьте email и пароль: пароль — не короче {MIN_PASSWORD_LENGTH} символов'
)


async def _login_redirect(user: User, next_url: str) -> RedirectResponse:
    """Редирект с cookie-сессией."""
    response = redirect(safe_next_url(next_url))
    set_access_cookie(response, await get_access_jwt_strategy().write_token(user))
    return response


@router.get('/login', response_class=HTMLResponse)
async def login_page(
    request: Request,
    next_url: str = Query('/', alias='next'),
    current_user: User | None = Depends(optional_user),
):
    return render(
        request,
        'public/pages/login.html',
        {'current_user': current_user, 'next_url': next_url},
    )


@forms_router.post('/login/submit', response_class=HTMLResponse)
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next_url: str = Form('/', alias='next'),
    user_manager: UserManager = Depends(get_user_manager),
):
    user = await user_manager.authenticate(
        OAuth2PasswordRequestForm(username=email, password=password),
    )
    if user is None or not user.is_active:
        return render(
            request,
            'public/pages/login.html',
            {
                'current_user': None,
                'next_url': next_url,
                'form': {'email': email},
                **toast_context('Неверный email или пароль'),
            },
            status_code=HTTPStatus.UNAUTHORIZED,
        )
    return await _login_redirect(user, next_url)


@router.get('/register', response_class=HTMLResponse)
async def register_page(
    request: Request,
    current_user: User | None = Depends(optional_user),
):
    return render(request, 'public/pages/register.html', {'current_user': current_user})


def _render_register_error(
    request: Request,
    form: dict[str, str | None],
    message: str,
) -> HTMLResponse:
    return render(
        request,
        'public/pages/register.html',
        {'current_user': None, 'form': form, **toast_context(message)},
        status_code=HTTPStatus.BAD_REQUEST,
    )


@forms_router.post('/register/submit', response_class=HTMLResponse)
async def register_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    first_name: str | None = Form(None),
    user_manager: UserManager = Depends(get_user_manager),
):
    form = {'email': email, 'first_name': first_name}
    try:
        payload = UserCreateSchema(
            email=email, password=password, first_name=first_name
        )
        user = await user_manager.create(payload, safe=True, request=request)
    except ValidationError, InvalidPasswordException:
        return _render_register_error(request, form, _REGISTER_ERROR)
    except UserAlreadyExists:
        return _render_register_error(request, form, 'Этот email уже зарегистрирован')
    return await _login_redirect(user, '/')


@forms_router.post('/logout/submit')
async def logout_submit() -> RedirectResponse:
    response = redirect('/')
    response.delete_cookie('access_token')
    return response


router.include_router(forms_router)
