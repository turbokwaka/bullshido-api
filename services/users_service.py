from typing import Optional
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import HTTPException, status

from models import User
from security import verify_password, validate_password_complexity, get_password_hash


async def get_user_by_username(session: AsyncSession, username: str) -> Optional[User]:
    statement = select(User).where(User.username == username)
    result = await session.exec(statement)
    return result.first()


async def update_user_me_service(
    update_data, current_user: User, session: AsyncSession
) -> User:
    if update_data.username and update_data.username != current_user.username:
        statement = select(User).where(User.username == update_data.username)
        result = await session.exec(statement)
        existing_user = result.first()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken"
            )

        current_user.username = update_data.username

    if update_data.avatar_url:
        current_user.avatar_url = update_data.avatar_url

    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)

    return current_user


async def delete_user_me_service(
    confirm_data, current_user: User, session: AsyncSession
):
    if not verify_password(confirm_data.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
        )

    await session.delete(current_user)
    await session.commit()

    return {"message": "User deleted successfully"}


async def change_password_service(
    password_data, current_user: User, session: AsyncSession
):
    if not verify_password(password_data.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect old password",
        )

    validate_password_complexity(password_data.new_password)

    current_user.hashed_password = get_password_hash(password_data.new_password)

    session.add(current_user)
    await session.commit()

    return {"message": "Password updated successfully"}
