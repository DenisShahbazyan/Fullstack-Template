from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_users.authentication.strategy.jwt import JWTStrategy
from fastapi_users.router.common import ErrorCode

from app.core.auth.backend import (
    auth_backend,
    get_access_jwt_strategy,
    get_refresh_jwt_strategy,
    set_refresh_cookie,
)
from app.core.auth.dependencies.manager import get_user_manager
from app.core.auth.manager import UserManager
from app.core.auth.users import current_user, fastapi_users
from app.models.user import User
from app.schemas.public.v1.user import (
    LoginRequestSchema,
    LoginResponseSchema,
    UserCreateSchema,
    UserReadSchema,
)

router = APIRouter()

# Форменный /login от fastapi-users подключается в корне приложения (см.
# mount_oauth2_form_login в main.py): кнопка "Authorize" в swagger шлёт запрос
# на /login без префикса API. Публичный JSON-логин объявлен здесь.
router.include_router(
    fastapi_users.get_register_router(UserReadSchema, UserCreateSchema),
    prefix='/auth',
    tags=['auth'],
)


@router.post('/auth/login', tags=['auth'])
async def login(
    request: Request,
    credentials: LoginRequestSchema,
    user_manager: UserManager = Depends(get_user_manager),
    access_strategy: JWTStrategy[User, int] = Depends(get_access_jwt_strategy),
    refresh_strategy: JWTStrategy[User, int] = Depends(get_refresh_jwt_strategy),
) -> Response:
    user = await user_manager.authenticate(
        OAuth2PasswordRequestForm(
            username=credentials.email,
            password=credentials.password,
        ),
    )
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=ErrorCode.LOGIN_BAD_CREDENTIALS,
        )
    response = await auth_backend.login(access_strategy, user)
    set_refresh_cookie(response, await refresh_strategy.write_token(user))
    await user_manager.on_after_login(user, request, response)
    return response


@router.post('/auth/refresh', tags=['auth'])
async def refresh_token(
    request: Request,
    user_manager: UserManager = Depends(get_user_manager),
    access_strategy: JWTStrategy[User, int] = Depends(get_access_jwt_strategy),
    refresh_strategy: JWTStrategy[User, int] = Depends(get_refresh_jwt_strategy),
) -> LoginResponseSchema:
    token = request.cookies.get('refresh_token')
    user = await refresh_strategy.read_token(token, user_manager) if token else None
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail='Недействительный refresh-токен',
        )
    access_token = await access_strategy.write_token(user)
    return LoginResponseSchema(access_token=access_token, token_type='bearer')


@router.post('/auth/logout', tags=['auth'])
async def logout(response: Response) -> dict[str, str]:
    response.delete_cookie('refresh_token')
    return {'message': 'Успешный выход'}


@router.get('/me', tags=['users'])
async def me(user: User = Depends(current_user)) -> UserReadSchema:
    return UserReadSchema.model_validate(user, from_attributes=True)
