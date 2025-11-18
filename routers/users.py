from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from db import USERS_DB
from schemas import (
    User,
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
    dependencies=[Depends(get_current_user)],
)


@users_router.get("/me", response_model=User)
async def read_users_me(current_user: Annotated[dict, Depends(get_current_user)]):
    return current_user


@users_router.patch("/me", response_model=User)
async def update_user_me(
    update_data: UserUpdate,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    current_username = current_user["username"]
    user_data = USERS_DB[current_username]

    if update_data.username and update_data.username != current_username:
        if update_data.username in USERS_DB:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Username already taken")
        USERS_DB[update_data.username] = USERS_DB.pop(current_username)
        user_data["username"] = update_data.username

    if update_data.avatar_url:
        user_data["avatar_url"] = update_data.avatar_url

    return user_data


@users_router.delete("/me", status_code=status.HTTP_200_OK)
async def delete_user_me(
    confirm_data: UserPasswordConfirm,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    username = current_user["username"]
    user_data = USERS_DB.get(username)

    if not user_data or not verify_password(
        confirm_data.password, user_data["hashed_password"]
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
        )

    del USERS_DB[username]

    return {"message": "User deleted successfully"}


@users_router.post("/me/password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: UserPasswordChange,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    validate_password_complexity(password_data.new_password)
    user_data = USERS_DB[current_user["username"]]

    if not verify_password(password_data.old_password, user_data["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect old password",
        )

    user_data["hashed_password"] = get_password_hash(password_data.new_password)

    return {"message": "Password updated successfully"}
