# API_CALL 프롬프트 수정 가이드

**수정일**: 2025-11-09  
**상태**: ✅ 완료  
**적용 범위**: 생성 프롬프트 + 수정 프롬프트 (모두 적용)

---

## 📋 **문제**

LLM이 API_CALL 스텝 생성 시 **잘못된 JSON 형식**을 만들고 있었습니다:

```json
❌ 잘못된 형식 (이전):
{
  "url": "https://api.example.com/search?q={query}&limit=10",  ← 쿼리스트링 포함
  "params": {}  ← 잘못된 키 이름!
}

✅ 올바른 형식 (수정 후):
{
  "url": "https://api.example.com/search",  ← 베이스 URL만
  "query_params": {  ← 올바른 키 이름!
    "q": "{query}",
    "limit": 10
  }
}
```

---

## 🔧 **수정 내용**

### **파일**: `src/agents/prompts.py`

### **수정 위치 1**: WORKFLOW_CREATION_SYSTEM_PROMPT (라인 228-251)

```python
# 이전 (불충분한 설명):
- **API_CALL**: HTTP API call (config: {method, url, headers, body, params})

# 수정 후 (상세한 설명):
- **API_CALL**: REST API HTTP call
  * config MUST have: 
    {
      "method": "GET|POST|PUT|DELETE|PATCH",
      "url": "https://api.example.com/endpoint",  ← Base URL ONLY (no query string!)
      "query_params": {                           ← IMPORTANT: "query_params" NOT "params"!
        "param1": "{variable_name}",
        "param2": "literal_value",
        "limit": 10
      },
      "headers": {...},
      "body": null
    }
  * ⭐ CRITICAL Rules:
    1. URL must be base path ONLY - no query string!
    2. ALL query parameters must go in "query_params" object
    3. Use "query_params" NOT "params"!
    4. Variables use single braces: {variable_name}
```

### **수정 위치 2**: WORKFLOW_MODIFICATION_SYSTEM_PROMPT (라인 468-491)

```python
# 동일한 API_CALL 설명 추가
- **API_CALL**: REST API HTTP call
  * config MUST have: {...}
  * ⭐ CRITICAL Rules: {...}
```

---

## ✨ **추가된 명확한 지침**

### **LLM이 이제 이해하는 것**

```
1️⃣ URL 형식
   ❌ "url": "https://api.example.com/search?q={query}&limit=10"
   ✅ "url": "https://api.example.com/search"

2️⃣ 파라미터 저장소
   ❌ "params": {}, "url"에 직접 작성
   ✅ "query_params": {...}, 파라미터 분리

3️⃣ 변수 형식
   ✅ "{variable_name}" (단일 중괄호)
   ✅ "literal_value" (리터럴 값)
   ✅ 숫자 값도 가능

4️⃣ 매핑
   ✅ input_mapping: 이전 단계 → 현재 단계
   ✅ output_mapping: 응답 → 다음 단계
```

---

## 🎯 **기대 결과**

### **수정 전 (❌ 틀림)**
```
사용자 요청: "기상청 API 호출해줘"
   ↓
LLM 생성:
{
  "url": "https://apihub.kma.go.kr/api/...?base_date={base_date}&nx={nx}",
  "params": {}
}
   ↓
결과: 변수 포맷팅 안 됨 → API 호출 실패 (401 에러)
```

### **수정 후 (✅ 올바름)**
```
사용자 요청: "기상청 API 호출해줘"
   ↓
LLM 생성:
{
  "url": "https://apihub.kma.go.kr/api/...",
  "query_params": {
    "base_date": "{base_date}",
    "nx": "{nx}",
    ...
  }
}
   ↓
결과: 변수 포맷팅 성공 → API 호출 성공 ✅
```

---

## 📝 **LLM이 생성할 API_CALL 예시**

### **예시 1: GET 요청**
```json
{
  "name": "Fetch News",
  "step_type": "API_CALL",
  "config": {
    "method": "GET",
    "url": "https://newsapi.org/v2/top-headlines",
    "query_params": {
      "country": "kr",
      "category": "{news_category}",
      "apiKey": "{news_api_key}"
    }
  },
  "input_mapping": {
    "news_category": "category",
    "news_api_key": "api_key"
  },
  "output_mapping": {
    "response": "news_articles"
  }
}
```

### **예시 2: POST 요청**
```json
{
  "name": "Create User",
  "step_type": "API_CALL",
  "config": {
    "method": "POST",
    "url": "https://api.example.com/users",
    "query_params": {
      "token": "{auth_token}"
    },
    "body": {
      "name": "{user_name}",
      "email": "{user_email}"
    }
  },
  "input_mapping": {
    "user_name": "name",
    "user_email": "email",
    "auth_token": "token"
  },
  "output_mapping": {
    "response": "user_created"
  }
}
```

---

## 🚀 **적용 후 테스트**

### **Step 1: Streamlit 재시작**
```bash
Ctrl+C  # 현재 Streamlit 중지
streamlit run app.py  # 재시작
```

### **Step 2: 새 워크플로우 생성**
Streamlit → **Create Workflow** → "기상청 API 호출"

### **Step 3: LLM 출력 확인**
생성된 JSON에서 확인:
```
✅ "url": "https://apihub.kma.go.kr/..." (쿼리스트링 없음)
✅ "query_params": {...} (모든 파라미터 포함)
✅ 변수는 "{변수명}" 형식
```

### **Step 4: API 호출 성공 확인**
실행 후 로그:
```
[API_MCP] Calling GET ...&base_date=20251109&nx=55&ny=127&authKey=...
[API_MCP] ✅ Success on attempt 1
[API_MCP] ✅ API call successful: 200
```

---

## 📊 **프롬프트 수정 효과**

| 기능 | 생성 워크플로우 | 수정 워크플로우 |
|------|-----------------|-----------------|
| **API_CALL 설명** | ✅ 상세히 설명 | ✅ 상세히 설명 |
| **query_params 강조** | ✅ 강조됨 | ✅ 강조됨 |
| **잘못된 예시** | ✅ 제시됨 | ✅ 제시됨 |
| **올바른 예시** | ✅ 제시됨 | ✅ 제시됨 |
| **적용 범위** | 새 워크플로우 생성 | 기존 워크플로우 수정 |

---

## ✅ **체크리스트**

```
☑️ 프롬프트 파일 수정 완료
☑️ WORKFLOW_CREATION_SYSTEM_PROMPT 업데이트
☑️ WORKFLOW_MODIFICATION_SYSTEM_PROMPT 업데이트
☑️ API_CALL 설명 명확화
☑️ 린트 검사 통과
☑️ 생성/수정 모두 적용됨
```

---

## 🎓 **이제 LLM은**

```
✅ query_params를 올바르게 사용
✅ URL에 쿼리스트링 포함 안 함
✅ 변수를 {변수명} 형식으로 사용
✅ input_mapping / output_mapping 올바르게 생성
✅ API 호출이 성공하도록 JSON 생성
```

---

**프롬프트 수정 완료! 이제 워크플로우를 생성해보세요!** 🚀


