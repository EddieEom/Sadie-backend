import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta

# 기존 라이브러리들
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# 라우터 및 분석기 import
from routes import auth, user, chat, analysis
from services.analysis_service import SadieAnalyzer

app = FastAPI()

# 1. Rate Limiter 설정 (기존 로직 유지)
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.exception_handler(RateLimitExceeded)(_rate_limit_exceeded_handler)

# 3. CORS 설정 (기존 유지)

ALLOWED_ORIGINS = [
    "http://localhost:8000",      # 로컬 API 서버 주소
    "http://127.0.0.1:8000",
    "https://sadie-api.onrender.com", # 👈 Render 실서버 주소 (프로토콜 중복 제거 & 포트 제거)
    # Flutter 웹 테스트를 하신다면 아래 주소도 추가하는 것이 좋습니다.
    "http://localhost:5000",      # 보통 Flutter 웹 실행 기본 포트
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# 2. 통합 스케줄러 로직 (배치 함수)
# ---------------------------------------------------------
def batch_generate_weekly_reports():
    print(f"🚀 [{datetime.now()}] Sadie 주간 리포트 자동 생성을 시작합니다...")
    analyzer = SadieAnalyzer()
    conn = None
    cur = None
    
    try:
        conn = analyzer.get_db_connection()
        cur = conn.cursor()
        
        # 모든 유저 ID 조회
        cur.execute("SELECT user_id FROM users")
        users = cur.fetchall()
        
        success_count = 0
        for user_row in users:
            # DB 커서 설정에 따라 접근 방식 대응 (딕셔너리 or 튜플)
            uid = str(user_row.get('user_id') if isinstance(user_row, dict) else user_row[0])
            
            # SadieAnalyzer의 리포트 생성 함수 호출
            if analyzer.create_weekly_report(uid):
                success_count += 1
        
        print(f"✅ [Scheduler] 완료! 총 {success_count}명의 리포트가 생성되었습니다.")
        
    except Exception as e:
        print(f"❌ [Scheduler] 오류 발생: {e}")
    finally:
        if cur: cur.close()
        if conn: conn.close()

# 스케줄러 인스턴스 (Background 타입이라 API 응답을 방해하지 않습니다)
scheduler = BackgroundScheduler()

@app.on_event("startup")
async def start_scheduler():
    # 매주 월요일 오전 09:00 실행
    scheduler.add_job(
        batch_generate_weekly_reports, 
        'cron', 
        day_of_week='mon', 
        hour=9, 
        minute=0,
        id="weekly_sadie_report"
    )
    # 2. [테스트용] 서버 시작 5초 뒤에 즉시 실행!
    # 이 줄만 추가하고 저장하면 uvicorn이 리로드되면서 바로 실행됩니다.
    # scheduler.add_job(
    #     batch_generate_weekly_reports, 
    #     'date', 
    #     run_date=datetime.now() + timedelta(seconds=5),
    #     id="test_report_job"
    # )

    scheduler.start()
    print("⏰ [System] Sadie 스케줄러 활성화 & 5초 뒤 테스트 실행 대기 중...")
    
@app.on_event("shutdown")
async def stop_scheduler():
    scheduler.shutdown()


# 4. 라우터 등록 (경로 겹침 방지)
# auth.py와 chat.py 내부에서 prefix를 조절했으므로 아래처럼 등록합니다.
app.include_router(user.router)
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(analysis.router)

@app.get("/")
def read_root():
    return {"message": "Sadie AI Server is Online!"}