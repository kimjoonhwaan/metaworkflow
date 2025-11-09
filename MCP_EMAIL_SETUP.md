# MCP Email Notification Setup Guide

## 개요

이 프로젝트에는 MCP (Model Context Protocol) 기반의 이메일 발송 기능이 구현되어 있습니다.

## 아키텍처

```
WorkflowEngine (LangGraph)
    ↓
StepExecutor
    ↓
NOTIFICATION 스텝 (type: "email")
    ↓
EmailMCPServer (src/mcp/email_server.py)
    ↓
SMTP (Gmail, Office365, SendGrid 등)
    ↓
사용자에게 메일 발송
```

## 설정 방법

### 1️⃣ Gmail 사용 (권장)

**단계:**

1. [Google Account Security](https://myaccount.google.com/apppasswords) 방문
2. App Password 생성 (Gmail 앱)
3. `.env` 파일 작성:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password_here
FROM_EMAIL=your_email@gmail.com
```

### 2️⃣ Office365 사용

```env
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=your_email@outlook.com
SMTP_PASSWORD=your_password
FROM_EMAIL=your_email@outlook.com
```

### 3️⃣ SendGrid 사용

```env
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=your_sendgrid_api_key
FROM_EMAIL=your_email@sendgrid.com
```

## 워크플로우에서 사용하기

### 워크플로우 JSON 예시

```json
{
  "workflow": {
    "name": "News Summarizer with Email",
    "steps": [
      {
        "name": "Fetch News",
        "step_type": "API_CALL",
        "order": 0,
        "config": {
          "method": "GET",
          "url": "https://news.example.com/api/latest",
          "headers": {"Authorization": "Bearer {api_token}"}
        },
        "output_mapping": {
          "news_data": "output"
        }
      },
      {
        "name": "Summarize with LLM",
        "step_type": "LLM_CALL",
        "order": 1,
        "config": {
          "prompt": "{news_data}를 3줄로 요약해줘",
          "system_prompt": "너는 뉴스 요약 전문가야"
        },
        "input_mapping": {
          "news_data": "news_data"
        },
        "output_mapping": {
          "summary": "output"
        }
      },
      {
        "name": "Send Email",
        "step_type": "NOTIFICATION",
        "order": 2,
        "config": {
          "type": "email",
          "to": "{recipient_email}",
          "subject": "뉴스 요약: {news_title}",
          "body": "{summary}",
          "html": false
        },
        "input_mapping": {
          "recipient_email": "user_email",
          "news_title": "title",
          "summary": "summary"
        }
      }
    ],
    "variables": {
      "api_token": "your_token",
      "user_email": "user@example.com"
    }
  }
}
```

## NOTIFICATION 스텝 설정

### Email 타입

```json
{
  "step_type": "NOTIFICATION",
  "config": {
    "type": "email",
    "to": "recipient@example.com",                    // 필수
    "subject": "Email Subject",                       // 필수
    "body": "Email body content",                     // 필수
    "cc": "cc@example.com",                          // 선택
    "bcc": "bcc@example.com",                        // 선택
    "html": false                                     // 선택 (기본값: false)
  }
}
```

### Log 타입 (기존)

```json
{
  "step_type": "NOTIFICATION",
  "config": {
    "type": "log",
    "message": "This is a log message"
  }
}
```

## 변수 포맷팅

모든 필드에서 `{변수명}` 형식으로 이전 스텝의 변수를 사용할 수 있습니다:

```json
{
  "to": "{user_email}",
  "subject": "Order #{order_id} Confirmation",
  "body": "Hello {customer_name},\n\nYour order has been processed.\n\nThank you!"
}
```

## 에러 처리

SMTP 설정이 없거나 잘못된 경우:

```
ERROR - [NOTIFICATION] Error sending notification: SMTP credentials not configured
```

**해결책:**
1. `.env` 파일에 SMTP 설정이 있는지 확인
2. 앱 비밀번호가 정확한지 확인
3. 2단계 인증이 활성화되어 있는지 확인
4. 방화벽/네트워크에서 SMTP 포트가 열려있는지 확인

## 테스트하기

### CLI 테스트

```bash
# Python 인터프리터에서
from src.mcp.email_server import email_mcp
import asyncio

async def test():
    result = await email_mcp.send_email(
        to="test@example.com",
        subject="Test Email",
        body="This is a test email"
    )
    print(result)

asyncio.run(test())
```

### 워크플로우 테스트

1. Streamlit UI에서 "Create Workflow" 탭 이동
2. 다음과 같은 워크플로우 생성:

```
네이버 뉴스를 가져와서 요약한 다음 이메일로 test@example.com에 보내줘
```

3. 생성된 워크플로우의 NOTIFICATION 스텝이 올바르게 설정되어 있는지 확인
4. "Manage Workflows" 탭에서 워크플로우 실행

## 문제 해결

### 문제 1: "SMTP credentials not configured"

**원인**: `.env` 파일에 SMTP 설정이 없음

**해결책**:
```env
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
```

### 문제 2: "SMTP authentication failed"

**원인**: 이메일 또는 비밀번호가 잘못됨

**해결책**:
- Gmail의 경우 [App Password](https://myaccount.google.com/apppasswords) 생성
- Office365의 경우 2단계 인증 확인

### 문제 3: "Connection timeout"

**원인**: 네트워크 또는 방화벽 문제

**해결책**:
- 방화벽에서 SMTP 포트 (587) 열기
- 네트워크 연결 확인
- VPN 사용 시 VPN 설정 확인

## 향후 계획

- [ ] Slack MCP 서버 구현
- [ ] Teams MCP 서버 구현
- [ ] HTML 템플릿 지원
- [ ] 이메일 첨부파일 지원
- [ ] 예약 발송 (Scheduler와 통합)

## 참고 자료

- [SMTP Protocol](https://en.wikipedia.org/wiki/Simple_Mail_Transfer_Protocol)
- [Gmail App Passwords](https://support.google.com/accounts/answer/185833)
- [MCP Specification](https://github.com/anthropics/mcp)

