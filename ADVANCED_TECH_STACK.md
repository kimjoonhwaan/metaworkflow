# 🚀 고급 기술 스택: LLM, LangGraph, RAG, MCP, Memory

## 1️⃣ **LLM (Large Language Model) Integration**

### **현재 선택: OpenAI GPT**

```
프로젝트에서 LLM의 역할:
├─ 워크플로우 생성 (자연어 → 워크플로우 JSON)
├─ 코드 생성 (프롬프트 → Python 코드)
├─ 오류 해결 (오류 로그 → 해결책)
├─ 문서 요약 (긴 문서 → 짧은 요약)
└─ 의도 분석 (사용자 쿼리 → 워크플로우 의도)
```

#### **사용 중인 LLM 모델들**

```python
from openai import AsyncOpenAI

class LLMManager:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    
    # 1. 워크플로우 생성
    async def generate_workflow(self, user_query: str):
        """자연어 → 워크플로우 JSON"""
        response = await self.client.chat.completions.create(
            model="gpt-4-turbo",          # ⭐ 최고 성능
            messages=[
                {"role": "system", "content": WORKFLOW_GENERATION_PROMPT},
                {"role": "user", "content": user_query}
            ],
            temperature=0.7,               # 창의성: 0.7
            max_tokens=4096
        )
        return response.choices[0].message.content
    
    # 2. 코드 생성
    async def generate_code(self, task: str):
        """작업 → Python 코드"""
        response = await self.client.chat.completions.create(
            model="gpt-4",                 # 코드 생성은 gpt-4
            messages=[...],
            temperature=0.3                # 정확성: 0.3
        )
        return response.choices[0].message.content
    
    # 3. 임베딩 생성 (RAG용)
    async def generate_embedding(self, text: str):
        """텍스트 → 벡터 (384차원)"""
        response = await self.client.embeddings.create(
            model="text-embedding-3-small",  # ⭐ RAG용
            input=text,
            dimensions=384
        )
        return response.data[0].embedding
```

#### **모델별 선택 기준**

| 모델 | 용도 | 성능 | 속도 | 비용 | 선택 |
|------|------|------|------|------|------|
| **GPT-4 Turbo** | 복잡한 작업 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 비쌈 | ✅ 워크플로우 생성 |
| **GPT-4** | 코드 생성 | ⭐⭐⭐⭐⭐ | ⭐⭐ | 비쌈 | ✅ 코드 생성 |
| **GPT-3.5-Turbo** | 간단한 작업 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 쌈 | ✅ 요약, 분류 |
| **text-embedding-3-small** | 임베딩 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 매우쌈 | ✅ RAG |

#### **LLM 성능 최적화**

```python
# 1. 프롬프트 엔지니어링
SYSTEM_PROMPT = """
당신은 전문 워크플로우 설계자입니다.
사용자의 자연어 요청을 실행 가능한 JSON 워크플로우로 변환합니다.

규칙:
1. 각 단계는 명확한 목표를 가져야 함
2. 데이터 흐름은 단계별로 명확함
3. 오류 처리는 필수
4. 변수명은 snake_case 사용

출력 형식: 유효한 JSON
"""

# 2. Few-shot 프롬프팅
examples = [
    {
        "input": "네이버 뉴스에서 IT 뉴스 3개를 크롤링해줘",
        "output": {
            "workflow": {
                "name": "Naver IT News Crawler",
                "steps": [
                    {"type": "API_CALL", "service": "naver", ...},
                    {"type": "DATA_FILTER", "query": "IT", ...},
                    {"type": "DATA_FORMAT", "format": "json", ...}
                ]
            }
        }
    }
]

# 3. 토큰 최적화
async def optimize_prompt(query: str, max_tokens: int = 4096):
    """
    토큰 사용량 최적화:
    - 불필요한 설명 제거
    - 핵심 정보만 포함
    - 컨텍스트 창 효율적 사용
    """
    return compressed_prompt
```

---

## 2️⃣ **LangGraph - 에이전트 오케스트레이션**

### **LangGraph란?**

```
LangGraph는 Multi-step 에이전트 시스템을 구축하기 위한 라이브러리입니다.

특징:
✅ 상태 관리 (State Machine)
✅ 도구 사용 (Tool Use)
✅ 조건부 분기 (Conditional Branching)
✅ 루핑 (Agentic Loop)

📌 현재 상태: ✅ **완전히 적용됨** (v0.2.45)
```

### **프로젝트에 이미 적용된 구현**

#### **1️⃣ WorkflowState 정의** (`src/engines/workflow_state.py`)

```python
from typing import TypedDict, List, Dict, Any, Optional

class StepStatus(TypedDict):
    """각 스텝의 상태"""
    status: str                    # PENDING, RUNNING, SUCCESS, FAILED
    output: Optional[Dict[str, Any]]
    error: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

class WorkflowState(TypedDict):
    """LangGraph 워크플로우 상태"""
    workflow_id: str               # 워크플로우 ID
    execution_id: str              # 실행 ID
    current_step_index: int        # 현재 스텝 인덱스
    variables: Dict[str, Any]      # 워크플로우 변수 (데이터 전달용)
    step_results: List[Dict]       # 각 스텝 결과 누적
    step_statuses: Dict[str, StepStatus]  # 스텝별 상태
    execution_status: str          # 전체 실행 상태
    approval_required: bool        # 승인 대기 여부
    approval_data: Optional[Dict]  # 승인 필요 데이터
    error: Optional[str]           # 오류 메시지
    total_duration: float          # 총 실행 시간
```

#### **2️⃣ WorkflowEngine 구현** (`src/engines/workflow_engine.py`)

```python
class WorkflowEngine:
    """LangGraph 기반 워크플로우 실행 엔진"""
    
    def __init__(self):
        self.step_executor = StepExecutor()
        self.memory = MemorySaver()  # 상태 체크포인트
    
    def create_graph(
        self,
        workflow_steps: List[WorkflowStep],
        on_step_complete: Optional[Callable] = None,
    ) -> StateGraph:
        """✨ LangGraph StateGraph 생성"""
        
        # Step 1: 스텝별 노드 생성
        graph = StateGraph(WorkflowState)
        
        for i, step in enumerate(sorted_steps):
            node_name = f"step_{step.order}_{step.id}"
            
            # 각 스텝을 LangGraph 노드로 추가
            async def step_node(state: WorkflowState, step=step):
                # 스텝 실행
                result = await self.step_executor.execute(
                    step,
                    state["variables"]
                )
                
                # 상태 업데이트
                state["step_results"].append(result)
                state["variables"].update(result.get("variables", {}))
                
                return state
            
            graph.add_node(node_name, step_node)
        
        # Step 2: 조건부 라우팅 추가
        graph.add_conditional_edges(
            current_node,
            lambda state: self._should_continue(state),  # 라우팅 함수
            {
                "continue": next_node,      # 다음 스텝으로
                "stop": END,               # 종료
                "wait_approval": END,      # 승인 대기
            }
        )
        
        # Step 3: 그래프 컴파일 (체크포인트 저장 활성화)
        return graph.compile(checkpointer=self.memory)
    
    async def execute_workflow(
        self,
        workflow: Workflow,
        execution_id: str,
        variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """🚀 워크플로우 실행 (LangGraph ainvoke)"""
        
        # 초기 상태 설정
        initial_state = WorkflowState(
            workflow_id=workflow.id,
            execution_id=execution_id,
            current_step_index=0,
            variables=variables,
            step_results=[],
            step_statuses={},
            execution_status="RUNNING",
            approval_required=False,
            approval_data=None,
            error=None,
            total_duration=0.0
        )
        
        # LangGraph 실행
        graph = self.create_graph(workflow.steps)
        
        # ✨ ainvoke: 비동기 실행 (상태 추적)
        final_state = await graph.ainvoke(
            initial_state,
            config={"configurable": {"thread_id": execution_id}}
        )
        
        return {
            "execution_id": execution_id,
            "final_state": final_state,
            "variables": final_state["variables"],
            "results": final_state["step_results"],
            "status": final_state["execution_status"]
        }
```

### **LangGraph의 핵심 동작**

```
1️⃣ StateGraph 생성
   ├─ WorkflowState 타입 정의
   ├─ 스텝별 노드 추가 (add_node)
   └─ 조건부 엣지 추가 (add_conditional_edges)

2️⃣ 조건부 라우팅
   ├─ _should_continue() 함수로 다음 액션 결정
   ├─ "continue" → 다음 스텝
   ├─ "stop" → 워크플로우 종료
   └─ "wait_approval" → 승인 대기

3️⃣ 상태 관리
   ├─ 각 스텝 후 WorkflowState 업데이트
   ├─ step_results에 결과 누적
   ├─ variables에 데이터 전달
   └─ MemorySaver로 체크포인트 저장

4️⃣ 비동기 실행
   └─ graph.ainvoke()로 비동기 실행
```

### **현재 적용 상황** ✅

| 항목 | 상태 | 파일 | 설명 |
|------|------|------|------|
| **StateGraph** | ✅ | `workflow_engine.py` | 스텝 기반 그래프 생성 |
| **조건부 라우팅** | ✅ | `workflow_engine.py` | continue/stop/approval |
| **상태 추적** | ✅ | `workflow_state.py` | WorkflowState 정의 |
| **체크포인트** | ✅ | `workflow_engine.py` | MemorySaver 통합 |
| **비동기 실행** | ✅ | `workflow_engine.py` | ainvoke 사용 |
| **오류 처리** | ✅ | `step_executor.py` | 예외 처리 및 상태 기록 |

### **LangGraph 사용 흐름**

```
사용자 쿼리
    ↓
워크플로우 생성 (JSON)
    ↓
WorkflowState 초기화
    ↓
StateGraph 생성
    ├─ 스텝1 노드 + 라우팅
    ├─ 스텝2 노드 + 라우팅
    └─ 스텝N 노드 + 종료
    ↓
graph.ainvoke() 실행
    ├─ 스텝1 실행 (상태 업데이트)
    ├─ 조건부 라우팅 (continue/stop)
    ├─ 스텝2 실행 (변수 전달)
    └─ 최종 상태 반환
    ↓
결과 수집 및 저장
```

### **LangGraph의 실제 장점 (이미 누리고 있는 것)**

```
✅ 복잡한 워크플로우 자동 관리
   → 우리는 스텝만 정의, LangGraph가 실행 흐름 관리

✅ 상태 기반 로직
   → 각 스텝 후 자동으로 상태 업데이트
   → 데이터 손실 없음

✅ 조건부 분기 처리
   → if/else 로직을 선언적으로 정의
   → 유지보수 쉬움

✅ 비동기 실행 + 체크포인트
   → 대규모 워크플로우도 안정적 실행
   → 중단/재개 가능

✅ 디버깅 용이
   → LangGraph는 상태 변화를 기록
   → 각 스텝의 입출력 추적 가능
```

---

## 3️⃣ **RAG (Retrieval-Augmented Generation)**

### **현재 RAG 아키텍처**

```
사용자 쿼리 입력
    ↓
[Step 1] 쿼리 분해 (Query Decomposition)
    ↓
[Step 2] 도메인별 검색 (Domain-specific Search)
    ├─ collection_naver 검색
    ├─ collection_weather 검색
    ├─ collection_kakao 검색
    ├─ collection_google 검색
    └─ collection_common 검색
    ↓
[Step 3] 결과 융합 (Result Fusion)
    ├─ 중복 제거
    ├─ 유사도순 정렬
    └─ 도메인 우선순위 적용
    ↓
[Step 4] 전체 컨텍스트 구성 (Context Building)
    ↓
[Step 5] LLM 프롬프트 생성 (Prompt Generation)
    ↓
LLM 생성 (워크플로우 JSON)
```

### **RAG 구현 상세**

```python
class RAGService:
    def __init__(self):
        self.chroma_client = chromadb.PersistentClient()
        self.embedding_fn = OpenAIEmbeddingFunction()
    
    # 도메인별 컬렉션 관리
    DOMAINS = ["naver", "weather", "kakao", "google", "common"]
    
    async def search_with_domain_separation(
        self,
        query: str,
        target_domain: str = None,
        limit: int = 5
    ) -> List[Dict]:
        """
        도메인별 분리 검색 전략:
        
        1. target_domain 지정 시:
           - 해당 도메인 + common 검색 (도메인 우선)
        
        2. target_domain 미지정 시:
           - 모든 도메인 검색 (유사도순)
        """
        
        if target_domain:
            # 특정 도메인 + common
            specific_collection = self._get_collection(target_domain)
            common_collection = self._get_collection("common")
            
            specific_results = await specific_collection.query(
                query_texts=[query],
                n_results=limit
            )
            common_results = await common_collection.query(
                query_texts=[query],
                n_results=limit
            )
            
            # 병합 (도메인 우선)
            results = self._merge_results(
                specific_results,
                common_results,
                primary_domain=target_domain
            )
        else:
            # 모든 도메인 검색
            all_results = []
            for domain in self.DOMAINS:
                collection = self._get_collection(domain)
                results = await collection.query(
                    query_texts=[query],
                    n_results=limit
                )
                all_results.extend(results)
            
            # 유사도순 정렬
            results = sorted(
                all_results,
                key=lambda x: x["similarity_score"],
                reverse=True
            )[:limit]
        
        return results
    
    async def build_context_for_workflow_generation(
        self,
        query: str,
        max_tokens: int = 30000
    ) -> str:
        """
        워크플로우 생성을 위한 컨텍스트 구축
        """
        
        # 1. 쿼리 분해
        subqueries = await self._decompose_query(query)
        
        # 2. 각 서브쿼리별 검색
        all_documents = []
        for subquery in subqueries:
            docs = await self.search_with_domain_separation(subquery)
            all_documents.extend(docs)
        
        # 3. 중복 제거
        unique_docs = self._deduplicate(all_documents)
        
        # 4. 컨텍스트 구성 (토큰 제한)
        context = self._build_context_within_token_limit(
            unique_docs,
            max_tokens
        )
        
        return context
```

### **RAG의 역할**

```
RAG를 통해 얻는 것:
✅ 최신 정보 (문서 기반)
✅ 정확한 정보 (소스 명시)
✅ 할루시네이션 감소
✅ 도메인 특화 지식

프로젝트에서:
→ 워크플로우 생성 시 필요한 모든 정보 제공
→ 도메인별 특화 문서 우선 제시
→ 공통 기술 문서는 항상 포함
```

---

## 4️⃣ **MCP (Model Context Protocol) - 추후 도입**

### **MCP란?**

```
MCP는 LLM과 외부 도구/데이터소스를 연결하는 표준 프로토콜입니다.

장점:
✅ 표준화된 도구 연동
✅ 플러그인 생태계
✅ 보안 (권한 관리)
✅ 확장성 (새로운 도구 쉽게 추가)
```

### **프로젝트에서의 미래 활용**

```python
# MCP를 통해 연동할 도구들
MCP_TOOLS = {
    "naver": {
        "api_endpoint": "https://api.naver.com",
        "tools": ["search", "news", "blog"],
        "permissions": ["read"]
    },
    "weather": {
        "api_endpoint": "https://api.kma.go.kr",
        "tools": ["forecast", "data"],
        "permissions": ["read"]
    },
    "database": {
        "endpoint": "postgresql://...",
        "tools": ["query", "insert", "update"],
        "permissions": ["read", "write"]
    },
    "code_executor": {
        "endpoint": "http://localhost:9000",
        "tools": ["execute", "validate"],
        "permissions": ["execute"]
    }
}

# MCP 클라이언트 구현 (추후)
class MCPClient:
    async def call_tool(
        self,
        tool_name: str,
        args: dict
    ):
        """
        "search_naver_news" 호출 시:
        1. MCP 서버에 요청
        2. 권한 확인
        3. 도구 실행
        4. 결과 반환
        """
        pass
```

### **MCP 도입 시 이점**

```
현재 (직접 API 호출):
├─ 각 서비스별 따로 구현
├─ 보안 관리 복잡
└─ 새로운 서비스 추가 어려움

MCP 도입 후:
├─ 표준 프로토콜로 통일
├─ 중앙 권한 관리
└─ 플러그인처럼 추가 가능
```

---

## 5️⃣ **Memory / Meta Memory - 상태 관리**

### **Memory 구조**

```
┌────────────────────────────────────┐
│      Session Memory (단기)         │
│  현재 대화 컨텍스트                │
│  - 현재 워크플로우                 │
│  - 사용자 입력 기록               │
│  - 최근 생성 결과                 │
└────────────────────────────────────┘
             ↓
┌────────────────────────────────────┐
│     Persistent Memory (장기)       │
│  데이터베이스에 저장              │
│  - 사용자 프로필                  │
│  - 워크플로우 이력                │
│  - 선호도                         │
└────────────────────────────────────┘
             ↓
┌────────────────────────────────────┐
│     Meta Memory (메타 정보)        │
│  시스템 메타데이터                │
│  - 사용 패턴                      │
│  - 성능 지표                      │
│  - 학습 데이터                    │
└────────────────────────────────────┘
```

### **구현 예시**

```python
class MemoryManager:
    def __init__(self):
        self.session_memory = {}  # 단기 메모리
        self.db = PostgreSQL()    # 장기 메모리
        self.meta_store = Redis() # 메타 메모리
    
    # 1. Session Memory (단기)
    class SessionMemory:
        def __init__(self, session_id: str):
            self.session_id = session_id
            self.conversation = []
            self.current_workflow = None
            self.context = {}
        
        async def add_turn(self, user_input: str, ai_response: str):
            """대화 턴 추가"""
            self.conversation.append({
                "user": user_input,
                "ai": ai_response,
                "timestamp": datetime.now()
            })
        
        async def get_context(self, max_turns: int = 5):
            """최근 컨텍스트 반환"""
            return self.conversation[-max_turns:]
    
    # 2. Persistent Memory (장기)
    class PersistentMemory:
        async def save_workflow(self, user_id: str, workflow: dict):
            """워크플로우 저장"""
            await db.insert(
                "user_workflows",
                {
                    "user_id": user_id,
                    "workflow": workflow,
                    "created_at": datetime.now()
                }
            )
        
        async def get_user_preferences(self, user_id: str):
            """사용자 선호도 반환"""
            return await db.query(
                "SELECT preferences FROM users WHERE id = ?",
                [user_id]
            )
    
    # 3. Meta Memory (메타)
    class MetaMemory:
        async def record_query_pattern(self, user_id: str, query: str):
            """쿼리 패턴 기록"""
            # 사용 통계 수집
            await redis.incr(f"query_pattern:{user_id}:{query_type}")
        
        async def record_performance(self, workflow_id: str, metrics: dict):
            """성능 메트릭 기록"""
            await redis.set(
                f"performance:{workflow_id}",
                json.dumps(metrics),
                ex=86400  # 1일 TTL
            )
        
        async def get_trending_workflows(self, limit: int = 10):
            """인기 워크플로우 반환"""
            return await redis.zrange(
                "trending_workflows",
                0,
                limit - 1,
                withscores=True
            )
```

### **Memory 활용 사례**

```python
# 사용 사례 1: 사용자 맞춤형 추천
async def recommend_workflows(user_id: str):
    # Meta Memory: 사용자 쿼리 패턴 분석
    patterns = await meta_memory.get_user_patterns(user_id)
    
    # Persistent Memory: 사용자 선호도
    preferences = await persistent_memory.get_user_preferences(user_id)
    
    # Session Memory: 현재 컨텍스트
    recent_queries = await session_memory.get_context()
    
    # 추천 생성
    recommendations = ai.recommend(
        patterns,
        preferences,
        recent_queries
    )
    return recommendations

# 사용 사례 2: 오류 예방 (패턴 학습)
async def predict_user_intent(user_id: str, query: str):
    # Meta Memory: 과거 실패 패턴 학습
    failure_patterns = await meta_memory.get_failure_patterns(user_id)
    
    # 사용자의 쿼리가 실패 패턴과 유사한지 체크
    if query.matches_failure_pattern(failure_patterns):
        # 사전에 경고 제시
        return await suggest_alternatives(query)
    
    return await normal_processing(query)
```

---

## 🔄 **통합 플로우**

```
사용자 쿼리
    ↓
[Session Memory] 대화 히스토리 추가
    ↓
[LLM] 의도 이해
    ↓
[RAG] 관련 문서 검색
    ↓
[LangGraph] 멀티-스텝 에이전트 실행
    ├─ Plan (계획 수립)
    ├─ Generate (생성)
    ├─ Validate (검증)
    └─ Refine (정제)
    ↓
[MCP] 외부 도구 호출 (추후)
    ↓
[Persistent Memory] 결과 저장
    ↓
[Meta Memory] 성능 기록
    ↓
최종 워크플로우 반환
```

---

## 📊 **기술 성숙도 로드맵**

```
현재 (Phase 1) ✅
├─ ✅ LLM 기본 통합
├─ ✅ RAG 도메인 분리
├─ ✅ Session Memory
└─ ✅ LangGraph 완전 적용 (NEW!)
   ├─ StateGraph 구현
   ├─ 조건부 라우팅
   ├─ 상태 추적
   └─ MemorySaver 체크포인트

근시간 (3개월, Phase 2) 🚀
├─ ✅ 고급 Memory 시스템 (지속 학습)
├─ ✅ 다중 모델 지원
├─ ✅ LangGraph 고도화
│  ├─ 병렬 스텝 실행
│  ├─ 동적 라우팅
│  └─ 스텝 재시도 로직
└─ ⏳ MCP 프로토타입

중기 (6개월, Phase 3) 🎯
├─ ✅ MCP 본격 도입
├─ ✅ 도구 생태계
├─ ✅ LangGraph 에이전트 루프
└─ ⏳ 자가학습 시스템

장기 (1년, Phase 4) 🌟
├─ ✅ 완전 자동화 에이전트
├─ ✅ 지속적 학습
├─ ✅ 예측 기능
└─ ✅ 자기 최적화
```

---

## 💡 **선택 기준**

### **왜 이 고급 기술들인가?**

```
LLM: 
✅ 자연어 이해 및 생성
✅ 멀티-태스크 가능

LangGraph:
✅ 복잡한 워크플로우 관리
✅ 조건부 분기 처리

RAG:
✅ 정확한 정보 제공
✅ 할루시네이션 감소

MCP:
✅ 표준화된 도구 연동
✅ 플러그인 생태계

Memory:
✅ 사용자 맞춤화
✅ 성능 최적화
```

---

**이 고급 기술 스택으로 진정한 AI-Native 시스템을 구축합니다!** 🚀
