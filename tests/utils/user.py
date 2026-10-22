from httpx import AsyncClient, Response

from tests.config import API_PUBLIC_V1

DEFAULT_PASSWORD = 'password123'


async def register_user_request(
    async_client: AsyncClient,
    email: str,
    password: str = DEFAULT_PASSWORD,
) -> Response:
    return await async_client.post(
        url=f'{API_PUBLIC_V1}/auth/register',
        json={'email': email, 'password': password, 'first_name': 'Тест'},
    )


async def login_request(
    async_client: AsyncClient,
    email: str,
    password: str = DEFAULT_PASSWORD,
) -> Response:
    return await async_client.post(
        url=f'{API_PUBLIC_V1}/auth/login',
        json={'email': email, 'password': password},
    )
