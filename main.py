from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import auth, users, videos

app = FastAPI(title="Bullshido API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.auth_router)
app.include_router(users.users_router)
app.include_router(videos.videos_router)


@app.get("/", tags=["Root"])
async def root():
    return {"message": "Далі бога нема."}
