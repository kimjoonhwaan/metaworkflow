# LangGraph 워크플로우 실행 메커니즘

## 🔄 전체 실행 흐름

```
사용자 실행 요청
    ↓
WorkflowRunner.execute_workflow()
    ↓
WorkflowEngine.run_workflow()
    ↓
LangGraph StateGraph 생성 및 실행
    ↓
각 스텝을 노드로 실행
    ↓
상태 업데이트 및 다음 스텝으로 전환
    ↓
완료 또는 중단
```

---

## 1️⃣ 워크플로우 실행 시작

### `WorkflowRunner.execute_workflow()` (src/runners/workflow_runner.py)

```python
async def execute_workflow(workflow_id, input_data):
    # 1. 워크플로우 및 스텝 로드
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    steps = db.query(WorkflowStep).filter(...).order_by(order).all()
    
    # 2. 실행 레코드 생성
    execution = WorkflowExecution(
        workflow_id=workflow_id,
        status=ExecutionStatus.RUNNING,
        started_at=datetime.utcnow()
    )
    
    # 3. 각 스텝의 실행 레코드 생성
    step_executions = {}
    for step in steps:
        step_exec = StepExecution(
            workflow_execution_id=execution.id,
            step_id=step.id,
            status=ExecutionStatus.PENDING
        )
        step_executions[step.id] = step_exec
    
    # 4. 콜백 함수 정의 (스텝 완료 시 DB 업데이트)
    async def on_step_complete(step_id, status, result, duration):
        step_exec = step_executions[step_id]
        step_exec.status = status
        step_exec.output_data = result
        step_exec.duration_seconds = duration
        db.commit()
    
    # 5. 워크플로우 엔진으로 실행
    final_state = await engine.run_workflow(
        workflow_id=workflow_id,
        execution_id=execution.id,
        workflow_steps=steps,
        initial_variables=initial_variables,
        on_step_complete=on_step_complete
    )
    
    # 6. 최종 결과 저장
    execution.status = determine_final_status(final_state)
    execution.completed_at = datetime.utcnow()
    db.commit()
```

---

## 2️⃣ LangGraph StateGraph 생성

### `WorkflowEngine.create_graph()` (src/engines/workflow_engine.py)

```python
def create_graph(workflow_steps, on_step_complete):
    # 1. LangGraph StateGraph 초기화
    graph = StateGraph(WorkflowState)
    
    # 2. 각 스텝을 노드로 추가
    for i, step in enumerate(sorted_steps):
        node_name = f"step_{step.order}_{step.id}"
        
        # 노드 함수 생성 (클로저)
        async def step_node(state: WorkflowState, step=step, step_idx=i):
            return await self._execute_step_node(
                state, step, step_idx, on_step_complete
            )
        
        graph.add_node(node_name, step_node)
    
    # 3. 엣지 추가 (스텝 간 연결)
    for i, step in enumerate(sorted_steps):
        current_node = f"step_{step.order}_{step.id}"
        
        if i == 0:
            # 첫 번째 스텝을 진입점으로 설정
            graph.set_entry_point(current_node)
        
        if i < len(sorted_steps) - 1:
            next_step = sorted_steps[i + 1]
            next_node = f"step_{next_step.order}_{next_step.id}"
            
            # 조건부 엣지 추가
            graph.add_conditional_edges(
                current_node,
                lambda state: self._should_continue(state),
                {
                    "continue": next_node,      # 정상 → 다음 스텝
                    "stop": END,                # 실패 → 종료
                    "wait_approval": END,       # 승인 대기 → 종료
                }
            )
        else:
            # 마지막 스텝은 END로
            graph.add_edge(current_node, END)
    
    # 4. 메모리를 포함하여 컴파일
    return graph.compile(checkpointer=self.memory)
```

### 📊 그래프 구조 예시

```
[ENTRY]
   ↓
[Step 0: Fetch Data]
   ↓
 조건 체크 (should_continue?)
   ├─ continue → [Step 1: Process Data]
   ├─ stop → [END]
   └─ wait_approval → [END]
              ↓
        조건 체크
          ├─ continue → [Step 2: Save Data]
          ├─ stop → [END]
          └─ wait_approval → [END]
                     ↓
                   [END]
```

---

## 3️⃣ 워크플로우 상태 (WorkflowState)

### 상태 구조 (src/engines/workflow_state.py)

```python
class WorkflowState(TypedDict):
    # 실행 정보
    workflow_id: str
    execution_id: str
    
    # 진행 상태
    current_step: int                    # 현재 스텝 번호 (0부터 시작)
    total_steps: int                     # 전체 스텝 수
    
    # 각 스텝의 상태
    step_statuses: Dict[str, StepStatus]  # {"step_id": "SUCCESS|FAILED|..."}
    
    # 데이터 저장소
    variables: Dict[str, Any]            # 글로벌 워크플로우 변수
    step_outputs: Dict[str, Any]         # {"step_id": output_data}
    
    # 에러 추적
    errors: List[Dict[str, Any]]         # 발생한 에러 목록
    
    # 제어 플래그
    should_stop: bool                    # True면 즉시 중단
    waiting_approval: bool               # 승인 대기 중
    approval_step_id: Optional[str]      # 승인 대기 스텝 ID
    
    # 로그
    logs: List[str]                      # 실행 로그
```

### 상태 초기화

```python
initial_state: WorkflowState = {
    "workflow_id": "abc-123",
    "execution_id": "exec-456",
    "current_step": 0,
    "total_steps": 3,
    "step_statuses": {
        "step-1": StepStatus.PENDING,
        "step-2": StepStatus.PENDING,
        "step-3": StepStatus.PENDING
    },
    "variables": {"user_input": "hello"},  # 초기 변수
    "step_outputs": {},
    "errors": [],
    "should_stop": False,
    "waiting_approval": False,
    "approval_step_id": None,
    "logs": ["[2025-10-09T10:00:00] Workflow started"]
}
```

---

## 4️⃣ 각 스텝 실행 (노드 함수)

### `_execute_step_node()` (src/engines/workflow_engine.py)

```python
async def _execute_step_node(state, step, step_idx, on_step_complete):
    step_id = step.id
    
    # 1. 상태 업데이트: RUNNING
    state["step_statuses"][step_id] = StepStatus.RUNNING
    state["current_step"] = step_idx + 1
    state["logs"].append(f"Starting step: {step.name}")
    
    # 2. 조건 체크 (있으면)
    if step.condition:
        condition_met = await self._evaluate_condition(step.condition, state["variables"])
        if not condition_met:
            # 조건 미충족 → SKIPPED
            state["step_statuses"][step_id] = StepStatus.SKIPPED
            return state
    
    # 3. 입력 변수 준비
    input_vars = self._prepare_step_input(step, state)
    # input_vars = {
    #     "user_input": "hello",          # 초기 변수
    #     "step-1-output": {...},          # 이전 스텝 출력
    #     "mapped_var": "specific_value"   # input_mapping 결과
    # }
    
    logger.info(f"Step '{step.name}' input variables: {list(input_vars.keys())}")
    
    # 4. 스텝 실행
    try:
        result = await self.step_executor.execute_step(
            step_type=step.step_type.value,
            step_config=step.config,
            variables=input_vars,
            code=step.code
        )
        
        # 5. 승인 필요 체크
        if result.get("requires_approval"):
            state["step_statuses"][step_id] = StepStatus.WAITING_APPROVAL
            state["waiting_approval"] = True
            state["approval_step_id"] = step_id
            return state
        
        # 6. 출력 처리
        output_data = result.get("output", {})
        state["step_outputs"][step_id] = output_data
        
        # 7. 변수 매핑 (output_mapping 적용)
        if step.output_mapping:
            for var_name, output_key in step.output_mapping.items():
                if output_key == "output":
                    state["variables"][var_name] = output_data
                elif isinstance(output_data, dict) and output_key in output_data:
                    state["variables"][var_name] = output_data[output_key]
                else:
                    state["variables"][var_name] = output_data
        
        # 8. 성공 표시
        state["step_statuses"][step_id] = StepStatus.SUCCESS
        
        # 9. 콜백 호출 (DB 업데이트)
        await on_step_complete(step_id, ExecutionStatus.SUCCESS, result, duration)
    
    except Exception as e:
        # 10. 실패 처리
        state["step_statuses"][step_id] = StepStatus.FAILED
        state["errors"].append({
            "step_id": step_id,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        })
        state["should_stop"] = True  # 즉시 중단!
        
        await on_step_complete(step_id, ExecutionStatus.FAILED, {"error": str(e)}, 0)
    
    return state  # 업데이트된 상태 반환
```

---

## 5️⃣ 조건부 라우팅

### `_should_continue()` (src/engines/workflow_engine.py)

```python
def _should_continue(state: WorkflowState) -> str:
    """다음 스텝으로 진행할지 결정"""
    
    if state["should_stop"]:
        # 에러 발생 → 즉시 중단
        return "stop"
    
    if state["waiting_approval"]:
        # 승인 대기 → 대기 상태로 종료
        return "wait_approval"
    
    # 정상 → 다음 스텝 계속
    return "continue"
```

### 라우팅 흐름

```
Step 1 실행 완료
    ↓
_should_continue(state) 호출
    ↓
state 검사:
    - should_stop == True? → "stop" → [END]
    - waiting_approval == True? → "wait_approval" → [END]
    - 정상? → "continue" → [Step 2]
```

---

## 6️⃣ 변수 전달 메커니즘

### 입력 변수 준비 (`_prepare_step_input`)

```python
def _prepare_step_input(step, state):
    # 1. 모든 현재 변수 복사
    input_vars = state["variables"].copy()
    # {
    #     "user_input": "hello",
    #     "api_key": "sk-...",
    # }
    
    # 2. 모든 이전 스텝 출력 추가
    input_vars.update(state["step_outputs"])
    # {
    #     "user_input": "hello",
    #     "api_key": "sk-...",
    #     "step-1-id": {"data": [...]},     # Step 1 출력
    #     "step-2-id": {"result": "..."}    # Step 2 출력
    # }
    
    # 3. input_mapping 적용 (특정 매핑)
    if step.input_mapping:
        for step_var, workflow_var in step.input_mapping.items():
            if workflow_var in state["variables"]:
                input_vars[step_var] = state["variables"][workflow_var]
            elif workflow_var in state["step_outputs"]:
                input_vars[step_var] = state["step_outputs"][workflow_var]
    
    return input_vars
```

### 출력 변수 매핑

```python
# 스텝 실행 결과
result = {
    "output": {
        "news_data": [...],
        "count": 3
    }
}

# output_mapping 적용
if step.output_mapping:
    # {"news_data": "news_data"}
    for var_name, output_key in step.output_mapping.items():
        if output_key == "news_data":
            state["variables"]["news_data"] = output["news_data"]

# 결과:
state["variables"] = {
    "news_data": [...]  # 다음 스텝에서 사용 가능!
}
```

---

## 7️⃣ 실제 실행 예시

### 예시: 3단계 뉴스 수집 워크플로우

```python
# 워크플로우 정의
steps = [
    {
        "order": 0,
        "name": "Fetch News",
        "step_type": "PYTHON_SCRIPT",
        "output_mapping": {"news_data": "news_data"}
    },
    {
        "order": 1,
        "name": "Format News",
        "step_type": "PYTHON_SCRIPT",
        "input_mapping": {"input_news": "news_data"},
        "output_mapping": {"formatted_text": "formatted_text"}
    },
    {
        "order": 2,
        "name": "Save to File",
        "step_type": "PYTHON_SCRIPT",
        "input_mapping": {"text": "formatted_text"}
    }
]
```

### LangGraph 그래프 구조

```
              [ENTRY]
                 ↓
      [step_0_fetch-news-id]
                 ↓
         should_continue?
        /       |        \
    continue   stop   wait_approval
       ↓        ↓          ↓
   [step_1] [END]      [END]
       ↓
should_continue?
       ↓
   [step_2]
       ↓
     [END]
```

### 실행 과정 (타임라인)

**T=0: 초기 상태**
```python
state = {
    "current_step": 0,
    "total_steps": 3,
    "step_statuses": {
        "step-0-id": "PENDING",
        "step-1-id": "PENDING",
        "step-2-id": "PENDING"
    },
    "variables": {},
    "step_outputs": {},
    "should_stop": False
}
```

**T=1: Step 0 실행 (Fetch News)**
```python
# 1. 상태 업데이트
state["step_statuses"]["step-0-id"] = "RUNNING"
state["current_step"] = 1

# 2. 입력 준비
input_vars = {}  # 초기 상태, 변수 없음

# 3. 스텝 실행
result = await execute_step(
    step_type="PYTHON_SCRIPT",
    code="#!/usr/bin/env python3\nimport json\n...",
    variables=input_vars
)
# 결과: {"status": "success", "news_data": [...3 items...]}

# 4. 출력 저장
state["step_outputs"]["step-0-id"] = {
    "status": "success",
    "news_data": [...3 items...]
}

# 5. 변수 매핑
state["variables"]["news_data"] = [...3 items...]

# 6. 성공 표시
state["step_statuses"]["step-0-id"] = "SUCCESS"

# 7. 다음 스텝으로
return "continue"
```

**T=2: Step 1 실행 (Format News)**
```python
# 1. 상태 업데이트
state["step_statuses"]["step-1-id"] = "RUNNING"
state["current_step"] = 2

# 2. 입력 준비
input_vars = {
    "news_data": [...3 items...],           # 전역 변수
    "step-0-id": {"news_data": [...]},      # Step 0 출력
    "input_news": [...3 items...]           # input_mapping 적용
}

# 3. 스텝 실행
result = await execute_step(
    step_type="PYTHON_SCRIPT",
    code="format news...",
    variables=input_vars
)
# 결과: {"status": "success", "formatted_text": "Title: ...\n..."}

# 4. 변수 매핑
state["variables"]["formatted_text"] = "Title: ...\n..."

# 5. 성공
state["step_statuses"]["step-1-id"] = "SUCCESS"

return "continue"
```

**T=3: Step 2 실행 (Save to File)**
```python
# 입력 준비
input_vars = {
    "news_data": [...],
    "formatted_text": "Title: ...\n...",
    "step-0-id": {...},
    "step-1-id": {...},
    "text": "Title: ...\n..."  # input_mapping
}

# 실행
result = {"status": "success", "file_path": "news_20251009.txt"}

# 성공
state["step_statuses"]["step-2-id"] = "SUCCESS"

# 마지막 스텝이므로 END
```

**T=4: 최종 상태**
```python
final_state = {
    "current_step": 3,
    "step_statuses": {
        "step-0-id": "SUCCESS",
        "step-1-id": "SUCCESS",
        "step-2-id": "SUCCESS"
    },
    "variables": {
        "news_data": [...],
        "formatted_text": "...",
    },
    "step_outputs": {
        "step-0-id": {...},
        "step-1-id": {...},
        "step-2-id": {...}
    },
    "errors": [],
    "should_stop": False
}
```

---

## 8️⃣ 에러 발생 시 동작

### 시나리오: Step 1에서 실패

```python
# T=1: Step 0 성공
state["step_statuses"]["step-0-id"] = "SUCCESS"

# T=2: Step 1 실행 중 에러
try:
    result = await execute_step(...)
except Exception as e:
    # 에러 처리
    state["step_statuses"]["step-1-id"] = "FAILED"
    state["errors"].append({
        "step_id": "step-1-id",
        "error": str(e),
        "timestamp": "2025-10-09T10:00:05"
    })
    state["should_stop"] = True  # ← 중단 플래그 설정
    
    return state

# T=3: 조건 체크
_should_continue(state)
    → state["should_stop"] == True
    → return "stop"
    → LangGraph가 END로 이동

# Step 2는 실행되지 않음!
state["step_statuses"]["step-2-id"] = "PENDING"  # 그대로 유지
```

---

## 9️⃣ 승인 워크플로우

### 시나리오: Step 1에서 승인 대기

```python
# Step 1: APPROVAL 타입
result = await execute_step(step_type="APPROVAL", ...)
# 결과: {"requires_approval": True, "approval_message": "계속하시겠습니까?"}

# 상태 업데이트
state["step_statuses"]["step-1-id"] = "WAITING_APPROVAL"
state["waiting_approval"] = True
state["approval_step_id"] = "step-1-id"

# 조건 체크
_should_continue(state)
    → state["waiting_approval"] == True
    → return "wait_approval"
    → END

# 워크플로우 일시 중지!
# 사용자가 승인/거부 결정할 때까지 대기
```

### 사용자가 승인하면

```python
# WorkflowRunner.approve_execution()
execution.status = ExecutionStatus.SUCCESS
# 또는 거부하면
execution.status = ExecutionStatus.CANCELLED
```

---

## 🔟 LangGraph의 핵심 기능

### 1. **상태 관리**
```python
# LangGraph가 자동으로 상태를 추적
state = graph.invoke(initial_state, config)
# 각 노드 실행 후 상태가 업데이트됨
```

### 2. **메모리 (Checkpointing)**
```python
graph.compile(checkpointer=self.memory)
# execution_id별로 상태 저장
# 중단 후 재개 가능 (미래 기능)
```

### 3. **조건부 라우팅**
```python
graph.add_conditional_edges(
    "step_1",
    routing_function,  # state를 받아 "continue"|"stop" 반환
    {
        "continue": "step_2",
        "stop": END
    }
)
```

### 4. **비동기 실행**
```python
final_state = await graph.ainvoke(initial_state, config)
# 모든 스텝이 async로 실행
# 네트워크 I/O, LLM 호출 등 효율적
```

---

## 📊 실행 흐름 다이어그램

```
┌─────────────────────────────────────────────────────────┐
│                   WorkflowRunner                        │
│  1. DB에서 워크플로우/스텝 로드                           │
│  2. 실행 레코드 생성                                     │
│  3. 초기 변수 준비                                       │
└──────────────────┬──────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────┐
│                 WorkflowEngine                          │
│  1. LangGraph StateGraph 생성                           │
│  2. 스텝을 노드로 추가                                   │
│  3. 조건부 엣지 추가                                     │
│  4. 그래프 컴파일 (메모리 포함)                          │
└──────────────────┬──────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────┐
│              LangGraph 실행 (graph.ainvoke)             │
│                                                         │
│  [ENTRY] → [Step 0 Node]                               │
│               ↓                                         │
│           상태 업데이트                                  │
│               ↓                                         │
│        입력 변수 준비                                    │
│               ↓                                         │
│        StepExecutor 호출                                │
│               ↓                                         │
│        출력 변수 매핑                                    │
│               ↓                                         │
│      should_continue? ──→ "continue"                    │
│               ↓                                         │
│         [Step 1 Node]                                   │
│               ↓                                         │
│             ...                                         │
│               ↓                                         │
│            [END]                                        │
└─────────────────┬───────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────────┐
│              최종 상태 반환                              │
│  - step_statuses: {"step-0": "SUCCESS", ...}           │
│  - variables: {...}                                    │
│  - step_outputs: {...}                                 │
│  - errors: [...]                                       │
└──────────────────┬──────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────┐
│            WorkflowRunner                               │
│  1. 최종 상태를 DB에 저장                                │
│  2. 실행 상태 결정 (SUCCESS/FAILED/WAITING_APPROVAL)    │
│  3. 완료 시간 및 duration 계산                           │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 LangGraph의 장점

### 1. **상태 기반 실행**
- 각 스텝이 독립적으로 실행
- 상태를 명시적으로 관리
- 디버깅이 쉬움

### 2. **조건부 분기**
```python
if data > threshold:
    next_step = "alert"
else:
    next_step = "log_only"
```

### 3. **에러 복구**
- 실패한 스텝부터 재실행 가능
- 상태가 저장되어 있어 재개 가능

### 4. **승인 워크플로우**
- 중요한 작업 전 일시 중지
- 사용자 승인 후 재개

### 5. **추적 가능성**
- 각 스텝의 입력/출력 기록
- 상태 변화 추적
- LangSmith로 시각화

---

## 🔍 디버깅 방법

### 로그 확인

```python
# 로그에서 볼 수 있는 정보:

2025-10-09 22:00:00 - workflow_engine - INFO - Executing step 1/3: Fetch_News
2025-10-09 22:00:00 - workflow_engine - INFO - Step 'Fetch_News' input variables: ['user_input']
2025-10-09 22:00:01 - workflow_engine - INFO - Step 'Fetch_News' output type: <class 'dict'>, keys: ['status', 'news_data']
2025-10-09 22:00:01 - workflow_engine - INFO - Mapped output['news_data'] to variable 'news_data'
2025-10-09 22:00:01 - workflow_engine - INFO - Step completed successfully (Duration: 0.63s)

2025-10-09 22:00:01 - workflow_engine - INFO - Executing step 2/3: Format_News
2025-10-09 22:00:01 - workflow_engine - INFO - Step 'Format_News' input variables: ['user_input', 'news_data', 'step-0-id']
```

### Streamlit UI에서 확인

```
실행 기록 → 상세 로그 → 스텝별 실행 기록
  - Step 0: ✅ SUCCESS (0.63s)
    - 입력: {}
    - 출력: {"news_data": [...]}
  - Step 1: ✅ SUCCESS (0.12s)
    - 입력: {"news_data": [...]}
    - 출력: {"formatted_text": "..."}
  - Step 2: ✅ SUCCESS (0.05s)
    - 입력: {"formatted_text": "..."}
    - 출력: {"file_path": "news.txt"}
```

---

## 💡 핵심 요약

1. **LangGraph는 상태 기반 워크플로우 엔진**
2. **각 스텝 = 노드**, **진행 경로 = 엣지**
3. **상태 (WorkflowState)**가 모든 데이터를 담음
4. **조건부 라우팅**으로 유연한 흐름 제어
5. **메모리**로 중단/재개 가능
6. **비동기**로 효율적 실행

**결과**: 복잡한 워크플로우도 명확하고 추적 가능하게 실행! 🚀

