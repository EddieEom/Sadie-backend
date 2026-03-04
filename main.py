from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# 분리한 라우터들 import (파일명과 위치 확인 필수)
from routes import auth, user, chat

app = FastAPI()

# 1. Rate Limiter 설정 (기존 로직 유지)
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.exception_handler(RateLimitExceeded)(_rate_limit_exceeded_handler)


# 2. 정적 파일 서버 설정 (프로필 이미지 등)
# app.mount("/static", StaticFiles(directory="static"), name="static")

# 3. CORS 설정 (기존 유지)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. 라우터 등록 (경로 겹침 방지)
# auth.py와 chat.py 내부에서 prefix를 조절했으므로 아래처럼 등록합니다.
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(chat.router)

@app.get("/")
def read_root():
    return {"message": "Sadie AI Server is Online!"}