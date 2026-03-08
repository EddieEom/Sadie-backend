import bcrypt
import random
import time
import sib_api_v3_sdk
from typing import Dict, Any, Optional, cast
from fastapi import APIRouter, HTTPException, Request, Header
from sib_api_v3_sdk.rest import ApiException

# [변경 포인트] 파일명 변경에 따른 import 수정
import google_auth_service 
from core.database import get_db_connection
from core.security import create_access_token, verify_token
from core.config import BREVO_API_KEY
from schemas import (
    UserAuth, LoginRequest, ResetRequest, 
    VerifyReset, PasswordChange, GoogleLoginRequest
)
from psycopg2.extras import RealDictCursor

# [긴급 수리] passlib/bcrypt 버그 우회
if not hasattr(bcrypt, "__about__"):
    bcrypt.__about__ = type("About", (), {"__version__": bcrypt.__version__})

router = APIRouter(tags=["auth"])

# Brevo 설정 초기화
configuration = sib_api_v3_sdk.Configuration()
configuration.api_key['api-key'] = str(BREVO_API_KEY)
api_client = sib_api_v3_sdk.ApiClient(configuration)
api_instance = sib_api_v3_sdk.TransactionalEmailsApi(api_client)

# 인증 코드 임시 저장소
reset_codes: Dict[str, dict] = {}

@router.post("/signup")
async def signup(request: Request, user: UserAuth):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        salt = bcrypt.gensalt()
        hashed_pw = bcrypt.hashpw(user.password.encode('utf-8'), salt).decode('utf-8')
        cur.execute(
            "INSERT INTO users (user_id, hashed_password, email) VALUES (%s, %s, %s)",
            (user.user_id, hashed_pw, user.email)
        )
        conn.commit()
        return {"status": "success", "message": "회원가입 완료!"}
    except Exception:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail="아이디 중복 또는 가입 오류")
    finally:
        cur.close()
        conn.close()

@router.post("/login")
async def login(request: Request, user: LoginRequest):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT hashed_password FROM users WHERE user_id = %s", (user.user_id,))
        result = cur.fetchone()
        if result:
            res_dict = cast(Dict[str, Any], result)
            if bcrypt.checkpw(user.password.encode('utf-8'), res_dict['hashed_password'].encode('utf-8')):
                access_token = create_access_token(data={"sub": user.user_id})
                return {"access_token": access_token, "token_type": "bearer"}
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 틀렸습니다.")
    finally:
        cur.close()
        conn.close()

@router.post("/request-reset-code")
async def request_reset_code(req: ResetRequest):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT email FROM users WHERE user_id = %s", (req.user_id,))
    user_res = cur.fetchone()
    cur.close()
    conn.close()

    if not user_res:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    user_dict = cast(Dict[str, Any], user_res)
    if user_dict['email'] != req.email:
        raise HTTPException(status_code=404, detail="정보가 일치하지 않습니다.")
    
    code = f"{random.randint(100000, 999999)}"
    reset_codes[req.user_id] = {"code": code, "expiry": time.time() + 300}

    try:
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            sender={"name": "Sadie", "email": "sadie.noreply@gmail.com"},
            to=[{"email": req.email}],
            subject="[Sadie] 비밀번호 재설정 인증번호",
            html_content=f"""
                <div style="font-family: sans-serif; padding: 20px; border: 1px solid #eee;">
                    <h2 style="color: #008080;">비밀번호 재설정 안내</h2>
                    <p>안녕하세요, Sadie 상담소입니다.</p>
                    <p>요청하신 인증번호는 다음과 같습니다:</p>
                    <div style="font-size: 24px; font-weight: bold; color: #333; margin: 20px 0;">{code}</div>
                    <p>인증번호는 5분 후 만료됩니다.</p>
                </div>
            """
        )
        api_instance.send_transac_email(send_smtp_email)
        return {"message": "인증번호 발송 완료"}
    except ApiException as e:
        print(f"Brevo API Error: {e}")
        raise HTTPException(status_code=500, detail="메일 발송 중 오류가 발생했습니다.")

@router.post("/verify-and-reset")
async def verify_and_reset(req: VerifyReset):
    info = reset_codes.get(req.user_id)
    if not info or info["code"] != req.code or time.time() > info["expiry"]:
        raise HTTPException(status_code=400, detail="인증번호가 틀렸거나 만료되었습니다.")

    salt = bcrypt.gensalt()
    new_hashed_pw = bcrypt.hashpw(req.new_password.encode('utf-8'), salt).decode('utf-8')
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE users SET hashed_password = %s WHERE user_id = %s", (new_hashed_pw, req.user_id))
        conn.commit()
        if req.user_id in reset_codes: del reset_codes[req.user_id]
        return {"message": "비밀번호 변경 성공"}
    except Exception:
        conn.rollback()
        raise HTTPException(status_code=500, detail="변경 중 오류 발생")
    finally:
        cur.close()
        conn.close()

@router.delete("/delete-account")
async def delete_account(
    request: Request, 
    authorization: Optional[str] = Header(None)
):
    current_user_id = verify_token(authorization)
    
    # 프론트에서 보낸 JSON 바디(비밀번호)를 읽습니다.
    # DELETE 요청도 바디를 가질 수 있습니다.
    data = await request.json()
    password_provided = data.get("password")

    conn = get_db_connection()
    # 컬럼명으로 데이터를 가져오기 위해 RealDictCursor를 사용합니다.
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # 1. 유저의 소셜 가입 여부와 비밀번호 해시를 가져옴
        cur.execute("SELECT hashed_password, is_social FROM users WHERE user_id = %s", (current_user_id,))
        user_res = cur.fetchone()

        if not user_res:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

        user_dict = cast(Dict[str, Any], user_res)
        
        # 2. 일반 계정(is_social = False)인 경우에만 비밀번호 검증
        if not user_dict.get('is_social'):
            if not password_provided:
                raise HTTPException(status_code=400, detail="비밀번호를 입력해주세요.")
            
            # 기존 login 로직에서 사용하신 bcrypt 검증 방식 그대로 사용
            if not bcrypt.checkpw(password_provided.encode('utf-8'), user_dict['hashed_password'].encode('utf-8')):
                raise HTTPException(status_code=401, detail="비밀번호가 일치하지 않습니다.")

        # 3. 데이터 삭제 (추가된 분석 테이블 포함)
            cur.execute("DELETE FROM user_daily_moods WHERE user_id = %s", (current_user_id,))
            cur.execute("DELETE FROM user_reports WHERE user_id = %s", (current_user_id,))
            cur.execute("DELETE FROM user_psych_profiles WHERE user_id = %s", (current_user_id,))

            # 기존 로직 (채팅 내역 등)
            cur.execute("DELETE FROM messages WHERE room_id IN (SELECT id FROM chat_rooms WHERE user_id = %s)", (current_user_id,))
            cur.execute("DELETE FROM chat_rooms WHERE user_id = %s", (current_user_id,))
            cur.execute("DELETE FROM users WHERE user_id = %s", (current_user_id,))
        

        conn.commit()
        return {"status": "success", "message": "회원 탈퇴 및 모든 데이터 삭제 완료"}

    except Exception as e:
        if conn: conn.rollback()
        # 에러가 HTTPException이면 그대로 던지고, 아니면 500 에러 발생
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=f"탈퇴 처리 중 오류 발생: {str(e)}")
    finally:
        cur.close()
        conn.close()

@router.post("/change-password")
async def change_password(request: Request, data: PasswordChange, authorization: Optional[str] = Header(None)):
    current_user_id = verify_token(authorization)
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT hashed_password FROM users WHERE user_id = %s", (current_user_id,))
        user_res = cur.fetchone()
        if user_res:
            user_dict = cast(Dict[str, Any], user_res)
            if not bcrypt.checkpw(data.current_password.encode('utf-8'), user_dict['hashed_password'].encode('utf-8')):
                raise HTTPException(status_code=401, detail="현재 비밀번호가 일치하지 않습니다.")
        
        salt = bcrypt.gensalt()
        new_hashed_pw = bcrypt.hashpw(data.new_password.encode('utf-8'), salt).decode('utf-8')
        cur.execute("UPDATE users SET hashed_password = %s WHERE user_id = %s", (new_hashed_pw, current_user_id))
        conn.commit()
        return {"status": "success", "message": "비밀번호 변경 완료"}
    finally:
        cur.close()
        conn.close()

@router.post("/auth/google")
async def google_auth(data: GoogleLoginRequest): # schemas에서 가져온 타입 사용
    # 실제 처리는 google_auth_service에 맡깁니다.
    return await google_auth_service.process_google_login(
        data, 
        get_db_connection, 
        create_access_token
    )



async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """토큰을 검증하고 현재 유저의 정보를 반환합니다."""
    user_id = verify_token(authorization) # 내부에서 유효하지 않으면 401 raise 한다고 가정
    return {"id": user_id}