#!/usr/bin/env python3
"""Test RAG system functionality"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set environment variables
os.environ["OPENAI_API_KEY"] = "dummy_key"

from src.services.rag_service import get_rag_service

async def test_rag():
    """Test RAG system"""
    print("🧠 Testing RAG system...")
    
    try:
        rag = get_rag_service()
        print("✅ RAG service initialized successfully")
        
        # Test search
        print("\n🔍 Testing search functionality...")
        results = await rag.hybrid_search('워크플로우 생성', limit=3)
        print(f"검색 결과 수: {len(results)}")
        
        for i, result in enumerate(results):
            print(f"\n{i+1}. {result['metadata']['title']} (점수: {result['final_score']:.3f})")
            print(f"   내용: {result['content'][:100]}...")
        
        if len(results) == 0:
            print("⚠️ 검색 결과가 없습니다. 지식 베이스에 문서를 추가해보세요.")
        
        # Test context generation
        print("\n📝 Testing context generation...")
        context = await rag.get_relevant_context_for_workflow_generation("데이터 처리 워크플로우를 만들어줘")
        print(f"생성된 컨텍스트 길이: {len(context)}자")
        
        if context:
            print(f"컨텍스트 미리보기: {context[:200]}...")
        else:
            print("⚠️ 컨텍스트가 생성되지 않았습니다.")
        
        print("\n✅ RAG 시스템 테스트 완료!")
        
    except Exception as e:
        print(f"❌ RAG 시스템 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_rag())
