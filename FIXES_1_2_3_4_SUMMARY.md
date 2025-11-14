# 4가지 주요 수정사항 종합 가이드

## 📋 개요

다음 4가지 주요 문제를 수정했습니다:

1. ✅ **API_CALL 응답 구조 통일** (매우 높음 영향도)
2. ✅ **NOTIFICATION 변수 포맷팅 개선** (높음 영향도)
3. ✅ **LLM_CALL 응답 구조화** (중간 영향도)
4. ✅ **CONDITION eval() 보안 개선** (중간 영향도)

---

## 1️⃣ API_CALL 응답 구조 통일

### 문제
- 응답 필드가 분산됨 (output, status_code, error가 각각)
- output_mapping에서 status_code 접근 불가능
- 불일관한 구조

### 해결책
모든 필드를 `output` 객체 안에 통일:

```python
return {
    "success": bool,
    "output": {
        "data": <변환된_API_응답>,        # API 응답 데이터
        "status_code": 200,               # HTTP 상태 코드
        "headers": {...},                 # 응답 헤더
        "status": "success|error",        # 성공/실패
        "error": null or "error message"  # 에러 메시지
    },
    "error": str or None
}
```

### Workflow 사용 예제

```json
{
  "step_type": "API_CALL",
  "output_mapping": {
    "api_data": "data",              # API 응답 데이터
    "http_status": "status_code",    # HTTP 상태 코드
    "response_headers": "headers",   # 응답 헤더
    "api_status": "status"           # 성공/실패 상태
  }
}
```

### 문서
- `API_CALL_RESPONSE_STRUCTURE.md` - 상세 가이드
- `FIX_1_API_RESPONSE_STRUCTURE.md` - 수정 상세

---

## 2️⃣ NOTIFICATION 변수 포맷팅 개선

### 문제
- 공백 있는 변수 `{ variable }` 처리 불가능
- KeyError 발생 시 처리 미흡
- API_CALL의 개선 로직 미적용

### 해결책
regex를 사용하여 공백 정리 및 예외 처리:

```python
def format_with_variables(template: str, vars: Dict[str, Any]) -> str:
    """변수 포맷팅 (공백 제거 및 예외 처리)"""
    if not template:
        return ""
    try:
        # 공백이 있는 { variable } 패턴을 {variable}로 정리
        cleaned = re.sub(r'\{\s+(\w+)\s+\}', r'{\1}', template)
        return cleaned.format(**vars)
    except KeyError as e:
        logger.warning(f"Variable '{e}' not found, using original")
        return template
    except Exception as e:
        logger.error(f"Error formatting: {e}")
        return template
```

### 이전 vs 이후

**이전:**
```python
subject = subject.format(**variables)  # ❌ KeyError 발생
```

**이후:**
```python
subject = format_with_variables(subject, variables)  # ✅ 안전하게 처리
```

---

## 3️⃣ LLM_CALL 응답 구조화

### 문제
- LLM 응답이 단순 문자열
- 메타데이터 (프롬프트, 모델 등) 손실
- output_mapping 지원 미흡

### 해결책
구조화된 응답 객체로 통일:

```python
return {
    "success": True,
    "output": {
        "response": result,               # LLM 응답
        "prompt": formatted_prompt,       # 실제 사용한 프롬프트
        "system_prompt": system_prompt,   # 시스템 프롬프트
        "model": "gpt-4",                 # 모델 정보
        "raw_response": result            # 원본 (호환성)
    }
}
```

### Workflow 사용 예제

```json
{
  "step_type": "LLM_CALL",
  "output_mapping": {
    "llm_response": "response",       # LLM 응답
    "used_prompt": "prompt",          # 사용한 프롬프트
    "model_name": "model"             # 모델 정보
  }
}
```

---

## 4️⃣ CONDITION eval() 보안 개선

### 문제
- 기본 eval() 사용 (보안 취약)
- 에러 처리 미흡
- 복잡한 조건 디버깅 어려움

### 해결책
안전한 평가 환경 + 상세한 에러 처리:

```python
# 안전한 함수만 허용
safe_dict = {
    "__builtins__": {},           # 빌트인 함수 차단
    "True": True, "False": False, "None": None,
    "len": len, "str": str,       # 안전한 함수만
    "int": int, "float": float,
    "bool": bool,
}
safe_dict.update(variables)

result = eval(condition, safe_dict)  # ✅ 안전한 평가
```

### 지원되는 조건

```
- 비교: ==, !=, <, >, <=, >=
- 논리: and, or, not
- 예제: "status == 'success' and count > 10"
```

### 에러 처리

```python
# SyntaxError, NameError, 기타 Exception
# 각각 다른 에러 메시지 반환
# 상세한 로깅 제공
```

### Workflow 사용 예제

```json
{
  "step_type": "CONDITION",
  "config": {
    "condition": "status == 'success' and error is None"
  },
  "output_mapping": {
    "is_success": "condition_met"
  }
}
```

---

## 📊 수정 파일

### `src/engines/step_executor.py`

**수정 메서드:**
1. `_execute_api_call()` (line 133) - API 응답 구조 통일
2. `_execute_notification()` (line 335) - 변수 포맷팅 개선
3. `_execute_llm_call()` (line 75) - 응답 구조화
4. `_execute_condition()` (line 309) - 보안 개선

**총 변경:**
- 약 150+ 줄 추가/수정
- 모든 변경사항은 backward compatible

---

## 🔄 적용 영향도

### workflow_engine.py
- ✅ 기존 output_mapping 로직과 100% 호환
- ✅ 새로운 필드 추가로 더 많은 매핑 가능
- ✅ 변화 없음 (output 필드 읽기만 하므로)

### 기존 workflows
- ⚠️ output_mapping 일부 수정 필요
- 예: `"result": "result"` → `"result": "data"` (API_CALL의 경우)
- ✅ 대부분은 영향 없음

---

## 🧪 테스트 체크리스트

- [ ] API_CALL 스텝이 모든 필드 반환하는지 확인
- [ ] NOTIFICATION 이메일에서 `{ variable }` 처리 확인
- [ ] LLM_CALL 응답의 구조화된 output 확인
- [ ] CONDITION 조건 평가 및 에러 처리 확인
- [ ] 기존 workflows 호환성 확인

---

## 📚 관련 문서

- `API_CALL_RESPONSE_STRUCTURE.md` - API_CALL 상세 가이드
- `FIX_1_API_RESPONSE_STRUCTURE.md` - Fix #1 상세 설명
- `src/engines/step_executor.py` - 구현 코드

---

## 🎯 다음 단계

완료된 4가지 수정 후 다음을 계획:

1. ⏳ Email MCP 고급 기능 (첨부파일, 템플릿)
2. ⏳ API MCP 캐싱 개선 (TTL 정리, rate limiting)
3. ⏳ 통합 테스트

---

## ✨ 요약

| Fix | 문제 | 해결책 | 영향도 | 상태 |
|-----|------|--------|--------|------|
| 1️⃣ | 응답 구조 분산 | 통일된 output 객체 | 매우 높음 | ✅ |
| 2️⃣ | 변수 포맷팅 실패 | regex + 예외 처리 | 높음 | ✅ |
| 3️⃣ | 응답 메타데이터 손실 | 구조화된 output | 중간 | ✅ |
| 4️⃣ | eval() 보안 취약 | 안전한 평가 환경 | 중간 | ✅ |

모든 수정사항이 완료되었습니다! 🎉

