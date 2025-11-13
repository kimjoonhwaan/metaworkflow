"""범용 REST API MCP 서버 - 모든 REST API 호출 지원"""

import httpx
import json
import base64
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from src.utils import settings, get_logger

logger = get_logger("api_mcp")


class APIMCPServer:
    """범용 REST API 호출 MCP 서버 - 모든 API를 통합 처리"""
    
    def __init__(self):
        """API MCP 서버 초기화"""
        self.timeout = 30
        self.max_retries = 3
        self.cache = {}
        self.cache_ttl = {}
        self.request_count = defaultdict(int)
        self.request_time = defaultdict(list)
        logger.info("✅ APIMCPServer initialized")
    
    async def call(
        self,
        config: Dict[str, Any],
        variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        범용 API 호출
        
        Args:
            config: API 설정
                {
                    "url": "https://api.example.com/endpoint",
                    "method": "GET|POST|PUT|DELETE|PATCH",
                    "auth": {
                        "type": "none|api_key|basic|oauth|jwt|custom",
                        "key": "...",
                        "username": "...",
                        "password": "...",
                        "token": "..."
                    },
                    "headers": {...},
                    "query_params": {...},
                    "body": {...},
                    "timeout": 30,
                    "retry": {
                        "max_retries": 3,
                        "delay": 1,
                        "backoff": 2,
                        "retry_on": [429, 500, 502, 503]
                    },
                    "cache": {
                        "enabled": true,
                        "ttl": 300
                    },
                    "response": {
                        "extract": "data.items",
                        "map": {...}
                    }
                }
            variables: 워크플로우 변수
        
        Returns:
            API 호출 결과
        """
        try:
            logger.info(f"[API_MCP] Calling {config.get('method', 'GET')} {config.get('url')}")
            
            # ✅ 0️⃣ 기본 브라우저 헤더 설정 (처음부터!)
            from urllib.parse import urlparse
            
            try:
                parsed_url = urlparse(config.get("url", ""))
                domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
            except:
                domain = "https://api.example.com"
            
            # 기본 헤더 (모든 API에 공통)
            default_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "ko-KR,ko;q=0.9",
                "Referer": domain,
                "Cache-Control": "no-cache",
                "Pragma": "no-cache"
            }
            logger.debug(f"[API_MCP] Base headers set for domain: {domain}")
            
            # 1️⃣ 인증 처리
            auth_headers = await self._prepare_auth(config, variables)
            default_headers.update(auth_headers)
            if auth_headers:
                logger.debug(f"[API_MCP] Auth headers added")
            
            # 2️⃣ 사용자 정의 헤더 (우선순위: 사용자 > 인증 > 기본)
            user_headers = config.get("headers", {})
            default_headers.update(user_headers)
            if user_headers:
                logger.debug(f"[API_MCP] User headers added: {list(user_headers.keys())}")
            
            headers = default_headers
            logger.debug(f"[API_MCP] Final headers prepared")
            
            # 3️⃣ URL 포맷팅
            url = self._format_url(config.get("url", ""), variables)
            logger.debug(f"[API_MCP] Formatted URL: {url}")
            
            # 4️⃣ 파라미터 준비
            query_params = self._format_params(config.get("query_params", {}), variables)
            body = self._format_body(config.get("body", {}), variables)
            
            logger.debug(f"[API_MCP] Query params: {list(query_params.keys())}")
            
            # 5️⃣ 캐시 확인
            cache_key = self._get_cache_key(url, config)
            if cached := await self._get_cache(cache_key):
                logger.info(f"[API_MCP] ✅ Cache hit for {url}")
                return cached
            
            logger.debug(f"[API_MCP] Cache miss, making request...")
            
            # 6️⃣ 재시도 로직으로 요청
            result = await self._call_with_retry(
                url=url,
                method=config.get("method", "GET"),
                headers=headers,
                params=query_params,
                body=body,
                timeout=config.get("timeout", self.timeout),
                retry_config=config.get("retry", {})
            )
            
            logger.info(f"[API_MCP] ✅ API call successful: {result.get('status_code')}")
            
            # 7️⃣ 응답 변환
            data = self._transform_response(result.get("data"), config.get("response", {}))
            
            # 8️⃣ 캐싱
            response = {
                "status": "success",
                "data": data,
                "status_code": result.get("status_code"),
                "headers": dict(result.get("headers", {}))
            }
            
            if config.get("cache", {}).get("enabled"):
                await self._set_cache(cache_key, response, config.get("cache", {}))
            
            return response
        
        except Exception as e:
            logger.error(f"[API_MCP] ❌ Error: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    async def _prepare_auth(self, config: Dict[str, Any], variables: Dict[str, Any]) -> Dict[str, str]:
        """인증 헤더 생성"""
        auth = config.get("auth", {})
        auth_type = auth.get("type", "none")
        
        if auth_type == "none":
            return {}
        
        try:
            if auth_type == "api_key":
                key = auth.get("key", "").format(**variables)
                logger.debug(f"[API_MCP] Using API Key authentication")
                return {"Authorization": f"Bearer {key}"}
            
            elif auth_type == "basic":
                username = auth.get("username", "").format(**variables)
                password = auth.get("password", "").format(**variables)
                credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
                logger.debug(f"[API_MCP] Using Basic authentication")
                return {"Authorization": f"Basic {credentials}"}
            
            elif auth_type == "jwt":
                token = auth.get("token", "").format(**variables)
                logger.debug(f"[API_MCP] Using JWT authentication")
                return {"Authorization": f"Bearer {token}"}
            
            elif auth_type == "oauth":
                token = auth.get("token", "").format(**variables)
                logger.debug(f"[API_MCP] Using OAuth authentication")
                return {"Authorization": f"Bearer {token}"}
            
            elif auth_type == "custom":
                headers = config.get("headers", {})
                logger.debug(f"[API_MCP] Using custom headers authentication")
                return headers
            
            return {}
        
        except Exception as e:
            logger.warning(f"[API_MCP] Auth preparation failed: {e}")
            return {}
    
    def _format_url(self, url: str, variables: Dict[str, Any]) -> str:
        """URL 포맷팅 - {variable_name} 패턴 치환"""
        try:
            import re
            result = url
            
            # {variable_name} 패턴 찾기
            pattern = r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}'
            matches = re.findall(pattern, url)
            
            if matches:
                logger.debug(f"[API_MCP] Found variables in URL: {matches}")
                for var_name in matches:
                    if var_name in variables:
                        var_value = variables[var_name]
                        result = result.replace(f'{{{var_name}}}', str(var_value))
                        logger.debug(f"[API_MCP] Replaced {{{var_name}}} with {var_value}")
                    else:
                        logger.warning(f"[API_MCP] Variable '{var_name}' not found in variables")
            
            logger.debug(f"[API_MCP] Formatted URL: {result}")
            return result
        except Exception as e:
            logger.warning(f"[API_MCP] Error formatting URL: {e}")
            return url
    
    def _format_params(self, params: Dict[str, Any], variables: Dict[str, Any]) -> Dict[str, Any]:
        """쿼리 파라미터 포맷팅"""
        formatted = {}
        for key, value in params.items():
            try:
                if isinstance(value, str):
                    # 문자열에서 변수 추출 및 포맷팅
                    import re
                    # {variable_name} 패턴 찾기
                    pattern = r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}'
                    matches = re.findall(pattern, value)
                    
                    if matches:
                        # 변수가 포함된 경우
                        result = value
                        for var_name in matches:
                            if var_name in variables:
                                var_value = variables[var_name]
                                result = result.replace(f'{{{var_name}}}', str(var_value))
                            else:
                                logger.warning(f"[API_MCP] Variable '{var_name}' not found in variables")
                        formatted[key] = result
                    else:
                        # 변수가 없는 순수 문자열
                        formatted[key] = value
                else:
                    # 정수, 불린 등 다른 타입은 그대로 사용
                    formatted[key] = value
            except Exception as e:
                logger.warning(f"[API_MCP] Error formatting param '{key}': {e}")
                formatted[key] = value
        
        logger.debug(f"[API_MCP] Formatted params: {formatted}")
        return formatted
    
    def _format_body(self, body: Any, variables: Dict[str, Any]) -> Any:
        """바디 포맷팅"""
        try:
            if isinstance(body, str):
                # 문자열 바디 포맷팅
                import re
                result = body
                pattern = r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}'
                matches = re.findall(pattern, body)
                
                if matches:
                    for var_name in matches:
                        if var_name in variables:
                            var_value = variables[var_name]
                            result = result.replace(f'{{{var_name}}}', str(var_value))
                        else:
                            logger.warning(f"[API_MCP] Variable '{var_name}' not found in body")
                return result
            elif isinstance(body, dict):
                # 딕셔너리 바디 포맷팅
                return self._format_params(body, variables)
            return body
        except Exception as e:
            logger.warning(f"[API_MCP] Body formatting failed: {e}")
            return body
    
    async def _call_with_retry(
        self,
        url: str,
        method: str,
        headers: Dict[str, str],
        params: Dict[str, Any],
        body: Any,
        timeout: int,
        retry_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """재시도 로직으로 API 호출"""
        max_retries = retry_config.get("max_retries", self.max_retries)
        base_delay = retry_config.get("delay", 1)
        backoff = retry_config.get("backoff", 2)
        retry_on = retry_config.get("retry_on", [429, 500, 502, 503])
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"[API_MCP] Attempt {attempt + 1}/{max_retries}")
                
                # ✅ httpx 클라이언트에 디코딩 옵션 추가 (gzip, deflate 자동 처리)
                async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=headers,
                        params=params,
                        json=body if body else None
                    )
                
                logger.debug(f"[API_MCP] Response status: {response.status_code}")
                
                # 성공
                if 200 <= response.status_code < 300:
                    try:
                        data = response.json() if response.content else None
                    except json.JSONDecodeError:
                        data = response.text
                    
                    logger.info(f"[API_MCP] ✅ Success on attempt {attempt + 1}")
                    return {
                        "data": data,
                        "status_code": response.status_code,
                        "headers": response.headers
                    }
                
                # 재시도 가능한 에러
                if response.status_code in retry_on and attempt < max_retries - 1:
                    wait_time = base_delay * (backoff ** attempt)
                    logger.warning(f"[API_MCP] Status {response.status_code}, retrying in {wait_time}s (attempt {attempt + 1})")
                    await asyncio.sleep(wait_time)
                    continue
                
                # 재시도 불가능한 에러 또는 마지막 시도
                error_msg = f"HTTP {response.status_code}"
                try:
                    error_detail = response.json()
                    error_msg += f": {error_detail}"
                except:
                    error_msg += f": {response.text[:200]}"
                
                raise Exception(error_msg)
            
            except httpx.TimeoutException:
                if attempt < max_retries - 1:
                    wait_time = base_delay * (backoff ** attempt)
                    logger.warning(f"[API_MCP] Timeout, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                    continue
                raise
            
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"[API_MCP] Attempt {attempt + 1} failed: {e}")
    
    def _get_cache_key(self, url: str, config: Dict[str, Any]) -> str:
        """캐시 키 생성"""
        method = config.get("method", "GET")
        return f"{method}:{url}"
    
    async def _get_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """캐시에서 조회"""
        if key in self.cache:
            # TTL 확인
            if key in self.cache_ttl and datetime.now() > self.cache_ttl[key]:
                # 만료됨
                del self.cache[key]
                del self.cache_ttl[key]
                return None
            return self.cache[key]
        return None
    
    async def _set_cache(self, key: str, value: Dict[str, Any], cache_config: Dict[str, Any]):
        """캐시에 저장"""
        self.cache[key] = value
        ttl = cache_config.get("ttl", 300)
        self.cache_ttl[key] = datetime.now() + timedelta(seconds=ttl)
        logger.debug(f"[API_MCP] Cached for {ttl}s")
    
    def _transform_response(self, data: Any, transform_config: Dict[str, Any]) -> Any:
        """응답 데이터 변환 (JSONPath 추출, 필드 매핑)"""
        if not transform_config:
            return data
        
        try:
            # JSONPath 추출
            if "extract" in transform_config:
                path = transform_config["extract"]
                current = data
                
                for key in path.split("."):
                    if isinstance(current, dict):
                        current = current.get(key)
                    elif isinstance(current, list):
                        current = [item.get(key) if isinstance(item, dict) else item for item in current]
                
                logger.debug(f"[API_MCP] Extracted path: {path}")
                return current
            
            # 필드 매핑
            if "map" in transform_config:
                mapping = transform_config["map"]
                if isinstance(data, list):
                    return [
                        {new_key: item.get(old_key) for new_key, old_key in mapping.items()}
                        for item in data
                    ]
                elif isinstance(data, dict):
                    return {new_key: data.get(old_key) for new_key, old_key in mapping.items()}
            
            return data
        
        except Exception as e:
            logger.warning(f"[API_MCP] Response transformation failed: {e}")
            return data


# 글로벌 인스턴스
api_mcp = APIMCPServer()

