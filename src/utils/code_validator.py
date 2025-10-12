"""Code validator for Python scripts"""
import ast
import re
from typing import List, Tuple


class CodeValidator:
    """Validates Python code for common errors"""
    
    @staticmethod
    def validate_python_code(code: str) -> Tuple[bool, List[str]]:
        """Validate Python code for syntax and common issues
        
        Args:
            code: Python code to validate
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # 1. Check syntax by parsing AST
        try:
            ast.parse(code)
        except SyntaxError as e:
            issues.append(f"문법 오류 (Line {e.lineno}): {e.msg}")
            return False, issues
        
        # 2. Check for --variables-file handling
        if 'PYTHON_SCRIPT' in code or 'import sys' in code:
            if '--variables-file' not in code:
                if '--variables' in code:
                    issues.append("경고: --variables 대신 --variables-file을 사용해야 합니다 (Windows 명령줄 길이 제한)")
                elif 'argv' not in code:
                    issues.append("경고: --variables-file 인자 처리가 없습니다")
        
        # 3. Check for stdout/stderr usage
        lines = code.split('\n')
        has_stdout_json = False
        problematic_prints = []
        
        for i, line in enumerate(lines, 1):
            # Check for print statements
            if 'print(' in line and 'file=sys.stderr' not in line:
                if 'json.dumps' in line:
                    has_stdout_json = True
                elif 'print(' in line and not line.strip().startswith('#'):
                    problematic_prints.append(f"Line {i}: stdout에 출력 (JSON 파싱 깨질 수 있음)")
        
        if not has_stdout_json:
            issues.append("경고: JSON 출력(print(json.dumps(...)))이 없습니다")
        
        if problematic_prints:
            issues.append("경고: stderr 대신 stdout으로 출력하는 print문 발견")
        
        # 4. Check for f-string quote nesting (MOST COMMON ERROR!)
        fstring_issues = CodeValidator._check_fstring_quotes(code)
        issues.extend(fstring_issues)
        
        # 5. Check for error handling
        if 'try:' not in code or 'except' not in code:
            issues.append("경고: try-except 에러 처리가 없습니다")
        
        # 6. Check imports
        if 'import json' not in code:
            issues.append("경고: json 모듈을 import하지 않았습니다")
        
        if 'import sys' not in code:
            issues.append("경고: sys 모듈을 import하지 않았습니다")
        
        is_valid = len([i for i in issues if i.startswith("문법 오류")]) == 0
        
        return is_valid, issues
    
    @staticmethod
    def _check_fstring_quotes(code: str) -> List[str]:
        """Check for problematic f-string quote nesting
        
        Args:
            code: Python code
            
        Returns:
            List of issues found
        """
        issues = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Check for f-string patterns
            
            # Pattern 1: f'...{dict['key']}...'
            if re.search(r"f'[^']*\{[^}]*\['[^']*'\][^}]*\}", line):
                issues.append(
                    f"문법 오류 (Line {i}): f-string 안에 작은따옴표 중첩 - "
                    f"변수를 먼저 추출하세요"
                )
            
            # Pattern 2: f"...{dict["key"]}..."
            if re.search(r'f"[^"]*\{[^}]*\["[^"]*"\][^}]*\}', line):
                issues.append(
                    f"문법 오류 (Line {i}): f-string 안에 큰따옴표 중첩 - "
                    f"변수를 먼저 추출하세요"
                )
            
            # Pattern 3: Multi-line f-string
            if line.strip().startswith('f"') or line.strip().startswith("f'"):
                if '{' in line and '}' not in line:
                    issues.append(
                        f"경고 (Line {i}): 여러 줄에 걸친 f-string일 수 있음 - "
                        f"각 줄을 개별로 작성하세요"
                    )
        
        return issues
    
    @staticmethod
    def suggest_fix(code: str, issues: List[str]) -> str:
        """Suggest fixes for common issues
        
        Args:
            code: Python code with issues
            issues: List of issues found
            
        Returns:
            Suggested fix or explanation
        """
        suggestions = []
        
        for issue in issues:
            if "f-string 안에" in issue and "따옴표 중첩" in issue:
                suggestions.append(
                    "수정 방법: 변수를 먼저 추출하세요\n"
                    "예시:\n"
                    "  # 수정 전: f'Title: {news['title']}'\n"
                    "  # 수정 후:\n"
                    "  title = news.get('title', 'N/A')\n"
                    "  result = f\"Title: {title}\""
                )
            
            elif "--variables" in issue or "variables-file" in issue:
                suggestions.append(
                    "수정 방법: 스크립트 시작 부분에 다음 코드 추가\n"
                    "  variables = {}\n"
                    "  if '--variables-file' in sys.argv:\n"
                    "      idx = sys.argv.index('--variables-file')\n"
                    "      if idx + 1 < len(sys.argv):\n"
                    "          with open(sys.argv[idx + 1], 'r', encoding='utf-8') as f:\n"
                    "              variables = json.load(f)"
                )
            
            elif "JSON 출력" in issue:
                suggestions.append(
                    "수정 방법: 스크립트 끝에 JSON 출력 추가\n"
                    "  result = {'status': 'success', 'data': your_data}\n"
                    "  print(json.dumps(result))"
                )
        
        return "\n\n".join(suggestions) if suggestions else "문제를 수정하고 다시 시도하세요"

