import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from openai import OpenAI
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional, cast

load_dotenv()

class SadieAnalyzer:
    def __init__(self):
        self.db_url = os.getenv("DB_URL")
        self.client = OpenAI(
            base_url="https://router.huggingface.co/v1", 
            api_key=os.getenv("HF_TOKEN")
        )
        # 이사님이 선택하신 무료 20B 모델 유지
        self.model_name = "openai/gpt-oss-20b" 

    def get_db_connection(self):
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)

    def create_weekly_report(self, user_id: str):
        conn = self.get_db_connection()
        cur = conn.cursor()
        
        try:
            one_week_ago = datetime.now() - timedelta(days=7)

            # 1. 사용자 닉네임 가져오기
            cur.execute("SELECT nickname FROM users WHERE user_id::text = %s", (user_id,))
            
            # [수정 포인트] fetchone() 결과를 Dict[str, Any]로 캐스팅
            user_data = cast(Optional[Dict[str, Any]], cur.fetchone())
            
            # [수정 포인트] 튜플이 아닌 딕셔너리 접근 방식으로 안전하게 처리
            nickname = "여행자"
            if user_data and 'nickname' in user_data:
                nickname = user_data['nickname']
            elif user_data and user_data.get('nickname'): # .get() 사용 가능
                nickname = user_data['nickname']

            # 2. 기분 데이터 및 대화 데이터 쿼리
            # [수정] 기분 데이터 쿼리
            cur.execute("""
                SELECT mood_score, mood_tag, created_at FROM user_daily_moods 
                WHERE user_id::text = %s AND created_at >= %s ORDER BY created_at ASC
            """, (user_id, one_week_ago))
            moods: List[Dict[str, Any]] = cur.fetchall() # type: ignore

            # [핵심 수정] 메시지 테이블 스키마에 맞춰 JOIN 쿼리로 변경
            cur.execute("""
                SELECT m.content 
                FROM public.messages m
                JOIN public.chat_rooms r ON m.room_id = r.id
                WHERE r.user_id::text = %s AND m.created_at >= %s 
                ORDER BY m.created_at ASC 
                LIMIT 50
            """, (user_id, one_week_ago))
            chats: List[Dict[str, Any]] = cur.fetchall() # type: ignore

            if not moods and not chats:
                return {
                    "weekly_title": f"{nickname}님과 Sadie의 첫 만남",
                    "emotion_pattern": "아직 기록된 마음의 발자취가 없어요.",
                    "sadie_message": f"반가워요, {nickname}님! 저는 {nickname}님의 마음을 읽어주는 Sadie예요. "
                                    f"오늘의 기분을 기록하거나 저와 짧은 대화를 나눠주시면, "
                                    f"다음 주에는 {nickname}님만을 위한 특별한 마음 리포트를 작성해 드릴게요! ✨",
                    "status_score": 36.5
                }

            # 3. 분석을 위한 데이터 요약
            mood_summary = ", ".join([
                f"{str(m.get('created_at')).split(' ')[0]}({m.get('mood_score')}점)" 
                for m in moods
            ])
            chat_context = "\n".join([f"- {c.get('content')}" for c in chats])

            # 4. 리포트 생성 (닉네임 주입 프롬프트)
            prompt = f"""
            당신은 다정한 AI 상담사 'Sadie'입니다. {nickname}님의 일주일간 데이터를 기반으로 따뜻한 분석 리포트를 작성하세요.
            반드시 {nickname}님의 이름을 부르며 첫 인사를 다정하게 건네주세요.
            
            [기분 데이터]: {mood_summary}
            [상담 내용]: {chat_context}
            
            반드시 아래 JSON 형식으로만 답변하세요:
            {{
                "weekly_title": "{nickname}님을 위한 이번 주의 마음 요약",
                "emotion_pattern": "관찰된 감정의 흐름과 패턴",
                "sadie_message": "{nickname}님에게 전하는 Sadie의 다정한 조언과 응원",
                "status_score": 36.5    # 30.0 ~ 42.0 사이의 '마음 체온'으로 표현하세요. 
                                        # 스트레스가 높으면 고열(39도 이상), 우울감이 깊으면 저체온(35도 이하)으로 분석합니다.
            }}
            """

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": f"너는 {nickname}님의 마음을 가장 잘 이해하는 다정한 상담가 Sadie야."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500
            )

            res_content = response.choices[0].message.content

            # 1. 기본값 선언 (Fallback)
            analysis = {
                "weekly_title": f"{nickname}님의 마음 기록",
                "emotion_pattern": "마음을 정리하고 있어요.",
                "sadie_message": "잠시만 기다려 주세요, Sadie가 곧 다정한 분석을 들고 올게요!",
                "status_score": 36.5
            }

            # 2. 파싱 시도
            if res_content:
                try:
                    cleaned_content = res_content.replace("```json", "").replace("```", "").strip()
                    analysis = json.loads(cleaned_content)
                except json.JSONDecodeError:
                    print(f"JSON Parsing Failed: {res_content[:100]}...") # 로그 확인용
            
            # 5. 결과 저장
            cur.execute("""
                INSERT INTO user_reports (user_id, report_type, content)
                VALUES (%s, %s, %s)
            """, (user_id, 'weekly', json.dumps(analysis)))
            
            conn.commit()
            return analysis

        except Exception as e:
            if conn: conn.rollback()
            print(f"Analysis Error: {e}")
            return None
        finally:
            if cur: cur.close()
            if conn: conn.close()