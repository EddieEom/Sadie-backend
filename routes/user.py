import os
from typing import Optional, Dict, Any, cast
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Header
from supabase import create_client, Client

from core.database import get_db_connection
from core.security import verify_token
from psycopg2.extras import RealDictCursor

router = APIRouter(prefix="/users", tags=["users"])

# 환경 변수 설정
SUPABASE_URL: str = os.getenv("SUPABASE_URL") or ""
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY") or ""

# Supabase 클라이언트 초기화 (URL/KEY가 없어도 서버가 죽지 않도록 방어)
# 2. 선언부 수정
supabase: Optional[Client] = None # 처음부터 Optional로 선언

try:
    if SUPABASE_URL and SUPABASE_KEY:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    else:
        print("Warning: Supabase credentials missing.")
except Exception as e:
    print(f"Error initializing Supabase: {e}")

@router.post("/me/profile")
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

        # 1. 이미지 처리 로직 (Supabase 에러가 나도 전체가 멈추지 않도록 개별 try-except 적용)
        try:
            # 직접 업로드한 파일이 있는 경우
            if profile_image and profile_image.filename and supabase:
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
            
            # 파일은 없지만 구글 이미지 URL을 사용하는 경우
            elif google_image_url:
                image_url = google_image_url
                
        except Exception as img_err:
            # 이미지 업로드 실패 시 로그만 남기고 닉네임 업데이트는 진행할 수 있게 함
            print(f"Image Upload Failed (Ignored): {img_err}")
            # 이미지가 실패해도 기존 구글 이미지 URL이 있다면 그것이라도 유지
            if google_image_url:
                image_url = google_image_url

        # 2. DB 업데이트 (핵심 로직)
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
        print(f"Critical Update Error: {e}")
        raise HTTPException(status_code=500, detail="프로필 업데이트 중 오류가 발생했습니다.")
    finally:
        cur.close()
        conn.close()

@router.get("/me")
async def get_my_profile(authorization: Optional[str] = Header(None)):
    current_user_id = verify_token(authorization)
    conn = get_db_connection()
    
    # 2. RealDictCursor를 사용하여 데이터를 딕셔너리 형태로 가져옵니다.
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # 3. SELECT 절에 'is_social' 필드를 반드시 추가합니다.
        cur.execute(
            """
            SELECT user_id, email, nickname, profile_image, is_social, created_at 
            FROM users 
            WHERE user_id = %s
            """,
            (current_user_id,)
        )
        user = cur.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

        # 4. 서버 터미널 디버깅 로그 (이제 필드가 보일 겁니다)
        print(f"--- [DEBUG] user.py /me 호출됨: {user} ---", flush=True)
            
        return {
            "status": "success",
            "data": {
                "user_id": user['user_id'],
                "email": user['email'],
                "nickname": user['nickname'],
                "profile_image": user['profile_image'],
                # 5. bool 형변환을 통해 확실하게 true/false 전달
                "is_social": bool(user.get('is_social')), 
                "created_at": user['created_at'].isoformat() if user.get('created_at') else None
            }
        }
    except Exception as e:
        print(f"Profile Fetch Error: {e}")
        raise HTTPException(status_code=500, detail="프로필 정보를 가져오는데 실패했습니다.")
    finally:
        cur.close()
        conn.close()


@router.put("/me/nickname")
async def update_nickname(
    payload: dict, 
    authorization: Optional[str] = Header(None)
):
    current_user_id = verify_token(authorization)
    new_nickname = payload.get("nickname")

    if not new_nickname or len(new_nickname.strip()) < 2:
        raise HTTPException(status_code=400, detail="닉네임은 최소 2글자 이상이어야 합니다.")

    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute(
            "UPDATE users SET nickname = %s WHERE user_id = %s",
            (new_nickname, current_user_id)
        )
        conn.commit()
        
        return {"status": "success", "message": "닉네임이 성공적으로 변경되었습니다."}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail="닉네임 변경 중 오류가 발생했습니다.")
    finally:
        cur.close()
        conn.close()