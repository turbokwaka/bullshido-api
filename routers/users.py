from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlmodel.ext.asyncio.session import AsyncSession

from db import get_session
from models import User
from schemas import (
    User as UserSchema,
    UserUpdate,
    UserPasswordConfirm,
    UserPasswordChange,
)
from security import get_current_user
from services.users_service import (
    update_user_me_service,
    delete_user_me_service,
    change_password_service,
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
    return await update_user_me_service(update_data, current_user, session)


@users_router.delete("/me", status_code=status.HTTP_200_OK)
async def delete_user_me(
    confirm_data: UserPasswordConfirm,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    return await delete_user_me_service(confirm_data, current_user, session)


@users_router.post("/me/password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: UserPasswordChange,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    return await change_password_service(password_data, current_user, session)
