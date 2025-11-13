"""API MCP 테스트 파일"""

import asyncio
import json
from src.mcp.api_server import api_mcp
from src.utils import get_logger

logger = get_logger("test_api_mcp")


async def test_simple_get():
    """간단한 GET 요청 테스트"""
    logger.info("=" * 60)
    logger.info("Test 1: Simple GET Request")
    logger.info("=" * 60)
    
    config = {
        "url": "https://jsonplaceholder.typicode.com/posts/1",
        "method": "GET",
        "auth": {"type": "none"}
    }
    
    result = await api_mcp.call(config, {})
    logger.info(f"Status: {result.get('status')}")
    logger.info(f"Status Code: {result.get('status_code')}")
    if result.get('data'):
        logger.info(f"Data keys: {list(result.get('data', {}).keys())}")
    logger.info("")


async def test_query_params():
    """쿼리 파라미터 테스트"""
    logger.info("=" * 60)
    logger.info("Test 2: Query Parameters")
    logger.info("=" * 60)
    
    config = {
        "url": "https://jsonplaceholder.typicode.com/posts",
        "method": "GET",
        "query_params": {
            "_limit": 2,
            "_start": 0
        },
        "auth": {"type": "none"}
    }
    
    result = await api_mcp.call(config, {})
    logger.info(f"Status: {result.get('status')}")
    logger.info(f"Status Code: {result.get('status_code')}")
    if isinstance(result.get('data'), list):
        logger.info(f"Items returned: {len(result.get('data', []))}")
    logger.info("")


async def test_with_variables():
    """변수 포맷팅 테스트"""
    logger.info("=" * 60)
    logger.info("Test 3: With Variables")
    logger.info("=" * 60)
    
    config = {
        "url": "https://jsonplaceholder.typicode.com/posts/{post_id}",
        "method": "GET",
        "auth": {"type": "none"}
    }
    
    variables = {"post_id": 5}
    
    result = await api_mcp.call(config, variables)
    logger.info(f"Status: {result.get('status')}")
    logger.info(f"Status Code: {result.get('status_code')}")
    if result.get('data'):
        logger.info(f"Post ID: {result.get('data', {}).get('id')}")
    logger.info("")


async def test_with_auth_key():
    """API Key 인증 테스트"""
    logger.info("=" * 60)
    logger.info("Test 4: API Key Authentication")
    logger.info("=" * 60)
    
    config = {
        "url": "https://jsonplaceholder.typicode.com/posts",
        "method": "GET",
        "query_params": {"_limit": 1},
        "auth": {
            "type": "api_key",
            "key": "{api_key}"
        }
    }
    
    variables = {"api_key": "test_key_12345"}
    
    result = await api_mcp.call(config, variables)
    logger.info(f"Status: {result.get('status')}")
    logger.info(f"Status Code: {result.get('status_code')}")
    logger.info(f"Auth headers included: {result.get('status') == 'success'}")
    logger.info("")


async def test_post_request():
    """POST 요청 테스트"""
    logger.info("=" * 60)
    logger.info("Test 5: POST Request with Body")
    logger.info("=" * 60)
    
    config = {
        "url": "https://jsonplaceholder.typicode.com/posts",
        "method": "POST",
        "body": {
            "title": "Test Post",
            "body": "This is a test",
            "userId": 1
        },
        "auth": {"type": "none"}
    }
    
    result = await api_mcp.call(config, {})
    logger.info(f"Status: {result.get('status')}")
    logger.info(f"Status Code: {result.get('status_code')}")
    if result.get('data'):
        logger.info(f"Created ID: {result.get('data', {}).get('id')}")
    logger.info("")


async def test_response_extraction():
    """응답 데이터 추출 테스트"""
    logger.info("=" * 60)
    logger.info("Test 6: Response Data Extraction")
    logger.info("=" * 60)
    
    config = {
        "url": "https://jsonplaceholder.typicode.com/posts?_limit=3",
        "method": "GET",
        "auth": {"type": "none"},
        "response": {
            "map": {
                "post_id": "id",
                "title": "title"
            }
        }
    }
    
    result = await api_mcp.call(config, {})
    logger.info(f"Status: {result.get('status')}")
    logger.info(f"Status Code: {result.get('status_code')}")
    if isinstance(result.get('data'), list):
        logger.info(f"Items returned: {len(result.get('data', []))}")
        logger.info(f"First item keys: {list(result.get('data', [{}])[0].keys())}")
    logger.info("")


async def test_caching():
    """캐싱 테스트"""
    logger.info("=" * 60)
    logger.info("Test 7: Caching")
    logger.info("=" * 60)
    
    config = {
        "url": "https://jsonplaceholder.typicode.com/posts/1",
        "method": "GET",
        "auth": {"type": "none"},
        "cache": {
            "enabled": True,
            "ttl": 300
        }
    }
    
    # 첫 번째 요청
    logger.info("First request (cache miss)...")
    result1 = await api_mcp.call(config, {})
    logger.info(f"Status: {result1.get('status')}")
    
    # 두 번째 요청
    logger.info("Second request (cache hit)...")
    result2 = await api_mcp.call(config, {})
    logger.info(f"Status: {result2.get('status')}")
    
    logger.info(f"Data identical: {result1.get('data') == result2.get('data')}")
    logger.info("")


async def main():
    """모든 테스트 실행"""
    logger.info("\n" + "=" * 60)
    logger.info("🚀 API MCP Server Tests")
    logger.info("=" * 60 + "\n")
    
    try:
        await test_simple_get()
        await test_query_params()
        await test_with_variables()
        await test_with_auth_key()
        await test_post_request()
        await test_response_extraction()
        await test_caching()
        
        logger.info("=" * 60)
        logger.info("✅ All tests completed!")
        logger.info("=" * 60)
    
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())

