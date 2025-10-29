# RAG 청크 분화 해결 - 전체 문맥 전달 가이드

## 📋 문제점: 청크가 너무 분화되어 전체 문맥 손실

### 이전 상황
```
원본 문서:
"한국 경제가 어려워지고 있습니다. GDP 성장률이 감소하고 있습니다. 
 실업률도 증가하고 있습니다. 이는 전 세계 경기 침체 때문입니다."

청크 분화 (chunk_size=500, overlap=50):
├─ chunk_1: "한국 경제가 어려워지고 있습니다. GDP"
├─ chunk_2: "GDP 성장률이 감소하고 있습니다..."
├─ chunk_3: "있습니다. 실업률도 증가하고"
└─ chunk_4: "...전 세계 경기 침체 때문입니다"

↓ LLM에 전달 시
"한국 경제가 어려워지고 있습니다. GDP"

❌ 문제: 단독으로는 의미 불완전
❌ 문제: 전체 문맥 손실
❌ 문제: LLM 생성 코드 품질 저하
```

---

## ✅ 해결책: 3단계 순차 구현

### **1️⃣ 청크 크기/오버랩 증가**

**파일**: `src/services/rag_service.py` 라인 102

```python
# 변경 전
def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50):

# 변경 후
def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200):
```

**효과**:
- 청크 크기: 500 → **1000 토큰** (+100%)
- 오버랩: 50 → **200 토큰** (+300%)
- 더 긴 문맥 보존
- 더 강한 청크 간 연결

**예시**:
```
이전: "한국 경제가 어려워지고 있습니다. GDP"
이후: "한국 경제가 어려워지고 있습니다. GDP 성장률이 감소하고 있습니다. 
      실업률도 증가하고 있습니다. 이는 전 세계 경기 침체 때문입니다."
```

---

### **2️⃣ 검색 함수에 Context 반경 추가**

**파일**: `src/services/rag_service.py` 라인 415-462, 463-515 (신규)

#### **A. `hybrid_search()` 메서드 개선**

```python
async def hybrid_search(
    self,
    query: str,
    category: KnowledgeBaseCategory = None,
    limit: int = 5,
    semantic_weight: float = 0.3,
    include_context: bool = True,      # ← 신규!
    context_radius: int = 1            # ← 신규!
) -> List[Dict[str, Any]]:
```

**파라미터**:
- `include_context`: True = 주변 청크 포함
- `context_radius`: 1 = 앞뒤 1개씩 청크 포함 (총 3개 청크)

#### **B. `_expand_with_context()` 메서드 추가 (신규)**

```python
async def _expand_with_context(
    self,
    results: List[Dict[str, Any]],
    context_radius: int = 1
) -> List[Dict[str, Any]]:
    """인접 청크를 포함하여 결과 확장"""
    
    # 예: context_radius=1인 경우
    # 원본 청크 (chunk_2) + 이전 청크 (chunk_1) + 다음 청크 (chunk_3)
    # = 총 3개 청크를 하나로 병합
```

**동작 메커니즘**:
```
검색 결과: chunk_2 (chunk_index=2)
           ↓
         _expand_with_context(context_radius=1)
           ↓
       경계 계산: start_idx = max(0, 2-1) = 1
                 end_idx = min(len, 2+1+1) = 4
           ↓
       범위: chunks[1:4] = [chunk_1, chunk_2, chunk_3]
           ↓
       병합:
       "[Chunk 1] {...}"
       "[Chunk 2] {...}"
       "[Chunk 3] {...}"
           ↓
       결과에 추가:
       - content: 병합된 전체 텍스트
       - context_chunks_count: 3
       - context_range: "1~3"
```

**반환 데이터 예시**:
```python
{
    "content": "[Chunk 1] 한국 경제가 어려워지고...\n\n[Chunk 2] GDP 성장률이 감소하고...\n\n[Chunk 3] 이는 전 세계 경기 침체...",
    "original_chunk": "GDP 성장률이 감소하고...",  # 원본 보존
    "original_chunk_index": 2,
    "context_chunks_count": 3,
    "context_range": "1~3",
    "metadata": {...},
    "final_score": 0.85
}
```

---

### **3️⃣ LLM 프롬프트에 확장 컨텍스트 적용**

**파일**: `src/services/rag_service.py` 라인 605-650, 651-690

#### **A. 워크플로우 생성 시 (`get_relevant_context_for_workflow_generation`)**

```python
# 변경 전
results = await self.hybrid_search(
    query=user_input,
    category=category,
    limit=3,
    semantic_weight=0.3
)

# 변경 후
results = await self.hybrid_search(
    query=user_input,
    category=category,
    limit=3,
    semantic_weight=0.3,
    include_context=True,      # ✨ 활성화
    context_radius=1           # ✨ 1칸씩 확장
)

# max_tokens도 증가
context = self.build_context(top_results, max_tokens=15000)  # 10000 → 15000
```

#### **B. 오류 해결 시 (`get_relevant_context_for_error_fix`)**

```python
# 변경 전
results = await self.hybrid_search(
    query=error_message,
    category=KnowledgeBaseCategory.ERROR_SOLUTIONS,
    limit=5
)

# 변경 후
results = await self.hybrid_search(
    query=error_message,
    category=KnowledgeBaseCategory.ERROR_SOLUTIONS,
    limit=5,
    include_context=True,      # ✨ 활성화
    context_radius=1           # ✨ 1칸씩 확장
)
```

**효과**:
- LLM이 **더 완전한 문맥** 받음
- 코드 생성 시 **품질 향상**
- 오류 해결 시 **더 정확한 솔루션** 제시

---

## 📊 변경 사항 요약

| 단계 | 파일 | 변경 내용 | 효과 |
|------|------|---------|------|
| 1️⃣ | rag_service.py | chunk_size: 500→1000, overlap: 50→200 | 기본 청크 크기 2배 확대 |
| 2️⃣ | rag_service.py | `hybrid_search()` 개선 + `_expand_with_context()` 추가 | 검색 시 인접 청크 자동 포함 |
| 3️⃣ | rag_service.py | `get_relevant_context_*` 함수에 context 확장 적용 | LLM이 전체 문맥 활용 |

---

## 🎯 최종 효과

### 이전 (문제점)
```
원본: "경제 성장률이 감소했습니다. 이는 수출 부진 때문입니다. 
      정부가 대책을 마련하고 있습니다."

LLM에 전달된 컨텍스트:
"경제 성장률이 감소했습니다. 이는"

❌ LLM: "무엇이 감소했다는 건지 불명확"
❌ 코드 생성: 불완전
❌ 오류율: 높음
```

### 이후 (개선됨)
```
원본: "경제 성장률이 감소했습니다. 이는 수출 부진 때문입니다. 
      정부가 대책을 마련하고 있습니다."

LLM에 전달된 컨텍스트:
"[Chunk 1] 경제 성장률이 감소했습니다.
 [Chunk 2] 이는 수출 부진 때문입니다. 정부가 대책을 마련하고 있습니다.
 [Chunk 3] 정부의 경기 부양 정책은 다음과 같습니다..."

✅ LLM: "명확한 전체 맥락 이해"
✅ 코드 생성: 완전하고 정확
✅ 오류율: 크게 감소
```

---

## 🔧 설정 튜닝 가능

### 더 많은 컨텍스트 필요 시
```python
# context_radius를 2로 증가 (앞뒤 2칸 = 5개 청크)
results = await self.hybrid_search(
    query=query,
    include_context=True,
    context_radius=2  # 1 → 2
)

# max_tokens도 증가
context = self.build_context(results, max_tokens=20000)
```

### 좀 더 간결한 컨텍스트 필요 시
```python
# context 확장 비활성화
results = await self.hybrid_search(
    query=query,
    include_context=False  # True → False
)
```

---

## 🚀 다음 단계

### 1️⃣ 기존 지식 베이스 재처리 (선택사항)
```
기존 문서들이 작은 청크로 저장되었을 수 있으니, 
새로운 문서 업로드 시부터 자동으로 적용됩니다.
```

### 2️⃣ 워크플로우 생성/수정 테스트
```
새로운 워크플로우 생성 → 더 완전한 코드 생성 확인
기존 워크플로우 수정 → 더 정확한 오류 해결 확인
```

### 3️⃣ 모니터링
```
- RAG 컨텍스트 길이 모니터링
- LLM 생성 코드 품질 비교
- 오류율 추이 관찰
```

---

## 📝 기술 세부사항

### Context Expansion 흐름도
```
┌─────────────────────────────────┐
│  Hybrid Search 실행             │
│  (semantic + keyword)           │
└────────────┬────────────────────┘
             ↓
┌─────────────────────────────────┐
│  결과 정렬 및 필터링              │
│  (final_score 기준)             │
└────────────┬────────────────────┘
             ↓
┌─────────────────────────────────┐
│  _expand_with_context() 호출     │
│  (include_context=True)         │
└────────────┬────────────────────┘
             ↓
┌─────────────────────────────────┐
│  DB에서 인접 청크 조회            │
│  (context_radius 범위)          │
└────────────┬────────────────────┘
             ↓
┌─────────────────────────────────┐
│  청크 병합                       │
│  ("[Chunk N] ...")               │
└────────────┬────────────────────┘
             ↓
┌─────────────────────────────────┐
│  메타데이터 추가                  │
│  (context_chunks_count, etc)    │
└────────────┬────────────────────┘
             ↓
┌─────────────────────────────────┐
│  LLM 프롬프트에 전달             │
│  (전체 문맥 포함)               │
└─────────────────────────────────┘
```

### 토큰 사용량 비교

| 구분 | 이전 | 이후 | 증가율 |
|------|------|------|--------|
| 기본 청크 크기 | 500 토큰 | 1000 토큰 | +100% |
| 오버랩 | 50 토큰 | 200 토큰 | +300% |
| 검색 결과 청크 수 | 1 | 3 (context_radius=1) | +200% |
| max_tokens | 10,000 | 15,000 | +50% |

---

## ⚙️ 구현 상세

### 변경된 함수 시그니처

```python
# 1. chunk_text() - 기본 청킹
def chunk_text(
    self,
    text: str,
    chunk_size: int = 1000,    # ↑ 500→1000
    overlap: int = 200          # ↑ 50→200
) -> List[str]

# 2. hybrid_search() - 하이브리드 검색
async def hybrid_search(
    self,
    query: str,
    category: KnowledgeBaseCategory = None,
    limit: int = 5,
    semantic_weight: float = 0.3,
    include_context: bool = True,   # ← 신규
    context_radius: int = 1         # ← 신규
) -> List[Dict[str, Any]]

# 3. _expand_with_context() - 컨텍스트 확장 (신규)
async def _expand_with_context(
    self,
    results: List[Dict[str, Any]],
    context_radius: int = 1
) -> List[Dict[str, Any]]

# 4. get_relevant_context_for_workflow_generation() - 워크플로우 컨텍스트
async def get_relevant_context_for_workflow_generation(
    self,
    user_input: str
    # include_context=True, context_radius=1 적용됨
)

# 5. get_relevant_context_for_error_fix() - 오류 해결 컨텍스트
async def get_relevant_context_for_error_fix(
    self,
    error_message: str,
    workflow_context: str = None
    # include_context=True, context_radius=1 적용됨
)
```

---

이제 LLM이 **완전한 문맥을 기반으로** 더 정확하고 완성도 높은 워크플로우를 생성할 수 있습니다! 🎉
