# AI-Powered Workflow Management System

대화형 AI를 활용한 워크플로우 자동 생성 및 관리 시스템

## 💡 핵심 개념

이 시스템은 **"AI가 AI를 관리하는 Self-Healing 워크플로우 시스템"**입니다.

### 🔑 3가지 핵심 원칙

1. **Zero Manual Coding** 
   - 사용자는 자연어로만 업무 설명
   - AI가 완전한 Python 코드 자동 생성
   - 수동 코딩 불필요

2. **Self-Healing**
   ```
   AI 생성 → 자동 검증 → 오류 발견 → AI 재생성 → ✅
   ```
   - AI가 생성한 코드를 AI가 검증
   - 문제 발견 시 자동으로 수정
   - 문법 오류 사전 차단

3. **Production-Ready**
   - 모든 코드에 에러 처리 필수
   - 문법 검증 통과만 저장 가능
   - 격리된 실행 환경 (subprocess)

---

## 주요 기능

### 🤖 AI 워크플로우 생성 & 관리
- **AI 기반 생성**: 자연어로 업무를 설명하면 LLM이 완전한 Python 코드 워크플로우 자동 생성
- **대화형 구체화**: AI가 필요 정보를 질문하며 워크플로우 점진적 개선
- **자동 코드 검증**: AI 생성 코드 자동 검증, 오류 발견 시 스스로 수정 ✨
- **AI 수정**: 자연어로 기존 워크플로우 수정 가능

### 🧠 RAG 지식 베이스 (최신 개선)
- **도메인 기반 검색**: 자동 도메인 감지 (네이버, 기상청, 카카오 등)
- **Smart Search**: 원본 쿼리 한 번에 감지된 도메인 + common 도메인에서 최적 검색
- **하이브리드 검색**: 의미론적 검색 + 키워드 검색 통합
- **다양한 파일 지원**: PDF, Word, Excel, 이미지, 텍스트 파일 업로드 및 OCR 처리
- **자동 컨텍스트 제공**: 워크플로우 생성 시 자동으로 관련 지식 활용

### 🔄 워크플로우 실행 & 모니터링
- **LangGraph 기반 실행**: 각 스텝별 상태 관리 및 조건부 실행
- **7가지 스텝 타입**: LLM_CALL, API_CALL, PYTHON_SCRIPT, CONDITION, APPROVAL, NOTIFICATION, DATA_TRANSFORM
- **실시간 모니터링**: 워크플로우 실행 상태, 스텝별 로그, 통계 추적
- **고급 제어**: 재시도, 승인/거부, 실행 취소 기능

### ⏰ 자동 트리거 & 스케줄링
- **Cron 기반 스케줄**: 시간 기반 자동 실행 (매일, 매주, 매월 등)
- **이벤트 트리거**: 특정 이벤트 발생 시 자동 실행
- **웹훅**: 외부 시스템 연동
- **백그라운드 스케줄러**: 자동 감시 및 실행

### 📊 고급 기능
- **폴더 & 태그 관리**: 워크플로우 조직화 및 필터링
- **버전 관리**: 워크플로우 수정 이력 추적
- **실행 통계**: 성공률, 평균 실행 시간, 실패 원인 분석
- **LangSmith 추적**: 모든 LLM 호출 및 워크플로우 실행 추적

---

## 기술 스택

### 🎯 핵심 기술
| 계층 | 기술 | 버전/설명 |
|-----|------|----------|
| **Frontend** | Streamlit | 최신 |
| **Backend** | Python | 3.10+ |
| **LLM** | OpenAI GPT-4 | 고급 추론 능력 |
| **Workflow Engine** | LangGraph | 상태 기반 실행 엔진 |
| **Database** | SQLite + SQLAlchemy | 가벼운 로컬 DB |
| **Vector DB** | ChromaDB | 도메인별 컬렉션 분리 |
| **Embeddings** | OpenAI text-embedding-3-small | 384 차원 |
| **RAG** | LangChain | 최신 RAG 패턴 |

### 📦 주요 패키지
```
streamlit              # UI 프레임워크
langchain             # LLM 체인 및 RAG
langgraph             # 상태 기반 워크플로우
chroma                # 벡터 데이터베이스
sqlalchemy            # ORM
openai                # API 통합
```

---

## 빠른 시작

### 1️⃣ 설치

```bash
# 저장소 클론
git clone <repository-url>
cd projWorkFlow4

# 가상 환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 2️⃣ 환경 설정

```bash
# .env 파일 생성
cp .env.example .env
```

`.env` 파일에 필수 정보 입력:
```env
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4  # 또는 gpt-4o-mini
DATABASE_URL=sqlite:///workflows.db
```

### 3️⃣ 데이터베이스 초기화

```bash
# 테이블 및 초기 도메인 생성
python -m src.database.init_db
```

### 4️⃣ 애플리케이션 시작

```bash
streamlit run app.py
```

웹 브라우저에서 `http://localhost:8501` 접속

---

## 프로젝트 구조

```
projWorkFlow4/
├── src/                                    # 소스 코드
│   ├── agents/                             # AI 에이전트
│   │   ├── meta_agent.py                   # 워크플로우 생성 에이전트
│   │   ├── workflow_modifier.py            # 워크플로우 수정 에이전트
│   │   └── prompts.py                      # AI 프롬프트 템플릿
│   │
│   ├── database/                           # 데이터베이스 레이어
│   │   ├── models.py                       # SQLAlchemy 모델 (Workflow, Domain 등)
│   │   ├── session.py                      # DB 세션 관리
│   │   ├── base.py                         # SQLAlchemy 기본 설정
│   │   └── init_db.py                      # DB 초기화
│   │
│   ├── engines/                            # LangGraph 워크플로우 엔진
│   │   ├── workflow_engine.py              # 상태 기반 워크플로우 실행
│   │   ├── step_executor.py                # 스텝 타입별 실행 로직
│   │   └── workflow_state.py               # 상태 정의
│   │
│   ├── runners/                            # 실행 관리
│   │   └── workflow_runner.py              # 라이프사이클 관리
│   │
│   ├── services/                           # 비즈니스 로직
│   │   ├── workflow_service.py             # 워크플로우 CRUD
│   │   ├── execution_service.py            # 실행 기록 관리
│   │   ├── folder_service.py               # 폴더 관리
│   │   ├── rag_service.py                  # RAG 시스템 (도메인 기반 검색) ⭐
│   │   ├── domain_service.py               # 도메인 관리
│   │   ├── file_parser.py                  # 파일 파싱
│   │   └── file_service.py                 # 파일 업로드 관리
│   │
│   ├── triggers/                           # 자동 트리거
│   │   ├── trigger_manager.py              # 트리거 CRUD
│   │   └── scheduler.py                    # 백그라운드 스케줄러
│   │
│   └── utils/                              # 유틸리티
│       ├── config.py                       # 환경 설정
│       ├── logger.py                       # 로깅
│       ├── code_validator.py               # Python 코드 검증
│       └── domain_detector.py              # 도메인 감지
│
├── pages/                                  # Streamlit 페이지
│   ├── 1_Create_Workflow.py                # 워크플로우 생성
│   ├── 2_Manage_Workflows.py               # 워크플로우 관리
│   ├── 3_Executions.py                     # 실행 기록
│   ├── 4_Triggers.py                       # 트리거 관리
│   └── 5_Knowledge_Base.py                 # RAG 지식 베이스 관리 (도메인 기반) ⭐
│
├── app.py                                  # Streamlit 메인 대시보드
├── requirements.txt                        # Python 의존성
├── .env                                    # 환경 변수
├── workflows.db                            # SQLite 데이터베이스
├── data/chroma_db/                         # ChromaDB 벡터 저장소
├── logs/                                   # 로그 파일
│
├── README.md                               # 이 파일
├── USAGE_GUIDE.md                          # 사용 가이드
├── ADVANCED_TECH_STACK.md                  # 기술 스택 상세
├── COMPREHENSIVE_PROJECT_ANALYSIS.md       # 프로젝트 분석
└── LANGGRAPH_WORKFLOW.md                   # LangGraph 동작 원리
```

---

## 🔄 핵심 워크플로우

### 워크플로우 생성 흐름

```
자연어 입력
  ↓
MetaWorkflowAgent (AI)
  ├─ RAG Smart Search (도메인 감지 포함) ⭐
  ├─ LLM 호출 (GPT-4)
  └─ 워크플로우 JSON 생성
      ↓
CodeValidator
  ├─ Python 문법 검증 (AST)
  ├─ f-string 따옴표 검증
  └─ ✅ 통과 시 저장
      ↓
WorkflowService
  ├─ DB에 저장
  └─ Python 스크립트 생성 (참고용)
```

### 워크플로우 실행 흐름

```
WorkflowRunner
  ↓
WorkflowEngine (LangGraph)
  ├─ StateGraph 생성
  └─ 각 스텝 순서대로 실행
      ↓
각 스텝 타입별 실행
  ├─ LLM_CALL → OpenAI API
  ├─ API_CALL → HTTP 요청
  ├─ PYTHON_SCRIPT → subprocess 격리 실행
  ├─ CONDITION → 조건 평가
  ├─ APPROVAL → 사용자 승인 대기
  └─ NOTIFICATION → 알림 전송
      ↓
결과 DB 저장
```

---

## 🧠 RAG 시스템 (최신 아키텍처)

### 도메인 기반 검색 아키텍처

```
사용자 쿼리
  ↓
DomainService.find_domain_by_keywords()
  ├─ 도메인 자동 감지 (네이버, 기상청, 카카오 등) ⭐
  └─ detected_domain = "naver"
      ↓
RAGService.search_metadata()
  ├─ collection_naver (감지 도메인) 검색
  ├─ collection_common (공통) 검색
  └─ 결과 병합 & 정렬
      ↓
결과 표시 (도메인별 탭)
```

### 컬렉션 구조

| 컬렉션 | 용도 | 문서 예시 |
|--------|------|----------|
| `collection_common` | 모든 쿼리 포함 | Python 기초, REST API 개념 |
| `collection_naver` | 네이버 관련 | 네이버 API, 뉴스 크롤링 |
| `collection_weather` | 기상청 관련 | 기상청 API, 날씨 데이터 |
| `collection_kakao` | 카카오 관련 | 카카오 맵, 인증 |
| `collection_google` | Google 관련 | Gmail, Drive API |

### 주요 개선사항 (최근)

✅ **도메인 자동 감지**: 쿼리에서 도메인 자동 추출
✅ **Smart Search**: 1회 쿼리로 관련 도메인 + common 검색
✅ **확장성**: 새 도메인 동적 추가 가능
✅ **정확도**: 도메인별 임베딩 공간 분리로 관련도 향상

---

## 📊 주요 기능 현황

### ✅ 완성된 기능
- ✅ AI 기반 워크플로우 생성 및 자동 코드 검증
- ✅ LangGraph 기반 상태 관리 실행 엔진
- ✅ 7가지 스텝 타입 지원 (LLM, API, Python 등)
- ✅ 자동 트리거 및 Cron 스케줄링
- ✅ 도메인 기반 RAG 시스템 (최신)
- ✅ 실행 이력 및 통계 추적
- ✅ AI 기반 워크플로우 수정

### 🚀 향후 계획
- 🔲 더 많은 도메인 추가 (Slack, GitHub 등)
- 🔲 웹훅 기반 트리거
- 🔲 실시간 콜라보레이션
- 🔲 워크플로우 마켓플레이스

---

## 🎯 사용 예시

### 예시 1: 이메일 자동화

```
자연어 입력: "매일 아침 9시에 Gmail에서 중요 이메일을 확인하고 
           내용을 슬랙 채널에 전송해줘"

자동 흐름:
1. AI가 "Gmail API", "Slack API" 관련 문서 자동 검색
2. Python 코드 자동 생성 (Gmail 연결, 이메일 파싱, Slack 전송)
3. 코드 검증 통과 후 저장
4. 매일 9시 자동 실행
```

### 예시 2: 뉴스 요약 및 배포

```
자연어 입력: "네이버 뉴스에서 경제분야 최신뉴스 3개를 뽑아서
           제목, 요약, 링크로 정리해서 메일 보내줘"

자동 흐름:
1. "네이버" 도메인 자동 감지 ⭐
2. collection_naver + collection_common에서 검색
3. 필요한 API 문서 자동 수집
4. 완전한 워크플로우 코드 생성
5. 매일/주간 자동 실행
```

---

## 🛠️ 개발 & 디버깅

### 로그 확인

```bash
# 최근 로그 확인
tail -f logs/meta_agent_*.log
tail -f logs/workflow_engine_*.log

# 특정 문자 검색
grep "ERROR" logs/*.log
```

### 데이터베이스 검사

```bash
# SQLite CLI로 확인
sqlite3 workflows.db

# 워크플로우 조회
SELECT id, name, status FROM workflows;

# 도메인 조회
SELECT id, name FROM domains;
```

### RAG 시스템 디버깅

```bash
# RAG 시스템 테스트 (과거)
# 현재는 Knowledge Base 페이지에서 직접 테스트 가능
```

---

## 📝 라이선스

MIT License

---

## 📚 추가 문서

- **[사용 가이드](USAGE_GUIDE.md)**: 기본 사용법 및 워크플로우 예시
- **[기술 스택 상세](ADVANCED_TECH_STACK.md)**: 각 기술의 역할 및 이유
- **[프로젝트 분석](COMPREHENSIVE_PROJECT_ANALYSIS.md)**: 전체 아키텍처 및 데이터 흐름
- **[LangGraph 동작](LANGGRAPH_WORKFLOW.md)**: 워크플로우 엔진 상세 설명

---

## 🤝 기여 방법

1. 이슈 제출 또는 기능 요청
2. 포크 및 브랜치 생성
3. 변경사항 커밋 및 푸시
4. 풀 리퀘스트 생성

---

**지난 일정 업데이트**

✅ 2025-11-02: 
- 프로젝트 정리 (65개 불필요 파일 삭제)
- RAG 시스템 도메인 기반 검색 개선
- Smart Search 구현 (부분쿼리 제거)
- README.md 최신화

