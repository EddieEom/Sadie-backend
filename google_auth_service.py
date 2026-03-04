import os
from fastapi import HTTPException
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from typing import Dict, Any, cast

# 구글 클라이언트 ID
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

async def process_google_login(data, get_db_connection, create_access_token):
    try:
        # 1. 구글 토큰 검증
        id_info = id_token.verify_oauth2_token(
            data.id_token, 
            google_requests.Request(), 
            GOOGLE_CLIENT_ID
        )

        email = id_info.get("email")
        user_id = f"google_{id_info.get('sub')}" 

        if not email:
            raise HTTPException(status_code=400, detail="이메일 정보를 가져올 수 없습니다.")

        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            # 2. 기존 유저 확인
            cur.execute("SELECT user_id FROM users WHERE email = %s", (email,))
            user = cur.fetchone()

            if not user:
                # 3. 신규 유저 자동 등록
                cur.execute(
                    "INSERT INTO users (user_id, hashed_password, email) VALUES (%s, %s, %s)",
                    (user_id, "SOCIAL_AUTH", email)
                )
                conn.commit()
                final_user_id = user_id
            else:
                final_user_id = cast(Dict[str, Any], user)['user_id']

            # 4. 토큰 생성
            access_token = create_access_token(data={"sub": final_user_id})
            return {"access_token": access_token, "token_type": "bearer"}

        finally:
            cur.close()
            conn.close()

    except ValueError:
        raise HTTPException(status_code=401, detail="유효하지 않은 구글 토큰입니다.")