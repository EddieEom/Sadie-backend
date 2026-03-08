from fastapi import APIRouter, Depends, HTTPException
from services.analysis_service import SadieAnalyzer
from routes.auth import get_current_user
from typing import cast # 타입을 강제하기 위해 추가

router = APIRouter(prefix="/analysis", tags=["Analysis"])
analyzer = SadieAnalyzer()

@router.post("/weekly")
async def generate_weekly_report(current_user: dict = Depends(get_current_user)):
    # 1. user_id를 가져온 뒤 확실히 존재하는지 체크
    user_id = current_user.get("id")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="사용자 ID를 찾을 수 없습니다.")
    
    # 2. Pylance에게 "이건 무조건 str이야"라고 알려줍니다 (cast 사용)
    report = analyzer.create_weekly_report(cast(str, user_id))
    
    if not report:
        raise HTTPException(status_code=500, detail="리포트 생성 중 오류가 발생했습니다.")
    return {"status": "success", "data": report}

@router.get("/history")
async def get_analysis_history(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("id")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="사용자 ID를 찾을 수 없습니다.")

    # 직접 쿼리로 히스토리 조회
    conn = analyzer.get_db_connection()
    cur = conn.cursor()
    # 여기도 안전하게 cast 처리
    cur.execute("SELECT * FROM user_reports WHERE user_id = %s ORDER BY created_at DESC", (cast(str, user_id),))
    history = cur.fetchall()
    cur.close()
    conn.close()
    return {"status": "success", "data": history}