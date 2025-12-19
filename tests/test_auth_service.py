import os
import sys
import pytest
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import User
from schemas import UserCreate
from services.auth_service import login_for_access_token_service, register_user_service


@pytest.mark.asyncio
async def test_login_success():
    mock_session = MagicMock()

    # mock bcrypt
    hashed_pw = "$2b$12$test_hash"
    user = User(
        id=1, username="testuser", email="test@example.com", hashed_password=hashed_pw
    )

    mock_result = MagicMock()
    mock_result.first.return_value = user
    mock_session.exec = AsyncMock(return_value=mock_result)

    form_data = SimpleNamespace(username="testuser", password="TestPass123")

    with (
        patch("services.auth_service.verify_password", return_value=True),
        patch("services.auth_service.create_access_token", return_value="mock_token"),
    ):
        result = await login_for_access_token_service(form_data, mock_session)

        assert result["access_token"] == "mock_token"
        assert result["token_type"] == "bearer"
        mock_session.exec.assert_awaited_once()


@pytest.mark.asyncio
async def test_login_wrong_username():
    mock_session = MagicMock()

    mock_result = MagicMock()
    mock_result.first.return_value = None
    mock_session.exec = AsyncMock(return_value=mock_result)

    form_data = SimpleNamespace(username="nonexistent", password="TestPass123")

    with pytest.raises(HTTPException) as exc_info:
        await login_for_access_token_service(form_data, mock_session)

    assert exc_info.value.status_code == 401
    assert "Incorrect username or password" in exc_info.value.detail


@pytest.mark.asyncio
async def test_login_wrong_password():
    mock_session = MagicMock()

    user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="$2b$12$test_hash",
    )

    mock_result = MagicMock()
    mock_result.first.return_value = user
    mock_session.exec = AsyncMock(return_value=mock_result)

    form_data = SimpleNamespace(username="testuser", password="WrongPass123")

    with patch("services.auth_service.verify_password", return_value=False):
        with pytest.raises(HTTPException) as exc_info:
            await login_for_access_token_service(form_data, mock_session)

        assert exc_info.value.status_code == 401
        assert "Incorrect username or password" in exc_info.value.detail


# Tests for register_user_service
@pytest.mark.asyncio
async def test_register_success():
    mock_session = MagicMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    async def mock_refresh(obj):
        obj.id = 1

    mock_session.refresh = AsyncMock(side_effect=mock_refresh)

    mock_username_result = MagicMock()
    mock_username_result.first.return_value = None

    mock_email_result = MagicMock()
    mock_email_result.first.return_value = None

    mock_session.exec = AsyncMock(side_effect=[mock_username_result, mock_email_result])

    form_data = UserCreate(
        username="newuser", email="new@example.com", password="NewPass123"
    )

    with (
        patch("services.auth_service.validate_password_complexity"),
        patch("services.auth_service.get_password_hash", return_value="hashed_pw"),
        patch("services.auth_service.create_access_token", return_value="mock_token"),
    ):
        result = await register_user_service(form_data, mock_session)

        assert result["access_token"] == "mock_token"
        assert result["token_type"] == "bearer"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_register_username_already_exists():
    mock_session = MagicMock()

    existing_user = User(
        id=1,
        username="existinguser",
        email="existing@example.com",
        hashed_password="hash",
    )

    mock_result = MagicMock()
    mock_result.first.return_value = existing_user
    mock_session.exec = AsyncMock(return_value=mock_result)

    form_data = UserCreate(
        username="existinguser", email="new@example.com", password="NewPass123"
    )

    with patch("services.auth_service.validate_password_complexity"):
        with pytest.raises(HTTPException) as exc_info:
            await register_user_service(form_data, mock_session)

        assert exc_info.value.status_code == 400
        assert "Username already registered" in exc_info.value.detail


@pytest.mark.asyncio
async def test_register_email_already_exists():
    mock_session = MagicMock()

    mock_username_result = MagicMock()
    mock_username_result.first.return_value = None

    existing_user = User(
        id=1, username="otheruser", email="existing@example.com", hashed_password="hash"
    )
    mock_email_result = MagicMock()
    mock_email_result.first.return_value = existing_user

    mock_session.exec = AsyncMock(side_effect=[mock_username_result, mock_email_result])

    form_data = UserCreate(
        username="newuser", email="existing@example.com", password="NewPass123"
    )

    with patch("services.auth_service.validate_password_complexity"):
        with pytest.raises(HTTPException) as exc_info:
            await register_user_service(form_data, mock_session)

        assert exc_info.value.status_code == 400
        assert "Email already registered" in exc_info.value.detail


@pytest.mark.asyncio
async def test_register_weak_password():
    mock_session = MagicMock()

    form_data = UserCreate(
        username="newuser", email="new@example.com", password="weakpass"
    )

    with patch(
        "services.auth_service.validate_password_complexity",
        side_effect=HTTPException(status_code=400, detail="Password must contain..."),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await register_user_service(form_data, mock_session)

        assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_login_with_empty_password():
    mock_session = MagicMock()

    user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="$2b$12$test_hash",
    )

    mock_result = MagicMock()
    mock_result.first.return_value = user
    mock_session.exec = AsyncMock(return_value=mock_result)

    form_data = SimpleNamespace(username="testuser", password="")

    with patch("services.auth_service.verify_password", return_value=False):
        with pytest.raises(HTTPException) as exc_info:
            await login_for_access_token_service(form_data, mock_session)

        assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_register_token_expiration():
    mock_session = MagicMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    async def mock_refresh(obj):
        obj.id = 1

    mock_session.refresh = AsyncMock(side_effect=mock_refresh)

    mock_username_result = MagicMock()
    mock_username_result.first.return_value = None
    mock_email_result = MagicMock()
    mock_email_result.first.return_value = None

    mock_session.exec = AsyncMock(side_effect=[mock_username_result, mock_email_result])

    user_data = UserCreate(
        username="newuser", email="new@example.com", password="NewPass123"
    )

    with (
        patch("services.auth_service.validate_password_complexity"),
        patch("services.auth_service.get_password_hash", return_value="hashed_pw"),
        patch(
            "services.auth_service.create_access_token", return_value="mock_token"
        ) as mock_create_token,
    ):
        await register_user_service(user_data, mock_session)

        mock_create_token.assert_called_once()
        call_args = mock_create_token.call_args
        assert "expires_delta" in call_args.kwargs
        assert isinstance(call_args.kwargs["expires_delta"], timedelta)
