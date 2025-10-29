#!/usr/bin/env python3
"""
DB 저장된 청크 vs 검색 청크 비교 진단
"""
import sys
import os

# 경로 설정 수정
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import asyncio
from src.database.session import get_session
from src.database.models import Document, DocumentChunk, KnowledgeBase
from src.services.rag_service import get_rag_service

async def main():
    print("=" * 80)
    print("🔍 DB 저장 청크 vs 검색 청크 비교 진단")
    print("=" * 80)
    
    try:
        # 1. DB에 저장된 청크 확인
        print("\n1️⃣ DB에 저장된 청크 정보")
        print("-" * 80)
        
        with get_session() as session:
            docs = session.query(Document).all()
            print(f"총 문서: {len(docs)}개\n")
            
            for doc in docs:
                print(f"📄 문서: {doc.title}")
                print(f"   ID: {doc.id}")
                print(f"   Knowledge Base: {doc.knowledge_base.name if doc.knowledge_base else 'N/A'}")
                
                chunks = session.query(DocumentChunk).filter(
                    DocumentChunk.document_id == doc.id
                ).all()
                
                print(f"   저장된 청크 수: {len(chunks)}개")
                
                for chunk in chunks:
                    content_preview = chunk.content[:100] if chunk.content else "EMPTY"
                    print(f"     - Chunk {chunk.chunk_index}: {len(chunk.content)} 글자, {chunk.token_count} 토큰")
                    print(f"       미리보기: {content_preview}...")
                print()
        
        # 2. ChromaDB 검색 결과 확인
        print("\n2️⃣ ChromaDB 검색 결과")
        print("-" * 80)
        
        rag_service = get_rag_service()
        
        test_query = "워크플로우"
        print(f"테스트 쿼리: '{test_query}'\n")
        
        # 직접 hybrid_search 호출
        results = await rag_service.hybrid_search(
            query=test_query,
            limit=10,
            include_context=True,
            context_radius=1
        )
        
        print(f"검색 결과: {len(results)}개\n")
        
        for i, result in enumerate(results, 1):
            metadata = result.get("metadata", {})
            content = result.get("content", "")
            content_preview = content[:100] if content else "EMPTY"
            
            print(f"  [{i}] 문서: {metadata.get('title', 'N/A')}")
            print(f"      Doc ID: {metadata.get('document_id', 'N/A')}")
            print(f"      Chunk Index: {metadata.get('chunk_index', 'N/A')}")
            print(f"      Content Length: {len(content)} 글자")
            print(f"      Score: {result.get('final_score', 'N/A')}")
            print(f"      Context Chunks Count: {result.get('context_chunks_count', 'N/A')}")
            print(f"      Context Range: {result.get('context_range', 'N/A')}")
            print(f"      미리보기: {content_preview}...")
            print()
        
        # 3. build_context 출력 확인
        print("\n3️⃣ build_context 출력")
        print("-" * 80)
        
        if results:
            context = rag_service.build_context(results, max_tokens=30000)
            context_lines = context.split('\n')
            print(f"총 줄 수: {len(context_lines)}")
            print(f"총 글자 수: {len(context)} 글자\n")
            
            # 각 섹션 분석
            chunk_count = context.count('**')
            print(f"포함된 청크 섹션: {chunk_count // 2}개")
            
            print("\n처음 500글자:")
            print("-" * 80)
            print(context[:500])
            print("\n마지막 500글자:")
            print("-" * 80)
            print(context[-500:])
        
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
