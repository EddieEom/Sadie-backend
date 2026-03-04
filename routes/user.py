import os
from typing import Optional, Dict, Any, cast, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Header
from supabase import create_client, Client

from core.database import get_db_connection
from core.security import verify_token

router = APIRouter(prefix="/users", tags=["users"])

# 환경 변수 설정 (os.getenv 결과가 None일 경우를 대비해 "" 처리)
# 부근 수정
SUPABASE_URL: str = os.getenv("SUPABASE_URL") or ""
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY") or ""

# URL이나 KEY가 없으면 서버 시작 단계에서 에러를 내서 알려줘야 합니다.
if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ 에러: SUPABASE_URL 또는 SUPABASE_KEY가 설정되지 않았습니다.")
else:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Supabase 클라이언트 초기화
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@router.patch("/me/profile")
async def update_profile(
    nickname: str = Form(...),
    profile_image: Optional[UploadFile] = File(None),
    google_image_url: Optional[str] = Form(None),
    authorization: Optional[str] = Header(None)
):
    # 1. 토큰 검증 (기존 로직 유지)
    current_user_id = verify_token(authorization)
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        image_url = None

        # 2. 이미지 파일 업로드 (기존 Supabase 로직 유지)
        if profile_image and profile_image.filename:
            file_content = await profile_image.read()
            file_ext = os.path.splitext(profile_image.filename)[1]
            file_path = f"profiles/{current_user_id}{file_ext}"

            supabase.storage.from_("profiles").upload(
                path=file_path,
                file=file_content,
                file_options={
                    "upsert": "true", 
                    "content-type": str(profile_image.content_type)
                }
            )
            image_url = supabase.storage.from_("profiles").get_public_url(file_path)

        # 3. 구글 이미지 URL 처리 (기존 꿀팁 로직 유지)
        elif google_image_url:
            image_url = google_image_url

        # 4. DB 업데이트 (기존 쿼리 유지)
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
    # 1. 토큰 검증
    current_user_id = verify_token(authorization)
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # 2. 사용자 정보 조회 (기존 정보 유지 + created_at 추가)
        cur.execute(
            "SELECT user_id, email, nickname, profile_image, created_at FROM users WHERE user_id = %s",
            (current_user_id,)
        )
        user = cur.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
        
        user_data = cast(Dict[str, Any], user)

        # 3. 내가 만든 챗봇 목록 조회 (Zeta 스타일 확장을 위해 추가된 부분, 기존 기능 방해 안함)
        # 테이블 명이나 컬럼 명은 현재 프로젝트의 DB 구조에 맞춰져 있습니다.
        cur.execute(
            """
            SELECT id, bot_name, profile_image, created_at 
            FROM chatbots 
            WHERE user_id = %s 
            ORDER BY created_at DESC
            """,
            (current_user_id,)
        )
        my_chatbots = cur.fetchall()
        chatbots_list = [cast(Dict[str, Any], bot) for bot in my_chatbots]
            
        return {
            "status": "success",
            "data": {
                "user_info": {
                    "user_id": user_data['user_id'],
                    "email": user_data['email'],
                    "nickname": user_data['nickname'] or "여행자",
                    "profile_image": user_data['profile_image'],
                    "created_at": user_data['created_at'].isoformat() if user_data.get('created_at') else None
                },
                "my_chatbots": chatbots_list
            }
        }
    except Exception as e:
        print(f"Get Profile Error: {e}")
        raise HTTPException(status_code=500, detail="정보를 가져오는 중 오류가 발생했습니다.")
    finally:
        cur.close()
        conn.close()