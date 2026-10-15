# Sadie 백엔드

LLM 학습과 AI 대화 앱 연동을 실험한 개인 프로젝트의 서버입니다.

## 시작한 이유와 학습 실험

LLM 파인튜닝에 관심이 생겨 혼자 시작한 프로젝트입니다.

1. 처음에는 LLaMA 3.1을 연결해 대화를 시도했습니다.
2. 한국어 응답이 기대에 미치지 못해 AI Hub 데이터를 가져왔습니다.
3. 데이터를 JSONL 형식으로 변환하고, 준비한 데이터의 약 5%를 사용해 학습을 시도했습니다.
4. 학교의 A100 GPU 2개가 장착된 서버에서 실험했습니다.

실험 이후에도 한국어 응답이 나아졌다고 느끼지 못했습니다. 학습 전후를 비교한 정량 평가나 학습 조건별 결과는 정리하지 못했습니다.

이 학습 실험과 현재 앱에서 외부 LLM API를 호출하는 구성은 구분해야 합니다. 현재 앱이 당시 학습한 모델로 실행된다는 의미는 아닙니다.

## 앱과 서버 구성

기존 저장소는 FastAPI와 PostgreSQL을 사용하고, Flutter 앱에서 서버 API를 호출하는 구성입니다.

- 회원가입·로그인과 사용자 정보 관리
- 채팅방 생성과 대화 기록 저장
- Hugging Face Router를 통한 외부 LLM 호출
- 임베딩과 pgvector 검색을 이용한 RAG 구성
- 대화·감정 데이터를 다루는 주간 리포트 기능
- Supabase Storage 및 Render 연동

위 내용은 기존 프로젝트에 작성된 기능 구성입니다. 앱 동작을 확인한 경험은 있지만, 현재 모든 기능을 다시 실행해 확인한 상태는 아닙니다.

## 결과와 확인하지 못한 부분

- 앱을 통해 대화 기능이 동작하는 것은 확인했습니다.
- LLaMA 학습 실험에서 기대한 한국어 응답 개선은 확인하지 못했습니다.
- RAG에 사용한 자료의 출처와 구성은 현재 정리하지 못했습니다.
- 검색 결과가 답변 품질을 얼마나 바꿨는지 비교한 기록은 없습니다.

이 프로젝트에서는 데이터 변환, 모델 학습 시도, 앱과 서버 연결을 경험했습니다. 학습 효과와 검색 품질을 평가하는 작업은 남아 있습니다.

## 사용 기술

Python, FastAPI, PostgreSQL, pgvector, Hugging Face, Flutter, Supabase, Render

초기 학습 실험에서는 LLaMA 3.1과 학교 GPU 서버를 사용했습니다.

## 환경변수

프로젝트 실행을 위해 `.env` 파일에 다음 환경변수가 필요합니다.

```env
DB_URL=
SECRET_KEY=
ALGORITHM=HS256

HF_TOKEN=

GOOGLE_CLIENT_ID=

SUPABASE_URL=
SUPABASE_KEY=

BREVO_API_KEY=
```

> 실제 API Key와 Secret 값은 Repository에 Commit하지 않습니다.



## 실행 방법

### 1. Clone Repository

```bash
git clone https://github.com/EddieEom/Sadie-backend.git
cd Sadie-backend
```

### 2. Create Virtual Environment

#### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

#### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

프로젝트 Root에 `.env` 파일을 생성합니다.

```env
DB_URL=YOUR_POSTGRESQL_CONNECTION_STRING
SECRET_KEY=YOUR_JWT_SECRET
ALGORITHM=HS256

HF_TOKEN=YOUR_HUGGINGFACE_TOKEN

GOOGLE_CLIENT_ID=YOUR_GOOGLE_CLIENT_ID

SUPABASE_URL=YOUR_SUPABASE_URL
SUPABASE_KEY=YOUR_SUPABASE_KEY

BREVO_API_KEY=YOUR_BREVO_API_KEY
```

### 5. Run Server

```bash
uvicorn main:app --reload
```

Server:

```text
http://127.0.0.1:8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

실행 안내는 기존 개발 환경 설정을 유지했습니다. DB 구조와 외부 서비스 설정도 함께 준비해야 합니다.

## 관련 저장소

[Sadie 프론트엔드](https://github.com/EddieEom/Sadie_frontend)
