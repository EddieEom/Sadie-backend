from pydantic import BaseModel, EmailStr
from typing import Optional, List

# --- 1. 인증 및 사용자 계정 관련 모델 ---
class UserAuth(BaseModel):
    """회원가입 모델"""
    user_id: str
    password: str
    email: str

class LoginRequest(BaseModel):
    """로그인 요청 모델"""
    user_id: str
    password: str

class ResetRequest(BaseModel):
    """비밀번호 재설정 요청 모델"""
    user_id: str
    email: EmailStr

class VerifyReset(BaseModel):
    """비밀번호 재설정 확인 및 변경 모델"""
    user_id: str
    code: str
    new_password: str

class GoogleLoginRequest(BaseModel):
    """구글 소셜 로그인 요청 모델"""
    id_token: str

class PasswordChange(BaseModel):
    """기존 비밀번호 변경 모델"""
    current_password: str
    new_password: str

class ProfileUpdate(BaseModel):
    """사용자 프로필(닉네임 등) 수정 모델"""
    nickname: str


# --- 2. 채팅방 및 메시지 관련 모델 ---
class ChatRequest(BaseModel):
    """채팅 메시지 전송 모델"""
    room_id: int
    message: str

class RoomCreate(BaseModel):
    """
    채팅방 생성 모델
    """
    title: str