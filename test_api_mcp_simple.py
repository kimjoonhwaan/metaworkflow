"""간단한 API MCP 테스트"""

import asyncio
import os

# 환경 변수 설정
os.environ["OPENAI_API_KEY"] = "test_key"

from src.mcp.api_server import api_mcp
from src.utils import get_logger

logger = get_logger("test_simple")


async def test_simple_get():
    """간단한 GET 요청 테스트"""
    logger.info("=" * 60)
    logger.info("Test 1: Simple GET Request (JSONPlaceholder)")
    logger.info("=" * 60)
    
    config = {
        "url": "https://jsonplaceholder.typicode.com/posts/1",
        "method": "GET",
        "auth": {"type": "none"}
    }
    
    result = await api_mcp.call(config, {})
    logger.info(f"✅ Status: {result.get('status')}")
    logger.info(f"   Status Code: {result.get('status_code')}")
    if result.get('data'):
        logger.info(f"   Data keys: {list(result.get('data', {}).keys())}")
        logger.info(f"   Post ID: {result.get('data', {}).get('id')}")
    logger.info("")
    
    return result.get('status') == 'success'


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
    logger.info(f"✅ Status: {result.get('status')}")
    logger.info(f"   Status Code: {result.get('status_code')}")
    if isinstance(result.get('data'), list):
        logger.info(f"   Items returned: {len(result.get('data', []))}")
    logger.info("")
    
    return result.get('status') == 'success'


async def test_with_variables():
    """변수 포맷팅 테스트"""
    logger.info("=" * 60)
    logger.info("Test 3: With Variables (URL Path)")
    logger.info("=" * 60)
    
    config = {
        "url": "https://jsonplaceholder.typicode.com/posts/{post_id}",
        "method": "GET",
        "auth": {"type": "none"}
    }
    
    variables = {"post_id": 7}
    
    result = await api_mcp.call(config, variables)
    logger.info(f"✅ Status: {result.get('status')}")
    logger.info(f"   Status Code: {result.get('status_code')}")
    if result.get('data'):
        logger.info(f"   Post ID: {result.get('data', {}).get('id')}")
        logger.info(f"   User ID: {result.get('data', {}).get('userId')}")
    logger.info("")
    
    return result.get('status') == 'success'


async def test_post_request():
    """POST 요청 테스트"""
    logger.info("=" * 60)
    logger.info("Test 4: POST Request with Body")
    logger.info("=" * 60)
    
    config = {
        "url": "https://jsonplaceholder.typicode.com/posts",
        "method": "POST",
        "body": {
            "title": "Test Post from API MCP",
            "body": "This is a test of the API MCP server",
            "userId": 1
        },
        "auth": {"type": "none"}
    }
    
    result = await api_mcp.call(config, {})
    logger.info(f"✅ Status: {result.get('status')}")
    logger.info(f"   Status Code: {result.get('status_code')}")
    if result.get('data'):
        logger.info(f"   Created ID: {result.get('data', {}).get('id')}")
    logger.info("")
    
    return result.get('status') == 'success'


async def test_response_mapping():
    """응답 필드 매핑 테스트"""
    logger.info("=" * 60)
    logger.info("Test 5: Response Field Mapping")
    logger.info("=" * 60)
    
    config = {
        "url": "https://jsonplaceholder.typicode.com/posts?_limit=2",
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
    logger.info(f"✅ Status: {result.get('status')}")
    logger.info(f"   Status Code: {result.get('status_code')}")
    if isinstance(result.get('data'), list) and result.get('data'):
        logger.info(f"   Items returned: {len(result.get('data', []))}")
        logger.info(f"   First item keys: {list(result.get('data', [{}])[0].keys())}")
    logger.info("")
    
    return result.get('status') == 'success'


async def main():
    """모든 테스트 실행"""
    logger.info("\n" + "=" * 60)
    logger.info("🚀 API MCP Server - Phase 1 Tests")
    logger.info("=" * 60 + "\n")
    
    results = []
    
    try:
        results.append(await test_simple_get())
        results.append(await test_query_params())
        results.append(await test_with_variables())
        results.append(await test_post_request())
        results.append(await test_response_mapping())
        
        logger.info("=" * 60)
        logger.info(f"✅ Test Results: {sum(results)}/{len(results)} passed")
        logger.info("=" * 60)
        
        if all(results):
            logger.info("\n🎉 All Phase 1 tests passed! API MCP is working correctly!")
        else:
            logger.info("\n⚠️  Some tests failed. Check logs above.")
    
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())

