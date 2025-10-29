#!/usr/bin/env python3
"""
직접 RAG 테스트 - get_relevant_context_for_workflow_generation 확인
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import asyncio

async def main():
    print("=" * 80)
    print("🔍 RAG 직접 테스트 (get_relevant_context_for_workflow_generation)")
    print("=" * 80)
    
    try:
        from services.rag_service import get_rag_service
        from database.session import get_session
        from database.models import Document, KnowledgeBase
        
        # 1. 데이터 확인
        print("\n1️⃣ 데이터베이스 상태 확인...")
        with get_session() as session:
            kbs = session.query(KnowledgeBase).all()
            docs = session.query(Document).all()
            
            print(f"   지식 베이스: {len(kbs)}개")
            print(f"   문서: {len(docs)}개")
            
            for kb in kbs:
                kb_docs = [d for d in docs if d.knowledge_base_id == kb.id]
                print(f"   - {kb.name}: {len(kb_docs)}개 문서")
        
        # 2. RAG 서비스 호출
        print("\n2️⃣ RAG 서비스 직접 호출...")
        rag_service = get_rag_service()
        
        test_queries = [
            "워크플로우",
            "파이썬",
            "API 호출",
            "데이터 처리"
        ]
        
        for query in test_queries:
            print(f"\n   쿼리: '{query}'")
            
            # 직접 호출
            context = await rag_service.get_relevant_context_for_workflow_generation(query)
            
            if context:
                print(f"   ✅ 결과: {len(context)} 글자")
                print(f"   미리보기: {context[:200]}...")
            else:
                print(f"   ❌ 결과: 비어있음")
        
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
