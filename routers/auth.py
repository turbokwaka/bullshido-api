from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from config import settings
from db import get_session
from models import User
from schemas import (
    Token,
    UserCreate,
)
from security import (
    verify_password,
    create_access_token,
    validate_password_complexity,
    get_password_hash,
)

auth_router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@auth_router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    statement = select(User).where(User.username == form_data.username)
    result = await session.exec(statement)
    user = result.first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@auth_router.post("/register", response_model=Token)
async def register_user(
    form_data: UserCreate, session: Annotated[AsyncSession, Depends(get_session)]
):
    validate_password_complexity(form_data.password)

    statement_username = select(User).where(User.username == form_data.username)
    result_username = await session.exec(statement_username)
    if result_username.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    statement_email = select(User).where(User.email == form_data.email)
    result_email = await session.exec(statement_email)
    if result_email.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    hashed_password = get_password_hash(form_data.password)
    new_user = User(
        username=form_data.username,
        email=form_data.email,
        hashed_password=hashed_password,
    )

    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": new_user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
