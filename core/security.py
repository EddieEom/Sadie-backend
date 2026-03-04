import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, cast
from fastapi import HTTPException
from core.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

# [긴급 수리] bcrypt 버그 우회
if not hasattr(bcrypt, "__about__"):
    bcrypt.__about__ = type("About", (), {"__version__": bcrypt.__version__})

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, str(SECRET_KEY), algorithm=ALGORITHM)

def verify_token(token: Optional[str]) -> str:
    if token is None:
        raise HTTPException(status_code=401, detail="토큰이 없습니다.")
    try:
        actual_token = token.replace("Bearer ", "")
        payload = jwt.decode(actual_token, str(SECRET_KEY), algorithms=[ALGORITHM])
        user_id = cast(Optional[str], payload.get("sub"))
        if not user_id:
            raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")
        return user_id
    except Exception:
        raise HTTPException(status_code=401, detail="인증에 실패했습니다.")