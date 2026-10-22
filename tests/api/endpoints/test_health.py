from http import HTTPStatus

from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    response = client.get('/health')
    assert response.status_code == HTTPStatus.OK
