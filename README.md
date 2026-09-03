# 🌸 Sadie Backend

<div align="center">

### AI Conversational Assistant Backend

**사용자의 대화와 감정 데이터를 저장·분석하고,
RAG 기반 AI 대화와 주간 감정 리포트를 제공하는 Backend Server입니다.**

<br>

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge\&logo=python\&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge\&logo=fastapi\&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge\&logo=postgresql\&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-3FCF8E?style=for-the-badge\&logo=supabase\&logoColor=white)
![HuggingFace](https://img.shields.io/badge/Hugging%20Face-FFD21E?style=for-the-badge\&logo=huggingface\&logoColor=black)
![Render](https://img.shields.io/badge/Render-000000?style=for-the-badge\&logo=render\&logoColor=white)

</div>

<br>

---

# 📌 Project Overview

**Sadie**는 사용자가 자신의 고민과 감정을 자유롭게 기록하고
AI와 지속적으로 대화를 나눌 수 있도록 개발한 Conversational Assistant입니다.

이 저장소는 Sadie 서비스의 **Backend Server**이며,

* 사용자 인증
* Google OAuth
* 상담방 및 대화 관리
* AI Conversation
* Embedding 생성
* pgvector 기반 RAG
* 사용자 감정 데이터 관리
* 주간 AI Report 생성
* Profile Image Storage
* 자동 Batch Scheduling

등의 기능을 담당합니다.

Mobile Client는 Flutter로 구현되어 있습니다.

👉 [Sadie Frontend](https://github.com/EddieEom/Sadie_frontend)

<br>

---

# 🏗️ System Architecture

```text
┌──────────────────────────────┐
│        Flutter Client        │
└──────────────┬───────────────┘
               │
               │ REST API / JWT
               ▼
┌──────────────────────────────┐
│       FastAPI Backend        │
│                              │
│  Auth / User / Chat / AI     │
└──────┬───────────┬───────────┘
       │           │
       │           │
       ▼           ▼
┌────────────┐  ┌──────────────────────┐
│ PostgreSQL │  │ Hugging Face Router  │
│            │  │                      │
│ Users      │  │ GPT-OSS 20B          │
│ Messages   │  └──────────────────────┘
│ Reports    │
│ Vectors    │
└──────┬─────┘
       │
       │ pgvector
       ▼
┌──────────────────────────────┐
│    Counseling Knowledge      │
│       Vector Search          │
└──────────────────────────────┘
```

<br>

---

# 🔄 AI Conversation Flow

Sadie의 AI 대화는 단순 LLM API 호출이 아니라
기존 대화와 Vector Search 결과를 함께 활용하도록 구성했습니다.

```text
User Message
     │
     ▼
JWT Authentication
     │
     ▼
Room Ownership Check
     │
     ▼
Recent Conversation History
     │
     ▼
Hugging Face Embedding API
     │
     ▼
Korean Sentence Embedding
     │
     ▼
pgvector Similarity Search
     │
     ▼
Relevant Counseling Knowledge
     │
     ▼
System Prompt + Knowledge + History
     │
     ▼
GPT-OSS 20B
     │
     ▼
AI Response
     │
     ▼
PostgreSQL Message Storage
     │
     ▼
Flutter Client
```

<br>

---

# 🤖 RAG Pipeline

## 1. User Query Embedding

사용자 메시지를 Hugging Face Inference API로 전달하여
Embedding Vector를 생성합니다.

사용 모델:

```text
jhgan/ko-sroberta-multitask
```

한국어 문장 의미를 Vector 형태로 변환하여
상담 지식 검색에 사용합니다.

<br>

## 2. Vector Similarity Search

PostgreSQL의 `pgvector`를 이용하여
사용자 질문과 의미적으로 가까운 상담 데이터를 검색합니다.

```sql
SELECT content
FROM counseling_knowledge
ORDER BY embedding <=> query_vector
LIMIT 2;
```

검색된 상담 지식은 LLM Context에 추가됩니다.

<br>

## 3. Context Construction

```text
Sadie Persona
      +
Retrieved Knowledge
      +
Recent Conversation History
      +
Current User Message
```

를 하나의 Context로 구성합니다.

최근 대화 기록도 함께 전달하여
단일 질문에 응답하는 것이 아니라 **이전 대화의 맥락을 유지하도록 구성**했습니다.

<br>

## 4. Response Generation

Hugging Face Router를 통해

```text
openai/gpt-oss-20b
```

모델을 호출하여 최종 AI 응답을 생성합니다.

생성된 사용자 메시지와 AI 응답은 PostgreSQL에 저장됩니다.

<br>

---

# 💬 Conversation Management

사용자별로 여러 개의 상담방을 생성하고 관리할 수 있습니다.

### Features

* 상담방 생성
* 상담방 목록 조회
* 상담방 이름 변경
* 상담방 삭제
* Conversation History 조회
* 사용자별 Room 접근 권한 확인
* 사용자 / Assistant Message 저장
* 최근 대화 Context 구성

첫 메시지가 입력된 상담방은
LLM이 대화 내용을 요약하여 자동으로 상담방 제목을 생성합니다.

```text
First User Message
       ↓
GPT-OSS 20B
       ↓
Short Conversation Title
       ↓
Chat Room Update
```

<br>

---

# 🌡️ Weekly AI Analysis

Sadie는 사용자의 단일 대화뿐 아니라
**일정 기간 누적된 데이터를 분석하는 기능**도 구현했습니다.

최근 7일 동안의

```text
Daily Mood Data
      +
Conversation History
```

를 AI가 분석하여 Weekly Report를 생성합니다.

### Report Structure

```json
{
  "weekly_title": "이번 주 마음 요약",
  "emotion_pattern": "관찰된 감정의 흐름과 패턴",
  "sadie_message": "사용자를 위한 Sadie의 메시지",
  "status_score": 36.5
}
```

`status_score`는 사용자의 감정 상태를
**Mind Temperature** 형태로 표현하기 위해 사용합니다.

생성된 결과는 `user_reports`에 저장되어
이후 Flutter Client에서 조회할 수 있습니다.

<br>

---

# ⏰ Automatic Report Scheduler

주간 분석은 `APScheduler`를 이용해 자동화했습니다.

```text
Every Monday 09:00
        │
        ▼
Load All Users
        │
        ▼
Collect Last 7 Days Data
        │
        ▼
Generate AI Report
        │
        ▼
Save to PostgreSQL
```

FastAPI 서버가 실행될 때 Background Scheduler가 시작되고,
매주 월요일 오전 09시에 사용자별 Weekly Report를 생성합니다.

API 요청과 별도의 Background Scheduler로 동작하도록 구성했습니다.

<br>

---

# 🔐 Authentication

Sadie는 일반 회원 인증과 Google Social Login을 지원합니다.

## Email Authentication

```text
Sign Up
   ↓
bcrypt Password Hashing
   ↓
PostgreSQL
   ↓
Login
   ↓
JWT Access Token
```

### Features

* 회원가입
* 로그인
* bcrypt Password Hashing
* JWT Access Token 발급
* Bearer Token 인증
* 비밀번호 변경
* 회원 탈퇴

<br>

## Google OAuth

Flutter Client에서 Google ID Token을 전달받아
Backend에서 Google 서버를 통해 Token을 검증합니다.

```text
Flutter
   ↓
Google Sign-In
   ↓
Google ID Token
   ↓
FastAPI
   ↓
Google Token Verification
   ↓
Find / Create User
   ↓
Sadie JWT
```

Google 계정이 처음 로그인한 경우 자동으로 사용자 계정을 생성하고
Sadie 서비스에서 사용할 JWT Access Token을 반환합니다.

<br>

---

# 📧 Password Recovery

비밀번호를 분실한 사용자를 위해
Email Verification 기반 Password Reset 기능을 구현했습니다.

### Flow

```text
User ID + Email
      ↓
Account Verification
      ↓
6-Digit Verification Code
      ↓
Brevo Email API
      ↓
5 Minute Expiration
      ↓
Verification
      ↓
bcrypt New Password
      ↓
Database Update
```

메일 발송에는 **Brevo Transactional Email API**를 사용합니다.

<br>

---

# 👤 User / Profile Management

사용자 Profile 관련 기능도 Backend에서 관리합니다.

### Features

* 사용자 정보 조회
* Nickname 설정 및 변경
* Profile Image 업로드
* Google Profile Image 사용
* Social Account 여부 관리
* Mind Temperature 조회
* 회원 탈퇴

Profile Image는 **Supabase Storage**를 이용해 저장합니다.

<br>

---

# 🗄️ Database

Sadie는 PostgreSQL을 Main Database로 사용합니다.

### 주요 Data 영역

```text
users
│
├── User Account
├── Authentication
├── Profile
└── Social Login

chat_rooms
│
└── User Conversation Session

messages
│
├── User Message
└── Assistant Message

counseling_knowledge
│
├── Counseling Knowledge
└── Vector Embedding

user_daily_moods
│
└── Daily Mood Data

user_reports
│
└── Weekly AI Analysis

user_psych_profiles
│
└── User Analysis Data
```

<br>

---

# 🧰 Tech Stack

## Backend

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge\&logo=python\&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge\&logo=fastapi\&logoColor=white)

`REST API` `Pydantic` `Uvicorn`

<br>

## Database

![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge\&logo=postgresql\&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-3FCF8E?style=for-the-badge\&logo=supabase\&logoColor=white)

`psycopg2` `pgvector` `Vector Search`

<br>

## AI / RAG

![HuggingFace](https://img.shields.io/badge/Hugging%20Face-FFD21E?style=for-the-badge\&logo=huggingface\&logoColor=black)

`GPT-OSS 20B`
`ko-sRoBERTa`
`Embedding`
`RAG`
`Vector Similarity Search`

<br>

## Authentication

![Google](https://img.shields.io/badge/Google%20OAuth-4285F4?style=for-the-badge\&logo=google\&logoColor=white)

`JWT` `bcrypt` `Bearer Authentication`

<br>

## External Services

![Supabase](https://img.shields.io/badge/Supabase%20Storage-3FCF8E?style=for-the-badge\&logo=supabase\&logoColor=white)
![Render](https://img.shields.io/badge/Render-000000?style=for-the-badge\&logo=render\&logoColor=white)

`Brevo Email API`
`Hugging Face Inference API`

<br>

## Background Processing

`APScheduler` `Cron Scheduling`

<br>

---

# 🛡️ API Security

### JWT

보호된 API는 다음 Header를 통해 사용자 인증을 수행합니다.

```http
Authorization: Bearer <ACCESS_TOKEN>
```

JWT Payload의 `sub`에 사용자 ID를 저장하고
요청마다 Token을 검증하여 사용자 데이터를 분리합니다.

### Password

사용자 비밀번호는 평문으로 저장하지 않고
`bcrypt`를 이용해 Hashing 후 PostgreSQL에 저장합니다.

### Rate Limiting

`slowapi`를 이용한 Rate Limiter 설정을 서버에 구성했습니다.

<br>

---

# 📡 API

## Authentication

| Method   | Endpoint              | Description       |
| -------- | --------------------- | ----------------- |
| `POST`   | `/signup`             | 회원가입              |
| `POST`   | `/login`              | 로그인 및 JWT 발급      |
| `POST`   | `/auth/google`        | Google 로그인        |
| `POST`   | `/change-password`    | 비밀번호 변경           |
| `POST`   | `/request-reset-code` | 비밀번호 재설정 인증번호 요청  |
| `POST`   | `/verify-and-reset`   | 인증번호 검증 및 비밀번호 변경 |
| `DELETE` | `/delete-account`     | 회원 탈퇴             |

<br>

## User

| Method | Endpoint               | Description        |
| ------ | ---------------------- | ------------------ |
| `GET`  | `/users/me`            | 현재 사용자 정보          |
| `POST` | `/users/me/profile`    | Profile 수정         |
| `PUT`  | `/users/me/nickname`   | Nickname 변경        |
| `GET`  | `/users/me/mood-chart` | 사용자 감정 / 마음 온도 데이터 |

<br>

## Chat Room

| Method   | Endpoint                    | Description |
| -------- | --------------------------- | ----------- |
| `GET`    | `/rooms`                    | 상담방 목록 조회   |
| `POST`   | `/rooms`                    | 상담방 생성      |
| `PUT`    | `/rooms/{room_id}/title`    | 상담방 이름 변경   |
| `DELETE` | `/rooms/{room_id}`          | 상담방 삭제      |
| `GET`    | `/rooms/{room_id}/messages` | 대화 기록 조회    |

<br>

## AI Chat

| Method | Endpoint | Description  |
| ------ | -------- | ------------ |
| `POST` | `/chat`  | RAG 기반 AI 대화 |

<br>

## Analysis

| Method | Endpoint            | Description            |
| ------ | ------------------- | ---------------------- |
| `POST` | `/analysis/weekly`  | Weekly AI Report 수동 생성 |
| `GET`  | `/analysis/history` | AI Report History 조회   |

<br>

---

# 📂 Project Structure

```text
Sadie-backend/
│
├── main.py
├── schemas.py
├── google_auth_service.py
├── requirements.txt
│
├── core/
│   ├── config.py
│   ├── database.py
│   └── security.py
│
├── routes/
│   ├── auth.py
│   ├── user.py
│   ├── chat.py
│   └── analysis.py
│
└── services/
    └── analysis_service.py
```

### Responsibility

```text
main.py
 └─ Application / Middleware / Scheduler

core/
 ├─ Environment Configuration
 ├─ Database Connection
 └─ JWT Security

routes/
 ├─ Authentication API
 ├─ User API
 ├─ Conversation API
 └─ Analysis API

services/
 └─ Weekly AI Analysis

google_auth_service.py
 └─ Google OAuth Token Verification
```

<br>

---

# 🔐 Environment Variables

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

<br>

---

# 🚀 Getting Started

## 1. Clone Repository

```bash
git clone https://github.com/EddieEom/Sadie-backend.git
cd Sadie-backend
```

## 2. Create Virtual Environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## 4. Environment Configuration

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

## 5. Run Server

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

<br>

---

# ☁️ Deployment

Backend Server는 **Render**를 이용하여 배포했습니다.

```text
Flutter Client
      │
      │ HTTPS
      ▼
Render
      │
      ▼
FastAPI
      │
      ├── PostgreSQL
      ├── Supabase Storage
      ├── Hugging Face
      └── Brevo
```

서비스의 API Server와 Database / Storage / AI Service를 분리하여
외부 서비스들과 REST API 기반으로 통신하도록 구성했습니다.

<br>

---

# 🎯 What I Learned

Sadie Backend를 개발하면서 단순한 CRUD API를 넘어
**사용자 데이터가 AI 처리 과정까지 어떻게 연결되는지**를 구현하는 경험을 했습니다.

특히 다음 내용을 직접 다뤘습니다.

* FastAPI 기반 REST API 설계
* PostgreSQL 데이터 관리
* JWT Authentication
* bcrypt Password Hashing
* Google OAuth 연동
* Flutter ↔ FastAPI API Integration
* Conversation Session 및 History 관리
* LLM API Integration
* Korean Sentence Embedding
* pgvector 기반 Vector Similarity Search
* RAG Pipeline 구성
* 사용자 대화 데이터 기반 AI Analysis
* APScheduler 기반 정기 Batch Processing
* Supabase Storage 연동
* Brevo Email API 연동
* Render Backend Deployment

전체적으로

```text
User
 ↓
Flutter
 ↓
REST API
 ↓
Authentication
 ↓
Business Data
 ↓
Database
 ↓
Embedding / Vector Search
 ↓
LLM
 ↓
Analysis
 ↓
Database
 ↓
Flutter
```

로 이어지는 **서비스의 전체 Backend Data Flow**를 구현하는 데 초점을 두었습니다.

<br>

---

# 🔗 Related Repository

### 📱 Sadie Frontend

https://github.com/EddieEom/Sadie_frontend

<br>

---

# 👨‍💻 Developer

**엄인섭**

GitHub
https://github.com/EddieEom
