# Sadie 백엔드

**LLM 학습 실험부터 Flutter 앱·서버 연동까지 진행한 개인 프로젝트**입니다. 모델을 직접 다뤄 보고, 대화 내용을 저장하고 조회하는 앱으로 연결하는 데 관심을 갖고 시작했습니다.

## 주요 경험

- AI Hub 데이터를 학습용 JSONL 형식으로 변환
- 학교 GPU 서버에서 LLaMA 3.1 학습 실험 진행
- FastAPI·PostgreSQL 기반 대화 서버 구성
- Flutter 앱과 연결해 대화 기능 동작 확인

## 모델 학습 실험

LLaMA 3.1을 처음 연결했을 때 한국어 응답이 기대에 미치지 못해, AI Hub 데이터로 추가 학습을 시도했습니다. A100 GPU 2개가 장착된 학교 서버에서 준비한 데이터의 약 5%를 사용했습니다.

소규모 학습 실험에서 뚜렷한 한국어 응답 개선은 확인하지 못했습니다. 데이터 전처리와 학습 실행 과정을 경험했으며, 학습 조건과 전후 응답을 체계적으로 비교하는 평가를 후속 과제로 남겼습니다.

## 앱과 서버 구성

| 영역 | 구성 내용 |
| --- | --- |
| 계정 | 회원가입·로그인·사용자 정보 관리 |
| 대화 | 채팅방 생성, 메시지 저장 및 기록 조회 |
| LLM | Hugging Face Router를 통한 외부 모델 호출 |
| 검색 | 임베딩과 pgvector를 활용한 RAG 구성 |
| 리포트 | 대화·감정 데이터를 활용하는 주간 리포트 기능 |
| 외부 서비스 | Supabase Storage, Render 연동 |

초기 파인튜닝 실험과 현재 외부 LLM API를 사용하는 앱 구성은 별도로 진행한 범위입니다.

## 확인한 내용과 보완 과제

개발 당시 앱과 서버를 연결해 대화 기능의 동작을 확인했습니다. 후속 과제는 학습 데이터·RAG 자료의 출처와 구성을 정리하고, 검색 결과 및 응답 품질을 비교 평가하는 것입니다.

## 사용 기술

Python, FastAPI, PostgreSQL, pgvector, Hugging Face, Flutter, Supabase, Render

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

실행하려면 DB 구조와 외부 서비스 설정을 함께 준비해야 합니다.

## 관련 저장소

[Sadie 프론트엔드](https://github.com/EddieEom/Sadie_frontend)
