# API_CALL Step - 응답 구조 가이드

## 📋 개요

API_CALL 스텝의 응답 구조가 **통일**되었습니다. 모든 필드가 `output` 객체 안에 포함되므로 `output_mapping`에서 쉽게 접근할 수 있습니다.

---

## 🎯 API_CALL 응답 구조

```json
{
  "success": true,
  "output": {
    "data": "<변환된 API 응답 데이터>",
    "status_code": 200,
    "headers": {
      "content-type": "application/json",
      "...": "..."
    },
    "status": "success",
    "error": null
  },
  "error": null
}
```

### 필드 설명

| 필드 | 설명 | 예시 |
|------|------|------|
| `data` | API에서 반환한 실제 데이터 (response config로 변환 가능) | `[{...}, {...}]` |
| `status_code` | HTTP 상태 코드 | `200`, `404`, `500` |
| `headers` | 응답 헤더 | `{"content-type": "application/json"}` |
| `status` | 성공/실패 상태 | `"success"`, `"error"` |
| `error` | 에러 메시지 (없으면 null) | `"Connection timeout"` |

---

## ✅ output_mapping 사용법

### 기본 예제

```json
{
  "step_type": "API_CALL",
  "name": "Fetch Data",
  "config": {
    "method": "GET",
    "url": "https://api.example.com/data",
    "query_params": {
      "limit": 10
    }
  },
  "output_mapping": {
    "api_response": "data",           # API 응답 데이터
    "http_status": "status_code",     # HTTP 상태 코드
    "response_headers": "headers",    # 응답 헤더
    "api_status": "status"            # 성공/실패 상태
  }
}
```

### 결과

workflow 변수에 다음과 같이 저장됩니다:

```python
variables = {
    "api_response": [...],                # 실제 데이터
    "http_status": 200,                   # 상태 코드
    "response_headers": {...},            # 헤더
    "api_status": "success"               # 상태
}
```

---

## 🔄 API 응답 변환 설정 (response config)

복잡한 API 응답을 자동으로 변환할 수 있습니다.

### 예제 1: JSONPath 추출

**API 응답:**
```json
{
  "success": true,
  "data": {
    "items": [
      {"id": 1, "name": "Item 1"},
      {"id": 2, "name": "Item 2"}
    ]
  }
}
```

**Workflow config:**
```json
{
  "config": {
    "response": {
      "extract": "data.items"
    }
  },
  "output_mapping": {
    "items": "data"
  }
}
```

**결과:**
```python
variables["items"] = [
    {"id": 1, "name": "Item 1"},
    {"id": 2, "name": "Item 2"}
]
```

### 예제 2: 필드 매핑

**API 응답:**
```json
{
  "id": 123,
  "user_name": "John",
  "email_address": "john@example.com"
}
```

**Workflow config:**
```json
{
  "config": {
    "response": {
      "map": {
        "user_id": "id",
        "username": "user_name",
        "email": "email_address"
      }
    }
  },
  "output_mapping": {
    "user": "data"
  }
}
```

**결과:**
```python
variables["user"] = {
    "user_id": 123,
    "username": "John",
    "email": "john@example.com"
}
```

### 예제 3: 복합 변환

**Workflow config:**
```json
{
  "config": {
    "response": {
      "extract": "data.results",
      "map": {
        "item_id": "id",
        "title": "name",
        "description": "desc"
      }
    }
  },
  "output_mapping": {
    "processed_items": "data",
    "http_code": "status_code"
  }
}
```

---

## 🎯 실제 workflow 예제

```json
{
  "workflow": {
    "name": "API 데이터 조회",
    "steps": [
      {
        "name": "Fetch Weather",
        "step_type": "API_CALL",
        "order": 0,
        "config": {
          "method": "GET",
          "url": "https://api.example.com/weather",
          "query_params": {
            "city": "{city_name}",
            "lang": "ko"
          },
          "response": {
            "extract": "data.weather"
          }
        },
        "input_mapping": {
          "city_name": "selected_city"
        },
        "output_mapping": {
          "weather_data": "data",
          "http_status": "status_code"
        }
      },
      {
        "name": "Display Weather",
        "step_type": "NOTIFICATION",
        "order": 1,
        "config": {
          "type": "log",
          "message": "Weather: {weather_data}\nStatus: {http_status}"
        }
      }
    ]
  }
}
```

---

## ⚠️ 주의사항

### ❌ 틀린 예제

```json
{
  "output_mapping": {
    "result": "result"  // ❌ "result" 필드가 output에 없음!
  }
}
```

### ✅ 올바른 예제

```json
{
  "output_mapping": {
    "result": "data",           // ✅ "data" 필드에 접근
    "code": "status_code"       // ✅ "status_code" 필드에 접근
  }
}
```

---

## 📝 요약

| 상황 | 사용 필드 |
|------|---------|
| API 응답 데이터 필요 | `"output_mapping": {"var": "data"}` |
| HTTP 상태 코드 필요 | `"output_mapping": {"var": "status_code"}` |
| 응답 헤더 필요 | `"output_mapping": {"var": "headers"}` |
| 성공/실패 확인 | `"output_mapping": {"var": "status"}` |
| 에러 메시지 필요 | `"output_mapping": {"var": "error"}` |

---

## 🔗 참고

- API MCP: `src/mcp/api_server.py`
- Step Executor: `src/engines/step_executor.py`
- Workflow Engine: `src/engines/workflow_engine.py`

