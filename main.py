import re
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Annotated, Optional, List

from fastapi import APIRouter, Depends, FastAPI, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field

app = FastAPI(title="Bullshido API")

SECRET_KEY = "shimmy-shimmy-yai"
WORKER_SECRET_TOKEN = "bullshido-secret-worker-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

USERS_DB = {}
VIDEOS_DB = {}


class VoicePreset(str, Enum):
    rogue = "rogue"
    knight = "knight"
    wizard = "wizard"


class SubtitlePosition(str, Enum):
    top = "top"
    center = "center"
    bottom = "bottom"


class VideoStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class UserBase(BaseModel):
    username: str
    email: EmailStr
    avatar_url: Optional[str] = None


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str = Field(min_length=3, max_length=30)


class User(UserBase):
    pass


class UserUpdate(BaseModel):
    username: Optional[str] = None
    avatar_url: Optional[str] = None


class UserPasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(min_length=3, max_length=30)


class UserPasswordConfirm(BaseModel):
    password: str


class VideoCreateRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=500)
    voice: VoicePreset
    subtitle_style_id: int = Field(ge=1, le=10)
    subtitle_position: SubtitlePosition


class VideoResponse(BaseModel):
    id: str
    author_username: str
    text: str
    status: VideoStatus
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    created_at: datetime


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def validate_password_complexity(password: str):
    pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d@$!%*?&_\-]*$"
    if not re.match(pattern, password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one uppercase letter, one lowercase letter, and one digit.",
        )


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    user = USERS_DB.get(token_data.username)
    if user is None:
        raise credentials_exception

    return user


auth_router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

users_router = APIRouter(
    prefix="/users",
    tags=["Users"],
    dependencies=[Depends(get_current_user)],
)
videos_router = APIRouter(prefix="/videos", tags=["Videos"])


@auth_router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
):
    user = USERS_DB.get(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@auth_router.post("/register", response_model=Token)
async def register_user(form_data: UserCreate):
    validate_password_complexity(form_data.password)

    if form_data.username in USERS_DB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    if any(u.get("email") == form_data.email for u in USERS_DB.values()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    hashed_password = get_password_hash(form_data.password)
    new_user = {
        "username": form_data.username,
        "email": form_data.email,
        "hashed_password": hashed_password,
        "avatar_url": "https://i.pinimg.com/736x/3b/6a/d9/3b6ad93de7650b5720d55fbef63b45ad.jpg",
    }
    USERS_DB[form_data.username] = new_user

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": new_user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


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


@videos_router.post(
    "/generate", response_model=VideoResponse, status_code=status.HTTP_201_CREATED
)
async def create_video_generation_task(
    video_request: VideoCreateRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    video_id = str(uuid.uuid4())

    new_video = {
        "id": video_id,
        "author_username": current_user["username"],
        "text": video_request.text,
        "voice": video_request.voice,
        "subtitle_style_id": video_request.subtitle_style_id,
        "subtitle_position": video_request.subtitle_position,
        "status": VideoStatus.queued,
        "video_url": None,
        "created_at": datetime.now(timezone.utc),
    }

    VIDEOS_DB[video_id] = new_video
    return new_video


@videos_router.get("/gallery", response_model=List[VideoResponse])
async def get_video_gallery(
    current_user: Annotated[dict, Depends(get_current_user)],
    skip: int = 0,
    limit: int = 10,
):
    completed_videos = [
        v for v in VIDEOS_DB.values() if v["status"] == VideoStatus.completed
    ]
    return completed_videos[skip : skip + limit]


@videos_router.get("/history", response_model=List[VideoResponse])
async def get_my_videos_history(
    current_user: Annotated[dict, Depends(get_current_user)],
):
    username = current_user["username"]

    my_videos = [v for v in VIDEOS_DB.values() if v["author_username"] == username]

    my_videos.sort(key=lambda x: x["created_at"], reverse=True)

    return my_videos


@videos_router.get("/{video_id}", response_model=VideoResponse)
async def get_video_status(
    video_id: str, current_user: Annotated[dict, Depends(get_current_user)]
):
    video = VIDEOS_DB.get(video_id)
    if not video:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Video not found")

    return video


@videos_router.patch("/{video_id}/complete_simulation")
async def worker_complete_task(
    video_id: str,
    video_url: str,
    thumbnail_url: str,
    x_worker_token: Annotated[str, Header()],
):
    if x_worker_token != WORKER_SECRET_TOKEN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not authorized worker")

    video = VIDEOS_DB.get(video_id)
    if not video:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Task not found")

    video["status"] = VideoStatus.completed
    video["video_url"] = video_url
    video["thumbnail_url"] = thumbnail_url
    return {"message": "Доббі хоче бути вільним.", "video": video}


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(videos_router)


@app.get("/", tags=["Root"])
async def root():
    return {"message": "Далі бога нема."}
