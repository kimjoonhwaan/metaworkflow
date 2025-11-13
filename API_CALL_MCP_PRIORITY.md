# API_CALL MCP 우선순위 프롬프트 추가

**수정일**: 2025-11-09  
**상태**: ✅ 완료  
**적용 범위**: 생성 + 수정 프롬프트 모두

---

## 📋 **추가된 내용**

### **3가지 위치에 추가됨**

#### **위치 1: WORKFLOW_CREATION_SYSTEM_PROMPT (라인 228-249)**

```markdown
## ⭐ API 호출에 대한 중요 지침

**API 호출은 반드시 API_CALL 스텝 + MCP를 사용하세요!**

❌ 잘못된 방법:
- PYTHON_SCRIPT에서 requests 라이브러리로 직접 API 호출
- API_CALL 스텝 없이 Python에서 처리

✅ 올바른 방법:
- API_CALL 스텝 타입 사용
- MCP가 자동으로 처리 (인증, 재시도, 캐싱, 헤더 등)
- 변수 포맷팅도 자동

**장점:**
1. 🔐 보안: 인증 자동 처리
2. 🔄 재시도: 자동 재시도 (Exponential Backoff)
3. ⚡ 캐싱: 응답 자동 캐시
4. 📋 로깅: 상세 로깅
5. 🌐 헤더: 브라우저 헤더 자동 추가 (WAF 우회)
6. 🧬 변수: 자동 포맷팅
```

#### **위치 2: WORKFLOW_MODIFICATION_SYSTEM_PROMPT (라인 491-512)**

동일한 내용 추가 (수정 시에도 동일하게 적용)

#### **위치 3: CRITICAL RULES 섹션 (라인 311-317)**

```markdown
### 5. API 호출 우선순위
- ✅ API_CALL 스텝 사용 (MCP 자동 처리)
- ✅ query_params에 모든 파라미터 정의
- ✅ 베이스 URL만 작성 (쿼리스트링 X)
- ❌ PYTHON_SCRIPT에서 requests/urllib 직접 사용 금지
- ❌ API_CALL 없이 Python에서 API 호출 금지
- **이유**: MCP가 인증, 재시도, 캐싱, WAF 우회, 헤더 등을 자동으로 처리
```

추가로 **WORKFLOW_MODIFICATION_SYSTEM_PROMPT의 Important Rules (라인 588-594)**에도 동일 추가

---

## 🎯 **기대 효과**

### **LLM 행동 변화**

**수정 전:**
```
사용자: "API 호출 워크플로우 만들어줘"
LLM: PYTHON_SCRIPT에서 requests.get() 사용해서 만듦 ❌
```

**수정 후:**
```
사용자: "API 호출 워크플로우 만들어줘"
LLM: API_CALL 스텝 + MCP 사용해서 만듦 ✅
```

---

## ✨ **LLM이 이제 우선하는 것**

```
1️⃣ API 호출 = API_CALL 스텝
2️⃣ query_params 올바른 형식
3️⃣ MCP의 자동 기능 활용
4️⃣ 변수 자동 포맷팅
```

---

## 🚀 **테스트 방법**

### **Step 1: Streamlit 재시작**
```bash
Ctrl+C
streamlit run app.py
```

### **Step 2: 새 워크플로우 생성**
Streamlit → **Create Workflow** → "API로 뉴스를 가져와줘"

### **Step 3: 생성된 JSON 확인**

```
✅ "step_type": "API_CALL"  (PYTHON_SCRIPT 아님!)
✅ "query_params": {...}    (베이스 URL과 분리)
✅ "url": "https://..." (쿼리스트링 없음)
```

### **Step 4: 실행 후 결과**

```
[API_CALL] Calling API via MCP...
[API_MCP] ✅ API call successful: 200
```

---

## 📊 **적용 범위**

| 프롬프트 | 추가된 내용 | 적용 범위 |
|---------|-----------|---------|
| **WORKFLOW_CREATION_SYSTEM_PROMPT** | API 호출 지침 | 새 워크플로우 생성 |
| **CRITICAL RULES** | API 우선순위 규칙 | 생성 프롬프트 |
| **WORKFLOW_MODIFICATION_SYSTEM_PROMPT** | API 호출 지침 | 워크플로우 수정 |
| **MODIFICATION Important Rules** | API 우선순위 규칙 | 수정 프롬프트 |

---

## ✅ **수정 완료 확인**

```
☑️ WORKFLOW_CREATION_SYSTEM_PROMPT 업데이트
☑️ CRITICAL RULES 추가
☑️ WORKFLOW_MODIFICATION_SYSTEM_PROMPT 업데이트
☑️ MODIFICATION Important Rules 추가
☑️ 4가지 위치 모두 일관성 있게 추가됨
☑️ 린트 검사 통과
```

---

## 🎓 **이제 LLM은**

```
API 호출할 때:
✅ API_CALL 스텝을 먼저 생각함
✅ MCP의 자동 기능을 활용
✅ query_params 올바른 형식 사용
✅ 보안, 재시도, 캐싱 모두 고려

PYTHON_SCRIPT에서 requests:
❌ 피해야 할 방법으로 인식
❌ 기능이 부족한 방법으로 이해
```

---

**프롬프트 업데이트 완료! 이제 LLM이 자동으로 API_CALL + MCP를 우선합니다!** 🚀


