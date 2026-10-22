"""Проверяет полный сценарий кнопки Authorize в swagger на реальном пользователе."""

from http import HTTPStatus
from uuid import uuid4

from httpx import AsyncClient

from tests.config import API_PUBLIC_V1
from tests.utils.user import DEFAULT_PASSWORD, register_user_request


async def test_swagger_authorize_flow(async_client: AsyncClient) -> None:
    """Форменный /login выдаёт токен, и с ним проходит защищённый эндпоинт."""
    email = f'swagger_{uuid4()}@example.com'
    await register_user_request(async_client, email)

    # Ровно то, что делает кнопка "Authorize": form-data на tokenUrl из схемы
    response = await async_client.post(
        url='/login',
        data={'username': email, 'password': DEFAULT_PASSWORD},
    )
    assert response.status_code == HTTPStatus.OK, response.text
    token = response.json()['access_token']

    # Токен принимается защищённым эндпоинтом
    me = await async_client.get(
        url=f'{API_PUBLIC_V1}/me',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert me.status_code == HTTPStatus.OK, me.text
    assert me.json()['email'] == email


async def test_swagger_token_url_matches_route(async_client: AsyncClient) -> None:
    """tokenUrl в схеме указывает на существующий роут, а не на 405."""
    schema = (await async_client.get('/openapi.json')).json()
    flows = schema['components']['securitySchemes']['OAuth2PasswordBearer']['flows']
    token_url = flows['password']['tokenUrl']

    response = await async_client.post(
        url=token_url,
        data={'username': 'nobody@example.com', 'password': 'wrong'},
    )
    assert response.status_code != HTTPStatus.METHOD_NOT_ALLOWED
