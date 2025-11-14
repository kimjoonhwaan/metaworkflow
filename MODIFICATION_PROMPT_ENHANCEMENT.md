# 수정 프롬프트 개선: 크롤링 및 API 혼합 호출 지침 추가 ✅

## 🎯 목표

WORKFLOW_MODIFICATION_SYSTEM_PROMPT에 **크롤링 지침과 API 혼합 호출 처리** 추가

## 📝 추가된 내용

### 1️⃣ API_CALL 스텝 수정 가이드 (line 576-603)

**REST API 호출 에러 시 수정 체크리스트:**
- query_params 검토 (파라미터 누락 확인)
- headers 추가/수정 (User-Agent, Authorization)
- body 포맷 검증
- response 설정 추가 (JSONPath extract, field mapping)
- output_mapping 확인 (변수명 충돌)

---

### 2️⃣ HTML 크롤링 & 웹 스크래핑 수정 가이드 (line 606-625)

**크롤링 요청 감지:**
- "크롤링해줘", "웹사이트에서 긁어와", "HTML에서 추출해줘"
- "뉴스 페이지에서 기사 가져와", "상품 정보 수집해줘"

**수정 사항:**
- BeautifulSoup 선택자 최적화
- User-Agent 헤더 추가/수정
- tbody 체크 추가
- CSS 선택자 재검토 (0개 행 반환 문제)
- 에러 처리 개선 (타임아웃, 404, 인코딩)
- 결과 JSON 포맷 검증 (flat structure)

**일반적인 수정:**
- tbody 없는 HTML: `tr_list = table.find_all('tr')[1:]` (헤더 제외)
- 낮은 선택도: 다양한 CSS 선택자 시도
- 응답 인코딩: `response.encoding = 'utf-8'` 설정

---

### 3️⃣ JSON vs HTML 혼합 호출 처리 (line 629-640)

**문제 진단:**
- API_CALL이 JSON 반환하는데 PYTHON_SCRIPT가 HTML 기대
- resultList 비어있음 (데이터 없음)

**수정 사항:**
- input_mapping 검토 (변수명)
- 응답 포맷 변환 (JSON → HTML 또는 JSON 직접 처리)
- 파라미터 검증 (날짜, 지역코드)
- output_mapping 검토 (변수명 충돌)

---

## ✅ 수정 효과

### 이전 (문제)
```
사용자: "workflow를 수정해줘, 크롤링이 실패했어"
LLM: API 관련 지침만 적용 → 크롤링 구체적 가이드 없음
```

### 이후 (개선)
```
사용자: "workflow를 수정해줘, HTML 크롤링이 0개 행을 반환해"
LLM: BeautifulSoup 선택자 최적화, tbody 체크, User-Agent 헤더 → 정확한 수정! ✅
```

---

## 📊 코드 통계

| 항목 | 값 |
|------|-----|
| 파일 | `src/agents/prompts.py` |
| 추가된 섹션 | 3개 |
| 추가된 줄 | ~70줄 |
| Lint 에러 | 0개 ✅ |

---

## 🔄 생성 vs 수정 프롬프트 비교

### 생성 프롬프트 (WORKFLOW_CREATION_SYSTEM_PROMPT)
✅ API_CALL vs PYTHON_SCRIPT 구분
✅ 크롤링 요청 감지
✅ BeautifulSoup 패턴

### 수정 프롬프트 (WORKFLOW_MODIFICATION_SYSTEM_PROMPT)
**이전:**
- ❌ API 호출 지침만 있음
- ❌ 크롤링 지침 없음

**이후:**
- ✅ API_CALL 수정 가이드
- ✅ HTML 크롤링 수정 가이드
- ✅ JSON vs HTML 혼합 호출 처리

---

## 📚 관련 가이드

- `PROMPT_CRAWLING_ENHANCEMENT.md` - 생성 프롬프트 크롤링 개선
- `API_CALL_RESPONSE_STRUCTURE.md` - API_CALL 가이드
- `src/agents/prompts.py` - 전체 프롬프트

---

## ✨ 시스템 개선 요약

현재 시스템:
1. ✅ 생성 프롬프트: API vs 크롤링 구분 (이전)
2. ✅ 수정 프롬프트: API vs 크롤링 구분 (이번)
3. ✅ 4가지 주요 수정 (Fix #1-4)
4. ✅ API 응답 구조 통일

**결과:**
- LLM이 새로운 workflow 생성 시 크롤링 자동 감지 ✅
- LLM이 workflow 수정 시 크롤링 에러 자동 진단 ✅
- 혼합 API 호출 (API_CALL → PYTHON_SCRIPT) 처리 ✅

---

## 💾 커밋 메시지

```
✨ 수정 프롬프트 개선: 크롤링 및 API 혼합 호출 지침 추가

- REST API 호출 스텝 수정 가이드 추가
- HTML 크롤링 & 웹 스크래핑 수정 가이드 추가
- 크롤링 요청 감지 키워드 명시
- JSON vs HTML 혼합 호출 처리 방법 추가
- tbody 없는 HTML 처리 예제
- CSS 선택자 최적화 가이드

결과: 수정 프롬프트와 생성 프롬프트가 동일한 수준의 크롤링 지침 제공
```

---

## 📋 다음 단계

1. 기존 workflows의 에러 로그로 수정 프롬프트 테스트
2. 혼합 API 호출 (API_CALL + PYTHON_SCRIPT) 최적화
3. 다른 MCP 서버 (Slack, Database) 지침 추가 (선택사항)

