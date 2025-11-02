# 🎯 프로젝트 종합 분석 보고서

## 📋 목차
1. [프로젝트 정의](#프로젝트-정의)
2. [전체 아키텍처](#전체-아키텍처)
3. [핵심 모듈 분석](#핵심-모듈-분석)
4. [데이터 흐름](#데이터-흐름)
5. [기술 스택 상세](#기술-스택-상세)
6. [주요 기능 현황](#주요-기능-현황)
7. [성과 및 로드맵](#성과-및-로드맵)

---

## 프로젝트 정의

### 🎯 비전
**"AI가 AI를 관리하는 Self-Healing 워크플로우 시스템"**

### 3가지 핵심 원칙

```
1️⃣ Zero Manual Coding
   • 자연어로만 업무 설명
   • AI가 완전한 Python 코드 자동 생성
   • 수동 코딩 불필요

2️⃣ Self-Healing
   • AI 생성 → 자동 검증 → 오류 발견 → AI 재생성 → ✅
   • AI가 생성한 코드를 AI가 검증
   • 문법 오류 사전 차단

3️⃣ Production-Ready
   • 모든 코드에 에러 처리 필수
   • 문법 검증 통과만 저장 가능
   • 격리된 실행 환경 (subprocess)
```

---

## 전체 아키텍처

### 📐 3계층 구조

```
┌─────────────────────────────────────────────────────────────────┐
│                   🖥️ UI Layer (Streamlit)                        │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐       │
│  │Dashboard │ Create   │ Manage   │Executions│Knowledge │       │
│  │  (app)   │Workflow  │Workflows │          │   Base   │       │
│  │          │ (p1)     │ (p2)     │  (p3)    │  (p5)    │       │
│  └────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬─────┘       │
└───────┼──────────┼──────────┼──────────┼──────────┼─────────────┘
        │          │          │          │          │
┌───────┼──────────┼──────────┼──────────┼──────────┼─────────────┐
│       │     🧠 Business Logic Layer (Services)   │             │
│  ┌────▼────────┬──────────────┬──────────────┬────▼──────┐      │
│  │  Workflow   │  Execution   │    Folder    │  Trigger  │      │
│  │   Service   │   Service    │   Service    │  Manager  │      │
│  └────┬────────┴──────┬───────┴──────┬───────┴────┬──────┘      │
│       │                │              │            │             │
│  ┌────▼────────────────▼──────────────▼────────────▼─────┐      │
│  │   RAGService (지식베이스 + 도메인 분리)               │      │
│  └─────────────────────────────────────────────────────┘      │
└───────┼────────────────────────────────────────────────────────┘
        │
┌───────┼──────────────────────────────────────────────────────────┐
│       │  ⚙️ Execution Engine Layer                               │
│  ┌────▼──────────────────────────────────────────────────┐      │
│  │     WorkflowRunner → WorkflowEngine (LangGraph)       │      │
│  │                                                       │      │
│  │  LangGraph StateGraph 구조:                           │      │
│  │  ├─ WorkflowState (타입 정의)                         │      │
│  │  ├─ add_node() - 각 스텝을 노드로 추가                │      │
│  │  ├─ add_conditional_edges() - 조건부 라우팅          │      │
│  │  └─ compile() - 실행 엔진 컴파일                      │      │
│  │                                                       │      │
│  │  StepExecutor (7가지 스텝 타입 실행)                  │      │
│  │  ├─ PYTHON_SCRIPT (subprocess)                       │      │
│  │  ├─ LLM_CALL (OpenAI)                                │      │
│  │  ├─ API_CALL (httpx)                                 │      │
│  │  ├─ CONDITION (조건 평가)                             │      │
│  │  ├─ APPROVAL (승인 대기)                              │      │
│  │  ├─ NOTIFICATION (알림)                               │      │
│  │  └─ DATA_TRANSFORM (변수 변환)                        │      │
│  └─────────────────────────────────────────────────────┘      │
└───────┼──────────────────────────────────────────────────────────┘
        │
┌───────┼──────────────────────────────────────────────────────────┐
│       │  💾 Data Layer                                           │
│  ┌────▼────────────────┬─────────────────────┐                 │
│  │  SQLite (workflows.db)                    │                 │
│  │  ├─ workflows (워크플로우 정의)           │                 │
│  │  ├─ workflow_steps (Python 코드)         │                 │
│  │  ├─ workflow_executions (실행 기록)       │                 │
│  │  ├─ step_executions (스텝별 로그)        │                 │
│  │  ├─ triggers (자동 실행 설정)             │                 │
│  │  ├─ workflow_versions (버전 관리)        │                 │
│  │  └─ folders (폴더 구조)                  │                 │
│  └────────┬──────────────────────────────────┘                 │
│           │                                                     │
│  ┌────────▼──────────────────────────────────┐                 │
│  │  ChromaDB (벡터 저장소 + 메타데이터)      │                 │
│  │  ├─ collection_naver                      │                 │
│  │  ├─ collection_weather                    │                 │
│  │  ├─ collection_kakao                      │                 │
│  │  ├─ collection_google                     │                 │
│  │  └─ collection_common (공용)              │                 │
│  │                                            │                 │
│  │  메타데이터 저장 (제목, 키워드, 태그):    │                 │
│  │  • 임베딩: OpenAI text-embedding-3-small  │                 │
│  │  • 차원: 384                              │                 │
│  │  • 전체 내용: SQLite에서 조회             │                 │
│  └────────────────────────────────────────────┘                 │
└──────────────────────────────────────────────────────────────────┘
        │
        └─→ [OpenAI API]    [LangSmith 추적]    [로그 파일]
```

---

## 핵심 모듈 분석

### 1️⃣ AI 에이전트 (src/agents/) - ~1,125 줄

| 파일 | 역할 | 핵심 기능 |
|------|------|----------|
| **meta_agent.py** | 워크플로우 생성 | • 자연어 → JSON 변환<br>• 정보 부족 시 질문<br>• OpenAI API 호출<br>• **자동 코드 검증** |
| **workflow_modifier.py** | 워크플로우 수정 | • 에러 로그 분석<br>• AI 기반 자동 수정<br>• 재검증 (최대 1회)<br>• 버전 관리 |
| **prompts.py** | AI 규칙 정의 | • 워크플로우 생성 규칙 (450줄!)<br>• Python 코드 작성 가이드<br>• f-string 따옴표 규칙<br>• 변수 전달 방식 명시 |

**흐름:**
```
사용자 쿼리 → meta_agent.py (OpenAI) → code_validator.py 검증 
→ ❌ 오류? → 자동 재생성 → ✅ 통과 → 저장
```

### 2️⃣ 워크플로우 엔진 (src/engines/) - ~681 줄 (LangGraph 기반)

#### **WorkflowEngine (workflow_engine.py)**

```python
class WorkflowEngine:
    """LangGraph 기반 실행 엔진"""
    
    def create_graph(workflow_steps):
        # 1. StateGraph 생성
        graph = StateGraph(WorkflowState)
        
        # 2. 각 스텝을 노드로 추가
        for step in sorted_steps:
            graph.add_node(f"step_{i}_{id}", step_node)
        
        # 3. 조건부 라우팅 추가
        graph.add_conditional_edges(
            current_node,
            lambda state: self._should_continue(state),
            {
                "continue": next_node,
                "stop": END,
                "wait_approval": END
            }
        )
        
        # 4. 컴파일 (체크포인트 저장)
        return graph.compile(checkpointer=MemorySaver())
    
    async def execute_workflow(workflow, execution_id, variables):
        # 초기 상태 설정
        initial_state = WorkflowState(
            workflow_id=workflow.id,
            variables=variables,
            step_results=[],
            step_statuses={},
            # ... 기타 상태
        )
        
        # LangGraph 실행 (비동기)
        final_state = await graph.ainvoke(initial_state)
        return final_state
```

**LangGraph 장점:**
- ✅ 상태 자동 관리
- ✅ 조건부 분기 처리
- ✅ 비동기 실행
- ✅ 체크포인트 저장 (중단/재개 가능)

#### **StepExecutor (step_executor.py)**

7가지 스텝 타입 지원:

```python
class StepExecutor:
    async def execute(step, variables):
        if step.type == "PYTHON_SCRIPT":
            # subprocess로 격리 실행
            # 1. 임시 .py 파일 생성
            # 2. 임시 .json 파일 (variables)
            # 3. python script.py --variables-file vars.json
            # 4. stdout 파싱
            
        elif step.type == "LLM_CALL":
            # OpenAI API
            
        elif step.type == "API_CALL":
            # HTTP 요청 (httpx)
            
        elif step.type == "CONDITION":
            # 조건 평가 (if/else)
            
        elif step.type == "APPROVAL":
            # 사용자 승인 대기
            
        elif step.type == "NOTIFICATION":
            # 알림 전송
            
        elif step.type == "DATA_TRANSFORM":
            # 변수 변환
```

**중요한 설계:**
- subprocess로 **격리 실행** (메인 앱 영향 없음)
- **변수는 JSON 파일**로 전달 (명령줄 길이 제한 해결)
- **stdout/stderr 캡처** (결과 추출)

#### **WorkflowState (workflow_state.py)**

```python
class WorkflowState(TypedDict):
    """LangGraph 상태"""
    workflow_id: str
    execution_id: str
    variables: Dict[str, Any]          # 스텝 간 데이터 전달
    step_results: List[Dict]           # 각 스텝 결과 누적
    step_statuses: Dict[str, StepStatus]  # 스텝별 상태 추적
    execution_status: str              # RUNNING, SUCCESS, FAILED
    approval_required: bool            # 승인 필요 여부
    error: Optional[str]               # 오류 메시지
```

### 3️⃣ RAG 시스템 (src/services/rag_service.py) - 메타데이터 기반

#### **혁신적 설계: 메타데이터만 벡터화**

```python
class RAGService:
    """도메인 기반 분리 + 메타데이터 검색"""
    
    # 도메인별 컬렉션 분리
    AVAILABLE_DOMAINS = ["naver", "weather", "kakao", "google", "common"]
    DOMAIN_TO_COLLECTION = {
        "naver": "collection_naver",
        "weather": "collection_weather",
        # ...
        "common": "collection_common"
    }
    
    def add_document(document, metadata_obj, domain):
        # 메타데이터만 벡터화
        chroma_metadata = {
            "title": document.title,
            "keywords": document.keywords,
            "tags": document.tags,
            "summary": document.summary[:500],
            "domain": domain,
            "category": document.category,
            "doc_type": document.doc_type,
        }
        
        # 도메인별 컬렉션에 저장
        collection = self._get_collection_for_domain(domain)
        collection.add(
            ids=[document.id],
            documents=[chroma_metadata_text],  # 메타데이터 임베딩
            metadatas=[chroma_metadata]
        )
        
        # 전체 내용은 SQLite에만 저장
        # (SQL에서 빠르게 조회 가능)
    
    def search_metadata(query, domain=None):
        # 1. 도메인 지정 검색
        if domain:
            results = search_specific_collection(domain)
            results += search_common_collection()
        
        # 2. 전체 도메인 검색
        else:
            for domain in AVAILABLE_DOMAINS:
                results += search_domain(domain)
        
        # 3. 유사도 순 정렬
        results.sort(by_similarity, reverse=True)
        
        # 4. SQLite에서 전체 content 조회
        for result in results:
            result["content"] = sqlite.query(result["id"])
        
        return results
```

**메타데이터 기반 RAG의 장점:**

| 문제 | 기존 방식 | 메타데이터 방식 |
|------|---------|--------------|
| **코드/XML 검색** | ❌ 뒷부분 잘림 | ✅ 메타데이터만 임베딩 |
| **키워드 정확도** | ❌ "API" 검색 → 모든 API | ✅ 도메인 분리로 해결 |
| **검색 속도** | ❌ 큰 문서 처리 지연 | ✅ 메타데이터만 빠름 |
| **콘텐츠 전달** | ❌ 청크 조합 필요 | ✅ 전체 내용 직접 전달 |
| **확장성** | ❌ 도메인 혼재 | ✅ 도메인 분리 = 무한 확장 |

#### **도메인 분리 효과**

```
검색: "네이버 뉴스"

OLD (혼재):
├─ 네이버 뉴스 워크플로우 (0.425)
├─ 기상청 API (0.420) ← 불필요!
└─ 네이버 지도 API (0.418)

NEW (도메인 분리):
├─ 네이버 뉴스 워크플로우 (0.425) ✅
├─ 네이버 블로그 크롤러 (0.410)
└─ 네이버 검색 API (0.405)

기상청 API는 search_weather에서만 나옴!
```

### 4️⃣ 데이터베이스 (src/database/models.py) - 7개 테이블

```python
# 1. 폴더 구조
class Folder:
    id, name, parent_id, description, created_at

# 2. 워크플로우 정의
class Workflow:
    id, folder_id, name, definition (JSON)
    created_at, updated_at, version

# 3. 워크플로우 스텝 (코드 저장!)
class WorkflowStep:
    id, workflow_id, order, name
    step_type (PYTHON_SCRIPT, LLM_CALL, ...)
    code ← ⭐ 실제 실행 코드!
    created_at

# 4. 실행 기록
class WorkflowExecution:
    id, workflow_id, execution_id
    status (RUNNING, SUCCESS, FAILED)
    variables (JSON)
    created_at, completed_at

# 5. 스텝별 실행 로그
class StepExecution:
    id, execution_id, step_id
    status, output (JSON)
    error, duration
    created_at

# 6. 자동 트리거
class Trigger:
    id, workflow_id, trigger_type (SCHEDULE, EVENT, WEBHOOK)
    cron_expression, event_name
    is_active, next_run_time

# 7. 버전 관리
class WorkflowVersion:
    id, workflow_id, version
    definition (JSON)
    created_at, created_by
```

### 5️⃣ 파일 업로드 & 검색 (file_service.py + file_parser.py)

```
파일 업로드 흐름:
┌─────────────────┐
│ 파일 선택 (UI)  │
└────────┬────────┘
         │ (PDF, DOCX, XLSX, JPG, TXT)
         ▼
┌─────────────────────────┐
│ file_service.upload()   │
└────────┬────────────────┘
         │
┌────────▼────────────────────────┐
│ file_parser.parse_*()           │
├─ parse_pdf() → OCR             │
├─ parse_docx() → 단락 추출      │
├─ parse_xlsx() → 시트 처리      │
├─ parse_image() → Tesseract    │
└─ parse_text() → 인코딩 감지   │
         │
┌────────▼──────────────────────────┐
│ SQLite Document 테이블에 저장     │
└────────┬───────────────────────────┘
         │
┌────────▼──────────────────────────┐
│ ChromaDB 메타데이터 임베딩        │
│ (도메인별 컬렉션)                │
└────────┬───────────────────────────┘
         │
         ▼
검색 가능! ("5_Knowledge_Base.py")
```

---

## 데이터 흐름

### 🔄 워크플로우 생성 → 실행 흐름

```
1️⃣ 사용자: "매일 10시에 이메일 확인해서 중요 건 알려줘"
   ↓
2️⃣ pages/1_Create_Workflow.py
   └─ AI와 대화 시작
   ↓
3️⃣ src/agents/meta_agent.py
   ├─ RAGService.hybrid_search() → 관련 문서 검색
   ├─ OpenAI API 호출
   ├─ "Please generate workflow as JSON..."
   └─ 워크플로우 JSON 생성
   ↓
4️⃣ src/utils/code_validator.py
   ├─ AST 문법 체크
   ├─ f-string 따옴표 중첩 검사
   ├─ --variables-file 확인
   └─ 문법 오류? → AI 재생성 (자동!)
   ↓
5️⃣ src/services/workflow_service.py
   ├─ create_workflow()
   ├─ 각 스텝의 Python 코드 저장
   │  └─ 데이터베이스: workflow_steps.code
   ├─ 참고용 파일 생성: workflow_scripts/
   └─ DB 저장 완료
   ↓
6️⃣ pages/2_Manage_Workflows.py
   └─ "실행" 버튼 클릭
   ↓
7️⃣ src/runners/workflow_runner.py
   ├─ DB에서 workflow 로드
   ├─ WorkflowExecution 레코드 생성
   └─ execute_workflow() 호출
   ↓
8️⃣ src/engines/workflow_engine.py
   ├─ LangGraph StateGraph 생성
   ├─ 각 스텝 = 그래프 노드
   ├─ 조건부 라우팅 설정
   └─ graph.ainvoke() 실행 시작
   ↓
9️⃣ 각 스텝 노드 실행 (순서대로)
   ├─ src/engines/step_executor.py
   │  ├─ 1️⃣ 임시 .py 파일 생성 (step.code 사용!)
   │  ├─ 2️⃣ 임시 .json 파일 생성 (variables)
   │  ├─ 3️⃣ python script.py --variables-file vars.json
   │  ├─ 4️⃣ stdout 캡처
   │  └─ 5️⃣ JSON 파싱 → 결과 추출
   │
   ├─ state["variables"] 업데이트
   ├─ state["step_results"] 누적
   └─ 다음 스텝으로 → 라우팅 결정
   ↓
🔟 모든 스텝 완료 → END
   ↓
1️⃣1️⃣ src/runners/workflow_runner.py
   ├─ WorkflowExecution 업데이트
   ├─ StepExecution 레코드 생성
   └─ 결과 DB 저장
   ↓
1️⃣2️⃣ pages/3_Executions.py
   └─ 실행 결과 표시!
```

### 🔄 에러 발생 시 자동 수정 흐름

```
1️⃣ 워크플로우 실행 실패
   ↓
2️⃣ pages/3_Executions.py
   ├─ 에러 로그 표시
   ├─ 사용자: "이 에러 수정해줘"
   └─ 수정 요청 전송
   ↓
3️⃣ src/agents/workflow_modifier.py
   ├─ 에러 로그 분석
   ├─ 원본 워크플로우 + 에러 로그로 컨텍스트 구성
   ├─ OpenAI API 호출
   │  └─ "Please fix this code based on error..."
   └─ 수정된 워크플로우 JSON 생성
   ↓
4️⃣ src/utils/code_validator.py
   └─ 재검증 (최대 1회)
   ↓
5️⃣ src/services/workflow_service.py
   ├─ update_workflow()
   ├─ 버전 자동 증가
   ├─ DB 업데이트
   └─ 이력 저장
   ↓
6️⃣ pages/2_Manage_Workflows.py
   └─ "재실행" 가능!
```

---

## 기술 스택 상세

### 🔧 백엔드 (Python)

| 라이브러리 | 버전 | 용도 |
|-----------|------|------|
| **FastAPI / Streamlit** | 최신 | 웹 UI & API |
| **LangGraph** | 0.2.45 | ⭐ 워크플로우 실행 엔진 |
| **OpenAI** | 최신 | LLM + 임베딩 |
| **SQLAlchemy** | 최신 | ORM (데이터베이스) |
| **SQLite3** | 기본 | 로컬 DB |
| **ChromaDB** | 0.4+ | 벡터 저장소 |
| **httpx** | 최신 | 비동기 HTTP |
| **Pydantic** | v2 | 데이터 검증 |
| **APScheduler** | 최신 | 스케줄링 |
| **pytesseract** | 최신 | OCR (이미지) |

### 🤖 AI 모델

```
워크플로우 생성/수정:
└─ GPT-4 (OpenAI API)
   • 온도: 0.3 (일관성)
   • Max tokens: 4000
   • 구조화된 JSON 출력

임베딩:
└─ text-embedding-3-small (OpenAI)
   • 차원: 384
   • 비용 효율적
   • 빠른 검색
```

### 📊 데이터 저장

```
SQLite (workflows.db)
└─ 7개 테이블: 워크플로우, 스텝, 실행, 트리거, 버전, 폴더

ChromaDB (data/chroma_db/)
├─ collection_naver (네이버 관련)
├─ collection_weather (기상청 관련)
├─ collection_kakao (카카오 관련)
├─ collection_google (구글 관련)
└─ collection_common (공용 문서)

메타데이터만 임베딩:
├─ 제목
├─ 키워드
├─ 태그
├─ 요약
├─ 도메인
└─ 카테고리

전체 콘텐츠:
└─ SQLite Document 테이블
```

---

## 주요 기능 현황

### ✅ 완성된 기능

| 기능 | 파일 | 상태 | 설명 |
|------|------|------|------|
| **워크플로우 생성** | meta_agent.py | ✅ | AI 자동 생성 + 자동 검증 |
| **AI 기반 수정** | workflow_modifier.py | ✅ | 에러 분석 + 자동 수정 |
| **LangGraph 실행** | workflow_engine.py | ✅ | StateGraph + 조건부 라우팅 |
| **7가지 스텝 타입** | step_executor.py | ✅ | PYTHON/LLM/API/CONDITION/APPROVAL/NOTIFICATION/DATA_TRANSFORM |
| **도메인 기반 RAG** | rag_service.py | ✅ | naver/weather/kakao/google/common |
| **메타데이터 검색** | rag_service.py | ✅ | 제목+키워드+태그 임베딩 |
| **파일 업로드** | file_service.py | ✅ | PDF/DOCX/XLSX/JPG/TXT |
| **OCR 처리** | file_parser.py | ✅ | 이미지 → 텍스트 |
| **자동 트리거** | trigger_manager.py | ✅ | Cron + 이벤트 기반 |
| **실행 기록** | execution_service.py | ✅ | 상세 로그 + 통계 |
| **Streamlit UI** | pages/ | ✅ | 5개 페이지 + 대시보드 |

### 🚀 개선된 기능 (최근)

```
1️⃣ 메타데이터 기반 RAG (NEW)
   • 코드/XML 손실 해결
   • 키워드 검색 정확도 향상
   • 도메인 분리로 무관 문서 제거

2️⃣ LangGraph 완전 통합
   • StateGraph 기반 실행
   • 조건부 라우팅 (continue/stop/approval)
   • 비동기 실행 + 체크포인트

3️⃣ 자동 코드 검증
   • AST 문법 체크
   • f-string 따옴표 중첩 감지
   • AI 자동 수정
```

---

## 성과 및 로드맵

### 📈 현재 프로젝트 규모

```
Python 파일:        29개
총 코드 라인:      ~7,400 라인
문서:             6개 (~2,100 라인)
데이터베이스 테이블: 7개
Streamlit 페이지:  5개
AI 에이전트:       2개 (생성/수정)
스텝 타입:         7가지
```

### 🎯 기술 성숙도 로드맵

```
Phase 1 (현재) ✅ COMPLETE
├─ ✅ LLM 기본 통합
├─ ✅ RAG 도메인 분리
├─ ✅ Session Memory
├─ ✅ LangGraph 완전 적용
│  ├─ StateGraph 구현
│  ├─ 조건부 라우팅
│  ├─ 상태 추적
│  └─ MemorySaver 체크포인트
└─ ✅ 메타데이터 기반 검색

Phase 2 (3개월) 🚀 IN PROGRESS
├─ 🚀 LangGraph 고도화
│  ├─ 병렬 스텝 실행
│  ├─ 동적 라우팅
│  └─ 스텝 재시도 로직
├─ 🚀 고급 Memory 시스템 (지속 학습)
├─ 🚀 다중 모델 지원
└─ ⏳ MCP 프로토타입

Phase 3 (6개월) 🎯 PLANNED
├─ ✅ MCP 본격 도입
├─ ✅ 도구 생태계
├─ ✅ LangGraph 에이전트 루프
└─ ⏳ 자가학습 시스템

Phase 4 (1년) 🌟 VISION
├─ ✅ 완전 자동화 에이전트
├─ ✅ 지속적 학습
├─ ✅ 예측 기능
└─ ✅ 자기 최적화
```

### 🏆 핵심 성과

```
✅ Zero-Code 워크플로우 생성
   → 사용자는 자연어만 입력
   → AI가 Python 코드 자동 생성

✅ Self-Healing 아키텍처
   → AI 생성 → 자동 검증 → 오류 시 자동 수정
   → 수동 개입 최소화

✅ Production-Ready 시스템
   → 모든 코드 자동 검증
   → 격리된 실행 환경
   → 상세한 에러 추적

✅ 도메인 기반 RAG
   → 메타데이터만 벡터화
   → 도메인 분리로 검색 정확도 향상
   → 무한 확장 가능

✅ LangGraph 완전 통합
   → 복잡한 워크플로우 자동 관리
   → 조건부 분기 처리
   → 비동기 실행 + 체크포인트
```

---

## 💡 다음 단계

### 🔍 현재 이해도 수준

**강점:**
- ✅ 전체 아키텍처 명확
- ✅ 각 모듈 역할 이해
- ✅ 데이터 흐름 파악
- ✅ LangGraph 기반 실행 엔진 완벽
- ✅ RAG 시스템 도메인 분리 완성

**다음 초점:**
- 🎯 Phase 2: LangGraph 고도화 (병렬 실행, 동적 라우팅)
- 🎯 MCP 통합 (외부 도구 연결)
- 🎯 Advanced Memory (지속 학습)
- 🎯 성능 최적화

### 📝 질문이 있으신가요?

프로젝트의 특정 부분에 대해 더 알고 싶으시면:
1. 특정 모듈/파일 지정
2. 특정 기능 흐름 추적
3. 성능/확장성 분석
4. 버그/개선 사항

편하게 말씀해주세요! 🚀
