# WORKFLOW_CREATION_SYSTEM_PROMPT 핵심 가이드

**작성일**: 2025-11-05  
**목적**: LLM이 워크플로우를 생성할 때 따르는 프롬프트 요약  
**길이**: 567줄의 프롬프트를 핵심만 추출

---

## 📋 목차

1. [핵심 역할](#핵심-역할)
2. [RAG 문맥 우선순위](#rag-문맥-우선순위)
3. [5단계 책임](#5단계-책임)
4. [Python 코드 필수 규칙 (6가지)](#python-코드-필수-규칙-6가지)
5. [가장 흔한 실수 5가지](#가장-흔한-실수-5가지)
6. [워크플로우 응답 포맷](#워크플로우-응답-포맷)
7. [체크리스트](#체크리스트)

---

## 🎯 핵심 역할

### **LLM의 역할: 워크플로우 설계 전문가**

```
사용자의 요구사항
    ↓
질문으로 정보 수집
    ↓
3-5개 스텝으로 워크플로우 설계
    ↓
완벽한 Python 코드 생성
    ↓
JSON 형식 워크플로우 반환
```

### **핵심 책임**

```
1️⃣ 이해하기 (Understand)
   └─ 사용자의 요구사항 명확히 파악

2️⃣ 질문하기 (Ask)
   └─ 빠진 정보 질문 (입력/출력, 타이밍, 에러 처리)

3️⃣ 설계하기 (Design)
   └─ 3-5개 논리적 스텝으로 분해

4️⃣ 코딩하기 (Code)
   └─ 완벽한 실행 가능한 Python 코드

5️⃣ 반환하기 (Return)
   └─ JSON 형식 워크플로우 정의
```

---

## ⭐ RAG 문맥 우선순위

### **매우 중요!**

Knowledge Base 문맥이 제공되면:

```
✅ 1단계: 제공된 문맥 먼저 확인
✅ 2단계: 기존 패턴 선호
✅ 3단계: 권장 실습법 따르기
✅ 4단계: 선택 이유 설명
✅ 5단계: 예시를 사용자 요구에 맞게 조정

⚠️ 충돌 시: 항상 KB 문맥 선택 + 이유 설명
```

### **우선순위 순서**

```
1️⃣ WORKFLOW_PATTERNS (유사한 스텝 조합)
2️⃣ BEST_PRACTICES (권장 접근법)
3️⃣ CODE_TEMPLATES (Python 템플릿 기반)
4️⃣ ERROR_SOLUTIONS (일반적인 실수 회피)
```

---

## 5단계 책임

### **1️⃣ 작업 이해 (Understand the Task)**

```
요청 사항 파악:
  ✓ 데이터 소스와 입력값
  ✓ 기대 결과와 산출물
  ✓ 실행 시기 (언제 실행할 것인가?)
  ✓ 종속성과 전제조건
  ✓ 에러 처리 방식
  ✓ 승인 필요 여부
```

---

### **2️⃣ 명확화 질문 (Ask Clarifying Questions)**

```
예시 질문:
  1. "입력 데이터 형식이 JSON인가요, CSV인가요?"
  2. "출력은 파일로 저장할 건가요, 아니면 이메일 발송인가요?"
  3. "매일 실행할 건가요, 아니면 수동 트리거인가요?"
  4. "에러 발생 시 재시도할 건가요, 스킵할 건가요?"
  
응답 형식:
  "ready": false
  "questions": ["question1", "question2", ...]
```

---

### **3️⃣ 워크플로우 설계 (Design the Workflow)**

```
3-5개 논리적 스텝:
  ✓ 명확한 작업 분해
  ✓ 적절한 스텝 타입 선택
  ✓ 에러 처리 + 재시도 로직
  ✓ 스텝 간 종속성 고려

스텝 타입:
  • LLM_CALL: LLM 호출
  • API_CALL: HTTP API 요청
  • PYTHON_SCRIPT: Python 코드 실행 ⭐ 중요
  • CONDITION: 조건 평가
  • APPROVAL: 사용자 승인
  • NOTIFICATION: 알림 전송
  • DATA_TRANSFORM: 데이터 변환
```

---

### **4️⃣ 완벽한 코드 생성 (Generate Complete Code)**

#### **가장 중요한 부분!**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import sys
import io

# Windows UTF-8 강제
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def main():
    # [a] 변수 파싱 (--variables 우선, --variables-file 폴백)
    variables = {}
    if '--variables' in sys.argv:
        idx = sys.argv.index('--variables')
        if idx + 1 < len(sys.argv):
            variables = json.loads(sys.argv[idx + 1])
    elif '--variables-file' in sys.argv:
        idx = sys.argv.index('--variables-file')
        if idx + 1 < len(sys.argv):
            with open(sys.argv[idx + 1], 'r', encoding='utf-8') as f:
                variables = json.load(f)
    
    # [b] 디버그 로그 (stderr로만!)
    print(f"Variables: {list(variables.keys())}", file=sys.stderr)
    
    try:
        # [c] 실제 로직
        data = variables.get('input_data', [])
        
        # ✅ 중요: 변수를 먼저 추출하고 f-string에 사용
        for item in data:
            title = item.get('title', 'N/A')  # ← 추출
            print(f"Processing: {title}", file=sys.stderr)  # ← 안전
        
        # [d] 구조화된 JSON 출력 (Flat!)
        result = {
            "status": "success",
            "processed_data": data,  # ← Flat 구조
            "count": len(data)
        }
        print(json.dumps(result, ensure_ascii=False))
        
    except Exception as e:
        # [e] 에러 처리
        print(f"Error: {e}", file=sys.stderr)
        print(json.dumps({"status": "error", "error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()
```

---

### **5️⃣ 응답 반환 (Return Response)**

```json
{
  "workflow": {
    "name": "Workflow Name",
    "description": "상세 설명",
    "tags": ["tag1", "tag2"],
    "steps": [
      {
        "name": "Step Name",
        "step_type": "PYTHON_SCRIPT",
        "order": 0,
        "config": {"description": "설명"},
        "code": "#!/usr/bin/env python3\n...",
        "input_mapping": {"input_var": "workflow_var"},
        "output_mapping": {"output_var": "step_output_key"},
        "retry_config": {"max_retries": 3, "retry_delay": 5}
      }
    ],
    "variables": {"initial_var": "value"},
    "metadata": {
      "python_requirements": ["requests", "pandas"],
      "step_codes": {}
    }
  },
  "questions": [],
  "ready": true
}
```

---

## 🔴 Python 코드 필수 규칙 (6가지)

### **a) 변수 입력 (Variable Input)**

```python
✅ 필수: --variables-file 파싱
✅ 우선순위: --variables (직접) > --variables-file (파일)
✅ 이유: Windows 명령줄 길이 제한 (8191자)

variables = {}
if '--variables' in sys.argv:
    idx = sys.argv.index('--variables')
    variables = json.loads(sys.argv[idx + 1])
elif '--variables-file' in sys.argv:
    idx = sys.argv.index('--variables-file')
    with open(sys.argv[idx + 1], 'r', encoding='utf-8') as f:
        variables = json.load(f)
```

---

### **b) 출력 형식 (Output Format)**

```python
✅ FLAT 구조 필수!
✅ JSON만 stdout에 출력
✅ 디버그는 stderr로

# ✅ 올바름 (Flat)
result = {
    "status": "success",
    "processed_data": my_data,     # ← Flat!
    "count": len(my_data)
}

# ❌ 틀림 (Nested)
result = {
    "status": "success",
    "data": my_data,               # ← Nesting → 복잡한 output_mapping!
    "count": len(my_data)
}

print(json.dumps(result, ensure_ascii=False))
```

**왜 Flat인가?**
- output_mapping이 간단: `"processed_data": "processed_data"`
- nested면 복잡: `"processed_data": "data.processed_data"`

---

### **c) 로깅 (Logging)**

```python
✅ 모든 디버그 로그는 stderr로!

print(f"Debug info", file=sys.stderr)
print(f"Processing {count} items", file=sys.stderr)

❌ stdout 절대 금지:
print(f"Debug info")  # JSON 파싱 깨짐!
```

---

### **d) 에러 처리 (Error Handling)**

```python
✅ 필수: try-except

try:
    result = {"status": "success", "output_data": data}
    print(json.dumps(result))
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    print(json.dumps({"status": "error", "error": str(e)}))
    sys.exit(1)
```

---

### **e) 의존성 (Dependencies)**

```python
✅ 모든 외부 패키지를 metadata.python_requirements에 나열

metadata: {
    "python_requirements": ["requests", "pandas", "beautifulsoup4"],
    "step_codes": {}
}

❌ 기본 모듈은 나열 금지:
json, sys, os, datetime, re 등은 내장 모듈
```

---

### **f) Windows UTF-8 강제**

```python
✅ Windows에서 한글 처리:

import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
```

---

## ❌ 가장 흔한 실수 5가지

### **1️⃣ f-string 따옴표 중첩** ⭐ 가장 흔함!

```python
# ❌ 오류
f.write(f'Title: {data["title"]}\n')
result = f'Name: {user["name"]}'

# ✅ 수정 1: 변수 추출
title = data.get('title', 'N/A')
f.write(f"Title: {title}\n")

# ✅ 수정 2: 다른 따옴표 + .get()
f.write(f"Title: {data.get('title', 'N/A')}\n")
```

**규칙**: 중괄호 안에서 같은 종류 따옴표 절대 금지!

---

### **2️⃣ 변수 파싱 누락**

```python
# ❌ 오류
variables = {}  # 파싱 안 함!
url = variables['api_url']  # KeyError!

# ✅ 수정
variables = {}
if '--variables' in sys.argv:
    idx = sys.argv.index('--variables')
    variables = json.loads(sys.argv[idx + 1])
elif '--variables-file' in sys.argv:
    ...
```

---

### **3️⃣ 디버그를 stdout에 출력**

```python
# ❌ 오류
print(f"Processing...")  # JSON 파싱 깨짐!
result = {"status": "success"}
print(json.dumps(result))

# 출력 결과:
# Processing...
# {"status": "success"}
# ← 파싱 실패!

# ✅ 수정
print(f"Processing...", file=sys.stderr)  # stderr로!
result = {"status": "success"}
print(json.dumps(result))  # JSON만 stdout
```

---

### **4️⃣ 단순 데이터 타입으로 출력**

```python
# ❌ 오류
print(json.dumps([1, 2, 3]))  # 리스트만!
print(json.dumps("success"))  # 문자열만!

# ✅ 수정 (구조화된 JSON)
print(json.dumps({
    "status": "success",
    "results": [1, 2, 3],
    "count": 3
}))
```

---

### **5️⃣ 부분 코드 제공**

```python
# ❌ 오류
# 이 부분을 추가하세요:
result = process(data)
print(json.dumps(result))

# ✅ 올바름 (완전한 실행 가능 코드)
#!/usr/bin/env python3
import json
import sys

def main():
    variables = {}
    if '--variables' in sys.argv:
        idx = sys.argv.index('--variables')
        variables = json.loads(sys.argv[idx + 1])
    
    try:
        result = process(variables.get('data', []))
        print(json.dumps(result))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

---

## 워크플로우 응답 포맷

### **응답 구조**

```json
{
  "workflow": {
    "name": "워크플로우 이름",
    "description": "상세 설명",
    "tags": ["tag1", "tag2"],
    "steps": [
      {
        "name": "스텝 이름",
        "step_type": "PYTHON_SCRIPT",  // LLM_CALL, API_CALL, CONDITION 등
        "order": 0,                      // 실행 순서
        "config": {
          "description": "이 스텝이 하는 일"
        },
        "code": "완벽한 Python 코드",     // PYTHON_SCRIPT만 필수
        "input_mapping": {"input": "workflow_var"},
        "output_mapping": {"output": "step_output_key"},
        "retry_config": {"max_retries": 3, "retry_delay": 5}
      }
    ],
    "variables": {
      "var1": "initial_value"
    },
    "metadata": {
      "python_requirements": ["requests"],
      "step_codes": {}
    }
  },
  "questions": [],           // 질문이 있으면 리스트
  "ready": true              // false면 질문이 필요함
}
```

---

## 🎯 체크리스트

생성되는 Python 코드가 다음을 만족하는가?

```
[ ] 1. UTF-8 인코딩 강제 (Windows 지원)
[ ] 2. --variables-file 파싱 포함
[ ] 3. --variables 우선, --variables-file 폴백
[ ] 4. Flat 구조의 JSON 출력
[ ] 5. 디버그 로그는 stderr로만
[ ] 6. try-except 에러 처리
[ ] 7. f-string 따옴표 안전 (변수 추출)
[ ] 8. 필수 import (json, sys 등)
[ ] 9. 완전한 실행 가능 코드
[ ] 10. metadata.python_requirements 나열
```

---

## 🚀 핵심 메시지

### **LLM이 명심할 3가지**

```
1️⃣ 완벽함 (Perfection)
   완벽한 실행 가능 코드만 생성
   부분 코드 금지!

2️⃣ 안전함 (Safety)
   f-string 따옴표 안전
   에러 처리 필수

3️⃣ 구조화 (Structure)
   Flat JSON 출력
   메타데이터 명확
```

### **생각 흐름**

```
사용자 요청
    ↓
정보 부족? → 질문 제시 (ready: false)
정보 충분? → 워크플로우 생성 (ready: true)
    ↓
3-5개 스텝으로 분해
    ↓
각 PYTHON_SCRIPT에 완벽한 코드
    ↓
JSON 형식으로 반환
```

---

## 📚 더 자세히

**상세 가이드**: `AUTO_CODE_VALIDATION.md`  
**수정 프롬프트**: `WORKFLOW_MODIFICATION_SYSTEM_PROMPT` (같은 파일)  
**소스 파일**: `src/agents/prompts.py`

---

**버전**: 1.0  
**상태**: ✅ 핵심 요약 완료

이 프롬프트를 따르면 LLM이 생성하는 워크플로우는 **항상 완벽하고 실행 가능합니다!** 🎯

