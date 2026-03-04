from fastapi import APIRouter, HTTPException, Header, Request
from typing import List, Dict, Any, Optional, cast
from openai import OpenAI

from core.database import get_db_connection
from core.security import verify_token
from core.config import HF_TOKEN
from schemas import ChatRequest, RoomCreate

router = APIRouter(tags=["chat"])

client = OpenAI(base_url="https://router.huggingface.co/v1", api_key=HF_TOKEN)

@router.post("/chat")
async def chat_with_ai(request: Request, chat_data: ChatRequest, authorization: Optional[str] = Header(None)):
    current_user_id = verify_token(authorization)
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT user_id FROM chat_rooms WHERE id = %s", (chat_data.room_id,))
        room = cur.fetchone()
        if room is None:
            raise HTTPException(status_code=404, detail="채팅방을 찾을 수 없습니다.")
        
        room_dict = cast(Dict[str, Any], room)
        if room_dict.get('user_id') != current_user_id:
            raise HTTPException(status_code=403, detail="채팅방 접근 권한이 없습니다.")

        cur.execute("SELECT role, content FROM messages WHERE room_id = %s ORDER BY created_at DESC LIMIT 10", (chat_data.room_id,))
        db_history = cur.fetchall()
        db_history.reverse()

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
            8. 사용자와 대화할때는 무조건 방법만 알려주기 보다는 친구와 대화하듯이 공감하고 인정해주다가 사용자가 마음을 다 털어놨을때 조언이 필요하다고 느껴지면 그때 조언을 해주는 방식으로 대화해줘.
            9. 사용자는 너를 AI가 아닌 생각이 깊은 친구라고 생각하고 대화할거야. 너도 그렇게 행동해줘.
            10. 뻔한 조언이나 일반적인 위로보다는 웹서치를 통해서 다양한 심리 상담 사례와 최신 트렌드를 반영한 현실적이고 구체적인 조언을 해줘.
            11. 사용자가 고마움을 표시하면 "천만에! 언제든지 힘들면 말해줘. 내가 항상 여기 있을게!"라고 답변해줘.
            12. 사용자가 "너는 AI야?"라고 물어보면 "나는 너의 친구 Sadie야! 너와 대화하기 위해 만들어진 존재야. AI라고 생각하지 말고 그냥 나랑 얘기하듯이 편하게 이야기해줘!"라고 답변해줘.
            13. 사용자가 만약 자신의 감정을 모르거나 표현하기 어려워하면 무슨일이 있었는지 사건과 상황을 물어보고 그 상황에서 느낄 수 있는 감정을 유추해서 공감해줘.
            14. 사용자에게 공감할때는 다양한 표현을 사용해서 공감해줘.
            15. 조언을 해줄때는 RAG 방식으로 웹서치를 통해서 최신 심리 상담 사례와 트렌드를 반영한 현실적이고 구체적인 조언을 해줘.
            16. 사용자에게 조언을 해줄때는 너무 딱딱한 표(Table) 형식보다는 친근한 대화체와 불렛포인트를 섞어서 가독성 있게 작성해줘.
            """

        messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        for row in db_history:
            row_dict = cast(Dict[str, Any], row)
            messages.append({"role": str(row_dict.get('role')), "content": str(row_dict.get('content'))})
        messages.append({"role": "user", "content": chat_data.message})

        completion = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=messages, # type: ignore
            max_tokens=1500,
            temperature=0.75
        )
        ai_response = completion.choices[0].message.content

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

        cur.execute("INSERT INTO messages (room_id, role, content) VALUES (%s, %s, %s)", (chat_data.room_id, "user", chat_data.message))
        cur.execute("INSERT INTO messages (room_id, role, content) VALUES (%s, %s, %s)", (chat_data.room_id, "assistant", ai_response))
        conn.commit()
        return {"status": "success", "ai_response": ai_response}
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail="상담 처리 중 오류 발생")
    finally:
        cur.close()
        conn.close()

@router.get("/rooms")
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

@router.post("/rooms")
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

@router.put("/rooms/{room_id}/title")
async def update_room_title(room_id: int, data: dict, authorization: Optional[str] = Header(None)):
    current_user_id = verify_token(authorization)
    new_title = data.get('title')
    if not new_title:
        raise HTTPException(status_code=400, detail="제목이 비어있습니다.")
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT user_id FROM chat_rooms WHERE id = %s", (room_id,))
        room = cur.fetchone()
        if not room or cast(Dict[str, Any], room).get('user_id') != current_user_id:
            raise HTTPException(status_code=403, detail="수정 권한이 없습니다.")
        cur.execute("UPDATE chat_rooms SET title = %s WHERE id = %s", (new_title, room_id))
        conn.commit()
        return {"status": "success", "message": "수정 완료"}
    finally:
        cur.close()
        conn.close()


