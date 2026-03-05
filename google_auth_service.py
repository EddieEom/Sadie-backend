import os
from fastapi import HTTPException
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from typing import Dict, Any, cast

# 구글 클라이언트 ID
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

async def process_google_login(data, get_db_connection, create_access_token):
    try:
        id_info = id_token.verify_oauth2_token(
            data.id_token, 
            google_requests.Request(), 
            GOOGLE_CLIENT_ID
        )

        email = id_info.get("email")
        user_id = f"google_{id_info.get('sub')}" 
        # 구글에서 주는 기본 정보 추출
        google_name = id_info.get("name", "")
        google_picture = id_info.get("picture")

        if not email:
            raise HTTPException(status_code=400, detail="이메일 정보를 가져올 수 없습니다.")

        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            # 2. 기존 유저 확인 (닉네임이 있는지까지 확인하면 더 좋습니다)
            cur.execute("SELECT user_id, nickname FROM users WHERE email = %s", (email,))
            user = cur.fetchone()

            is_new_user = False
            if not user:
                # 3. 신규 유저 등록 (is_social 필드 추가!)
                cur.execute(
                    """
                    INSERT INTO users (user_id, hashed_password, email, is_social) 
                    VALUES (%s, %s, %s, %s)
                    """,
                    (user_id, "SOCIAL_AUTH", email, True) # True 값을 명시적으로 전달
                )
                conn.commit()
                final_user_id = user_id
                is_new_user = True
            else:
                user_dict = cast(Dict[str, Any], user)
                final_user_id = user_dict['user_id']
                # 아이디는 있는데 닉네임이 없다면 온보딩을 거치게 하기 위해 신규 유저로 취급
                if not user_dict.get('nickname'):
                    is_new_user = True

            # 4. 토큰 생성 및 응답 데이터 구성
            access_token = create_access_token(data={"sub": final_user_id})
            
            return {
                "access_token": access_token, 
                "token_type": "bearer",
                "is_new_user": is_new_user,
                "google_name": google_name,
                "google_picture": google_picture
            }

        finally:
            cur.close()
            conn.close()

    except ValueError:
        raise HTTPException(status_code=401, detail="유효하지 않은 구글 토큰입니다.")