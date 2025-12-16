import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import User
from services.users_service import (
    get_user_by_username,
    update_user_me_service,
    delete_user_me_service,
    change_password_service,
)
from schemas import UserUpdate, UserPasswordConfirm, UserPasswordChange


@pytest.mark.asyncio
async def test_get_user_by_username_found():
    mock_session = MagicMock()

    user = User(
        id=1, username="testuser", email="test@example.com", hashed_password="hash"
    )

    mock_result = MagicMock()
    mock_result.first.return_value = user
    mock_session.exec = AsyncMock(return_value=mock_result)

    result = await get_user_by_username(mock_session, "testuser")

    assert result == user
    assert result.username == "testuser"
    mock_session.exec.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_user_by_username_not_found():
    mock_session = MagicMock()

    mock_result = MagicMock()
    mock_result.first.return_value = None
    mock_session.exec = AsyncMock(return_value=mock_result)

    result = await get_user_by_username(mock_session, "nonexistent")

    assert result is None


@pytest.mark.asyncio
async def test_update_username_success():
    mock_session = MagicMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    current_user = User(
        id=1, username="oldusername", email="test@example.com", hashed_password="hash"
    )

    mock_result = MagicMock()
    mock_result.first.return_value = None
    mock_session.exec = AsyncMock(return_value=mock_result)

    update_data = UserUpdate(username="newusername")

    result = await update_user_me_service(update_data, current_user, mock_session)

    assert result.username == "newusername"
    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_username_already_taken():
    mock_session = MagicMock()

    current_user = User(
        id=1, username="oldusername", email="test@example.com", hashed_password="hash"
    )

    existing_user = User(
        id=2,
        username="takenusername",
        email="other@example.com",
        hashed_password="hash",
    )

    mock_result = MagicMock()
    mock_result.first.return_value = existing_user
    mock_session.exec = AsyncMock(return_value=mock_result)

    update_data = UserUpdate(username="takenusername")

    with pytest.raises(HTTPException) as exc_info:
        await update_user_me_service(update_data, current_user, mock_session)

    assert exc_info.value.status_code == 400
    assert "Username already taken" in exc_info.value.detail


@pytest.mark.asyncio
async def test_update_avatar_url():
    mock_session = MagicMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    current_user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="hash",
        avatar_url=None,
    )

    update_data = UserUpdate(avatar_url="https://example.com/avatar.jpg")

    result = await update_user_me_service(update_data, current_user, mock_session)

    assert result.avatar_url == "https://example.com/avatar.jpg"
    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_username_and_avatar():
    mock_session = MagicMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    current_user = User(
        id=1, username="oldusername", email="test@example.com", hashed_password="hash"
    )

    mock_result = MagicMock()
    mock_result.first.return_value = None
    mock_session.exec = AsyncMock(return_value=mock_result)

    update_data = UserUpdate(
        username="newusername", avatar_url="https://example.com/avatar.jpg"
    )

    result = await update_user_me_service(update_data, current_user, mock_session)

    assert result.username == "newusername"
    assert result.avatar_url == "https://example.com/avatar.jpg"


@pytest.mark.asyncio
async def test_update_same_username():
    mock_session = MagicMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.exec = AsyncMock()

    current_user = User(
        id=1, username="sameusername", email="test@example.com", hashed_password="hash"
    )

    update_data = UserUpdate(username="sameusername")

    await update_user_me_service(update_data, current_user, mock_session)

    mock_session.exec.assert_not_called()
    mock_session.add.assert_called_once()


@pytest.mark.asyncio
async def test_delete_user_success():
    mock_session = MagicMock()
    mock_session.delete = AsyncMock()
    mock_session.commit = AsyncMock()

    current_user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password",
    )

    confirm_data = UserPasswordConfirm(password="correct_password")

    with patch("services.users_service.verify_password", return_value=True):
        result = await delete_user_me_service(confirm_data, current_user, mock_session)

        assert result["message"] == "User deleted successfully"
        mock_session.delete.assert_awaited_once_with(current_user)
        mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_user_wrong_password():
    mock_session = MagicMock()

    current_user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password",
    )

    confirm_data = UserPasswordConfirm(password="wrong_password")

    with patch("services.users_service.verify_password", return_value=False):
        with pytest.raises(HTTPException) as exc_info:
            await delete_user_me_service(confirm_data, current_user, mock_session)

        assert exc_info.value.status_code == 401
        assert "Incorrect password" in exc_info.value.detail
        mock_session.delete.assert_not_called()


@pytest.mark.asyncio
async def test_change_password_success():
    mock_session = MagicMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    current_user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="old_hashed_password",
    )

    password_data = UserPasswordChange(
        old_password="OldPass123", new_password="NewPass123"
    )

    with (
        patch("services.users_service.verify_password", return_value=True),
        patch("services.users_service.validate_password_complexity"),
        patch(
            "services.users_service.get_password_hash",
            return_value="new_hashed_password",
        ),
    ):
        result = await change_password_service(
            password_data, current_user, mock_session
        )

        assert result["message"] == "Password updated successfully"
        assert current_user.hashed_password == "new_hashed_password"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_change_password_wrong_old_password():
    mock_session = MagicMock()

    current_user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="old_hashed_password",
    )

    password_data = UserPasswordChange(
        old_password="WrongOldPass123", new_password="NewPass123"
    )

    with patch("services.users_service.verify_password", return_value=False):
        with pytest.raises(HTTPException) as exc_info:
            await change_password_service(password_data, current_user, mock_session)

        assert exc_info.value.status_code == 400
        assert "Incorrect old password" in exc_info.value.detail


@pytest.mark.asyncio
async def test_change_password_weak_new_password():
    mock_session = MagicMock()

    current_user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="old_hashed_password",
    )

    password_data = UserPasswordChange(old_password="OldPass123", new_password="weak")

    with (
        patch("services.users_service.verify_password", return_value=True),
        patch(
            "services.users_service.validate_password_complexity",
            side_effect=HTTPException(
                status_code=400, detail="Password must contain..."
            ),
        ),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await change_password_service(password_data, current_user, mock_session)

        assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_change_password_same_as_old():
    mock_session = MagicMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    current_user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="old_hashed_password",
    )

    password_data = UserPasswordChange(
        old_password="SamePass123", new_password="SamePass123"
    )

    with (
        patch("services.users_service.verify_password", return_value=True),
        patch("services.users_service.validate_password_complexity"),
        patch(
            "services.users_service.get_password_hash",
            return_value="new_hashed_password",
        ),
    ):
        result = await change_password_service(
            password_data, current_user, mock_session
        )

        assert result["message"] == "Password updated successfully"
