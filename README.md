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

- 🤖 **AI 기반 워크플로우 생성**: 자연어로 업무를 설명하면 LLM이 자동으로 워크플로우 생성
- 💬 **대화형 구체화**: 필요한 정보를 AI가 질문하며 워크플로우를 점진적으로 개선
- ✨ **자동 코드 검증**: AI가 생성한 Python 코드를 자동으로 검증하고 문제 발견 시 스스로 수정
- 🧠 **RAG 기반 지식 활용**: 지식 베이스에서 관련 정보를 검색하여 더 정확한 워크플로우 생성
- 📁 **다양한 파일 형식 지원**: PDF, Word, Excel, 이미지, 텍스트 파일 업로드 및 OCR 처리
- 🔄 **LangGraph 기반 실행**: 각 스텝별 상태 관리 및 조건부 실행
- 🐍 **Python 하이브리드**: 복잡한 로직은 Python 스크립트로 구현 가능
- 🛡️ **견고한 에러 처리**: 실패 시 중단하고 재시도/수정 가능
- 📊 **실시간 모니터링**: 워크플로우 실행 상태 및 로그 추적
- ⏰ **자동 트리거**: 시간 기반 및 이벤트 기반 자동 실행
- 🔍 **LangSmith 추적**: 모든 LLM 호출 및 워크플로우 실행 추적

## 기술 스택

- **Frontend**: Streamlit
- **Backend**: Python 3.10+
- **LLM**: OpenAI GPT-4
- **Workflow Engine**: LangGraph
- **Database**: SQLite + SQLAlchemy
- **Vector Database**: ChromaDB
- **Embeddings**: OpenAI text-embedding-3-small
- **Tracing**: LangSmith

## 설치 방법

```bash
# 1. 저장소 클론
git clone <repository-url>
cd projWorkFlow4

# 2. 가상 환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 의존성 설치
pip install -r requirements.txt

# 4. 환경 변수 설정
cp .env.example .env
# .env 파일에 OpenAI API 키 등 설정

# 5. 데이터베이스 초기화 (RAG 지식 베이스 포함)
python -m src.database.init_db

# 6. RAG 시스템 테스트 (선택사항)
python test_rag_system.py

# 7. 애플리케이션 실행
streamlit run app.py
```

## 프로젝트 구조

```
projWorkFlow4/
├── src/                                    # 소스 코드 루트
│   ├── agents/                             # AI 에이전트 (워크플로우 생성/수정)
│   │   ├── __init__.py
│   │   ├── meta_agent.py                   # Meta Workflow Agent - 대화형 워크플로우 생성
│   │   │                                   #   - 자연어로 워크플로우 생성
│   │   │                                   #   - 필요 정보 질문 및 수집
│   │   │                                   #   - 자동 코드 검증 및 재생성
│   │   ├── workflow_modifier.py            # Workflow Modifier - AI 기반 수정
│   │   │                                   #   - 자연어로 워크플로우 수정
│   │   │                                   #   - 에러 로그 분석 및 자동 수정
│   │   │                                   #   - 개선 제안
│   │   └── prompts.py                      # AI 프롬프트 템플릿
│   │                                       #   - 워크플로우 생성 프롬프트
│   │                                       #   - 수정 프롬프트
│   │                                       #   - Python 코드 작성 규칙 (50줄+)
│   │
│   ├── database/                           # 데이터베이스 레이어
│   │   ├── __init__.py
│   │   ├── base.py                         # SQLAlchemy 기본 설정 (engine, Base)
│   │   ├── models.py                       # 데이터베이스 모델
│   │   │                                   #   - Folder (워크플로우 폴더)
│   │   │                                   #   - Workflow (워크플로우 정의)
│   │   │                                   #   - WorkflowStep (개별 스텝)
│   │   │                                   #   - WorkflowExecution (실행 기록)
│   │   │                                   #   - StepExecution (스텝 실행 기록)
│   │   │                                   #   - Trigger (트리거 설정)
│   │   │                                   #   - WorkflowVersion (버전 히스토리)
│   │   ├── session.py                      # 세션 관리
│   │   │                                   #   - get_session() - DB 세션 획득
│   │   │                                   #   - init_db() - 테이블 생성
│   │   │                                   #   - get_db_context() - Context manager
│   │   └── init_db.py                      # DB 초기화 스크립트
│   │
│   ├── engines/                            # LangGraph 워크플로우 엔진
│   │   ├── __init__.py
│   │   ├── workflow_engine.py              # WorkflowEngine - LangGraph 기반 실행 엔진
│   │   │                                   #   - create_graph() - StateGraph 생성
│   │   │                                   #   - run_workflow() - 워크플로우 실행
│   │   │                                   #   - 조건부 라우팅 (continue/stop/wait_approval)
│   │   │                                   #   - 변수 매핑 및 전파
│   │   ├── step_executor.py                # StepExecutor - 스텝 타입별 실행 로직
│   │   │                                   #   - LLM_CALL: OpenAI API 호출
│   │   │                                   #   - API_CALL: HTTP 요청
│   │   │                                   #   - PYTHON_SCRIPT: subprocess로 Python 실행
│   │   │                                   #   - CONDITION: 조건 평가
│   │   │                                   #   - APPROVAL: 승인 대기
│   │   │                                   #   - NOTIFICATION: 알림 전송
│   │   │                                   #   - DATA_TRANSFORM: 데이터 변환
│   │   └── workflow_state.py               # WorkflowState - LangGraph 상태 정의
│   │                                       #   - 스텝 상태 추적
│   │                                       #   - 변수 및 출력 저장
│   │                                       #   - 에러 추적
│   │
│   ├── runners/                            # 워크플로우 실행 관리
│   │   ├── __init__.py
│   │   └── workflow_runner.py              # WorkflowRunner - 실행 라이프사이클 관리
│   │                                       #   - execute_workflow() - 워크플로우 실행
│   │                                       #   - retry_execution() - 재시도
│   │                                       #   - approve_execution() - 승인/거부
│   │                                       #   - cancel_execution() - 실행 취소
│   │                                       #   - get_execution_logs() - 상세 로그
│   │
│   ├── services/                           # 비즈니스 로직 레이어
│   │   ├── __init__.py
│   │   ├── workflow_service.py             # WorkflowService - 워크플로우 CRUD
│   │   │                                   #   - create_workflow() - 워크플로우 생성
│   │   │                                   #   - update_workflow() - 수정 (버전 관리)
│   │   │                                   #   - delete_workflow() - 삭제 (cascade)
│   │   │                                   #   - list_workflows() - 조회 (필터링)
│   │   │                                   #   - Python 스크립트 파일 생성
│   │   │                                   #   - 자동 코드 검증
│   │   ├── execution_service.py            # ExecutionService - 실행 기록 관리
│   │   │                                   #   - list_executions() - 실행 기록 조회
│   │   │                                   #   - get_execution_stats() - 통계
│   │   │                                   #   - cleanup_old_executions() - 정리
│   │   └── folder_service.py               # FolderService - 폴더 관리
│   │                                       #   - create/update/delete/list folders
│   │   ├── rag_service.py                  # RAGService - 지식 베이스 관리
│   │   │                                   #   - create_knowledge_base() - KB 생성
│   │   │                                   #   - add_document() - 문서 추가
│   │   │                                   #   - hybrid_search() - 하이브리드 검색
│   │   │                                   #   - get_relevant_context() - 컨텍스트 제공
│   │   ├── file_parser.py                  # FileParser - 파일 파싱 서비스
│   │   │                                   #   - parse_pdf() - PDF 텍스트 추출
│   │   │                                   #   - parse_docx() - Word 문서 파싱
│   │   │                                   #   - parse_xlsx() - Excel 파일 파싱
│   │   │                                   #   - parse_image() - OCR 이미지 처리
│   │   │                                   #   - parse_text() - 텍스트 파일 처리
│   │   └── file_service.py                 # FileService - 파일 업로드 관리
│   │                                       #   - upload_file() - 파일 업로드 및 처리
│   │                                       #   - get_uploaded_files() - 업로드된 파일 목록
│   │                                       #   - delete_uploaded_file() - 파일 삭제
│   │                                       #   - search_files() - 파일 내용 검색
│   │
│   ├── triggers/                           # 자동 트리거 시스템
│   │   ├── __init__.py
│   │   ├── trigger_manager.py              # TriggerManager - 트리거 CRUD
│   │   │                                   #   - create/update/delete triggers
│   │   │                                   #   - get_due_triggers() - 실행 대상 조회
│   │   │                                   #   - fire_event_trigger() - 이벤트 트리거
│   │   │                                   #   - Cron 표현식 처리
│   │   └── scheduler.py                    # TriggerScheduler - 백그라운드 스케줄러
│   │                                       #   - start() - 스케줄러 시작
│   │                                       #   - 주기적으로 트리거 체크
│   │                                       #   - 자동 워크플로우 실행
│   │
│   └── utils/                              # 유틸리티 함수
│       ├── __init__.py
│       ├── config.py                       # Settings - 환경 변수 관리 (Pydantic)
│       ├── logger.py                       # get_logger() - 로깅 설정
│       └── code_validator.py               # CodeValidator - Python 코드 검증
│                                           #   - 문법 체크 (AST)
│                                           #   - f-string 따옴표 중첩 감지
│                                           #   - --variables-file 처리 확인
│                                           #   - 수정 제안
│
├── pages/                                  # Streamlit 페이지
│   ├── __init__.py
│   ├── 1_Create_Workflow.py                # 워크플로우 생성 페이지
│   │                                       #   - AI 대화형 생성
│   │                                       #   - 실시간 코드 검증
│   │                                       #   - 샘플 워크플로우
│   ├── 2_Manage_Workflows.py               # 워크플로우 관리 페이지
│   │                                       #   - CRUD 작업
│   │                                       #   - AI 수정
│   │                                       #   - 상태 관리
│   │                                       #   - 폴더 관리
│   ├── 3_Executions.py                     # 실행 기록 페이지
│   │                                       #   - 실행 목록
│   │                                       #   - 상세 로그
│   │                                       #   - 재시도/승인/취소
│   │                                       #   - 통계
│   ├── 4_Triggers.py                       # 트리거 관리 페이지
│   │                                       #   - 트리거 생성/수정/삭제
│   │                                       #   - 스케줄/이벤트/웹훅 설정
│   │                                       #   - 수동 실행
│   └── 5_Knowledge_Base.py                 # RAG 지식 베이스 관리 페이지
│                                           #   - 문서 업로드/검색/관리
│                                           #   - 지식 베이스 생성
│                                           #   - 검색 결과 분석
│
├── workflow_scripts/                       # 워크플로우별 Python 스크립트 (참고용)
│   └── {workflow_id}/                      # 워크플로우 ID별 디렉토리
│       ├── step_0_{step_name}.py           # 스텝 0 스크립트
│       ├── step_1_{step_name}.py           # 스텝 1 스크립트
│       └── ...                             # 주의: 실행은 DB의 code 사용!
│
├── logs/                                   # 로그 파일
│   ├── meta_agent_YYYYMMDD.log
│   ├── workflow_engine_YYYYMMDD.log
│   ├── step_executor_YYYYMMDD.log
│   └── ...
│
├── app.py                                  # Streamlit 메인 애플리케이션
│                                           #   - 대시보드
│                                           #   - 워크플로우 통계
│                                           #   - 최근 실행 기록
│                                           #   - 빠른 작업 버튼
│
├── init_app.py                             # 초기화 스크립트
│                                           #   - 데이터베이스 생성
│                                           #   - 샘플 폴더 생성
│
├── run_scheduler.py                        # 트리거 스케줄러 백그라운드 실행
│                                           #   - 60초마다 트리거 체크
│                                           #   - 스케줄된 워크플로우 자동 실행
│
├── requirements.txt                        # Python 의존성
├── .env                                    # 환경 변수 (API 키 등)
├── .gitignore                              # Git 제외 파일
├── README.md                               # 이 파일
├── USAGE_GUIDE.md                          # 사용 가이드
├── LANGGRAPH_WORKFLOW.md                   # LangGraph 동작 원리
├── AI_QUALITY_SYSTEM.md                    # AI 자동 품질 관리 시스템
├── PYTHON_EXECUTION_FLOW.md                # Python 코드 실행 메커니즘
├── RAG_SYSTEM_DESIGN.md                    # RAG 시스템 설계 문서
├── RAG_USAGE_GUIDE.md                      # RAG 시스템 사용 가이드
├── init_rag_data.py                        # RAG 샘플 데이터 초기화
├── test_rag_system.py                      # RAG 시스템 테스트
├── workflows.db                            # SQLite 데이터베이스
└── data/chroma_db/                         # ChromaDB 벡터 저장소
```

## 📂 주요 파일 역할 상세

### 🤖 AI 에이전트 (src/agents/)

| 파일 | 역할 | 핵심 기능 |
|------|------|----------|
| `meta_agent.py` | 워크플로우 생성 에이전트 | • 자연어 대화 처리<br>• 워크플로우 자동 생성<br>• 정보 부족 시 질문<br>• **자동 코드 검증** 및 재생성 |
| `workflow_modifier.py` | 워크플로우 수정 에이전트 | • 자연어로 수정 요청 처리<br>• 에러 로그 분석<br>• 자동 코드 수정<br>• **자동 재검증** (최대 1회) |
| `prompts.py` | AI 프롬프트 | • 워크플로우 생성 규칙 (50줄+)<br>• Python 코드 작성 템플릿<br>• 흔한 오류 경고<br>• 수정 가이드 |

### 💾 데이터베이스 (src/database/)

| 파일 | 역할 | 주요 모델 |
|------|------|----------|
| `models.py` | SQLAlchemy 모델 | • Folder (폴더 구조)<br>• Workflow (워크플로우 정의, JSON)<br>• WorkflowStep (스텝, 코드 저장)<br>• WorkflowExecution (실행 기록)<br>• StepExecution (스텝별 실행)<br>• Trigger (자동 실행 설정)<br>• WorkflowVersion (버전 관리) |
| `session.py` | DB 세션 관리 | • get_session() - 세션 생성<br>• init_db() - 테이블 생성<br>• 트랜잭션 관리 |
| `base.py` | SQLAlchemy 설정 | • Engine 생성<br>• SessionLocal 설정<br>• Base 선언 |

### ⚙️ 워크플로우 엔진 (src/engines/)

| 파일 | 역할 | 핵심 기능 |
|------|------|----------|
| `workflow_engine.py` | LangGraph 기반 실행 엔진 | • **StateGraph 생성** (스텝 → 노드)<br>• **조건부 라우팅** (continue/stop/approval)<br>• 변수 준비 및 매핑<br>• 에러 시 즉시 중단<br>• 상태 추적 및 로깅 |
| `step_executor.py` | 스텝 실행기 | • **7가지 스텝 타입** 실행<br>• PYTHON_SCRIPT: **subprocess로 격리 실행**<br>• LLM_CALL: OpenAI API<br>• API_CALL: HTTP 요청<br>• 임시 파일 관리<br>• stdout/stderr 캡처 |
| `workflow_state.py` | 상태 정의 | • WorkflowState TypedDict<br>• 스텝 상태 추적<br>• 변수 및 출력 저장<br>• 에러 목록 |

### 🏃 실행 관리 (src/runners/)

| 파일 | 역할 | 핵심 기능 |
|------|------|----------|
| `workflow_runner.py` | 실행 라이프사이클 관리 | • DB 레코드 생성<br>• WorkflowEngine 호출<br>• **실행 상태 DB 저장**<br>• 재시도/승인/취소<br>• 상세 로그 조회 |

### 🔧 서비스 레이어 (src/services/)

| 파일 | 역할 | 핵심 기능 |
|------|------|----------|
| `workflow_service.py` | 워크플로우 CRUD | • 워크플로우 생성/수정/삭제<br>• **자동 코드 검증** (저장 시)<br>• 버전 관리 (자동 증가)<br>• Python 스크립트 파일 생성<br>• 필터링 및 검색 |
| `execution_service.py` | 실행 기록 관리 | • 실행 목록 조회<br>• 통계 계산 (성공률, 평균 시간)<br>• 오래된 기록 정리 |
| `folder_service.py` | 폴더 관리 | • 폴더 CRUD<br>• 계층 구조 지원 |
| `rag_service.py` | RAG 시스템 관리 | • 지식 베이스 CRUD<br>• 문서 임베딩 및 저장<br>• 하이브리드 검색 (의미적 + 키워드)<br>• AI 에이전트 컨텍스트 제공 |
| `file_parser.py` | 파일 파싱 | • PDF/DOCX/XLSX/이미지/텍스트 파싱<br>• OCR 이미지 처리<br>• 메타데이터 추출<br>• 인코딩 자동 감지 |
| `file_service.py` | 파일 업로드 관리 | • 파일 업로드 및 처리<br>• 리포트 시스템 통합<br>• 파일 검색 기능<br>• 업로드 통계 관리 |

### ⏰ 트리거 시스템 (src/triggers/)

| 파일 | 역할 | 핵심 기능 |
|------|------|----------|
| `trigger_manager.py` | 트리거 관리 | • 트리거 CRUD<br>• Cron 표현식 파싱<br>• 다음 실행 시간 계산<br>• 이벤트 트리거 발동 |
| `scheduler.py` | 백그라운드 스케줄러 | • 60초마다 트리거 체크<br>• 실행 대상 자동 실행<br>• asyncio 기반 |

### 🛠️ 유틸리티 (src/utils/)

| 파일 | 역할 | 핵심 기능 |
|------|------|----------|
| `config.py` | 환경 설정 | • Pydantic Settings<br>• .env 파일 로드<br>• API 키, DB URL 등 |
| `logger.py` | 로깅 | • 파일 + 콘솔 로깅<br>• 날짜별 로그 파일<br>• UTF-8 인코딩 |
| `code_validator.py` | **코드 검증** ✨ | • **AST 문법 체크**<br>• **f-string 따옴표 중첩 감지**<br>• --variables-file 확인<br>• 수정 제안 생성 |

### 🖥️ UI 페이지 (pages/)

| 파일 | 역할 | 주요 기능 |
|------|------|----------|
| `1_Create_Workflow.py` | 워크플로우 생성 | • **AI 대화형 생성**<br>• 실시간 코드 검증 표시<br>• 샘플 워크플로우<br>• 폴더/태그 설정 |
| `2_Manage_Workflows.py` | 워크플로우 관리 | • 워크플로우 목록<br>• 필터링 (폴더/상태/태그)<br>• **AI 수정**<br>• 상태 변경<br>• 삭제 (확인 다이얼로그) |
| `3_Executions.py` | 실행 기록 | • 실행 목록<br>• 상세 로그 (스텝별)<br>• **재시도/승인/취소**<br>• 통계 대시보드 |
| `4_Triggers.py` | 트리거 관리 | • 트리거 생성<br>• 스케줄(Cron)/이벤트/웹훅<br>• 활성화/비활성화<br>• 수동 실행 |
| `5_Knowledge_Base.py` | 지식 베이스 관리 | • **파일 업로드** (PDF/Word/Excel/이미지)<br>• 문서 검색 및 관리<br>• **하이브리드 검색**<br>• 업로드 통계 및 분석 |

### 📄 루트 파일

| 파일 | 역할 | 설명 |
|------|------|------|
| `app.py` | 메인 대시보드 | • 전체 통계<br>• 최근 워크플로우<br>• 최근 실행 기록<br>• 빠른 작업 버튼 |
| `init_app.py` | 초기화 스크립트 | • DB 테이블 생성<br>• 기본 폴더 생성 |
| `run_scheduler.py` | 스케줄러 실행 | • 백그라운드 서비스<br>• 자동 트리거 실행 |
| `requirements.txt` | 의존성 | 14개 주요 패키지 |
| `.env` | 환경 변수 | API 키, DB URL 등 |

---

## 🔄 실행 흐름 (파일 간 호출 관계)

```
app.py (Streamlit UI)
  ↓
pages/2_Manage_Workflows.py ("실행" 버튼 클릭)
  ↓
src/runners/workflow_runner.py
  ├─ DB 조회 (src/database/models.py)
  └─ execute_workflow()
      ↓
src/engines/workflow_engine.py
  ├─ create_graph() - LangGraph StateGraph 생성
  └─ run_workflow()
      ↓
각 스텝 노드 실행
  ↓
src/engines/step_executor.py
  ├─ PYTHON_SCRIPT: subprocess 실행
  │   ├─ 임시 .py 파일 생성
  │   ├─ 임시 .json 파일 생성
  │   ├─ python script.py --variables-file vars.json
  │   └─ stdout/stderr 캡처
  ├─ LLM_CALL: OpenAI API
  └─ API_CALL: httpx
      ↓
결과 반환
  ↓
src/runners/workflow_runner.py
  └─ DB 업데이트 (실행 결과 저장)
      ↓
pages/3_Executions.py (결과 표시)
```

---

## 🎯 데이터 흐름

```
사용자 입력 (자연어)
  ↓
src/agents/meta_agent.py
  ├─ OpenAI API 호출
  ├─ JSON 파싱
  ├─ src/utils/code_validator.py (자동 검증) ✨
  └─ 워크플로우 정의 반환
      ↓
src/services/workflow_service.py
  ├─ create_workflow() - DB 저장
  ├─ WorkflowStep 레코드 생성 (code 필드에 Python 코드 저장)
  └─ workflow_scripts/ 폴더에 참고용 파일 생성
      ↓
데이터베이스 (workflows.db)
  ├─ workflows 테이블
  └─ workflow_steps 테이블 (code 컬럼 ← 실제 실행 코드!)
      ↓
실행 시:
src/engines/step_executor.py
  ├─ DB에서 step.code 읽기
  ├─ 임시 파일 생성
  ├─ subprocess 실행
  └─ 결과 파싱
      ↓
src/engines/workflow_engine.py
  └─ state["variables"] 업데이트 (다음 스텝으로 전달)
```

---

## 🏗️ 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                        Streamlit UI Layer                        │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐       │
│  │Dashboard │ Create   │ Manage   │Executions│ Triggers │       │
│  │  (app)   │Workflow  │Workflows │          │          │       │
│  └────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬─────┘       │
└───────┼──────────┼──────────┼──────────┼──────────┼─────────────┘
        │          │          │          │          │
        ├──────────┴──────────┴──────────┴──────────┤
        │                                            │
┌───────┼────────────────────────────────────────────┼─────────────┐
│       │           Service Layer                    │             │
│  ┌────▼────────┬──────────────┬──────────────┬────▼──────┐      │
│  │  Workflow   │  Execution   │    Folder    │  Trigger  │      │
│  │   Service   │   Service    │   Service    │  Manager  │      │
│  └────┬────────┴──────┬───────┴──────┬───────┴────┬──────┘      │
└───────┼───────────────┼──────────────┼────────────┼─────────────┘
        │               │              │            │
┌───────┼───────────────┼──────────────┼────────────┼─────────────┐
│       │        Workflow Execution Layer           │             │
│  ┌────▼─────────┐    ┌────────────────┐    ┌─────▼──────┐      │
│  │   Workflow   │───▶│   Workflow     │◀───│  Trigger   │      │
│  │    Runner    │    │    Engine      │    │ Scheduler  │      │
│  └──────┬───────┘    │  (LangGraph)   │    └────────────┘      │
│         │            └────────┬───────┘                         │
│         │                     │                                 │
│         │            ┌────────▼───────┐                         │
│         │            │      Step      │                         │
│         │            │   Executor     │                         │
│         │            └────────┬───────┘                         │
└─────────┼─────────────────────┼─────────────────────────────────┘
          │                     │
          │     ┌───────────────┼───────────────┐
          │     │               │               │
┌─────────▼─────▼───────────────▼───────────────▼─────────────────┐
│                      Core Components                             │
│  ┌──────────────┬──────────────┬──────────────┬────────────┐    │
│  │   Database   │  AI Agents   │     Code     │   Logger   │    │
│  │    Models    │   (Meta/     │  Validator   │            │    │
│  │  (SQLite)    │   Modifier)  │              │            │    │
│  └──────────────┴──────────────┴──────────────┴────────────┘    │
└──────────────────────────────────────────────────────────────────┘
          │                     │               │
          ▼                     ▼               ▼
   [workflows.db]         [OpenAI API]    [Log Files]
```

### 데이터 저장 위치

| 데이터 | 저장 위치 | 용도 |
|--------|----------|------|
| **워크플로우 정의** | `workflows.db` → `workflows` 테이블 | 이름, 설명, 정의(JSON) |
| **Python 코드** | `workflows.db` → `workflow_steps.code` | **실행 시 사용** ⭐ |
| **참고용 스크립트** | `workflow_scripts/{id}/step_*.py` | 디버깅용, 실행 안 됨 |
| **실행 기록** | `workflows.db` → `workflow_executions` | 상태, 입출력, 에러 |
| **스텝 실행 기록** | `workflows.db` → `step_executions` | 스텝별 상세 로그 |
| **트리거 설정** | `workflows.db` → `triggers` | Cron, 이벤트, 웹훅 |
| **로그** | `logs/*.log` | 날짜별 로그 파일 |

---

## 📊 프로젝트 통계

| 구성 요소 | 파일 수 | 코드 라인 수 (추정) |
|----------|--------|------------------|
| AI 에이전트 | 3 | ~900 |
| 데이터베이스 | 4 | ~350 |
| 워크플로우 엔진 | 3 | ~700 |
| 실행 관리 | 1 | ~350 |
| 서비스 레이어 | 3 | ~600 |
| 트리거 시스템 | 2 | ~350 |
| 유틸리티 | 3 | ~250 |
| UI 페이지 | 4 | ~800 |
| 기타 스크립트 | 5 | ~200 |
| **전체** | **28개** | **~4,500 라인** |

### 핵심 통계
- ✅ **Python 파일**: 28개
- ✅ **문서 파일**: 6개 (README, USAGE_GUIDE, etc.)
- ✅ **데이터베이스 테이블**: 7개
- ✅ **스텝 타입**: 7가지
- ✅ **Streamlit 페이지**: 5개 (메인 + 4개)
- ✅ **AI 프롬프트**: 450줄+ (상세한 코드 작성 규칙)

---

## 사용 방법

1. **워크플로우 생성**: "매일 아침 9시에 이메일을 확인하고 중요 메일을 슬랙으로 전송"
2. **AI와 대화**: AI가 필요한 정보(이메일 서버, 슬랙 채널 등)를 질문
3. **자동 검증**: AI가 생성한 코드를 자동으로 검증하고 오류 발견 시 즉시 재생성 ✨
4. **워크플로우 저장**: 검증 통과한 워크플로우를 저장
5. **실행 및 모니터링**: 수동 실행 또는 트리거 설정으로 자동 실행
6. **자동 수정**: 실행 실패 시 AI가 에러 로그를 분석하여 자동 수정

## 🧠 RAG (Retrieval-Augmented Generation) 시스템

AI가 더 정확하고 완성도 높은 워크플로우를 생성할 수 있도록 RAG 시스템을 도입했습니다:

### 지식 베이스 카테고리
- **워크플로우 패턴**: 일반적인 워크플로우 템플릿
- **에러 해결책**: Python 오류 및 디버깅 가이드
- **코드 템플릿**: 검증된 Python 스크립트 템플릿
- **통합 예제**: 외부 서비스 연동 예제
- **베스트 프랙티스**: 업계 표준 및 가이드라인

### RAG 작동 원리
```
사용자 입력 → RAG 검색 → 관련 지식 검색 → AI 컨텍스트 제공 → 향상된 워크플로우 생성
```

### 주요 기능
- **하이브리드 검색**: 의미적 검색 + 키워드 검색
- **자동 컨텍스트 제공**: 워크플로우 생성/수정 시 자동으로 관련 지식 활용
- **지식 베이스 관리**: UI를 통한 문서 업로드, 검색, 관리
- **다양한 파일 형식 지원**: PDF, Word, Excel, 이미지, 텍스트 파일 업로드
- **OCR 이미지 처리**: 이미지에서 텍스트 추출하여 검색 가능
- **성능 모니터링**: 검색 통계 및 품질 지표 추적

## 🧠 AI 자동 품질 관리

시스템은 "AI가 AI를 검증"하는 Self-Healing 구조:

### 생성 시 자동 검증
```
사용자 → AI 생성 → 코드 검증 → ❌ 오류 발견
                          ↓
              AI에게 자동 수정 요청
                          ↓
                    재생성 → 검증 → ✅ 통과
```

### 실행 시 자동 수정
```
워크플로우 실행 → ❌ 실패 → 에러 로그 수집
                          ↓
              AI가 로그 분석 및 수정
                          ↓
                    수정된 워크플로우 → ✅ 재실행
```

### 검증 항목
- ✅ Python 문법 (AST 파싱)
- ✅ f-string 따옴표 중첩 감지 (가장 흔한 오류!)
- ✅ --variables 인자 처리
- ✅ 구조화된 JSON 출력
- ✅ stderr/stdout 올바른 사용
- ✅ try-except 에러 처리

## 라이선스

MIT License

