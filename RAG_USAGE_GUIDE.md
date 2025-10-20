# RAG 시스템 사용 가이드

## 🎯 개요

RAG (Retrieval-Augmented Generation) 시스템은 AI가 워크플로우를 생성하고 수정할 때 더 정확하고 완성도 높은 결과를 제공하기 위해 도입되었습니다. 이 시스템은 지식 베이스에서 관련 정보를 검색하여 AI에게 컨텍스트를 제공합니다.

## 🚀 빠른 시작

### 1. 시스템 초기화

```bash
# 데이터베이스 및 RAG 시스템 초기화
python -m src.database.init_db

# RAG 시스템 테스트
python test_rag_system.py
```

### 2. Streamlit 앱 실행

```bash
streamlit run app.py
```

"🧠 Knowledge Base Management" 페이지에서 RAG 시스템을 관리할 수 있습니다.

## 📚 지식 베이스 관리

### 지식 베이스 카테고리

1. **WORKFLOW_PATTERNS**: 워크플로우 패턴 및 템플릿
2. **ERROR_SOLUTIONS**: 에러 해결책 및 디버깅 가이드
3. **CODE_TEMPLATES**: 검증된 Python 코드 템플릿
4. **INTEGRATION_EXAMPLES**: 외부 서비스 연동 예제
5. **BEST_PRACTICES**: 베스트 프랙티스 및 가이드라인

### 문서 추가 방법

1. **UI를 통한 추가**:
   - "🧠 Knowledge Base Management" 페이지
   - "➕ Add Document" 탭
   - 지식 베이스 선택 또는 새로 생성
   - 문서 내용 입력 및 메타데이터 설정

2. **프로그래밍 방식 추가**:
```python
from src.services.rag_service import get_rag_service
from src.database.models import DocumentContentType

rag_service = get_rag_service()

# 문서 추가
doc_id = await rag_service.add_document(
    knowledge_base_id="kb_id",
    title="문서 제목",
    content="문서 내용",
    content_type=DocumentContentType.CODE,
    tags=["python", "template"]
)
```

## 🔍 검색 기능

### 하이브리드 검색

RAG 시스템은 의미적 검색과 키워드 검색을 결합한 하이브리드 검색을 제공합니다.

```python
# 하이브리드 검색
results = await rag_service.hybrid_search(
    query="Python script error handling",
    category=KnowledgeBaseCategory.ERROR_SOLUTIONS,
    limit=5
)
```

### 검색 옵션

- **category**: 특정 카테고리로 제한
- **limit**: 결과 개수 제한 (기본값: 5)
- **semantic_weight**: 의미적 검색 가중치 (기본값: 0.7)

## 🤖 AI 에이전트 통합

### 워크플로우 생성 시

AI가 워크플로우를 생성할 때 자동으로 관련 지식을 검색하여 컨텍스트를 제공합니다.

```python
# MetaWorkflowAgent에서 자동으로 실행됨
rag_context = await rag_service.get_relevant_context_for_workflow_generation(
    "Create a data processing workflow"
)
```

### 워크플로우 수정 시

에러가 발생하거나 수정이 필요할 때 관련 해결책을 검색합니다.

```python
# WorkflowModifier에서 자동으로 실행됨
rag_context = await rag_service.get_relevant_context_for_error_fix(
    "KeyError: 'data_field' not found"
)
```

## 📊 성능 모니터링

### 검색 통계

RAG 시스템은 모든 검색 쿼리를 기록하여 성능을 모니터링합니다.

- 검색 쿼리 기록
- 응답 시간 측정
- 결과 품질 추적
- 사용 패턴 분석

### 분석 데이터 확인

"📊 Analytics" 탭에서 다음 정보를 확인할 수 있습니다:

- 지식 베이스 통계
- 문서 처리 상태
- 카테고리별 분포
- 최근 활동

## 🛠️ 고급 기능

### 임베딩 모델 설정

```python
# ChromaDB 컬렉션 설정
collection = rag_service._get_or_create_collection(
    KnowledgeBaseCategory.WORKFLOW_PATTERNS
)
```

### 문서 청킹 설정

```python
# 문서를 청크로 분할
chunks = rag_service.chunk_text(
    text=document_content,
    chunk_size=500,  # 청크 크기
    overlap=50       # 겹치는 부분
)
```

### 커스텀 검색 전략

```python
# 의미적 검색만 사용
semantic_results = await rag_service.search_documents(
    query="your query",
    category=KnowledgeBaseCategory.ERROR_SOLUTIONS,
    limit=5
)

# 키워드 검색만 사용
keyword_results = await rag_service.search_with_keywords(
    query="your query",
    category=KnowledgeBaseCategory.CODE_TEMPLATES,
    limit=5
)
```

## 🔧 문제 해결

### 일반적인 문제

1. **임베딩 생성 실패**
   - OpenAI API 키 확인
   - 네트워크 연결 상태 확인
   - API 할당량 확인

2. **검색 결과 없음**
   - 지식 베이스에 관련 문서가 있는지 확인
   - 검색 쿼리 단어 조정
   - 카테고리 필터 확인

3. **성능 문제**
   - 문서 청크 크기 조정
   - 검색 결과 개수 제한
   - 캐싱 활용

### 로그 확인

```bash
# RAG 관련 로그 확인
tail -f logs/rag_service_*.log
```

## 📈 성능 최적화

### 권장 설정

- **청크 크기**: 500자 (일반 텍스트), 300자 (코드)
- **겹침 크기**: 50자
- **검색 결과**: 5개 이하
- **최소 점수**: 0.7

### 모니터링 지표

- 검색 응답 시간: < 2초
- 검색 정확도: > 80%
- 문서 처리 성공률: > 95%

## 🚀 확장 가능성

### 새로운 카테고리 추가

```python
# 새로운 카테고리 정의
class NewCategory(enum.Enum):
    CUSTOM_CATEGORY = "CUSTOM_CATEGORY"

# 지식 베이스 생성
kb_id = await rag_service.create_knowledge_base(
    name="Custom Knowledge Base",
    description="Custom category for specific use cases",
    category=NewCategory.CUSTOM_CATEGORY
)
```

### 커스텀 검색 로직

```python
# 커스텀 검색 함수 구현
async def custom_search(query: str, custom_params: dict):
    # 커스텀 검색 로직
    results = await rag_service.hybrid_search(query, **custom_params)
    # 결과 후처리
    return processed_results
```

## 📚 예제 사용 사례

### 1. 워크플로우 패턴 추가

```python
# 일반적인 데이터 처리 워크플로우 패턴 추가
pattern_content = """
# 데이터 처리 워크플로우 패턴
1. API에서 데이터 가져오기
2. 데이터 검증 및 정제
3. 비즈니스 로직 적용
4. 결과 저장
5. 알림 전송
"""

await rag_service.add_document(
    knowledge_base_id="workflow_patterns_kb_id",
    title="데이터 처리 워크플로우 패턴",
    content=pattern_content,
    content_type=DocumentContentType.TEMPLATE,
    tags=["data", "processing", "pattern"]
)
```

### 2. 에러 해결책 추가

```python
# 일반적인 Python 에러 해결책 추가
error_solution = """
# KeyError 해결 방법
원인: 변수가 존재하지 않음
해결: variables.get('key', default_value) 사용
예제: data = variables.get('data', [])
"""

await rag_service.add_document(
    knowledge_base_id="error_solutions_kb_id",
    title="KeyError 해결 방법",
    content=error_solution,
    content_type=DocumentContentType.ERROR_SOLUTION,
    tags=["python", "keyerror", "solution"]
)
```

### 3. 코드 템플릿 추가

```python
# 안전한 Python 스크립트 템플릿 추가
template_code = """
#!/usr/bin/env python3
import json
import sys

def main():
    # 변수 파싱
    variables = {}
    if '--variables-file' in sys.argv:
        # ... 안전한 변수 파싱 로직
    pass

if __name__ == "__main__":
    main()
"""

await rag_service.add_document(
    knowledge_base_id="code_templates_kb_id",
    title="안전한 Python 스크립트 템플릿",
    content=template_code,
    content_type=DocumentContentType.CODE,
    tags=["python", "template", "safe"]
)
```

## 🎉 결론

RAG 시스템을 통해 AI가 더 정확하고 완성도 높은 워크플로우를 생성할 수 있게 됩니다. 지식 베이스를 지속적으로 확장하고 개선하여 시스템의 성능을 향상시킬 수 있습니다.

### 주요 이점

- **정확도 향상**: 관련 지식 기반 생성
- **에러 감소**: 검증된 패턴과 해결책 활용
- **일관성**: 표준화된 접근 방식
- **학습 효과**: 지속적인 지식 축적

RAG 시스템을 활용하여 더욱 강력하고 신뢰할 수 있는 AI 워크플로우 관리 시스템을 구축하세요! 🚀
