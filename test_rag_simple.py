#!/usr/bin/env python3
"""
RAG 간단 테스트 - RAG 데이터가 프롬프트에 입력되는지 확인
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import asyncio
import json

async def main():
    print("=" * 80)
    print("🔍 RAG 데이터 조회 테스트")
    print("=" * 80)
    
    try:
        # 1. 데이터베이스 확인
        print("\n1️⃣ 데이터베이스 확인...")
        from database.session import get_session
        from database.models import Document, DocumentChunk, KnowledgeBase
        
        with get_session() as session:
            kb_count = session.query(KnowledgeBase).count()
            doc_count = session.query(Document).filter(Document.is_processed == True).count()
            chunk_count = session.query(DocumentChunk).count()
            
            print(f"   지식 베이스: {kb_count}개")
            print(f"   문서: {doc_count}개")
            print(f"   청크: {chunk_count}개")
            
            if doc_count == 0 or chunk_count == 0:
                print("\n   ⚠️  데이터가 없습니다!")
                return
        
        # 2. RAG 서비스 테스트
        print("\n2️⃣ RAG 서비스 테스트...")
        from services.rag_service import get_rag_service
        
        rag_service = get_rag_service()
        print("   ✅ RAG 서비스 초기화됨")
        
        # 3. 검색 테스트
        print("\n3️⃣ 검색 테스트...")
        test_query = "워크플로우"
        print(f"   쿼리: '{test_query}'")
        
        # 직접 hybrid_search 테스트
        print("\n   3-1. hybrid_search 테스트...")
        results = await rag_service.hybrid_search(
            query=test_query,
            limit=5,
            include_context=True,
            context_radius=1
        )
        print(f"       결과: {len(results)}개")
        
        if results:
            for i, r in enumerate(results[:2], 1):
                print(f"       [{i}] {r.get('metadata', {}).get('title', 'N/A')[:50]}")
        
        # 4. build_context 테스트
        print("\n4️⃣ build_context 테스트...")
        if results:
            context = rag_service.build_context(results, max_tokens=30000)
            print(f"   컨텍스트 길이: {len(context)} 글자")
            print(f"   토큰 수: {len(rag_service.tokenizer.encode(context))}")
            
            if context:
                print(f"   미리보기 (처음 200글자):")
                print("   " + context[:200].replace("\n", "\n   "))
            else:
                print("   ⚠️  컨텍스트가 비어있습니다!")
        
        # 5. get_relevant_context_for_workflow_generation 테스트
        print("\n5️⃣ get_relevant_context_for_workflow_generation 테스트...")
        rag_context = await rag_service.get_relevant_context_for_workflow_generation(test_query)
        
        if rag_context:
            print(f"   ✅ RAG 컨텍스트 반환됨")
            print(f"   길이: {len(rag_context)} 글자")
            print(f"   미리보기 (처음 300글자):")
            print("   " + rag_context[:300].replace("\n", "\n   "))
        else:
            print(f"   ❌ RAG 컨텍스트 비어있음!")
        
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
