from http import HTTPStatus

from httpx import AsyncClient

from tests.config import API_ADMIN_V1, API_PUBLIC_V1
from tests.utils.user import login_request, register_user_request


async def test_register_then_login_returns_token_and_me(
    async_client: AsyncClient,
) -> None:
    response = await register_user_request(async_client, 'User@Example.com')
    assert response.status_code == HTTPStatus.CREATED, response.text
    assert response.json()['email'] == 'user@example.com'

    login = await login_request(async_client, 'user@example.com')
    assert login.status_code == HTTPStatus.OK, login.text
    token = login.json()['access_token']

    me = await async_client.get(
        f'{API_PUBLIC_V1}/me', headers={'Authorization': f'Bearer {token}'}
    )
    assert me.status_code == HTTPStatus.OK
    assert me.json()['role'] == 'user'


async def test_register_rejects_short_password(async_client: AsyncClient) -> None:
    response = await register_user_request(async_client, 'a@example.com', 'short')
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


async def test_login_with_wrong_password_fails(async_client: AsyncClient) -> None:
    await register_user_request(async_client, 'b@example.com')
    response = await login_request(async_client, 'b@example.com', 'wrong-password')
    assert response.status_code == HTTPStatus.BAD_REQUEST


async def test_admin_api_is_closed_for_regular_user(async_client: AsyncClient) -> None:
    await register_user_request(async_client, 'c@example.com')
    token = (await login_request(async_client, 'c@example.com')).json()['access_token']
    response = await async_client.get(
        f'{API_ADMIN_V1}/users', headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == HTTPStatus.FORBIDDEN
