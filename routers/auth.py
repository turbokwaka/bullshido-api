from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel.ext.asyncio.session import AsyncSession

from db import get_session
from schemas import (
    Token,
    UserCreate,
)
from services.auth_service import (
    login_for_access_token_service,
    register_user_service,
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
    return await login_for_access_token_service(form_data, session)


@auth_router.post("/register", response_model=Token)
async def register_user(
    form_data: UserCreate, session: Annotated[AsyncSession, Depends(get_session)]
):
    return await register_user_service(form_data, session)
