import os
from typing import Optional, Dict, Any, cast
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Header
from supabase import create_client, Client

from core.database import get_db_connection
from core.security import verify_token

router = APIRouter(prefix="/users", tags=["users"])

# 환경 변수 설정
SUPABASE_URL: str = os.getenv("SUPABASE_URL") or ""
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY") or ""

# Supabase 클라이언트 초기화
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@router.patch("/me/profile")
async def update_profile(
    nickname: str = Form(...),
    profile_image: Optional[UploadFile] = File(None),
    google_image_url: Optional[str] = Form(None),
    authorization: Optional[str] = Header(None)
):
    current_user_id = verify_token(authorization)
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        image_url = None

        # 1. 이미지 파일이 직접 업로드된 경우
        if profile_image and profile_image.filename:
            file_content = await profile_image.read()
            file_ext = os.path.splitext(profile_image.filename)[1]
            file_path = f"profiles/{current_user_id}{file_ext}"

            # Supabase Storage 업로드
            supabase.storage.from_("profiles").upload(
                path=file_path,
                file=file_content,
                file_options={
                    "upsert": "true", 
                    "content-type": str(profile_image.content_type)
                }
            )
            image_url = supabase.storage.from_("profiles").get_public_url(file_path)

        # 2. 파일은 없지만 구글 이미지 URL을 쓰기로 한 경우
        elif google_image_url:
            image_url = google_image_url

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
        print(f"Update Error: {e}")
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
        # 가입일(created_at) 포함 정보 조회
        cur.execute(
            "SELECT user_id, email, nickname, profile_image, created_at FROM users WHERE user_id = %s",
            (current_user_id,)
        )
        user = cur.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

        # RealDictCursor 사용 시 Dict로 캐스팅하여 타입 에러 방지
        user_data = cast(Dict[str, Any], user)
            
        return {
            "status": "success",
            "data": {
                "user_id": user_data['user_id'],
                "email": user_data['email'],
                "nickname": user_data['nickname'],
                "profile_image": user_data['profile_image'],
                "created_at": user_data['created_at'].isoformat() if user_data.get('created_at') else None
            }
        }
    finally:
        cur.close()
        conn.close()