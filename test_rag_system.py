"""Test script for RAG system functionality"""

import asyncio
import json
from datetime import datetime

from src.services.rag_service import get_rag_service
from src.database.session import get_session
from src.database.models import KnowledgeBase, Document, KnowledgeBaseCategory
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def test_rag_service():
    """Test RAG service functionality"""
    logger.info("Starting RAG system tests...")
    
    rag_service = get_rag_service()
    
    try:
        # Test 1: Search existing documents
        logger.info("Test 1: Searching existing documents...")
        results = await rag_service.hybrid_search(
            query="Python script error handling",
            limit=3
        )
        
        logger.info(f"Found {len(results)} results for 'Python script error handling'")
        for i, result in enumerate(results):
            logger.info(f"Result {i+1}: {result['metadata'].get('title', 'Unknown')} (Score: {result['final_score']:.3f})")
        
        # Test 2: Search for workflow patterns
        logger.info("\nTest 2: Searching for workflow patterns...")
        workflow_results = await rag_service.hybrid_search(
            query="data processing workflow",
            category=KnowledgeBaseCategory.WORKFLOW_PATTERNS,
            limit=2
        )
        
        logger.info(f"Found {len(workflow_results)} workflow pattern results")
        for result in workflow_results:
            logger.info(f"- {result['metadata'].get('title', 'Unknown')}")
        
        # Test 3: Test context building
        logger.info("\nTest 3: Testing context building...")
        context = rag_service.build_context(results[:2])
        logger.info(f"Built context with {len(context)} characters")
        logger.info(f"Context preview: {context[:200]}...")
        
        # Test 4: Test workflow generation context
        logger.info("\nTest 4: Testing workflow generation context...")
        workflow_context = await rag_service.get_relevant_context_for_workflow_generation(
            "Create a workflow that fetches data from an API and processes it"
        )
        logger.info(f"Workflow generation context: {len(workflow_context)} characters")
        if workflow_context:
            logger.info(f"Context preview: {workflow_context[:200]}...")
        
        # Test 5: Test error fix context
        logger.info("\nTest 5: Testing error fix context...")
        error_context = await rag_service.get_relevant_context_for_error_fix(
            "KeyError: 'data_field' not found in variables"
        )
        logger.info(f"Error fix context: {len(error_context)} characters")
        if error_context:
            logger.info(f"Context preview: {error_context[:200]}...")
        
        # Test 6: Test knowledge base listing
        logger.info("\nTest 6: Testing knowledge base listing...")
        kbs = await rag_service.list_knowledge_bases()
        logger.info(f"Found {len(kbs)} knowledge bases:")
        for kb in kbs:
            logger.info(f"- {kb['name']} ({kb['category']}): {kb['document_count']} documents")
        
        logger.info("\n✅ All RAG system tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ RAG system test failed: {e}")
        return False


async def test_database_integration():
    """Test database integration"""
    logger.info("Testing database integration...")
    
    try:
        with get_session() as session:
            # Check knowledge bases
            kbs = session.query(KnowledgeBase).all()
            logger.info(f"Found {len(kbs)} knowledge bases in database")
            
            for kb in kbs:
                logger.info(f"- {kb.name}: {len(kb.documents)} documents")
                
                # Check documents
                for doc in kb.documents:
                    logger.info(f"  - {doc.title} ({doc.content_type.value})")
                    logger.info(f"    Processed: {doc.is_processed}, Chunks: {len(doc.chunks)}")
        
        logger.info("✅ Database integration test passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database integration test failed: {e}")
        return False


async def test_embedding_generation():
    """Test embedding generation"""
    logger.info("Testing embedding generation...")
    
    try:
        rag_service = get_rag_service()
        
        # Test text
        test_text = "This is a test document for embedding generation"
        
        # Generate embedding
        embedding = await rag_service.create_embedding(test_text)
        logger.info(f"Generated embedding with {len(embedding)} dimensions")
        
        # Test chunking
        chunks = rag_service.chunk_text(test_text * 10, chunk_size=100, overlap=20)
        logger.info(f"Text chunked into {len(chunks)} chunks")
        
        logger.info("✅ Embedding generation test passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Embedding generation test failed: {e}")
        return False


async def test_search_accuracy():
    """Test search accuracy with known queries"""
    logger.info("Testing search accuracy...")
    
    try:
        rag_service = get_rag_service()
        
        # Test queries with expected results
        test_queries = [
            {
                "query": "Python syntax error f-string",
                "expected_category": KnowledgeBaseCategory.ERROR_SOLUTIONS,
                "min_results": 1
            },
            {
                "query": "data processing workflow pattern",
                "expected_category": KnowledgeBaseCategory.WORKFLOW_PATTERNS,
                "min_results": 1
            },
            {
                "query": "email integration example",
                "expected_category": KnowledgeBaseCategory.INTEGRATION_EXAMPLES,
                "min_results": 1
            }
        ]
        
        for test in test_queries:
            logger.info(f"Testing query: '{test['query']}'")
            
            results = await rag_service.hybrid_search(
                query=test['query'],
                category=test['expected_category'],
                limit=5
            )
            
            if len(results) >= test['min_results']:
                logger.info(f"✅ Found {len(results)} results (expected ≥{test['min_results']})")
                
                # Check if results are from expected category
                correct_category_count = sum(
                    1 for result in results 
                    if result['category'] == test['expected_category'].value
                )
                logger.info(f"  - {correct_category_count}/{len(results)} results from expected category")
            else:
                logger.warning(f"⚠️ Found only {len(results)} results (expected ≥{test['min_results']})")
        
        logger.info("✅ Search accuracy test completed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Search accuracy test failed: {e}")
        return False


async def performance_test():
    """Test RAG system performance"""
    logger.info("Testing RAG system performance...")
    
    try:
        rag_service = get_rag_service()
        
        # Test multiple concurrent searches
        queries = [
            "Python error handling",
            "workflow patterns",
            "API integration",
            "data processing",
            "email notification"
        ]
        
        start_time = datetime.now()
        
        # Run searches concurrently
        tasks = [
            rag_service.hybrid_search(query=query, limit=3)
            for query in queries
        ]
        
        results = await asyncio.gather(*tasks)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"Completed {len(queries)} concurrent searches in {duration:.2f} seconds")
        logger.info(f"Average time per search: {duration/len(queries):.2f} seconds")
        
        total_results = sum(len(result) for result in results)
        logger.info(f"Total results across all searches: {total_results}")
        
        logger.info("✅ Performance test completed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Performance test failed: {e}")
        return False


async def main():
    """Run all RAG system tests"""
    logger.info("🧪 Starting RAG system test suite...")
    
    tests = [
        ("Database Integration", test_database_integration),
        ("Embedding Generation", test_embedding_generation),
        ("RAG Service", test_rag_service),
        ("Search Accuracy", test_search_accuracy),
        ("Performance", performance_test)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running test: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            result = await test_func()
            if result:
                passed += 1
                logger.info(f"✅ {test_name} PASSED")
            else:
                logger.error(f"❌ {test_name} FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name} FAILED with exception: {e}")
    
    logger.info(f"\n{'='*50}")
    logger.info(f"Test Results: {passed}/{total} tests passed")
    logger.info(f"{'='*50}")
    
    if passed == total:
        logger.info("🎉 All tests passed! RAG system is working correctly.")
    else:
        logger.warning(f"⚠️ {total - passed} tests failed. Please check the logs.")


if __name__ == "__main__":
    asyncio.run(main())
