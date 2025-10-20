# RAG (Retrieval-Augmented Generation) 시스템 설계

## 🎯 목표

워크플로우 생성 및 수정 시 AI가 더 정확하고 완성도 높은 결과를 생성할 수 있도록 RAG 시스템을 도입하여 오류와 실패를 감소시킵니다.

## 🏗️ 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                        RAG System Architecture                  │
│                                                                 │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐  │
│  │   Document   │   Embedding  │   Vector     │   Retrieval  │  │
│  │   Storage    │   Generator  │   Database   │   Engine     │  │
│  └──────┬───────┴──────┬───────┴──────┬───────┴──────┬───────┘  │
│         │              │              │              │         │
│         ▼              ▼              ▼              ▼         │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐  │
│  │  Knowledge   │   OpenAI     │   ChromaDB   │   Semantic   │  │
│  │   Base       │   Embeddings │   (Vector)   │   Search     │  │
│  │   (SQLite)   │   API        │   Storage    │   Logic      │  │
│  └──────────────┴──────────────┴──────────────┴──────────────┘  │
│         │              │              │              │         │
└─────────┼──────────────┼──────────────┼──────────────┼─────────┘
          │              │              │              │
          └──────────────┼──────────────┼──────────────┘
                         │              │
                    ┌────▼──────┐   ┌───▼────────┐
                    │   AI      │   │  Workflow  │
                    │  Agents   │   │  Engine    │
                    └───────────┘   └────────────┘
```

## 📊 데이터 모델

### 1. Knowledge Base (지식 베이스)
```python
class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    category = Column(String)  # "workflow_patterns", "error_solutions", "best_practices"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
```

### 2. Document (문서)
```python
class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True)
    knowledge_base_id = Column(String, ForeignKey("knowledge_bases.id"))
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    content_type = Column(String)  # "text", "code", "example", "error_solution"
    metadata = Column(JSON)  # 추가 메타데이터
    embedding_id = Column(String)  # ChromaDB에서의 ID
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### 3. Document Chunk (문서 청크)
```python
class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    
    id = Column(String, primary_key=True)
    document_id = Column(String, ForeignKey("documents.id"))
    chunk_index = Column(Integer)
    content = Column(Text, nullable=False)
    embedding_id = Column(String)  # ChromaDB에서의 ID
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
```

## 🔍 검색 및 임베딩 전략

### 1. 문서 청킹 (Chunking)
- **텍스트 문서**: 500자 단위로 분할
- **코드 문서**: 함수/클래스 단위로 분할
- **예제 문서**: 완전한 예제 단위로 분할

### 2. 임베딩 생성
- **모델**: OpenAI `text-embedding-3-small`
- **차원**: 1536차원
- **저장**: ChromaDB에 벡터 저장

### 3. 검색 전략
```python
class RAGSearchStrategy:
    def __init__(self):
        self.semantic_weight = 0.7
        self.keyword_weight = 0.3
    
    def search(self, query: str, category: str = None, limit: int = 5):
        # 1. 의미적 검색 (벡터 유사도)
        semantic_results = self.semantic_search(query, limit * 2)
        
        # 2. 키워드 검색 (BM25)
        keyword_results = self.keyword_search(query, limit * 2)
        
        # 3. 하이브리드 랭킹
        combined_results = self.hybrid_ranking(
            semantic_results, keyword_results
        )
        
        return combined_results[:limit]
```

## 🎯 RAG 통합 포인트

### 1. 워크플로우 생성 시
```python
class MetaWorkflowAgent:
    async def create_workflow_with_rag(self, user_input: str):
        # 1. 사용자 입력 분석
        intent = self.analyze_intent(user_input)
        
        # 2. 관련 지식 검색
        relevant_docs = await self.rag_service.search(
            query=user_input,
            category="workflow_patterns",
            limit=3
        )
        
        # 3. 컨텍스트 구성
        context = self.build_context(relevant_docs)
        
        # 4. LLM 호출 (컨텍스트 포함)
        workflow = await self.llm.ainvoke([
            SystemMessage(content=self.system_prompt + context),
            HumanMessage(content=user_input)
        ])
        
        return workflow
```

### 2. 워크플로우 수정 시
```python
class WorkflowModifier:
    async def modify_workflow_with_rag(self, workflow, error_logs: str):
        # 1. 에러 패턴 분석
        error_pattern = self.analyze_error_pattern(error_logs)
        
        # 2. 관련 해결책 검색
        solutions = await self.rag_service.search(
            query=error_pattern,
            category="error_solutions",
            limit=3
        )
        
        # 3. 수정 컨텍스트 구성
        context = self.build_fix_context(solutions, error_logs)
        
        # 4. LLM 호출 (해결책 포함)
        modified_workflow = await self.llm.ainvoke([
            SystemMessage(content=self.modification_prompt + context),
            HumanMessage(content=f"Fix this error: {error_logs}")
        ])
        
        return modified_workflow
```

## 📚 지식 베이스 카테고리

### 1. Workflow Patterns (워크플로우 패턴)
- 일반적인 워크플로우 템플릿
- 업계별 베스트 프랙티스
- 성공 사례

### 2. Error Solutions (에러 해결책)
- 일반적인 Python 오류 해결법
- API 호출 실패 대응
- 데이터 처리 오류 해결

### 3. Code Templates (코드 템플릿)
- 검증된 Python 스크립트 템플릿
- 에러 처리 패턴
- 성능 최적화 코드

### 4. Integration Examples (통합 예제)
- 외부 API 연동 예제
- 데이터베이스 연동 패턴
- 알림 시스템 연동

## 🔧 기술 스택

### 벡터 데이터베이스
- **ChromaDB**: 경량화된 벡터 데이터베이스
- **로컬 설치**: 별도 서버 불필요
- **Python SDK**: 쉬운 통합

### 임베딩 모델
- **OpenAI text-embedding-3-small**: 비용 효율적
- **차원**: 1536차원
- **API**: 기존 OpenAI 계정 활용

### 검색 엔진
- **하이브리드 검색**: 의미적 + 키워드 검색
- **랭킹 알고리즘**: BM25 + 코사인 유사도
- **필터링**: 카테고리, 메타데이터 기반

## 📈 성능 최적화

### 1. 캐싱 전략
- **임베딩 캐싱**: 동일 문서 재처리 방지
- **검색 결과 캐싱**: 빈번한 쿼리 결과 캐시
- **컨텍스트 캐싱**: 자주 사용되는 컨텍스트 캐시

### 2. 배치 처리
- **문서 임베딩**: 배치 단위로 임베딩 생성
- **청킹**: 비동기 청킹 처리
- **인덱싱**: 백그라운드 인덱싱

### 3. 모니터링
- **검색 성능**: 응답 시간, 정확도
- **사용 패턴**: 인기 쿼리, 카테고리
- **품질 지표**: 생성된 워크플로우 성공률

## 🚀 구현 단계

### Phase 1: 기본 RAG 인프라
1. 데이터베이스 모델 추가
2. ChromaDB 설정
3. 기본 검색 서비스 구현

### Phase 2: AI 에이전트 통합
1. MetaWorkflowAgent에 RAG 통합
2. WorkflowModifier에 RAG 통합
3. 컨텍스트 빌딩 로직 구현

### Phase 3: UI 및 관리 기능
1. 문서 관리 UI
2. 지식 베이스 관리
3. 검색 결과 시각화

### Phase 4: 최적화 및 모니터링
1. 성능 최적화
2. 품질 지표 모니터링
3. 자동 품질 개선

## 📊 예상 효과

### 정확도 향상
- **워크플로우 생성 정확도**: +30%
- **에러 해결 성공률**: +50%
- **코드 품질**: +40%

### 사용자 경험 개선
- **생성 시간 단축**: -20%
- **재시도 횟수 감소**: -60%
- **만족도 향상**: +35%

### 시스템 안정성
- **실행 실패율 감소**: -45%
- **에러 복구 시간 단축**: -70%
- **운영 비용 절감**: -25%

---

이 RAG 시스템을 통해 AI가 더 정확하고 완성도 높은 워크플로우를 생성할 수 있게 됩니다! 🚀✨
