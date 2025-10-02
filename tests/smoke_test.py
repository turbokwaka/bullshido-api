# tests/smoke_test.py

from fastapi.testclient import TestClient
from main import app


def test_app_starts():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code in (200, 404)
