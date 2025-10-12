# 프로젝트 전체 개요

## 📦 전체 파일 목록

### 📁 src/ (소스 코드)

#### src/agents/ - AI 에이전트
```
src/agents/
├── __init__.py              (5 lines)   - 모듈 exports
├── meta_agent.py            (~320 lines) - 대화형 워크플로우 생성 AI
├── workflow_modifier.py     (~350 lines) - 워크플로우 수정 AI
└── prompts.py               (~450 lines) - AI 프롬프트 및 규칙
                             ──────────
                             총 ~1,125 lines
```

#### src/database/ - 데이터베이스
```
src/database/
├── __init__.py              (24 lines)  - 모델 exports
├── base.py                  (22 lines)  - SQLAlchemy 설정
├── models.py                (~270 lines) - 7개 테이블 모델
├── session.py               (34 lines)  - 세션 관리
└── init_db.py               (9 lines)   - 초기화 스크립트
                             ──────────
                             총 ~359 lines
```

#### src/engines/ - 워크플로우 엔진
```
src/engines/
├── __init__.py              (5 lines)   - 모듈 exports
├── workflow_engine.py       (~330 lines) - LangGraph StateGraph 엔진
├── step_executor.py         (~300 lines) - 7가지 스텝 실행 로직
└── workflow_state.py        (46 lines)  - 상태 정의
                             ──────────
                             총 ~681 lines
```

#### src/runners/ - 실행 관리
```
src/runners/
├── __init__.py              (5 lines)   - 모듈 exports
└── workflow_runner.py       (~350 lines) - 실행 라이프사이클 관리
                             ──────────
                             총 ~355 lines
```

#### src/services/ - 서비스 레이어
```
src/services/
├── __init__.py              (7 lines)   - 서비스 exports
├── workflow_service.py      (~450 lines) - 워크플로우 CRUD + 코드 검증
├── execution_service.py     (~150 lines) - 실행 기록 관리
└── folder_service.py        (~120 lines) - 폴더 관리
                             ──────────
                             총 ~727 lines
```

#### src/triggers/ - 트리거 시스템
```
src/triggers/
├── __init__.py              (5 lines)   - 모듈 exports
├── trigger_manager.py       (~200 lines) - 트리거 CRUD, Cron 처리
└── scheduler.py             (~150 lines) - 백그라운드 스케줄러
                             ──────────
                             총 ~355 lines
```

#### src/utils/ - 유틸리티
```
src/utils/
├── __init__.py              (5 lines)   - 유틸 exports
├── config.py                (41 lines)  - Pydantic Settings
├── logger.py                (55 lines)  - 로깅 설정
└── code_validator.py        (~160 lines) - Python 코드 검증 ✨
                             ──────────
                             총 ~261 lines
```

### 📁 pages/ (Streamlit UI)

```
pages/
├── __init__.py              (1 line)    - 모듈 마커
├── 1_Create_Workflow.py     (~320 lines) - AI 대화형 생성 + 샘플
├── 2_Manage_Workflows.py    (~250 lines) - CRUD + AI 수정
├── 3_Executions.py          (~280 lines) - 실행 기록 + 상세 로그
└── 4_Triggers.py            (~250 lines) - 트리거 관리
                             ──────────
                             총 ~1,101 lines
```

### 📁 루트 파일

```
projWorkFlow4/
├── app.py                   (~165 lines) - 메인 대시보드
├── init_app.py              (~45 lines)  - 초기화 스크립트
├── run_scheduler.py         (~50 lines)  - 트리거 스케줄러 실행
├── requirements.txt         (14 lines)   - 의존성
├── .env.example             (12 lines)   - 환경 변수 예시
├── .gitignore               (40 lines)   - Git 제외 파일
├── README.md                (~470 lines) - 프로젝트 문서
├── USAGE_GUIDE.md           (~220 lines) - 사용 가이드
├── LANGGRAPH_WORKFLOW.md    (~800 lines) - LangGraph 동작 원리
├── AI_QUALITY_SYSTEM.md     (~220 lines) - AI 품질 관리
└── PYTHON_EXECUTION_FLOW.md (~400 lines) - Python 실행 메커니즘
                             ──────────
                             총 ~2,436 lines
```

---

## 📊 총 통계

| 카테고리 | Python 파일 | 코드 라인 | 비고 |
|---------|------------|----------|------|
| **AI 에이전트** | 3 | ~1,125 | 자동 생성/수정 |
| **데이터베이스** | 4 | ~359 | 7개 테이블 |
| **워크플로우 엔진** | 3 | ~681 | LangGraph 기반 |
| **실행 관리** | 1 | ~355 | 라이프사이클 |
| **서비스 레이어** | 3 | ~727 | CRUD + 검증 |
| **트리거 시스템** | 2 | ~355 | 자동 실행 |
| **유틸리티** | 3 | ~261 | 검증 ✨ |
| **UI 페이지** | 4 | ~1,101 | Streamlit |
| **루트 스크립트** | 3 | ~260 | 초기화/실행 |
| **문서** | 6 | ~2,110 | 상세 가이드 |
| **설정 파일** | 3 | ~66 | 의존성/환경 |
| **전체** | **29개** | **~7,400 라인** | ⭐ |

---

## 🎯 핵심 파일 (읽어야 할 순서)

시스템을 이해하려면 다음 순서로 읽으세요:

### 1단계: 개념 이해
1. `README.md` - 전체 개요
2. `AI_QUALITY_SYSTEM.md` - AI 자동 품질 관리
3. `LANGGRAPH_WORKFLOW.md` - LangGraph 동작 원리

### 2단계: 데이터 구조
4. `src/database/models.py` - 7개 테이블 이해
5. `src/engines/workflow_state.py` - 실행 상태 구조

### 3단계: AI 에이전트
6. `src/agents/prompts.py` - AI 프롬프트 (규칙 이해)
7. `src/agents/meta_agent.py` - 워크플로우 생성 로직
8. `src/utils/code_validator.py` - 자동 검증 로직

### 4단계: 실행 엔진
9. `src/engines/workflow_engine.py` - LangGraph 그래프 생성
10. `src/engines/step_executor.py` - 스텝 실행 (subprocess!)
11. `src/runners/workflow_runner.py` - 전체 라이프사이클

### 5단계: UI
12. `app.py` - 메인 대시보드
13. `pages/1_Create_Workflow.py` - AI 대화형 생성

---

## 🚀 핵심 기능별 파일

### AI 워크플로우 생성
```
사용자 입력 → src/agents/meta_agent.py
              ├─ OpenAI API 호출
              ├─ src/agents/prompts.py (규칙 적용)
              ├─ src/utils/code_validator.py (검증)
              └─ 워크플로우 JSON 반환
                  ↓
           pages/1_Create_Workflow.py (UI에 표시)
                  ↓
           src/services/workflow_service.py (DB 저장)
```

### 워크플로우 실행
```
pages/2_Manage_Workflows.py ("실행" 버튼)
  ↓
src/runners/workflow_runner.py
  ├─ src/database/models.py (워크플로우 로드)
  └─ execute_workflow()
      ↓
src/engines/workflow_engine.py
  ├─ LangGraph StateGraph 생성
  └─ run_workflow()
      ↓
src/engines/step_executor.py
  ├─ DB에서 step.code 읽기
  ├─ 임시 .py/.json 파일 생성
  ├─ subprocess로 Python 실행
  └─ stdout 파싱
      ↓
결과를 DB에 저장
  ↓
pages/3_Executions.py (결과 표시)
```

### AI 자동 수정
```
실행 실패 → pages/3_Executions.py (에러 표시)
              ↓
      사용자: "이 에러 수정해줘"
              ↓
src/agents/workflow_modifier.py
  ├─ 에러 로그 분석
  ├─ OpenAI API 호출
  ├─ 수정된 워크플로우 생성
  ├─ src/utils/code_validator.py (재검증)
  └─ 수정된 워크플로우 반환
      ↓
src/services/workflow_service.py
  └─ update_workflow() (버전 증가, DB 저장)
```

---

## 🔍 중요한 개념

### 1. **코드 저장 위치**
- ✅ **실제 실행 코드**: `workflows.db` → `workflow_steps.code` 컬럼
- ⚠️ **참고용 파일**: `workflow_scripts/{workflow_id}/step_*.py`
  - 디버깅 및 확인용
  - 실행 시 사용 안 됨!

### 2. **변수 전달 방식**
- 임시 JSON 파일 사용 (`--variables-file`)
- Windows 명령줄 길이 제한 해결
- 대용량 데이터 전달 가능

### 3. **격리된 실행**
- subprocess로 별도 Python 프로세스
- 메인 애플리케이션에 영향 없음
- 타임아웃으로 무한 루프 방지

### 4. **자동 품질 관리**
- AI 생성 → 즉시 검증
- 문법 오류 → AI 재생성
- 저장 전 100% 검증

---

## 💻 개발 가이드

### 새 스텝 타입 추가

1. `src/database/models.py` → `StepType` enum에 추가
2. `src/engines/step_executor.py` → `_execute_xxx()` 메서드 구현
3. `src/agents/prompts.py` → 프롬프트에 설명 추가
4. UI에서 사용 가능!

### 새 트리거 타입 추가

1. `src/database/models.py` → `TriggerType` enum에 추가
2. `src/triggers/trigger_manager.py` → 검증 로직 추가
3. `src/triggers/scheduler.py` → 실행 로직 추가
4. `pages/4_Triggers.py` → UI 추가

### 코드 검증 규칙 추가

1. `src/utils/code_validator.py` → 검증 로직 추가
2. `src/agents/prompts.py` → AI 프롬프트에 규칙 추가
3. AI가 자동으로 따름!

---

이 프로젝트는 **약 7,400줄의 Python 코드**로 구성된 **프로덕션급 워크플로우 관리 시스템**입니다! 🎉

