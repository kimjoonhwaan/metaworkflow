# Fix #1: API_CALL 응답 구조 통일 ✅

## 🎯 목표
API_CALL 스텝의 응답 구조를 통일하여 모든 필드를 `output` 객체 안에 포함시키기

## 🔴 문제점

### 이전 (분산된 구조):
```python
return {
    "success": True,
    "output": result.get("data"),           # ← API 응답 데이터
    "status_code": result.get("status_code"),  # ← output 밖에 있음!
    "error": result.get("error")            # ← output 밖에 있음!
}
```

**문제:**
- `output_mapping`에서 `"status_code"`를 찾을 수 없음
- `workflow_engine.py`의 `output_mapping` 로직이 `output` 필드만 봄
- 불일관한 응답 구조

### 워크플로우 엔진의 매핑 로직:
```python
# workflow_engine.py line 152
output_data = result.get("output", {})  # ← "output" 필드만 추출

# line 167
elif isinstance(output_data, dict) and output_key in output_data:
    # ← 여기서 output_data 안의 필드만 찾음
    state["variables"][var_name] = output_data[output_key]
```

---

## ✅ 해결책

### 이후 (통일된 구조):
```python
return {
    "success": result.get("status") == "success",
    "output": {
        "data": result.get("data"),                      # API 응답 데이터
        "status_code": result.get("status_code"),        # HTTP 상태 코드
        "headers": result.get("headers", {}),            # 응답 헤더
        "status": result.get("status"),                  # 성공/실패 상태
        "error": result.get("error")                     # 에러 메시지
    },
    "error": result.get("error")
}
```

**장점:**
- ✅ 모든 필드가 `output` 안에 포함
- ✅ `output_mapping`에서 쉽게 접근 가능
- ✅ 일관된 응답 구조
- ✅ 확장성 좋음 (새로운 필드 추가 쉬움)

---

## 📝 사용 예제

### Workflow JSON:
```json
{
  "step_type": "API_CALL",
  "name": "Fetch Weather",
  "config": {
    "method": "GET",
    "url": "https://api.example.com/weather",
    "query_params": {
      "city": "{city_name}"
    },
    "response": {
      "extract": "data.items"
    }
  },
  "output_mapping": {
    "weather_data": "data",           # API 응답 추출
    "http_code": "status_code",       # 상태 코드
    "headers_info": "headers",        # 응답 헤더
    "response_status": "status"       # 성공/실패
  }
}
```

### 결과:
```python
variables = {
    "weather_data": [...],            # 추출된 API 데이터
    "http_code": 200,                 # HTTP 상태 코드
    "headers_info": {...},            # 응답 헤더
    "response_status": "success"      # 성공 상태
}
```

---

## 🔧 수정 사항

### 파일: `src/engines/step_executor.py`

**메서드:** `_execute_api_call` (line 127-175)

**변경 사항:**
1. 응답 구조를 통일하여 모든 필드를 `output` 객체 안에 포함
2. 에러 케이스에서도 동일한 구조 유지
3. 상세한 로깅 추가 (`logger.debug`)
4. 명확한 주석 및 docstring 추가

**코드:**
```python
async def _execute_api_call(self, config: Dict[str, Any], variables: Dict[str, Any]) -> Dict[str, Any]:
    """Execute API call step via API MCP
    
    Returns structured output with all API response data:
    {
        "success": bool,
        "output": {
            "data": <api_response>,
            "status_code": int,
            "headers": dict,
            "status": str,
            "error": str or None
        },
        "error": str or None
    }
    """
    # ... 구현 ...
```

---

## 📊 호환성

### 기존 코드와의 호환성:
- ✅ `result.get("output", {})` - 여전히 작동 (이제는 dict)
- ✅ workflow_engine의 output_mapping 로직 - 완벽하게 지원
- ✅ 다른 스텝 타입 - 영향 없음

### 마이그레이션:
기존에 API_CALL 스텝을 사용하던 workflows:
- output_mapping을 `"data"`로 변경 필요
- 예: `"api_result": "data"` (이전: `"api_result": "result"`)

---

## 🎯 다음 단계

이 수정 후 다음을 진행할 예정:
1. ✅ API_CALL 응답 구조 통일 (현재)
2. ⏳ NOTIFICATION 변수 포맷팅 개선
3. ⏳ LLM_CALL 응답 구조화
4. ⏳ CONDITION eval() 보안 개선

---

## ✨ 테스트

### 검증 항목:
- [ ] API_CALL 스텝이 정상 작동
- [ ] output_mapping이 모든 필드 접근 가능
- [ ] 에러 케이스에서도 일관된 구조
- [ ] 기존 workflows 호환성

---

## 📚 참고 문서

- `API_CALL_RESPONSE_STRUCTURE.md` - 상세 사용 가이드
- `src/engines/step_executor.py` - 구현
- `src/engines/workflow_engine.py` - output_mapping 로직

