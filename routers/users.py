from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from db import get_session
from models import User
from schemas import (
    User as UserSchema,
    UserUpdate,
    UserPasswordConfirm,
    UserPasswordChange,
)
from security import (
    get_current_user,
    verify_password,
    validate_password_complexity,
    get_password_hash,
)

users_router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@users_router.get("/me", response_model=UserSchema)
async def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user


@users_router.patch("/me", response_model=UserSchema)
async def update_user_me(
    update_data: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
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


@users_router.delete("/me", status_code=status.HTTP_200_OK)
async def delete_user_me(
    confirm_data: UserPasswordConfirm,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    if not verify_password(confirm_data.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
        )

    await session.delete(current_user)
    await session.commit()

    return {"message": "User deleted successfully"}


@users_router.post("/me/password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: UserPasswordChange,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
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
