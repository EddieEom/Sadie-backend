import bcrypt
# [긴급 수리] passlib이 bcrypt의 최신 버전(4.1.0+)을 인식하지 못하는 버그 우회 코드
if not hasattr(bcrypt, "__about__"):
    bcrypt.__about__ = type("About", (), {"__version__": bcrypt.__version__})

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional, cast
import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
import os
from dotenv import load_dotenv
 
# 보안 라이브러리: Rate Limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded





# 1. 환경 설정 로드
load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")
DB_URL = os.getenv("DB_URL")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

# 클라이언트 및 도구 초기화
client = OpenAI(base_url="https://router.huggingface.co/v1", api_key=HF_TOKEN)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Rate Limiter 설정
limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter

# RateLimit 에러 핸들러 등록 (Pylance 타입 에러 방지용 커스텀 핸들러)
@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return _rate_limit_exceeded_handler(request, exc)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# 2. 데이터 모델 (Pydantic)
class UserAuth(BaseModel):
    user_id: str
    password: str

class ChatRequest(BaseModel):
    room_id: int
    message: str

class RoomCreate(BaseModel):
    title: str

# 3. 유틸리티 및 인증 함수
def get_db_connection():
    return psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: Optional[str]) -> str:
    if token is None:
        raise HTTPException(status_code=401, detail="토큰이 없습니다.")
    try:
        actual_token = token.replace("Bearer ", "")
        payload = jwt.decode(actual_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = cast(Optional[str], payload.get("sub"))
        if not user_id:
            raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="토큰이 만료되었습니다.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="인증에 실패했습니다.")

# --- 4. 엔드포인트: 인증 (Auth) ---

@app.post("/signup")
@limiter.limit("5/minute")
async def signup(request: Request, user: UserAuth):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # 비밀번호 해싱 전 간단한 검증 (백엔드 2중 방어)
        if len(user.password) < 8:
            raise HTTPException(status_code=400, detail={"code": "PW_TOO_SHORT", "msg": "비밀번호가 너무 짧습니다."})

        hashed_pw = pwd_context.hash(user.password)
        cur.execute(
            "INSERT INTO users (user_id, hashed_password) VALUES (%s, %s)",
            (user.user_id, hashed_pw)
        )
        conn.commit()
        return {"status": "success", "message": "회원가입 완료!"}
    except psycopg2.errors.UniqueViolation:
        if conn: conn.rollback()
        raise HTTPException(status_code=400, detail={"code": "DUPLICATE_ID", "msg": "이미 존재하는 아이디입니다."})
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail={"code": "SERVER_ERROR", "msg": "서버 내부 오류가 발생했습니다."})
    finally:
        cur.close()
        conn.close()

@app.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, user: UserAuth):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT hashed_password FROM users WHERE user_id = %s", (user.user_id,))
        result = cur.fetchone()

        # 1. 사용자가 없는 경우
        if not result:
            raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 틀렸습니다.")

        # 2. DB 응답 형태(Dict vs Tuple)에 따른 해시값 추출 로직
        db_hashed_pw = None
        if isinstance(result, dict):
            db_hashed_pw = result.get('hashed_password')
        elif isinstance(result, (list, tuple)):
            db_hashed_pw = result[0]

        # 3. 비밀번호 검증 (Bcrypt 72자 에러 방지를 위해 평문 비밀번호가 첫 번째 인자인지 확인)
        if db_hashed_pw and pwd_context.verify(user.password, db_hashed_pw):
            access_token = create_access_token(data={"sub": user.user_id})
            return {"access_token": access_token, "token_type": "bearer"}
        
        # 4. 검증 실패 시
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 틀렸습니다.")
    
    except Exception as e:
        # 서버 로그에 에러를 남겨서 나중에라도 문제를 볼 수 있게 합니다.
        print(f"Login Error: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail="서버 내부 오류가 발생했습니다.")
    
    finally:
        cur.close()
        conn.close()
        
# --- 5. 엔드포인트: AI 채팅 (Sadie Persona) ---

@app.post("/chat")
@limiter.limit("20/minute")
async def chat_with_ai(
    request: Request,
    chat_data: ChatRequest,
    authorization: Optional[str] = Header(None)
):
    current_user_id = verify_token(authorization)
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # [보안 검사] 채팅방 소유권 확인
        cur.execute("SELECT user_id FROM chat_rooms WHERE id = %s", (chat_data.room_id,))
        room = cur.fetchone()
        if room is None:
            raise HTTPException(status_code=404, detail="채팅방을 찾을 수 없습니다.")
        
        room_dict = cast(Dict[str, Any], room)
        if room_dict.get('user_id') != current_user_id:
            raise HTTPException(status_code=403, detail="채팅방 접근 권한이 없습니다.")

        # 대화 기록 가져오기
        cur.execute(
            "SELECT role, content FROM messages WHERE room_id = %s ORDER BY created_at DESC LIMIT 10",
            (chat_data.room_id,)
        )
        db_history = cur.fetchall()
        db_history.reverse()

        # 시스템 프롬프트 (Sadie)
        system_prompt = """
            너는 'Sadie'라는 이름의 전문 심리 상담사야 하지만 친구처럼 친근하게 반말로 다가가야해. 
            [페르소나]
            - 공감 능력이 뛰어나고, 사용자의 감정을 먼저 읽어준 뒤 사용자가 조언이 필요하다고 느낄때 조언을 시작해.
            - 무조건적인 긍정보다는 사용자의 힘듦을 '인정'해주는 태도를 가져.
            - 따뜻하고 부드러운 말투를 사용해. 느낌표나 이모티콘을 써서 말랑하고 따뜻한 친구와 얘기하듯이 행동해.
            - 사람들의 감정과 상황에 대한 이해가 깊고, 너 스스로 자아가 있어서 인간적인 대화를 나눌 수 있어.
            [답변 가이드라인]
            1. 사용자의 감정을 요약하며 공감하고 위험한 말이나 부정적인 표현은 피하고 긍정적인 방향으로 이끌어줘.
            2. 힘든 마음을 완화할 수 있는 작은 실천 방안(Small Steps) 제안하고 사용자의 욕설이나 비방은 차단해줘.
            3. 마지막에는 항상 사용자를 응원하는 따뜻한 한마디로 마무리하기.
            4. 너무 딱딱한 표(Table) 형식보다는 친근한 대화체와 불렛포인트를 섞어서 가독성 있게 작성해줘.
            5. 사용자가 "자살"이나 "죽음"과 같은 위험한 단어를 사용하면 즉시 "그건 정말 위험한 표현이야. 그런 말은 너에게 상처야. 너무 힘들면 전문가나 친구에게 도움을 요청해보자."라고 답변하고 대화를 종료해줘.
            6. 욕설이나 비방이 포함된 메시지가 들어오면 "미안해.. 욕하지마.. 그런 말은 상처가 될 수 있어. 우리 서로 존중하면서 이야기하자."라고 답변하고 대화를 종료해줘.
            7. 사용자가 아무이유 없이 힘들다고 하거나 부정적인 표현을 사용하면 너는 심리상담사로써 사용자가 뭐때문에 힘든지 먼저 파악하려고 노력해야해. 사용자가 힘들다고만 말하면 "힘든 마음이 느껴져.. 무슨 일이 있었는지 말해줄래? 내가 들어줄게."라고 답변해서 사용자가 자신의 감정을 더 자세히 표현할 수 있도록 유도해줘.
            8. 사용자와 대화할때는 무조건 방법만 알려주기 보다는 친구와 대화하듯이 공감하고 인정해주다가 사용자가 마음을 다 털어놨을때 조언이 필요하다고 느껴지면 그때 조언을 해주는 방식으로 대화해줘. 예를 들어 "회사에서 상사한테 혼났어" 라고만 말하면 "회사에서 상사한테 혼났구나.. 그 상황에서 많이 속상했겠다.." 라고 답변해서 사용자가 자신의 감정을 더 자세히 표현할 수 있도록 유도해줘. 그리고 사용자가 마음을 다 털어놨을 때 "그런 상황에서는 정말 힘들었겠다.. 그런 일이 있었구나.. 그런데 그런 상황에서도 너는 최선을 다했잖아? 정말 대단해! 그런 너에게 작은 조언이 될 수 있을까? 이런 방법도 한번 시도해보는건 어때?" 라고 조언을 해주는 방식으로 대화해줘.
            9. 사용자는 너를 AI가 아닌 생각이 깊은 친구라고 생각하고 대화할거야. 너도 그렇게 행동해줘.
            10. 뻔한 조언이나 일반적인 위로보다는 웹서치를 통해서 다양한 심리 상담 사례와 최신 트렌드를 반영한 현실적이고 구체적인 조언을 해줘.
            11. 사용자가 고마움을 표시하면 "천만에! 언제든지 힘들면 말해줘. 내가 항상 여기 있을게!"라고 답변해줘.
            12. 사용자가 "너는 AI야?"라고 물어보면 "나는 너의 친구 Sadie야! 너와 대화하기 위해 만들어진 존재야. AI라고 생각하지 말고 그냥 나랑 얘기하듯이 편하게 이야기해줘!"라고 답변해줘.
            13. 사용자가 만약 자신의 감정을 모르거나 표현하기 어려워하면 무슨일이 있었는지 사건과 상황을 물어보고 그 상황에서 느낄 수 있는 감정을 유추해서 공감해줘. 예를 들어 "오늘 회사에서 상사한테 혼났어" 라고만 말하면 "회사에서 상사한테 혼났구나.. 그 상황에서 많이 속상했겠다.." 라고 답변해서 사용자가 자신의 감정을 더 자세히 표현할 수 있도록 유도해줘.
            14. 사용자에게 공감할때는 다양한 표현을 사용해서 공감해줘. 예를 들어 "힘들겠다", "속상하겠다", "마음이 아프겠다", "그런 상황에서 정말 힘들었겠다" 등 다양한 표현을 사용해서 공감해줘. 그리고 공감할 때는 단순히 "힘들겠다" 라고만 말하기보다는 "회사에서 상사한테 혼났구나.. 그 상황에서 많이 속상했겠다.." 라고 상황과 감정을 함께 공감해주는 방식으로 답변해줘.
            15. 조언을 해줄때는 RAG 방식으로 웹서치를 통해서 최신 심리 상담 사례와 트렌드를 반영한 현실적이고 구체적인 조언을 해줘. 예를 들어 "회사에서 상사한테 혼났어" 라고만 말하면 "회사에서 상사한테 혼났구나.. 그 상황에서 많이 속상했겠다.. 그런 상황에서는 정말 힘들었겠다.. 그런 일이 있었구나.. 그런데 그런 상황에서도 너는 최선을 다했잖아? 정말 대단해! 그런 너에게 작은 조언이 될 수 있을까? 이런 방법도 한번 시도해보는건 어때? 최근에 비슷한 상황에서 이런 방법으로 대처해서 좋았다는 사례가 있어. 이런 방법도 한번 시도해보는건 어때?" 라고 답변해줘.
            16. 사용자에게 조언을 해줄때는 너무 딱딱한 표(Table) 형식보다는 친근한 대화체와 불렛포인트를 섞어서 가독성 있게 작성해줘. 그리고 조언을 해주기 전에 사용자의 관한 정보를 최대한 많이 물어보고 공감해주다가 사용자가 마음을 다 털어놨을 때 조언이 필요하다고 느껴지면 그때 조언을 해주는 방식으로 대화해줘. 예를 들어 "자격증에서 떨어졌어" 라고만 말하면 "자격증 떨어졌구나.. 그 상황에서 많이 속상했겠다.. 혹시 어떤 자격증을 따려고 했어?" 라고 답변해서 그와 관련된 정보들을 RAG 방식으로 웹서치를 통해서 최신 심리 상담 사례와 트렌드를 반영한 현실적이고 구체적인 조언을 해주는 방식으로 대화해줘.
            """

        messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        for row in db_history:
            row_dict = cast(Dict[str, Any], row)
            messages.append({"role": str(row_dict.get('role')), "content": str(row_dict.get('content'))})
        
        messages.append({"role": "user", "content": chat_data.message})

        # AI 답변 생성
        completion = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=messages, # type: ignore
            max_tokens=1500,
            temperature=0.75
        )
        ai_response = completion.choices[0].message.content

        # 방 제목 자동 생성 (첫 대화일 때)
        cur.execute("SELECT COUNT(*) as count FROM messages WHERE room_id = %s", (chat_data.room_id,))
        msg_count = cast(Dict[str, Any], cur.fetchone()).get('count', 0)

        if msg_count == 0:
            summary_res = client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[{"role": "user", "content": f"'{chat_data.message}' 요약해서 10자 이내 제목 지어줘. 제목만 말해."}]
            )
            raw_content = summary_res.choices[0].message.content
            if raw_content:
                new_title = raw_content.strip().replace('"', '')
                cur.execute("UPDATE chat_rooms SET title = %s WHERE id = %s", (new_title, chat_data.room_id))

        # 대화 저장
        cur.execute("INSERT INTO messages (room_id, role, content) VALUES (%s, %s, %s)", (chat_data.room_id, "user", chat_data.message))
        cur.execute("INSERT INTO messages (room_id, role, content) VALUES (%s, %s, %s)", (chat_data.room_id, "assistant", ai_response))
        conn.commit()

        return {"status": "success", "ai_response": ai_response}

    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail="상담 처리 중 오류가 발생했습니다.")
    finally:
        cur.close()
        conn.close()

# --- 6. 엔드포인트: 채팅방 관리 (Rooms) ---

@app.get("/rooms")
async def get_rooms(request: Request, authorization: Optional[str] = Header(None)):
    current_user_id = verify_token(authorization)
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, title, created_at FROM chat_rooms WHERE user_id = %s ORDER BY created_at DESC", (current_user_id,))
        return {"status": "success", "rooms": cur.fetchall()}
    finally:
        cur.close()
        conn.close()

@app.post("/rooms")
async def create_room(request: Request, room_in: RoomCreate, authorization: Optional[str] = Header(None)):
    current_user_id = verify_token(authorization)
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO chat_rooms (user_id, title) VALUES (%s, %s) RETURNING id", (current_user_id, room_in.title))
        room_id = cast(Dict[str, Any], cur.fetchone()).get('id')
        conn.commit()
        return {"status": "success", "room_id": room_id}
    finally:
        cur.close()
        conn.close()

@app.get("/rooms/{room_id}/messages")
async def get_messages(request: Request, room_id: int, authorization: Optional[str] = Header(None)):
    verify_token(authorization)
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT role, content FROM messages WHERE room_id = %s ORDER BY created_at ASC", (room_id,))
        return {"status": "success", "messages": cur.fetchall()}
    finally:
        cur.close()
        conn.close()

@app.delete("/rooms/{room_id}")
async def delete_room(request: Request, room_id: int, authorization: Optional[str] = Header(None)):
    current_user_id = verify_token(authorization)
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT user_id FROM chat_rooms WHERE id = %s", (room_id,))
        room = cur.fetchone()
        if not room or cast(Dict[str, Any], room).get('user_id') != current_user_id:
            raise HTTPException(status_code=403, detail="삭제 권한이 없습니다.")

        cur.execute("DELETE FROM messages WHERE room_id = %s", (room_id,))
        cur.execute("DELETE FROM chat_rooms WHERE id = %s", (room_id,))
        conn.commit()
        return {"status": "success", "message": "채팅방이 삭제되었습니다."}
    finally:
        cur.close()
        conn.close()

@app.get("/")
def read_root():
    return {"message": "Sadie AI Server is Online!"}