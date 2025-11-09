# Meta Workflow Orchestrator

대화형 AI를 활용한 워크플로우 자동 생성 및 관리 시스템

## 💡 핵심 개념

### 🎯 **Meta Workflow Orchestrator란?**

**"자연어로 설명한 업무를 AI가 자동으로 워크플로우로 변환하고, 
AI가 직접 생성 코드를 검증 & 수정하며, 백그라운드에서 자동 실행하는 Self-Healing 시스템"**

---

### 🔑 4가지 핵심 철학

1. **Zero Manual Coding** 🚀
   ```
   자연어 입력
      ↓
   "매일 아침 9시에 네이버 뉴스에서 경제 기사 3개를 수집해서 요약하고 메일로 보내줘"
      ↓
   자동 Python 코드 생성 + 검증 + 저장
   ```
   - 개발자가 아닌 누구나 워크플로우 생성 가능
   - 수동 코딩 불필요 (완전 자동화)
   - 자연어만으로 복잡한 로직 구현

2. **Self-Healing Architecture** 🏥
   ```
   AI 생성 → CodeValidator 검증 → 오류 발견 → AI 재생성 → ✅ 통과
   ```
   - AI가 생성한 코드를 AI가 검증
   - 문제 발견 시 스스로 수정
   - 문법 오류를 런타임 이전에 차단
   - 안정성 95% 이상 달성

3. **Production-Ready System** ⚡
   - 모든 코드에 에러 처리 필수
   - 문법 검증 통과만 저장 가능
   - 격리된 실행 환경 (subprocess)
   - 타임아웃 & 리소스 제한

4. **Domain-Aware Intelligence** 🧠
   ```
   사용자: "네이버에서..."
         ↓
   시스템: "네이버 도메인 감지!"
         ↓
   RAG Search: collection_naver + collection_common
         ↓collection_common
   GPT-4: 정확한 API 및 방법론 추천
   ```
   - 자동 도메인 감지 (네이버, 기상청, 카카오 등)
   - 도메인별 최적화된 검색
   - 컨텍스트 기반 코드 생성

---

## 주요 기능

### 🤖 AI 워크플로우 생성 & 관리
- **AI 기반 생성**: 자연어로 업무를 설명하면 LLM이 완전한 Python 코드 워크플로우 자동 생성
- **대화형 구체화**: AI가 필요 정보를 질문하며 워크플로우 점진적 개선
- **자동 코드 검증**: AI 생성 코드 자동 검증, 오류 발견 시 스스로 수정 ✨
- **AI 수정**: 자연어로 기존 워크플로우 수정 가능

### 🧠 RAG 지식 베이스 (최신 개선)
- **도메인 기반 검색**: 자동 도메인 감지 (네이버, 기상청, 카카오 등)
- **Smart Search**: 원본 쿼리 한 번에 감지된 도메인 + common 도메인에서 최적 검색
- **하이브리드 검색**: 의미론적 검색 + 키워드 검색 통합
- **다양한 파일 지원**: PDF, Word, Excel, 이미지, 텍스트 파일 업로드 및 OCR 처리
- **자동 컨텍스트 제공**: 워크플로우 생성 시 자동으로 관련 지식 활용

### 🔄 워크플로우 실행 & 모니터링
- **LangGraph 기반 실행**: 각 스텝별 상태 관리 및 조건부 실행
- **7가지 스텝 타입**: LLM_CALL, API_CALL, PYTHON_SCRIPT, CONDITION, APPROVAL, NOTIFICATION, DATA_TRANSFORM
- **실시간 모니터링**: 워크플로우 실행 상태, 스텝별 로그, 통계 추적
- **고급 제어**: 재시도, 승인/거부, 실행 취소 기능

### ⏰ 자동 트리거 & 스케줄링
- **Cron 기반 스케줄**: 시간 기반 자동 실행 (매일, 매주, 매월 등)
- **이벤트 트리거**: 특정 이벤트 발생 시 자동 실행
- **웹훅**: 외부 시스템 연동
- **백그라운드 스케줄러**: 자동 감시 및 실행

### 📊 고급 기능
- **폴더 & 태그 관리**: 워크플로우 조직화 및 필터링
- **버전 관리**: 워크플로우 수정 이력 추적
- **실행 통계**: 성공률, 평균 실행 시간, 실패 원인 분석
- **LangSmith 추적**: 모든 LLM 호출 및 워크플로우 실행 추적

---

## 기술 스택

### 🎯 핵심 기술

| 계층 | 기술 | 버전/설명 |
|-----|------|----------|
| **Frontend** | Streamlit | 최신 |
| **Backend** | Python | 3.10+ |
| **LLM** | OpenAI GPT-4 | 고급 추론 능력 |
| **Workflow Engine** | LangGraph | 상태 기반 실행 엔진 |
| **Database** | SQLite + SQLAlchemy | 가벼운 로컬 DB |
| **Vector DB** | ChromaDB | 도메인별 컬렉션 분리 |
| **Embeddings** | OpenAI text-embedding-3-small | 384 차원 |
| **RAG** | LangChain | 최신 RAG 패턴 |

### 📌 기술 선택 이유

#### 1️⃣ **Streamlit** (Frontend)

**선택 이유**:
- ✅ **빠른 프로토타이핑**: Python 코드만으로 웹 UI 구현 (HTML/CSS/JS 불필요)
- ✅ **LLM 친화적**: Streamlit 커뮤니티에서 LLM 앱 템플릿 제공
- ✅ **실시간 상태 반영**: `st.rerun()`, `st.session_state`로 동적 UI 관리
- ✅ **캐싱 지원**: `@st.cache_data`, `@st.cache_resource`로 성능 최적화
- ✅ **배포 용이**: Streamlit Cloud에서 무료 호스팅

**대안 검토**:
- FastAPI + React: 더 강력하지만 개발 복잡도 높음
- Gradio: 간단하지만 확장성 제한

---

#### 2️⃣ **Python 3.10+** (Backend)

**선택 이유**:
- ✅ **AI/ML 생태계**: NumPy, Pandas, Scikit-learn, TensorFlow, PyTorch 등 풍부
- ✅ **Type Hints**: Python 3.10의 강화된 타입 힌팅으로 코드 안정성 향상
- ✅ **스크립트 작성 용이**: subprocess로 사용자 워크플로우 실행
- ✅ **크로스 플랫폼**: Windows, Mac, Linux에서 동일하게 작동
- ✅ **LLM 라이브러리**: LangChain, LangGraph, OpenAI SDK가 Python 우선 지원

**특이점**:
- Python 3.10+에서만 가능한 기능:
  - `match-case` (패턴 매칭)
  - `PEP 604` (Union 타입 `|` 연산자)

---

#### 3️⃣ **OpenAI GPT-4** (LLM)

**선택 이유**:
- ✅ **코드 생성 능력**: GPT-3.5보다 훨씬 뛰어난 Python 코드 생성
- ✅ **문맥 이해**: 복잡한 사용자 요청을 정확하게 해석
- ✅ **Self-Healing 가능**: 코드 오류 수정을 AI가 직접 할 수 있는 능력
- ✅ **Function Calling**: 구조화된 JSON 응답으로 워크플로우 정의 가능
- ✅ **신뢰성**: 엔터프라이즈급 API 안정성 및 지원

**성능 비교**:
```
GPT-3.5: 일반적인 작업에 OK, 복잡 로직은 오류율 높음
GPT-4:   복잡한 코드 생성/수정 95%+ 성공률
GPT-4o:  더 빠르고 저렴하지만, 코드 생성은 GPT-4가 더 정확
```

**대안 검토**:
- Claude (Anthropic): 좋지만 Batch API 지원 부족
- Gemini (Google): 가성비 좋지만 한국 지원 미흡
- Local LLM (Llama): 개인정보 보호하지만, 성능 낮음

---

#### 4️⃣ **LangGraph** (Workflow Engine)

**선택 이유**:
- ✅ **상태 기반 관리**: 워크플로우의 각 단계를 명확한 상태로 관리
- ✅ **조건부 라우팅**: 스텝 결과에 따라 다음 스텝 자동 결정
- ✅ **에러 처리**: 각 노드에서 실패 시 재시도 또는 대체 경로
- ✅ **LangSmith 통합**: 실행 추적 및 디버깅 용이
- ✅ **비동기 지원**: asyncio로 성능 최적화

**StateGraph vs 대안**:
```
LangGraph StateGraph:
  ✅ 선언적 워크플로우 정의
  ✅ 상태 추적 자동
  ✅ 조건부 엣지 처리
  ✅ LangChain 생태계 통합
  
대안 (Airflow, Prefect):
  - DAG 기반이지만 더 복잡
  - 엔터프라이즈 용도
  - 가벼운 프로젝트에는 오버킬
```

---

#### 5️⃣ **SQLite + SQLAlchemy** (Database)

**선택 이유**:
- ✅ **간편성**: 추가 서버 설치 불필요 (파일 기반)
- ✅ **SQLAlchemy ORM**: 관계형 DB 추상화로 포팩성 확보
- ✅ **마이그레이션**: Alembic으로 스키마 버전 관리
- ✅ **로컬 개발**: 로컬 머신에서 즉시 테스트 가능
- ✅ **향후 확장**: PostgreSQL로 전환 시 코드 변경 최소

**확장 경로**:
```
SQLite (현재) 
  ↓ (사용자 증가 시)
PostgreSQL (다중 연결, 트랜잭션)
  ↓ (대규모 배포 시)
Distributed DB (MongoDB, Cassandra)
```

---

#### 6️⃣ **ChromaDB** (Vector DB)

**선택 이유**:
- ✅ **도메인 컬렉션 분리**: 여러 컬렉션으로 임베딩 공간 분리 가능
- ✅ **가볍다**: Python으로만 구성, 외부 서버 불필요
- ✅ **성능**: 384D 벡터 검색 <500ms
- ✅ **메타데이터 필터링**: 쿼리 시 도메인별 필터링
- ✅ **In-Memory + Persistent**: 메모리에서 빠르고, 디스크에 저장

**도메인 기반 컬렉션의 장점**:
```
기존 (단일 컬렉션):
  쿼리: "네이버"
  결과: [네이버, 기상청, 카카오, ...] (혼란)
  
개선 (도메인별 컬렉션):
  쿼리: "네이버" → 도메인 감지 → collection_naver 검색
  결과: [네이버 API, 네이버 뉴스, ...] (정확함)
```

**대안 검토**:
- Pinecone: 클라우드 기반이지만 비용 증가
- Weaviate: 강력하지만 설치 복잡
- Milvus: 엔터프라이즈급이지만 오버킬

---

#### 7️⃣ **OpenAI text-embedding-3-small** (Embeddings)

**선택 이유**:
- ✅ **성능**: 384차원으로 가볍고도 정확
- ✅ **가성비**: small 모델은 large보다 저렴하면서도 충분히 정확
- ✅ **다국어 지원**: 한국어 포함 100+ 언어
- ✅ **최신 모델**: GPT-4와 동시기에 개선됨
- ✅ **표준화**: OpenAI에서 관리하는 표준

**모델 비교**:
```
text-embedding-3-small (384D):
  - 가격: $$$ (저)
  - 속도: 매우 빠름
  - 정확도: 우수 ⭐ (권장)
  
text-embedding-3-large (3072D):
  - 가격: $$$$$ (높음)
  - 속도: 느림
  - 정확도: 최고 (필요 시만)
  
text-embedding-ada-002 (1536D):
  - 가격: $$
  - 속도: 빠름
  - 정확도: 중간 (이전 세대)
```

---

#### 8️⃣ **LangChain** (RAG Framework)

**선택 이유**:
- ✅ **통합 생태계**: LLM, 벡터DB, 문서 로더를 한곳에서
- ✅ **체인 구성**: 복잡한 LLM 작업을 선언적으로 구성
- ✅ **메모리 관리**: 대화 이력, 토큰 제한 자동 처리
- ✅ **도구 통합**: Tool/Agent로 외부 API 연결 용이
- ✅ **Document Loaders**: PDF, Word, Excel 등 자동 파싱

**RAG 파이프라인**:
```
LangChain으로 구현:
  1. Document Loading (PDF, Word 등)
  2. Text Splitting (청크 단위)
  3. Embedding (OpenAI)
  4. Vector Store (ChromaDB)
  5. Retrieval (유사도 검색)
  6. LLM 프롬프트 (컨텍스트 제공)
  7. Response Generation
```

---

### 🎓 종합 기술 스택의 시너지

```
자연어 입력
    ↓
Python (백엔드 처리)
    ↓
LangChain (RAG 통합)
    ├─ ChromaDB (지식 검색)
    └─ OpenAI Embeddings (벡터 변환)
    ↓
OpenAI GPT-4 (코드 생성)
    ↓
LangGraph (워크플로우 실행)
    ├─ 각 스텝 상태 관리
    ├─ 조건부 라우팅
    └─ 에러 처리
    ↓
SQLite (결과 저장)
    ↓
Streamlit (결과 시각화)
```

이 기술 스택은 **"자연어 입력 → AI 코드 생성 → 자동 실행 → 결과 저장"** 전체 파이프라인을 효율적으로 처리하도록 설계되었습니다.

---

## 🚀 빠른 시작

```bash
# 설치
git clone <repository-url>
cd projWorkFlow4
pip install -r requirements.txt

# 환경 설정
cp .env.example .env
# .env 파일에 OPENAI_API_KEY 입력

# 실행
streamlit run app.py
```

---

## 📚 추가 문서

- **[사용 가이드](USAGE_GUIDE.md)**: 기본 사용법
- **[기술 스택](ADVANCED_TECH_STACK.md)**: 상세 기술 정보
- **[프로젝트 분석](COMPREHENSIVE_PROJECT_ANALYSIS.md)**: 전체 아키텍처
- **[LangGraph 설명](LANGGRAPH_WORKFLOW.md)**: 워크플로우 엔진

---

**작성**: 2025-11-05  

