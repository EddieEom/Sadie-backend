from pydantic import BaseModel, EmailStr

class UserAuth(BaseModel):
    user_id: str
    password: str
    email: str

class LoginRequest(BaseModel):
    user_id: str
    password: str

class ResetRequest(BaseModel):
    user_id: str
    email: EmailStr

class VerifyReset(BaseModel):
    user_id: str
    code: str
    new_password: str

class ChatRequest(BaseModel):
    room_id: int
    message: str

class RoomCreate(BaseModel):
    title: str

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

# routes/user.py에서 사용할 모델도 추가 (필요시)
class ProfileUpdate(BaseModel):
    nickname: str

class GoogleLoginRequest(BaseModel):
    id_token: str