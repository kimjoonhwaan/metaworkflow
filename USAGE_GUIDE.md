# 사용 가이드

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# .env 파일 생성
OPENAI_API_KEY=your_api_key_here
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_key_here  # 선택사항
LANGCHAIN_PROJECT=workflow-manager
```

### 2. 초기화 및 실행

```bash
# 데이터베이스 초기화
python init_app.py

# 애플리케이션 실행
streamlit run app.py
```

## 📋 워크플로우 생성 방법

### 방법 1: AI와 대화하며 생성 (권장)

1. **워크플로우 생성** 페이지로 이동
2. 채팅창에 업무 설명 입력:
   ```
   "매일 아침 9시에 API에서 데이터를 가져와서 
   가공한 후 이메일로 보내는 워크플로우 만들어줘"
   ```
3. AI가 질문하면 답변
4. 완성되면 자동으로 코드 검증
5. 검증 통과 시 저장

### 방법 2: 샘플 워크플로우로 시작

1. **워크플로우 생성** 페이지
2. 사이드바에서 "📝 샘플 워크플로우 생성" 클릭
3. 검토 후 저장
4. 저장 후 수정 가능

## 🔧 워크플로우 수정

### AI 자동 수정 (권장)

1. **워크플로우 관리** 페이지
2. 수정할 워크플로우 찾기
3. **🤖 AI 수정** 버튼 클릭
4. 수정 요청 입력:
   ```
   "이메일 알림 스텝을 추가해줘"
   "에러 처리를 더 강화해줘"
   "데이터 검증 단계를 추가해줘"
   ```
5. AI가 자동으로 코드를 수정하고 검증
6. 변경사항 확인 후 적용

### 실행 실패 시 자동 수정

1. **실행 기록** 페이지에서 실패한 실행 찾기
2. **📋 상세 로그** 클릭하여 에러 확인
3. **워크플로우 관리**로 이동
4. **🤖 AI 수정** 클릭하고 에러 내용 입력:
   ```
   "실행 실패했어. 다음 에러를 수정해줘:
   KeyError: 'data_field'"
   ```
5. AI가 에러를 분석하고 수정된 워크플로우 생성

## ⚡ 워크플로우 실행

### 수동 실행

1. **워크플로우 관리** 페이지
2. **▶️ 실행** 버튼 클릭
3. **실행 기록** 페이지에서 결과 확인

### 자동 실행 (트리거)

1. **트리거 관리** 페이지
2. **➕ 트리거 생성** 탭
3. 트리거 설정:
   - **스케줄**: `0 9 * * *` (매일 오전 9시)
   - **이벤트**: 특정 이벤트 발생 시
   - **웹훅**: 외부 시스템에서 호출

## 📊 모니터링

### 실행 상태 확인

1. **대시보드**: 전체 통계 및 최근 실행
2. **실행 기록**: 상세 로그 및 단계별 결과
3. **📋 상세 로그** 버튼으로 각 스텝의:
   - 입력/출력 데이터
   - 실행 로그
   - 에러 트레이스백

### 실패 시 대응

1. **🔄 재시도**: 일시적 오류 (네트워크 등)
2. **🤖 AI 수정**: 코드 오류
3. **✅/❌ 승인/거부**: 승인 대기 중인 워크플로우

## 🎯 Best Practices

### 1. 워크플로우 설계

- **3-5 단계**로 구성 (너무 복잡하지 않게)
- **각 스텝의 역할을 명확히**
- **에러 처리**를 중요한 스텝에 추가
- **승인 스텝**을 중요한 작업 전에 배치

### 2. Python 코드 작성

AI가 자동으로 생성하지만, 직접 작성 시:

```python
#!/usr/bin/env python3
import json
import sys

def main():
    # 1. 변수 파싱 (필수!)
    variables = {}
    if '--variables' in sys.argv:
        idx = sys.argv.index('--variables')
        if idx + 1 < len(sys.argv):
            variables = json.loads(sys.argv[idx + 1])
    
    # 2. 디버그는 stderr로
    print(f"Processing...", file=sys.stderr)
    
    try:
        # 3. f-string 안전 사용 (중요!)
        data = variables.get('input', [])
        for item in data:
            # ✅ 올바른 방법: 변수 먼저 추출
            title = item.get('title', 'N/A')
            content = item.get('content', 'N/A')
            print(f"Title: {title}", file=sys.stderr)
            
            # ❌ 잘못된 방법: 따옴표 중첩
            # print(f'Title: {item['title']}')  # 문법 오류!
        
        # 4. 구조화된 JSON 출력 (필수!)
        result = {
            "status": "success",
            "output_data": processed,
            "count": len(processed)
        }
        print(json.dumps(result))
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        print(json.dumps({"status": "error", "error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### 3. 변수 매핑

```json
{
  "steps": [
    {
      "name": "Step 1",
      "output_mapping": {
        "my_variable": "result_key"
      }
    },
    {
      "name": "Step 2",
      "input_mapping": {
        "input_var": "my_variable"
      }
    }
  ]
}
```

### 4. 태그와 폴더 활용

- **폴더**: 워크플로우를 카테고리별로 정리
- **태그**: 검색 및 필터링에 활용
- **상태**: DRAFT (개발 중) → ACTIVE (운영) → ARCHIVED (보관)

## 🆘 문제 해결

### OpenAI API Quota 초과

```
Error code: 429 - insufficient_quota
```

**해결:**
1. OpenAI 계정에서 API quota 확인
2. 결제 정보 업데이트
3. 또는 새 API 키 생성

**참고:** 워크플로우 실행은 AI를 사용하지 않으므로 계속 사용 가능!

### 코드 검증 실패

UI에 표시되는 오류 메시지를 확인:
- **문법 오류**: AI에게 수정 요청
- **경고**: 작동하지만 개선 가능

### 실행 실패

1. **실행 기록**에서 상세 로그 확인
2. 어느 스텝에서 실패했는지 확인
3. **AI 수정** 기능으로 에러 내용 전달
4. AI가 자동으로 수정

## 💡 활용 예시

### 예시 1: 데이터 수집 및 알림

```
"매일 오후 6시에 특정 API에서 판매 데이터를 가져와서
전일 대비 10% 이상 증가한 경우에만 슬랙으로 알림 보내줘"
```

→ AI가 생성:
1. API 호출 스텝
2. 데이터 비교 스텝 (CONDITION)
3. 슬랙 알림 스텝 (조건부)

### 예시 2: 보고서 자동화

```
"매주 월요일 오전 9시에 주간 보고서를 생성하고
승인 후 이메일로 전송하는 워크플로우 만들어줘"
```

→ AI가 생성:
1. 데이터 수집 스텝
2. 보고서 생성 스텝 (PYTHON_SCRIPT)
3. 승인 대기 스텝 (APPROVAL)
4. 이메일 전송 스텝

## 📚 추가 리소스

- **LangGraph 문서**: https://langchain-ai.github.io/langgraph/
- **LangSmith 대시보드**: https://smith.langchain.com/
- **OpenAI API 문서**: https://platform.openai.com/docs/

## ⭐ 시스템의 핵심 가치

**"사용자는 업무만 설명하고, AI가 완벽한 코드를 자동으로 생성합니다"**

- 수동 코딩 불필요
- 자동 검증 및 수정
- Self-Healing 구조
- 프로덕션급 품질

