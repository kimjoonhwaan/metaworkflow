# 범용 API MCP 구현 가이드

**완료일**: 2025-11-09  
**상태**: ✅ Phase 1 완료  
**버전**: 1.0

---

## 📋 목차

1. [개요](#개요)
2. [아키텍처](#아키텍처)
3. [사용 방법](#사용-방법)
4. [지원하는 API 타입](#지원하는-api-타입)
5. [고급 기능](#고급-기능)
6. [예제](#예제)
7. [트러블슈팅](#트러블슈팅)

---

## 개요

### 🎯 범용 API MCP란?

**범용 API MCP (Model Context Protocol)**는 모든 REST API 호출을 통합으로 처리하는 서버입니다.

```
기존 방식:
  API_CALL → StepExecutor (200줄) → 각 API별 처리 로직

MCP 방식:
  API_CALL → StepExecutor (5줄) → API MCP → 모든 API 처리 ✅
```

### ✨ 주요 특징

```
✅ 모든 REST API 지원
✅ 자동 재시도 (Exponential Backoff)
✅ 자동 캐싱 (TTL)
✅ 통합 인증 (API Key, OAuth, JWT, Basic, Custom)
✅ 응답 데이터 변환 (JSONPath, 필드 매핑)
✅ 상세 로깅 및 모니터링
```

---

## 아키텍처

### 컴포넌트 구조

```
WorkflowEngine (LangGraph)
    ↓
StepExecutor (5줄!)
    ↓
API MCP Server (api_server.py)
    ├─ 인증 처리 (API Key, OAuth, JWT, Basic, Custom)
    ├─ URL 포맷팅 및 파라미터 준비
    ├─ 재시도 로직 (Exponential Backoff)
    ├─ 캐싱 시스템 (TTL 기반)
    ├─ 응답 변환 (JSONPath, 필드 매핑)
    └─ 상세 로깅
    ↓
REST API (기상청, 뉴스, 날씨, GitHub, Stripe, 커스텀)
```

### 파일 구조

```
src/mcp/
├── __init__.py          (API MCP export)
├── email_server.py      (Email MCP)
└── api_server.py        (범용 API MCP) ← 새로 추가!
```

---

## 사용 방법

### Step 1: 기본 API 호출

```json
{
  "step_type": "API_CALL",
  "config": {
    "url": "https://jsonplaceholder.typicode.com/posts/1",
    "method": "GET",
    "auth": {
      "type": "none"
    }
  }
}
```

### Step 2: 쿼리 파라미터 포함

```json
{
  "step_type": "API_CALL",
  "config": {
    "url": "https://api.example.com/search",
    "method": "GET",
    "query_params": {
      "q": "python",
      "limit": 10
    },
    "auth": {
      "type": "none"
    }
  }
}
```

### Step 3: 변수 사용

```json
{
  "step_type": "API_CALL",
  "config": {
    "url": "https://api.example.com/users/{user_id}/posts",
    "method": "GET",
    "auth": {
      "type": "none"
    }
  },
  "input_mapping": {
    "user_id": "current_user_id"
  }
}
```

### Step 4: 인증 추가

```json
{
  "step_type": "API_CALL",
  "config": {
    "url": "https://api.example.com/data",
    "method": "GET",
    "auth": {
      "type": "api_key",
      "key": "{api_key}"
    }
  },
  "input_mapping": {
    "api_key": "workflow_api_key"
  }
}
```

---

## 지원하는 API 타입

### 1️⃣ 기상청 API (단기 예보)

```json
{
  "url": "https://apihub.kma.go.kr/api/typ02/openApi/VilageFcstInfoService_2.0/getVilageFcst",
  "method": "GET",
  "query_params": {
    "pageNo": 1,
    "numOfRows": 1000,
    "dataType": "JSON",
    "base_date": "{today}",
    "base_time": "0500",
    "nx": 60,
    "ny": 127,
    "authKey": "{kma_api_key}"
  }
}
```

### 2️⃣ NewsAPI

```json
{
  "url": "https://newsapi.org/v2/top-headlines",
  "method": "GET",
  "query_params": {
    "country": "kr",
    "category": "business",
    "pageSize": 10,
    "apiKey": "{newsapi_key}"
  }
}
```

### 3️⃣ OpenWeatherMap API

```json
{
  "url": "https://api.openweathermap.org/data/2.5/weather",
  "method": "GET",
  "query_params": {
    "q": "Seoul",
    "appid": "{openweather_api_key}",
    "units": "metric"
  }
}
```

### 4️⃣ GitHub API (인증 필요)

```json
{
  "url": "https://api.github.com/user/repos",
  "method": "GET",
  "auth": {
    "type": "oauth",
    "token": "{github_token}"
  }
}
```

### 5️⃣ Stripe API (Basic Auth)

```json
{
  "url": "https://api.stripe.com/v1/customers",
  "method": "GET",
  "auth": {
    "type": "basic",
    "username": "{stripe_api_key}",
    "password": ""
  }
}
```

---

## 고급 기능

### 1️⃣ 재시도 로직 (Exponential Backoff)

```json
{
  "url": "https://api.example.com/data",
  "method": "GET",
  "retry": {
    "max_retries": 3,
    "delay": 1,
    "backoff": 2,
    "retry_on": [429, 500, 502, 503]
  }
}
```

**작동 원리:**
```
첫 번째 시도: 즉시
실패 (429 또는 500)
2번째 시도: 1초 후 (delay * backoff^0)
실패
3번째 시도: 2초 후 (delay * backoff^1)
실패
4번째 시도: 4초 후 (delay * backoff^2)
```

### 2️⃣ 캐싱 (TTL)

```json
{
  "url": "https://api.example.com/data",
  "method": "GET",
  "cache": {
    "enabled": true,
    "ttl": 300
  }
}
```

**특징:**
- 자동 만료 (TTL 초 후)
- 메모리 기반 (서버 재시작 시 초기화)
- GET 요청 권장

### 3️⃣ 응답 데이터 변환

#### JSONPath 추출

```json
{
  "url": "https://api.example.com/users/123/posts",
  "method": "GET",
  "response": {
    "extract": "data.items"
  }
}
```

**예시:**
```
원본: {"data": {"items": [1, 2, 3]}}
결과: [1, 2, 3]
```

#### 필드 매핑

```json
{
  "url": "https://api.example.com/posts",
  "method": "GET",
  "response": {
    "map": {
      "post_id": "id",
      "post_title": "title",
      "post_body": "body"
    }
  }
}
```

**예시:**
```
원본: [{"id": 1, "title": "Hello", "body": "World"}]
결과: [{"post_id": 1, "post_title": "Hello", "post_body": "World"}]
```

---

## 예제

### 예제 1: 뉴스 조회 및 요약

```json
{
  "steps": [
    {
      "name": "Fetch News from NewsAPI",
      "step_type": "API_CALL",
      "config": {
        "url": "https://newsapi.org/v2/top-headlines",
        "method": "GET",
        "query_params": {
          "country": "kr",
          "category": "business",
          "pageSize": 5,
          "apiKey": "{newsapi_key}"
        },
        "auth": {"type": "none"},
        "cache": {"enabled": true, "ttl": 300}
      },
      "output_mapping": {
        "news_data": "output"
      }
    },
    {
      "name": "Summarize News with LLM",
      "step_type": "LLM_CALL",
      "config": {
        "prompt": "다음 뉴스 목록을 한 문단으로 요약해줘:\n{news_data}",
        "system_prompt": "너는 뉴스 기자야"
      },
      "output_mapping": {
        "summary": "output"
      }
    }
  ]
}
```

### 예제 2: 날씨 조회 + 메일 발송

```json
{
  "steps": [
    {
      "name": "Get Weather",
      "step_type": "API_CALL",
      "config": {
        "url": "https://api.openweathermap.org/data/2.5/weather",
        "method": "GET",
        "query_params": {
          "q": "Seoul",
          "appid": "{weather_api_key}",
          "units": "metric"
        }
      }
    },
    {
      "name": "Send Weather Email",
      "step_type": "NOTIFICATION",
      "config": {
        "type": "email",
        "to": "{user_email}",
        "subject": "📊 오늘의 날씨",
        "body": "서울 날씨: {weather_data}"
      }
    }
  ]
}
```

---

## 트러블슈팅

### 문제 1: "HTTP 401: Unauthorized"

**원인:** 인증 실패

**해결책:**
```json
{
  "auth": {
    "type": "api_key",
    "key": "{correct_api_key}"
  }
}
```

---

### 문제 2: "HTTP 429: Too Many Requests"

**원인:** Rate limiting 걸림

**해결책:**
```json
{
  "retry": {
    "max_retries": 5,
    "delay": 2,
    "backoff": 2,
    "retry_on": [429]
  }
}
```

---

### 문제 3: "Response timeout"

**원인:** 요청 시간 초과

**해결책:**
```json
{
  "timeout": 60
}
```

---

## 🚀 다음 단계

### Phase 2: 고급 기능 (1주일)

- [ ] TTL 기반 캐시 자동 정리
- [ ] 레이트 리미팅 (API별 최대 요청 수)
- [ ] 응답 스키마 검증
- [ ] WebSocket 지원

### Phase 3: 완성 (1주일)

- [ ] 모니터링 대시보드
- [ ] 성능 메트릭 수집
- [ ] 연결 풀링 최적화
- [ ] HTTP/2 지원

---

## 📚 참고 자료

- [API MCP 테스트 파일](test_api_mcp.py)
- [StepExecutor](src/engines/step_executor.py)
- [워크플로우 생성 프롬프트](src/agents/prompts.py)

---

**Phase 1 완료!** ✅ 다음 Phase 2로 진행하려면 알려주세요! 🚀

