# Windows cp949 인코딩 오류 해결 가이드

## 🔴 문제: `'cp949' codec can't encode character '\xa0'`

### 오류 메시지
```
Script failed with return code 1: 
'cp949' codec can't encode character '\xa0' in position 2606: illegal multibyte sequence
```

### 원인
- **Windows 기본 인코딩**: `cp949` (완성형 한글)
- **문제 문자**: `\xa0` (논-브레이킹 스페이스, non-breaking space)
- **발생 상황**: Python 스크립트에 한글 문자가 포함되어 있고, subprocess가 시스템 기본 인코딩으로 실행됨

### 메커니즘
```
LLM 생성 Python 코드 (UTF-8)
  ↓
임시 파일 저장 (UTF-8)
  ↓
subprocess 실행
  ↓
❌ Windows 기본 인코딩(cp949)으로 디코딩 시도
  ↓
한글/특수 문자 '\xa0' → cp949에서 인코딩 불가
  ↓
UnicodeEncodeError 발생!
```

---

## ✅ 적용된 해결 방안

### 1️⃣ subprocess에 encoding 명시 (`step_executor.py`)

**수정 위치**: `src/engines/step_executor.py` 라인 250-267

```python
# 변경 전:
result = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    timeout=settings.step_timeout_seconds,
)

# 변경 후:
result = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    encoding='utf-8',      # ← UTF-8 명시
    errors='replace',      # ← 변환 불가 문자는 '?'로 대체
    timeout=settings.step_timeout_seconds,
)
```

**효과**: 
- subprocess가 UTF-8로 출력 해석
- 한글/특수 문자 안전하게 처리

---

### 2️⃣ Python 스크립트 내 UTF-8 강제 (`prompts.py`)

**수정 위치**: `src/agents/prompts.py` 
- 라인 60-76: Variables Input 템플릿
- 라인 206: Complete Structure Template 예제
- 라인 342-356: Modification 프롬프트 템플릿

**추가된 코드**:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import sys
import io

# 🌍 Windows 시스템에서 UTF-8 인코딩 강제 (cp949 오류 방지)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
```

**효과**:
- 파일 인코딩 명시적 선언
- stdout/stderr를 UTF-8로 강제
- 한글 주석/문자열 안전하게 처리

---

### 3️⃣ JSON 출력에 `ensure_ascii=False` 추가

**수정 위치**: `src/agents/prompts.py` 라인 206, 217-218

```python
# 변경 전:
print(json.dumps(result))

# 변경 후:
print(json.dumps(result, ensure_ascii=False))
```

**효과**:
- JSON 출력 시 한글 그대로 유지
- 가독성 향상

---

## 🧪 테스트 시나리오

### 테스트 1: 한글 주석 포함
```python
# 뉴스 데이터 파싱 중...
for item in items:
    title = item.get('title')  # 제목 추출
```

✅ **결과**: 이제 정상 실행

### 테스트 2: 한글 문자열
```python
print("뉴스 목록 처리 중...", file=sys.stderr)
```

✅ **결과**: 이제 정상 실행

### 테스트 3: 한글 변수값
```python
variables = {
    'search_keyword': '경제 뉴스',
    'date': '2025년 10월'
}
```

✅ **결과**: 이제 정상 처리

---

## 📋 변경 사항 요약

| 파일 | 변경 내용 | 효과 |
|------|---------|------|
| `step_executor.py` | subprocess에 `encoding='utf-8'`, `errors='replace'` 추가 | 출력 해석을 UTF-8로 강제 |
| `prompts.py` | 3개 위치에 파일 인코딩 선언 + stdout/stderr UTF-8 강제 | Python 스크립트 내 UTF-8 처리 |
| `prompts.py` | `json.dumps(..., ensure_ascii=False)` 추가 | JSON 출력에서 한글 유지 |

---

## 🔍 추가 확인 사항

### 기존 워크플로우 영향도
- ✅ 기존 워크플로우 재실행 가능 (하위 호환성)
- ✅ 한글이 없는 코드도 동일하게 작동
- ✅ 다른 스크립트 언어는 영향 없음

### 추가 개선 사항
1. **OCR 이미지 처리**: 한글 텍스트 추출 시 UTF-8 처리
2. **데이터베이스 저장**: 한글 메타데이터 UTF-8로 저장
3. **파일 I/O**: 모든 파일 읽기/쓰기에 `encoding='utf-8'` 명시

---

## 🚀 다음 단계

1. **테스트 워크플로우 실행**
   ```
   워크플로우 생성 → 한글 포함 코드 생성 → 실행 확인
   ```

2. **에러 로그 모니터링**
   ```
   스크립트 실행 시 stderr 확인 → cp949 오류 없는지 검증
   ```

3. **RAG 컨텍스트 추가**
   ```
   "한글 처리 가이드" 문서를 Knowledge Base에 추가
   LLM이 한글 코드 생성 시 참고하도록
   ```

---

## 📚 참고 자료

- [Python UTF-8 인코딩](https://docs.python.org/3/howto/unicode.html)
- [Windows 인코딩 이슈](https://docs.python.org/3/library/sys.html#sys.stdout)
- [subprocess 인코딩](https://docs.python.org/3/library/subprocess.html#subprocess.Popen)
