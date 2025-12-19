import asyncio
import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel.pool import StaticPool

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db import get_session
from main import app


@pytest.fixture(name="engine", scope="function")
def engine_fixture():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    yield engine
    engine.sync_engine.dispose()


@pytest.fixture(name="client", scope="function")
def client_fixture(engine):
    async def create_tables():
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    asyncio.run(create_tables())

    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async def get_session_override():
        async with async_session_maker() as session:
            yield session

    app.dependency_overrides[get_session] = get_session_override

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


def test_e2e_user_registration_and_login(client: TestClient):
    register_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPass123",
    }

    response = client.post("/auth/register", json=register_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    first_token = data["access_token"]

    login_data = {"username": "testuser", "password": "TestPass123"}

    response = client.post("/auth/login", data=login_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    headers = {"Authorization": f"Bearer {first_token}"}
    response = client.get("/users/me", headers=headers)
    assert response.status_code == 200
    user_data = response.json()
    assert user_data["username"] == "testuser"
    assert user_data["email"] == "test@example.com"


def test_e2e_user_registration_duplicate_username(client: TestClient):
    register_data = {
        "username": "duplicateuser",
        "email": "user1@example.com",
        "password": "TestPass123",
    }

    response = client.post("/auth/register", json=register_data)
    assert response.status_code == 200

    register_data["email"] = "user2@example.com"
    response = client.post("/auth/register", json=register_data)
    assert response.status_code == 400
    assert "Username already registered" in response.json()["detail"]


def test_e2e_login_with_wrong_credentials(client: TestClient):
    register_data = {
        "username": "logintest",
        "email": "login@example.com",
        "password": "CorrectPass123",
    }
    client.post("/auth/register", json=register_data)

    login_data = {"username": "logintest", "password": "WrongPass123"}

    response = client.post("/auth/login", data=login_data)
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]


def test_e2e_update_user_profile(client: TestClient):
    register_data = {
        "username": "profileuser",
        "email": "profile@example.com",
        "password": "TestPass123",
    }
    response = client.post("/auth/register", json=register_data)
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    update_data = {"avatar_url": "https://example.com/new-avatar.jpg"}
    response = client.patch("/users/me", json=update_data, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["avatar_url"] == "https://example.com/new-avatar.jpg"

    response = client.get("/users/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["avatar_url"] == "https://example.com/new-avatar.jpg"


def test_e2e_change_password(client: TestClient):
    register_data = {
        "username": "passchange",
        "email": "passchange@example.com",
        "password": "OldPass123",
    }
    response = client.post("/auth/register", json=register_data)
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    password_data = {"old_password": "OldPass123", "new_password": "NewPass456"}
    response = client.post("/users/me/password", json=password_data, headers=headers)
    assert response.status_code == 200
    assert response.json()["message"] == "Password updated successfully"

    login_data = {"username": "passchange", "password": "OldPass123"}
    response = client.post("/auth/login", data=login_data)
    assert response.status_code == 401

    login_data["password"] = "NewPass456"
    response = client.post("/auth/login", data=login_data)
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_e2e_delete_user(client: TestClient):
    register_data = {
        "username": "deleteuser",
        "email": "delete@example.com",
        "password": "TestPass123",
    }
    response = client.post("/auth/register", json=register_data)
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/users/me", headers=headers)
    assert response.status_code == 200

    delete_data = {"password": "TestPass123"}
    response = client.request("DELETE", "/users/me", json=delete_data, headers=headers)
    assert response.status_code == 200
    assert response.json()["message"] == "User deleted successfully"

    response = client.get("/users/me", headers=headers)
    assert response.status_code == 401


def test_e2e_unauthorized_access(client: TestClient):
    response = client.get("/users/me")
    assert response.status_code == 401

    headers = {"Authorization": "Bearer invalid_token_here"}
    response = client.get("/users/me", headers=headers)
    assert response.status_code == 401


def test_e2e_video_gallery_access(client: TestClient):
    register_data = {
        "username": "galleryuser",
        "email": "gallery@example.com",
        "password": "TestPass123",
    }
    response = client.post("/auth/register", json=register_data)
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/videos/gallery", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_e2e_video_history_empty(client: TestClient):
    register_data = {
        "username": "historyuser",
        "email": "history@example.com",
        "password": "TestPass123",
    }
    response = client.post("/auth/register", json=register_data)
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/videos/history", headers=headers)
    assert response.status_code == 200
    assert response.json() == []


def test_e2e_pagination_parameters(client: TestClient):
    register_data = {
        "username": "paginuser",
        "email": "pagin@example.com",
        "password": "TestPass123",
    }
    response = client.post("/auth/register", json=register_data)
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/videos/gallery?skip=0&limit=10", headers=headers)
    assert response.status_code == 200

    response = client.get("/videos/gallery?skip=0&limit=200", headers=headers)
    assert response.status_code == 422


def test_e2e_root_endpoint(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
