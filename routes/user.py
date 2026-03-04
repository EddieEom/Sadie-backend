import os
from typing import Optional, cast
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Header
from supabase import create_client, Client

from core.database import get_db_connection
from core.security import verify_token

router = APIRouter(prefix="/users", tags=["users"])

# 1. 환경 변수를 가져오되, 없을 경우를 대비해 빈 문자열이나 에러 처리를 합니다.
SUPABASE_URL: str = os.getenv("SUPABASE_URL") or ""
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY") or ""

# URL이나 KEY가 비어있으면 서버 시작 시 알 수 있게 체크 (선택 사항)
if not SUPABASE_URL or not SUPABASE_KEY:
    print("⚠️ 경고: SUPABASE 환경 변수가 설정되지 않았습니다.")

# 2. create_client에 들어가는 값이 str임을 명시적으로 알려줍니다.
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

        if profile_image and profile_image.filename:
            file_content = await profile_image.read()
            file_ext = os.path.splitext(profile_image.filename)[1]
            file_path = f"profiles/{current_user_id}{file_ext}"

            # 3. file_options 타입 에러 해결
            # dict 형태를 명시적으로 전달하거나, 필요한 값만 넘깁니다.
            supabase.storage.from_("profiles").upload(
                path=file_path,
                file=file_content,
                file_options={
                    "upsert": "true", 
                    "content-type": str(profile_image.content_type) # None 방지
                }
            )
            image_url = supabase.storage.from_("profiles").get_public_url(file_path)

        elif google_image_url:
            image_url = google_image_url

        # (이후 DB 업데이트 로직은 동일...)
        if image_url:
            cur.execute("UPDATE users SET nickname = %s, profile_image = %s WHERE user_id = %s", (nickname, image_url, current_user_id))
        else:
            cur.execute("UPDATE users SET nickname = %s WHERE user_id = %s", (nickname, current_user_id))
        
        conn.commit()
        return {"status": "success", "nickname": nickname, "profile_image": image_url}

    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=f"프로필 업데이트 오류: {str(e)}")
    finally:
        cur.close()
        conn.close()