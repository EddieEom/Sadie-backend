# Sadie · 백엔드와 LLM 학습 실험

LLM 파인튜닝이 궁금해서 **A100 GPU 2개가 장착된 학교 서버**에서 학습을 시도했습니다. AI Hub 데이터를 학습용 형식으로 정리하고 LLaMA 3.1의 추가 학습을 실행하는 과정을 경험했습니다.

## 실험하며 알게 된 것

학습을 실행하는 것과 응답이 좋아졌는지를 확인하는 것은 다른 문제였습니다. 소규모 실험에서 뚜렷한 한국어 응답 개선은 확인하지 못했고, 학습 조건과 전후 응답을 비교할 평가가 필요했습니다.

A100 2개는 서버의 장비 구성이며, 두 GPU를 이용한 분산 학습 성능을 검증했다는 뜻은 아닙니다.

## 이 저장소의 범위

현재 저장소에는 대화 앱에 연결한 FastAPI 백엔드가 있습니다. 파인튜닝 실험의 학습 스크립트·체크포인트·평가 로그는 포함되어 있지 않습니다. 현재 앱은 외부 LLM API를 사용하며 학습한 모델을 배포한 구성과는 구분합니다.

<details>
<summary><b>🔬 모델 학습 과정과 결과</b></summary>

## 모델 학습 실험

LLaMA 3.1을 처음 연결했을 때 한국어 응답이 기대에 미치지 못해, AI Hub 데이터로 추가 학습을 시도했습니다. A100 GPU 2개가 장착된 학교 서버에서 준비한 데이터의 약 5%를 사용했습니다.

소규모 학습 실험에서 뚜렷한 한국어 응답 개선은 확인하지 못했습니다. 데이터 전처리와 학습 실행 과정을 경험했으며, 학습 조건과 전후 응답을 체계적으로 비교하는 평가를 후속 과제로 남겼습니다.

</details>

<details>
<summary><b>📝 동작 확인 · 후속 과제</b></summary>

## 확인한 내용과 보완 과제

개발 당시 앱과 서버를 연결해 대화 기능의 동작을 확인했습니다. 후속 과제는 학습 데이터·RAG 자료의 출처와 구성을 정리하고, 검색 결과 및 응답 품질을 비교 평가하는 것입니다.

</details>

<details>
<summary><b>⚙️ 사용 기술 · 환경변수 · 실행</b></summary>

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

</details>


[📱 Flutter 앱 저장소 →](https://github.com/EddieEom/Sadie_frontend)
