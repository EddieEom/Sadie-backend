import os
from typing import Optional, Dict, Any, cast, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Header
from supabase import create_client, Client

from services.analysis_service import SadieAnalyzer
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
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # [수정] user_id 비교 시 ::text를 추가하여 UUID와 TEXT 타입 간 충돌을 해결합니다.
        cur.execute(
            """
            SELECT 
                u.user_id, u.email, u.nickname, u.profile_image, u.is_social, u.created_at,
                r.content->>'status_score' as mind_score
            FROM users u
            LEFT JOIN (
                SELECT DISTINCT ON (user_id::text) user_id, content, created_at
                FROM user_reports 
                WHERE report_type = 'weekly'
                ORDER BY user_id::text, created_at DESC
            ) r ON u.user_id::text = r.user_id::text
            WHERE u.user_id::text = %s
            """,
            (str(current_user_id),) # 안전하게 문자열로 변환하여 전달
        )
        user = cast(Dict[str, Any], cur.fetchone())
        
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

        return {
            "status": "success",
            "data": {
                "user_id": user['user_id'],
                "email": user['email'],
                "nickname": user['nickname'],
                "profile_image": user['profile_image'],
                "is_social": bool(user.get('is_social')),
                # [추가] 분석 리포트가 있으면 점수를, 없으면 기본값 100을 반환
                "mind_score": float(user['mind_score']) if user.get('mind_score') else 36.5,
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

        
@router.get("/me/mood-chart") # prefix가 /users이므로 실제 경로는 /users/me/mood-chart
async def get_combined_mood_data(authorization: Optional[str] = Header(None)):
    # 1. 안전하게 토큰에서 유저 ID 추출 (current_user_id 직접 받기보다 권장)
    current_user_id = verify_token(authorization)
    
    conn = None
    cur = None
    try:
        analyzer = SadieAnalyzer()
        conn = analyzer.get_db_connection()
        # [핵심] RealDictCursor를 써야 딕셔너리 형태(r['date'])로 접근 가능합니다.
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT 
                TO_CHAR(created_at, 'MM/DD') as date,
                (content->>'status_score')::float as score,
                content->>'weekly_title' as title,
                content->>'sadie_message' as message
            FROM user_reports
            WHERE user_id::text = %s AND report_type = 'weekly'
            ORDER BY created_at DESC
            LIMIT 7
        """, (str(current_user_id),))
        
        # Pylance를 위한 타입 캐스팅
        rows = cast(List[Dict[str, Any]], cur.fetchall())
        
        if not rows:
            return {
                "chart_data": [{"date": "오늘", "score": 36.5}],
                "latest_brief": "Sadie와 첫 대화를 나눠보세요!",
                "current_temp": 36.5
            }
            
        # 최신순(DESC)으로 가져왔으므로, 차트용으로 시간순(reversed) 정렬
        chart_data = list(reversed([
            {"date": r['date'], "score": r['score']} for r in rows
        ]))
        
        return {
            "chart_data": chart_data,
            "latest_brief": rows[0]['message'],
            "current_temp": rows[0]['score']
        }
    except Exception as e:
        print(f"Mood Chart Error: {e}")
        raise HTTPException(status_code=500, detail="차트 데이터를 가져오지 못했습니다.")
    finally:
        if cur: cur.close()
        if conn: conn.close()