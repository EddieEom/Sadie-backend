import os
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, cast
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Header

# 개편된 구조에 맞춰 import 경로 수정
from core.database import get_db_connection
from core.security import verify_token

router = APIRouter(prefix="/users", tags=["users"])

# 이미지 저장 경로 설정
UPLOAD_DIR = Path("static/profiles")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.patch("/me/profile")
async def update_profile(
    nickname: str = Form(...),
    profile_image: Optional[UploadFile] = File(None),
    authorization: Optional[str] = Header(None)
):
    # 1. 토큰 검증
    current_user_id = verify_token(authorization)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        image_url = None

        # 2. 이미지 파일 처리
        if profile_image and profile_image.filename:
            fname: str = profile_image.filename
            file_extension = os.path.splitext(fname)[1]
            
            # 파일명을 user_id로 고정하여 프로필 이미지 교체 시 이전 파일 관리 용이
            file_name = f"{current_user_id}{file_extension}"
            file_path = UPLOAD_DIR / file_name

            # 서버 로컬에 파일 저장
            with file_path.open("wb") as buffer:
                shutil.copyfileobj(profile_image.file, buffer)

            # DB에 저장할 상대 경로
            image_url = f"/static/profiles/{file_name}"

        # 3. DB 업데이트
        if image_url:
            cur.execute(
                "UPDATE users SET nickname = %s, profile_image = %s WHERE user_id = %s",
                (nickname, image_url, current_user_id)
            )
        else:
            cur.execute(
                "UPDATE users SET nickname = %s WHERE user_id = %s",
                (nickname, current_user_id)
            )
        
        conn.commit()
        
        return {
            "status": "success",
            "nickname": nickname,
            "profile_image": image_url
        }

    except Exception as e:
        if conn: conn.rollback()
        print(f"Update Profile Error: {e}")
        raise HTTPException(status_code=500, detail="프로필 업데이트 중 오류가 발생했습니다.")
    finally:
        cur.close()
        conn.close()

@router.get("/me")
async def get_my_profile(authorization: Optional[str] = Header(None)):
    current_user_id = verify_token(authorization)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute(
            "SELECT user_id, email, nickname, profile_image FROM users WHERE user_id = %s",
            (current_user_id,)
        )
        user = cur.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
            
        return {
            "status": "success",
            "data": user
        }
    finally:
        cur.close()
        conn.close()