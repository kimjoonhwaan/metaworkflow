# 프롬프트 개선: HTML 크롤링 지침 추가 ✅

## 🎯 목표

LLM이 **HTML 크롤링 요청을 받을 때 자동으로 PYTHON_SCRIPT를 사용**하도록 유도

## 📝 추가된 내용

### 1️⃣ API_CALL vs PYTHON_SCRIPT 구분 (line 228-295)

**새로운 섹션:** "⭐ API 호출 vs 웹 크롤링 구분 (매우 중요!)"

```markdown
### REST API 호출 (JSON 응답) → **API_CALL 스텝 사용**
- 기상청, 뉴스 API, 금융 API 등
- JSON 응답 반환
- MCP가 처리

### HTML 크롤링 & 웹 스크래핑 → **PYTHON_SCRIPT 스텝 사용**
- BeautifulSoup으로 파싱
- CSS 선택자로 추출
- User-Agent 헤더 필수
```

**크롤링 요청 감지 키워드:**
- "크롤링해줘", "웹사이트에서 긁어와", "HTML에서 추출해줘"
- "뉴스 페이지에서 기사 가져와", "상품 정보 수집해줘"
- "웹페이지의 데이터를 모아줘", "스크래핑해줘"

### 2️⃣ PYTHON_SCRIPT 설명 강화 (line 321-338)

**추가된 내용:**
```markdown
- 주요 사용 사례 (우선순위순):
  1. **HTML 크롤링 & 파싱** (BeautifulSoup + requests) - 가장 흔함!
  2. 데이터 변환 & 정제 (pandas, json processing)
  3. 파일 처리 (PDF, CSV, Excel 파싱)
  4. 이미지 처리 (PIL, resize, convert)
  5. 복잡한 비즈니스 로직

- 크롤링 코드 패턴 (필수!):
  * import requests, from bs4 import BeautifulSoup
  * headers = {'User-Agent': 'Mozilla/5.0...'}
  * response = requests.get(url, headers=headers, timeout=10)
  * soup = BeautifulSoup(response.text, 'html.parser')
  * items = soup.select('.article-class')  (CSS 선택자)

- metadata.python_requirements 필수 추가:
  * 크롤링: requests, beautifulsoup4
  * 데이터: pandas, numpy
  * 파일: PyPDF2, python-docx, openpyxl
  * 이미지: Pillow, pytesseract
```

### 3️⃣ CRITICAL RULES에 크롤링 규칙 추가 (line 382-392)

**새로운 섹션:** "### 6. HTML 크롤링 & 웹 스크래핑 규칙"

```markdown
### 6. HTML 크롤링 & 웹 스크래핑 규칙 (⭐ 매우 중요!)
- ✅ HTML 크롤링은 PYTHON_SCRIPT 사용 (BeautifulSoup + requests)
- ✅ User-Agent 헤더 필수 추가 (웹사이트 차단 우회)
- ✅ CSS 선택자로 데이터 추출 (soup.select('.class-name'))
- ✅ try-except로 네트워크 에러 처리
- ✅ 구조화된 JSON으로 결과 반환
- ✅ metadata.python_requirements에 requests, beautifulsoup4 추가
- ❌ API_CALL로 HTML 크롤링 시도 금지
- ❌ 파싱 없이 원본 HTML 반환 금지
- ❌ User-Agent 헤더 없이 요청 금지 (WAF 차단됨)
- **이유**: HTML은 반정형 데이터이므로 BeautifulSoup로 파싱 필수. API_CALL은 JSON API용
```

---

## ✅ 수정 효과

### 이전 (문제)
```
사용자: "네이버에서 뉴스 크롤링해줘"
LLM: API_CALL 스텝 생성 → API 응답이 JSON이 아니므로 실패
```

### 이후 (개선)
```
사용자: "네이버에서 뉴스 크롤링해줘"
LLM: PYTHON_SCRIPT 스텝 생성
      ├─ BeautifulSoup 임포트
      ├─ requests로 HTML 다운로드
      ├─ CSS 선택자로 파싱
      └─ 구조화된 JSON 반환 ✅ 성공!
```

---

## 📊 코드 통계

| 항목 | 값 |
|------|-----|
| 수정된 파일 | 1개 (src/agents/prompts.py) |
| 추가된 섹션 | 3개 |
| 추가된 줄 | ~70줄 |
| 삭제된 줄 | 0줄 |
| Lint 에러 | 0개 ✅ |

---

## 🎯 LLM의 의사결정 흐름

이제 LLM이 다음과 같이 판단합니다:

```
사용자 입력 분석
    ↓
크롤링 키워드 감지?
    ├─ YES: PYTHON_SCRIPT + BeautifulSoup ✅
    │       ├─ User-Agent 헤더 추가
    │       ├─ CSS 선택자 사용
    │       └─ JSON 반환
    │
    └─ NO: 
        JSON API 호출?
            ├─ YES: API_CALL + MCP ✅
            └─ NO: 다른 타입 결정
```

---

## 📚 관련 가이드

- `LATEST_CHANGES.md` - 최신 변경사항
- `FIXES_1_2_3_4_SUMMARY.md` - 4가지 주요 수정
- `API_CALL_RESPONSE_STRUCTURE.md` - API_CALL 가이드

---

## ✨ 다음 단계

이제 시스템은:
1. ✅ API 응답 구조 통일 (Fix #1-4)
2. ✅ 크롤링 자동 감지 (이번 수정)
3. ⏳ 크롤링 성공률 모니터링
4. ⏳ 기타 MCPs (Slack, Database) 추가

---

## 💾 커밋 메시지

```
✨ LLM 프롬프트 개선: HTML 크롤링 자동 감지

- API_CALL vs PYTHON_SCRIPT 명확한 구분
- 크롤링 요청 키워드 감지 가이드 추가
- BeautifulSoup 코드 패턴 제시
- CRITICAL RULES에 크롤링 규칙 추가
- User-Agent 헤더 필수 명시 (WAF 우회)

결과: 크롤링 요청 시 LLM이 자동으로 PYTHON_SCRIPT 생성
```

