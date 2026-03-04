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
    채팅방 생성 모델 (Zeta 스타일 확장)
    title: 방 제목
    chatbot_id: 대화할 캐릭터의 ID (선택 사항, 없으면 기본 Sadie 상담사)
    """
    title: str
    chatbot_id: Optional[int] = None


# --- 3. Zeta 스타일 캐릭터(챗봇) 관련 모델 ---
class ChatbotCreate(BaseModel):
    """캐릭터(챗봇) 생성 시 사용하는 모델"""
    bot_name: str
    introduction: Optional[str] = None
    persona: str  # 캐릭터 성격 및 세계관 설정
    first_message: Optional[str] = None
    categories: Optional[List[str]] = []
    is_public: bool = True

class ChatbotUpdate(BaseModel):
    """기존 캐릭터 수정 시 사용하는 모델"""
    bot_name: Optional[str] = None
    introduction: Optional[str] = None
    persona: Optional[str] = None
    first_message: Optional[str] = None
    categories: Optional[List[str]] = None
    is_public: Optional[bool] = None

class ChatbotResponse(BaseModel):
    """마이페이지나 목록에서 캐릭터 정보를 반환할 때 사용하는 모델"""
    id: int
    bot_name: str
    introduction: Optional[str]
    profile_image: Optional[str]
    is_public: bool
    created_at: str