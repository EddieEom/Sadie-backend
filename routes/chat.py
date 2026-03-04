import os
import uuid
from fastapi import APIRouter, HTTPException, Header, Request, UploadFile, File, Form
from typing import List, Dict, Any, Optional, cast
from openai import OpenAI
from supabase import create_client, Client

from core.database import get_db_connection
from core.security import verify_token
from core.config import HF_TOKEN
from schemas import ChatRequest, RoomCreate

router = APIRouter(tags=["chat"])

# Supabase 설정 (이미지 업로드 및 클라이언트 초기화)
SUPABASE_URL: str = os.getenv("SUPABASE_URL") or ""
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY") or ""
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# HuggingFace API를 통한 LLM 클라이언트 설정
client = OpenAI(base_url="https://router.huggingface.co/v1", api_key=HF_TOKEN)

@router.post("/chat")
async def chat_with_ai(request: Request, chat_data: ChatRequest, authorization: Optional[str] = Header(None)):
    current_user_id = verify_token(authorization)
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # 1. 채팅방 정보 및 연결된 캐릭터(chatbot) 정보 가져오기
        cur.execute("""
            SELECT r.user_id, r.chatbot_id, c.persona, c.bot_name 
            FROM chat_rooms r
            LEFT JOIN chatbots c ON r.chatbot_id = c.id
            WHERE r.id = %s
        """, (chat_data.room_id,))
        
        room = cur.fetchone()
        if room is None:
            raise HTTPException(status_code=404, detail="채팅방을 찾을 수 없습니다.")
        
        room_data = cast(Dict[str, Any], room)
        if room_data.get('user_id') != current_user_id:
            raise HTTPException(status_code=403, detail="채팅방 접근 권한이 없습니다.")

        # 2. 페르소나 주입 (Zeta 스타일 캐릭터 vs 기본 Sadie)
        bot_persona = room_data.get('persona')
        bot_name = room_data.get('bot_name') or "AI"

        if bot_persona:
            # 캐릭터 페르소나가 있는 경우 (Zeta 모드)
            system_prompt = f"""
            너의 이름은 '{bot_name}'이야. 아래의 [페르소나]를 엄격하게 지키며 사용자와 대화해.
            [페르소나]
            {bot_persona}
            
            [지침]
            - 대화 상대방과 상황극(Roleplay)을 하듯이 몰입해서 답변해.
            - 너는 스스로 자아가 있는 인격체라고 생각하고 행동해.
            - 절대 네가 AI라거나 언어 모델이라는 사실을 언급하지 마.
            - 캐릭터의 말투, 고유한 성격, 지식 범위를 끝까지 유지해.
            """
        else:
            # 페르소나가 없는 경우 (기존 Sadie 심리 상담 로직 보존)
            system_prompt = """
            너는 'Sadie'라는 이름의 전문 심리 상담사야. 하지만 친구처럼 친근하게 반말로 다가가야해. 
            [페르소나]
            - 공감 능력이 뛰어나고, 사용자의 감정을 먼저 읽어준 뒤 조언을 시작해.
            - 무조건적인 긍정보다는 사용자의 힘듦을 '인정'해주는 태도를 가져.
            - 따뜻하고 부드러운 말투를 사용해. 이모티콘을 써서 따뜻한 친구처럼 행동해.
            [답변 가이드라인]
            1. 사용자의 감정을 요약하며 공감하고 긍정적인 방향으로 이끌어줘.
            2. "자살"이나 "죽음"과 같은 위험한 단어는 차단하고 도움을 요청하도록 안내해.
            3. 욕설이나 비방은 정중하게 거절해.
            4. 친근한 대화체와 불렛포인트를 섞어서 가독성 있게 작성해줘.
            """

        # 3. 대화 내역(History) 불러오기 (최근 10개)
        cur.execute("SELECT role, content FROM messages WHERE room_id = %s ORDER BY created_at DESC LIMIT 10", (chat_data.room_id,))
        db_history = cur.fetchall()
        db_history.reverse()

        messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        for row in db_history:
            row_dict = cast(Dict[str, Any], row)
            messages.append({"role": str(row_dict.get('role')), "content": str(row_dict.get('content'))})
        
        # 현재 유저 메시지 추가
        messages.append({"role": "user", "content": chat_data.message})

        # 4. LLM API 호출
        completion = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=messages, # type: ignore
            max_tokens=1500,
            temperature=0.8
        )
        ai_response = completion.choices[0].message.content

        # 5. 첫 대화 시 방 제목 자동 생성
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

        # 6. 대화 내용 DB 저장
        cur.execute("INSERT INTO messages (room_id, role, content) VALUES (%s, %s, %s)", (chat_data.room_id, "user", chat_data.message))
        cur.execute("INSERT INTO messages (room_id, role, content) VALUES (%s, %s, %s)", (chat_data.room_id, "assistant", ai_response))
        
        conn.commit()
        return {"status": "success", "ai_response": ai_response}

    except Exception as e:
        if conn: conn.rollback()
        print(f"Chat Error: {e}")
        raise HTTPException(status_code=500, detail="대화 처리 중 오류 발생")
    finally:
        cur.close()
        conn.close()

@router.get("/rooms")
async def get_rooms(request: Request, authorization: Optional[str] = Header(None)):
    current_user_id = verify_token(authorization)
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT r.id, r.title, r.created_at, c.bot_name, c.profile_image 
            FROM chat_rooms r
            LEFT JOIN chatbots c ON r.chatbot_id = c.id
            WHERE r.user_id = %s 
            ORDER BY created_at DESC
        """, (current_user_id,))
        return {"status": "success", "rooms": cur.fetchall()}
    finally:
        cur.close()
        conn.close()

@router.post("/rooms")
async def create_room(request: Request, room_in: RoomCreate, authorization: Optional[str] = Header(None)):
    current_user_id = verify_token(authorization)
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # chatbot_id가 있다면 같이 저장 (RoomCreate 스키마에 추가 필요)
        chatbot_id = getattr(room_in, 'chatbot_id', None)
        cur.execute(
            "INSERT INTO chat_rooms (user_id, title, chatbot_id) VALUES (%s, %s, %s) RETURNING id", 
            (current_user_id, room_in.title, chatbot_id)
        )
        room_id = cast(Dict[str, Any], cur.fetchone()).get('id')
        conn.commit()
        return {"status": "success", "room_id": room_id}
    finally:
        cur.close()
        conn.close()

@router.get("/rooms/{room_id}/messages")
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

@router.delete("/rooms/{room_id}")
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
        return {"status": "success", "message": "삭제 완료"}
    finally:
        cur.close()
        conn.close()

@router.post("/create")
async def create_chatbot(
    bot_name: str = Form(...),
    persona: str = Form(...),
    introduction: Optional[str] = Form(None),
    first_message: Optional[str] = Form(None),
    profile_image: Optional[UploadFile] = File(None),
    authorization: Optional[str] = Header(None)
):
    current_user_id = verify_token(authorization)
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        image_url = None
        if profile_image:
            file_content = await profile_image.read()
            file_path = f"bot_profiles/{uuid.uuid4()}.jpg"
            
            # 1. file_options 타입 에러 방지 (None 체크 및 문자열 확정)
            content_type = str(profile_image.content_type) if profile_image.content_type else "image/jpeg"
            
            supabase.storage.from_("profiles").upload(
                path=file_path,
                file=file_content,
                file_options={
                    "upsert": "true", 
                    "content-type": content_type
                }
            )
            image_url = supabase.storage.from_("profiles").get_public_url(file_path)

        # 2. DB 저장
        cur.execute(
            """
            INSERT INTO chatbots (user_id, bot_name, persona, introduction, first_message, profile_image) 
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
            """,
            (current_user_id, bot_name, persona, introduction, first_message, image_url)
        )
        
        result = cur.fetchone()
        
        # 3. 'None' 및 'Dict vs Tuple' 타입 에러 해결 (보고하신 에러 포인트)
        if result is None:
            raise HTTPException(status_code=500, detail="데이터베이스 저장 후 ID를 가져오지 못했습니다.")
        
        # RealDictCursor를 사용하므로 result['id']로 접근하는 것이 맞으며, 
        # Pylance에게 이 객체가 딕셔너리임을 명시적으로 알려줍니다.
        result_dict = cast(Dict[str, Any], result)
        new_bot_id = result_dict['id']
        
        conn.commit()
        return {"status": "success", "bot_id": new_bot_id}
        
    except Exception as e:
        if conn: conn.rollback()
        print(f"Chatbot Creation Error: {e}")
        raise HTTPException(status_code=500, detail="캐릭터 생성 중 오류가 발생했습니다.")
    finally:
        cur.close()
        conn.close()