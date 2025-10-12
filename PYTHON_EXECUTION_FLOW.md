# Python 스크립트 실행 메커니즘

## 🔄 전체 실행 흐름

```
워크플로우 실행 요청
    ↓
WorkflowRunner → WorkflowEngine → StepExecutor
    ↓
임시 Python 파일 생성
    ↓
임시 JSON 파일에 변수 저장
    ↓
subprocess로 Python 실행
    ↓
stdout에서 JSON 파싱
    ↓
결과를 state에 저장
    ↓
다음 스텝으로 전달
```

---

## 1️⃣ 스텝 실행 진입점

### `StepExecutor.execute_step()` (src/engines/step_executor.py:41)

```python
async def execute_step(
    self,
    step_type: str,           # "PYTHON_SCRIPT"
    step_config: Dict,        # {"description": "..."}
    variables: Dict,          # {"news_data": [...], "user_input": "..."}
    code: Optional[str]       # 전체 Python 코드
):
    if step_type == StepType.PYTHON_SCRIPT.value:
        return await self._execute_python_script(step_config, variables, code)
    # ... 다른 타입들
```

**입력:**
- `step_type`: "PYTHON_SCRIPT"
- `variables`: `{"news_data": [...], "prev_step_output": {...}}`
- `code`: 완전한 Python 소스 코드 (문자열)

**출력:**
- `{"success": True, "output": {...}, "logs": "..."}`

---

## 2️⃣ Python 스크립트 실행

### `_execute_python_script()` (src/engines/step_executor.py:148)

```python
async def _execute_python_script(self, config, variables, code):
    logger.info("Executing Python script")
    
    # ═══════════════════════════════════════════════════════
    # STEP 1: 임시 Python 파일 생성
    # ═══════════════════════════════════════════════════════
    with tempfile.NamedTemporaryFile(
        mode='w', 
        suffix='.py', 
        delete=False, 
        encoding='utf-8'
    ) as f:
        f.write(code)  # DB에서 가져온 code 문자열을 파일로 저장
        script_path = f.name
    
    # 예시 경로: C:\Users\user\AppData\Local\Temp\tmpx46axf9r.py
    # 내용:
    # #!/usr/bin/env python3
    # import json
    # import sys
    # def main():
    #     variables = {}
    #     if '--variables-file' in sys.argv:
    #         ...
    
    # ═══════════════════════════════════════════════════════
    # STEP 2: 변수를 JSON 파일로 저장
    # ═══════════════════════════════════════════════════════
    with tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.json',
        delete=False,
        encoding='utf-8'
    ) as f:
        json.dump(variables, f)
        variables_path = f.name
    
    # 예시 경로: C:\Users\user\AppData\Local\Temp\tmpwin6xa96.json
    # 내용:
    # {
    #   "news_data": [
    #     {"title": "...", "summary": "..."},
    #     {"title": "...", "summary": "..."}
    #   ],
    #   "user_input": "hello",
    #   "step-0-id": {"status": "success"}
    # }
    
    try:
        # ═══════════════════════════════════════════════════════
        # STEP 3: subprocess로 Python 스크립트 실행
        # ═══════════════════════════════════════════════════════
        result = subprocess.run(
            [
                sys.executable,           # python.exe 경로
                script_path,              # 임시 .py 파일 경로
                "--variables-file",       # 인자 이름
                variables_path            # 임시 .json 파일 경로
            ],
            capture_output=True,          # stdout, stderr 캡처
            text=True,                    # 문자열로 반환
            timeout=settings.step_timeout_seconds  # 300초 (5분)
        )
        
        # 실제 실행되는 명령:
        # python.exe C:\...\tmpx46axf9r.py --variables-file C:\...\tmpwin6xa96.json
        
        # ═══════════════════════════════════════════════════════
        # STEP 4: 실행 결과 처리
        # ═══════════════════════════════════════════════════════
        
        # 4-1. stderr 로그 기록 (디버그 출력)
        if result.stderr:
            logger.info(f"Script stderr: {result.stderr}")
        # 예시 stderr:
        # "Variables: ['news_data', 'user_input']"
        # "Processing 3 news items"
        # "Writing to file: news_20251009.txt"
        
        # 4-2. 종료 코드 체크
        if result.returncode != 0:
            raise RuntimeError(f"Script failed with return code {result.returncode}: {result.stderr}")
        
        # 4-3. stdout에서 JSON 파싱
        try:
            output_data = json.loads(result.stdout.strip())
        except json.JSONDecodeError:
            # JSON이 아니면 텍스트로 처리
            output_data = {"result": result.stdout.strip()}
        
        # 예시 stdout (Python 스크립트의 print(json.dumps(...)) 결과):
        # {"status": "success", "news_data": [...], "count": 3}
        
        logger.info(f"Script executed successfully")
        
        # ═══════════════════════════════════════════════════════
        # STEP 5: 결과 반환
        # ═══════════════════════════════════════════════════════
        return {
            "success": True,
            "output": output_data,        # 파싱된 JSON
            "logs": result.stderr,        # 디버그 로그
        }
    
    finally:
        # ═══════════════════════════════════════════════════════
        # STEP 6: 임시 파일 삭제
        # ═══════════════════════════════════════════════════════
        os.unlink(script_path)      # .py 파일 삭제
        os.unlink(variables_path)   # .json 파일 삭제
```

---

## 3️⃣ Python 스크립트 내부 동작

### 생성된 Python 스크립트 (예시)

```python
#!/usr/bin/env python3
import json
import sys

def main():
    # ═══════════════════════════════════════════════════════
    # 1. 변수 파일 읽기
    # ═══════════════════════════════════════════════════════
    variables = {}
    if '--variables-file' in sys.argv:
        idx = sys.argv.index('--variables-file')
        if idx + 1 < len(sys.argv):
            # 임시 JSON 파일 읽기
            with open(sys.argv[idx + 1], 'r', encoding='utf-8') as f:
                variables = json.load(f)
    
    # 이 시점에서 variables는:
    # {
    #   "news_data": [...],
    #   "user_input": "hello",
    #   "step-0-id": {...}
    # }
    
    # ═══════════════════════════════════════════════════════
    # 2. 디버그 로그 (stderr로 출력)
    # ═══════════════════════════════════════════════════════
    print(f"Variables: {list(variables.keys())}", file=sys.stderr)
    # stderr → StepExecutor가 로그로 기록
    
    try:
        # ═══════════════════════════════════════════════════════
        # 3. 비즈니스 로직 실행
        # ═══════════════════════════════════════════════════════
        news_data = variables.get('news_data', [])
        
        # f-string 안전 사용 (변수 먼저 추출!)
        for item in news_data:
            title = item.get('title', 'N/A')
            summary = item.get('summary', 'N/A')
            print(f"Processing: {title}", file=sys.stderr)
        
        # 파일 저장
        filename = f"news_{datetime.now().strftime('%Y%m%d')}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            for item in news_data:
                title = item.get('title', '')
                summary = item.get('summary', '')
                f.write(f"Title: {title}\n")
                f.write(f"Summary: {summary}\n\n")
        
        # ═══════════════════════════════════════════════════════
        # 4. 구조화된 JSON 출력 (stdout으로!)
        # ═══════════════════════════════════════════════════════
        result = {
            "status": "success",
            "file_path": filename,
            "count": len(news_data)
        }
        print(json.dumps(result))
        # stdout → StepExecutor가 파싱
        
    except Exception as e:
        # ═══════════════════════════════════════════════════════
        # 5. 에러 처리
        # ═══════════════════════════════════════════════════════
        print(f"Error: {e}", file=sys.stderr)
        print(json.dumps({"status": "error", "error": str(e)}))
        sys.exit(1)  # 종료 코드 1 = 실패

if __name__ == "__main__":
    main()
```

---

## 4️⃣ 결과 전달 흐름

### 완전한 데이터 흐름

```python
# ═══════════════════════════════════════════════════════════════
# 시작: WorkflowEngine._execute_step_node()
# ═══════════════════════════════════════════════════════════════

# 1. 입력 준비
input_vars = {
    "news_data": [...],      # 이전 스텝에서 온 데이터
    "user_input": "hello"
}

# 2. StepExecutor 호출
result = await self.step_executor.execute_step(
    step_type="PYTHON_SCRIPT",
    step_config={...},
    variables=input_vars,
    code="#!/usr/bin/env python3\nimport json\n..."
)

# StepExecutor 내부에서:
# - 임시 .py 파일 생성 (code 저장)
# - 임시 .json 파일 생성 (input_vars 저장)
# - subprocess.run([python, script.py, --variables-file, vars.json])
# - stdout 캡처 및 JSON 파싱

# 3. 결과 반환
# result = {
#     "success": True,
#     "output": {
#         "status": "success",
#         "file_path": "news_20251009.txt",
#         "count": 3
#     },
#     "logs": "Variables: ['news_data']\nProcessing: Title 1\n..."
# }

# 4. 출력 데이터 추출
output_data = result.get("output", {})
# output_data = {
#     "status": "success",
#     "file_path": "news_20251009.txt",
#     "count": 3
# }

# 5. 스텝 출력 저장
state["step_outputs"][step_id] = output_data

# 6. 변수 매핑 (output_mapping 적용)
if step.output_mapping:
    # output_mapping = {"file_path": "file_path"}
    for var_name, output_key in step.output_mapping.items():
        if output_key in output_data:
            state["variables"][var_name] = output_data[output_key]

# 결과:
# state["variables"]["file_path"] = "news_20251009.txt"

# 7. 다음 스텝에서 사용 가능!
# next_step_input = state["variables"]
# → {"news_data": [...], "file_path": "news_20251009.txt"}
```

---

## 5️⃣ 구체적인 예시 (3단계 워크플로우)

### 워크플로우 정의

```json
{
  "steps": [
    {
      "order": 0,
      "name": "Fetch_Data",
      "step_type": "PYTHON_SCRIPT",
      "code": "... fetch code ...",
      "output_mapping": {"fetched_data": "data"}
    },
    {
      "order": 1,
      "name": "Process_Data",
      "step_type": "PYTHON_SCRIPT",
      "code": "... process code ...",
      "input_mapping": {"input": "fetched_data"},
      "output_mapping": {"processed_data": "result"}
    },
    {
      "order": 2,
      "name": "Save_Data",
      "step_type": "PYTHON_SCRIPT",
      "code": "... save code ...",
      "input_mapping": {"data_to_save": "processed_data"}
    }
  ]
}
```

### Step 0 실행 (Fetch_Data)

**1. 입력 준비**
```python
input_vars = {}  # 첫 스텝이므로 빈 상태
```

**2. 임시 파일 생성**

`C:\Temp\tmp123abc.py`:
```python
#!/usr/bin/env python3
import json
import sys

def main():
    variables = {}
    if '--variables-file' in sys.argv:
        idx = sys.argv.index('--variables-file')
        with open(sys.argv[idx + 1], 'r', encoding='utf-8') as f:
            variables = json.load(f)
    
    print("Fetching data...", file=sys.stderr)
    
    try:
        # 데이터 가져오기 로직
        data = [{"id": 1}, {"id": 2}, {"id": 3}]
        
        result = {
            "status": "success",
            "data": data,
            "count": len(data)
        }
        print(json.dumps(result))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        print(json.dumps({"status": "error", "error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()
```

`C:\Temp\tmp456def.json`:
```json
{}
```

**3. subprocess 실행**
```bash
python.exe C:\Temp\tmp123abc.py --variables-file C:\Temp\tmp456def.json
```

**4. 실행 중 출력**

*stderr (디버그 로그):*
```
Fetching data...
```

*stdout (결과 JSON):*
```json
{"status": "success", "data": [{"id": 1}, {"id": 2}, {"id": 3}], "count": 3}
```

**5. StepExecutor 결과 처리**
```python
# stdout 파싱
output_data = json.loads(stdout)
# → {"status": "success", "data": [...], "count": 3}

# 반환
return {
    "success": True,
    "output": output_data,
    "logs": "Fetching data...\n"
}
```

**6. WorkflowEngine 변수 매핑**
```python
# output_mapping = {"fetched_data": "data"}
state["variables"]["fetched_data"] = output_data["data"]

# state["variables"] 업데이트:
# {
#   "fetched_data": [{"id": 1}, {"id": 2}, {"id": 3}]
# }
```

**7. 임시 파일 삭제**
```python
os.unlink("C:\Temp\tmp123abc.py")
os.unlink("C:\Temp\tmp456def.json")
```

---

### Step 1 실행 (Process_Data)

**1. 입력 준비**
```python
# 기본 변수
input_vars = state["variables"].copy()
# {
#   "fetched_data": [{"id": 1}, {"id": 2}, {"id": 3}]
# }

# 이전 스텝 출력 추가
input_vars.update(state["step_outputs"])
# {
#   "fetched_data": [{"id": 1}, {"id": 2}, {"id": 3}],
#   "step-0-id": {"status": "success", "data": [...], "count": 3}
# }

# input_mapping 적용: {"input": "fetched_data"}
input_vars["input"] = state["variables"]["fetched_data"]

# 최종 input_vars:
# {
#   "fetched_data": [...],
#   "step-0-id": {...},
#   "input": [{"id": 1}, {"id": 2}, {"id": 3}]  # 매핑된 변수
# }
```

**2. 임시 파일 생성**

`C:\Temp\tmp789ghi.json`:
```json
{
  "fetched_data": [{"id": 1}, {"id": 2}, {"id": 3}],
  "step-0-id": {"status": "success", "data": [...], "count": 3},
  "input": [{"id": 1}, {"id": 2}, {"id": 3}]
}
```

**3. subprocess 실행**
```bash
python.exe C:\Temp\tmp999jkl.py --variables-file C:\Temp\tmp789ghi.json
```

**4. Python 스크립트 내부**
```python
# 변수 파일 읽기
with open('C:\Temp\tmp789ghi.json', 'r', encoding='utf-8') as f:
    variables = json.load(f)

# variables는 이제:
# {
#   "fetched_data": [...],
#   "step-0-id": {...},
#   "input": [{"id": 1}, {"id": 2}, {"id": 3}]
# }

# 비즈니스 로직
input_data = variables.get('input', [])
processed = [{"id": x["id"], "processed": True} for x in input_data]

# JSON 출력
result = {
    "status": "success",
    "result": processed,
    "count": len(processed)
}
print(json.dumps(result))
# stdout: {"status": "success", "result": [...], "count": 3}
```

**5. 결과 처리**
```python
# StepExecutor가 stdout 파싱
output_data = {"status": "success", "result": [...], "count": 3}

# output_mapping = {"processed_data": "result"}
state["variables"]["processed_data"] = output_data["result"]

# state["variables"] 업데이트:
# {
#   "fetched_data": [...],
#   "processed_data": [{"id": 1, "processed": True}, ...]
# }
```

---

### Step 2 실행 (Save_Data)

**1. 입력 준비**
```python
input_vars = {
    "fetched_data": [...],
    "processed_data": [...],
    "step-0-id": {...},
    "step-1-id": {...},
    "data_to_save": [...]  # input_mapping: {"data_to_save": "processed_data"}
}
```

**2. Python 스크립트 실행**
```python
# 변수 파일에서 읽기
variables = json.load(open(variables_file))

# data_to_save 사용
data = variables.get('data_to_save', [])

# 파일 저장
with open('output.json', 'w') as f:
    json.dump(data, f)

# 결과 출력
print(json.dumps({"status": "success", "file": "output.json"}))
```

**3. 최종 결과**
```python
state["step_outputs"]["step-2-id"] = {
    "status": "success",
    "file": "output.json"
}

# 워크플로우 완료!
```

---

## 6️⃣ 실제 파일 시스템 동작

### 실행 중 생성되는 파일들

```
실행 시작
  ↓
임시 디렉토리:
  C:\Users\user\AppData\Local\Temp\
    ├─ tmpABC123.py        ← Step 0 Python 코드
    ├─ tmpDEF456.json      ← Step 0 입력 변수
    ├─ tmpGHI789.py        ← Step 1 Python 코드
    ├─ tmpJKL012.json      ← Step 1 입력 변수
    ├─ tmpMNO345.py        ← Step 2 Python 코드
    └─ tmpPQR678.json      ← Step 2 입력 변수

워크플로우 스크립트 디렉토리:
  C:\dev\cursor\projWorkFlow4\workflow_scripts\
    └─ {workflow_id}\
         ├─ step_0_Fetch_Data.py     ← 참고용 (실행 안 됨!)
         ├─ step_1_Process_Data.py   ← 참고용
         └─ step_2_Save_Data.py      ← 참고용

출력 파일:
  C:\dev\cursor\projWorkFlow4\
    └─ news_20251009.txt   ← 워크플로우가 생성한 실제 파일
```

**중요:**
- `workflow_scripts/` 폴더는 **참고용**일 뿐
- 실제 실행은 **DB의 `WorkflowStep.code` 필드**를 사용
- 매번 **새로운 임시 파일**을 생성하여 실행

---

## 7️⃣ subprocess 실행의 장단점

### 왜 subprocess를 사용하나요?

**장점:**
✅ **격리된 실행**: 메인 프로세스에 영향 없음
✅ **타임아웃**: 무한 루프 방지
✅ **에러 캡처**: 예외를 안전하게 처리
✅ **리소스 제한**: CPU/메모리 제한 가능 (미래)
✅ **외부 패키지**: requirements 설치 후 실행 가능

**단점:**
⚠️ 프로세스 생성 오버헤드 (~100-200ms)
⚠️ 파일 I/O 필요

### 대안이 있나요?

```python
# 대안 1: exec() 사용 (위험!)
exec(code, globals(), locals())
# 문제: 메인 프로세스에 영향, 격리 안 됨

# 대안 2: multiprocessing
from multiprocessing import Process
# 문제: 상태 공유 복잡, Streamlit과 호환성 이슈

# ✅ subprocess가 가장 안전하고 격리됨!
```

---

## 8️⃣ 디버깅 방법

### 임시 파일 확인 (디버깅 시)

임시 파일을 삭제하지 않도록 수정:

```python
# src/engines/step_executor.py
finally:
    # 디버그 모드일 때만 삭제 안 함
    if not settings.debug_mode:
        os.unlink(script_path)
        os.unlink(variables_path)
    else:
        logger.info(f"Debug: Script saved to {script_path}")
        logger.info(f"Debug: Variables saved to {variables_path}")
```

### 수동으로 Python 스크립트 실행

```bash
# 1. workflow_scripts에서 코드 확인
cat workflow_scripts/{workflow_id}/step_0_Fetch_Data.py

# 2. 변수 파일 생성
echo '{"test": "value"}' > test_vars.json

# 3. 직접 실행
python workflow_scripts/{workflow_id}/step_0_Fetch_Data.py --variables-file test_vars.json

# 4. 출력 확인
# stdout: {"status": "success", ...}
```

---

## 9️⃣ 성능 최적화

### 현재 구현

```python
# 각 스텝마다:
- 임시 파일 2개 생성 (.py, .json)
- subprocess 생성
- Python 인터프리터 초기화
- 코드 실행
- 결과 파싱
- 파일 삭제
```

**예상 시간:**
- 파일 생성: ~10ms
- subprocess 시작: ~100-200ms
- 코드 실행: 비즈니스 로직에 따라 (1초~수분)
- 파싱 및 정리: ~10ms

**총 오버헤드: ~120-220ms per step**

### 미래 최적화 방안

```python
# 1. 코드 캐싱
# 같은 코드를 여러 번 실행할 때 컴파일 캐시 사용

# 2. Process Pool
# subprocess를 미리 생성해두고 재사용

# 3. 병렬 실행
# 독립적인 스텝들을 동시에 실행
```

---

## 🔟 요약: 완전한 실행 체인

```
1️⃣ 사용자 클릭 "실행"
    ↓
2️⃣ WorkflowRunner.execute_workflow(workflow_id)
    ↓
3️⃣ DB에서 Workflow + Steps 로드
    ↓
4️⃣ WorkflowEngine.run_workflow(steps, variables)
    ↓
5️⃣ LangGraph StateGraph 생성
    graph.add_node("step_0", step_0_node)
    graph.add_node("step_1", step_1_node)
    graph.add_conditional_edges(...)
    ↓
6️⃣ graph.ainvoke(initial_state)
    ↓
7️⃣ Step 0 노드 실행
    ├─ input_vars 준비
    ├─ StepExecutor.execute_step()
    │   ├─ 임시 .py 파일 생성 (code 저장)
    │   ├─ 임시 .json 파일 생성 (variables 저장)
    │   ├─ subprocess.run([python, script.py, --variables-file, vars.json])
    │   │   ↓
    │   │   Python 프로세스 시작
    │   │   ├─ sys.argv 파싱
    │   │   ├─ variables.json 읽기
    │   │   ├─ 비즈니스 로직 실행
    │   │   ├─ stderr: "Fetching..."
    │   │   └─ stdout: {"status": "success", "data": [...]}
    │   │
    │   ├─ stdout 캡처 및 JSON 파싱
    │   ├─ stderr 로그 기록
    │   └─ 임시 파일 삭제
    │
    ├─ 결과 반환: {"success": True, "output": {...}}
    ├─ state["step_outputs"]["step-0-id"] = {...}
    ├─ output_mapping 적용
    └─ state["variables"]["fetched_data"] = [...]
    ↓
8️⃣ should_continue(state) → "continue"
    ↓
9️⃣ Step 1 노드 실행
    ├─ input_vars = {"fetched_data": [...], ...}
    ├─ 임시 .py/.json 생성
    ├─ subprocess 실행
    ├─ 결과 파싱
    └─ state 업데이트
    ↓
🔟 should_continue(state) → "continue"
    ↓
1️⃣1️⃣ Step 2 노드 실행
    ↓
1️⃣2️⃣ END
    ↓
1️⃣3️⃣ final_state 반환
    ↓
1️⃣4️⃣ WorkflowRunner가 DB 업데이트
    execution.status = "SUCCESS"
    execution.output_data = final_state["step_outputs"]
    execution.completed_at = now()
    ↓
1️⃣5️⃣ 사용자 UI에 "✅ 성공" 표시
```

---

## 💡 핵심 포인트

### 1. **격리된 실행**
- 각 Python 스크립트는 독립된 프로세스
- 메인 애플리케이션에 영향 없음

### 2. **파일 기반 통신**
- 변수: JSON 파일로 전달 (Windows 명령줄 길이 제한 해결)
- 결과: stdout의 JSON으로 반환

### 3. **상태 전파**
```
Step 0 출력 → state.variables → Step 1 입력
                                    ↓
                            Step 1 출력 → state.variables → Step 2 입력
```

### 4. **에러 격리**
```
Step 1 실패 → subprocess 종료 (return code 1)
           → StepExecutor가 예외 발생
           → WorkflowEngine이 캐치
           → state["should_stop"] = True
           → Step 2 실행 안 됨
```

**이것이 시스템이 안전하고 견고한 이유입니다!** 🛡️

