#!/usr/bin/env python3
"""
RAG 진단 스크립트 - 청크가 제대로 확장되는지 확인
"""
import sys
import os
import asyncio

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from database.session import get_session
from database.models import Document, DocumentChunk, KnowledgeBase
from services.rag_service import RAGService
from utils import get_logger

logger = get_logger("diagnose_rag")

async def main():
    print("=" * 80)
    print("🔍 RAG 진단 시작")
    print("=" * 80)
    
    with get_session() as session:
        # 1. 지식 베이스 상태 확인
        print("\n1️⃣ 지식 베이스 상태")
        print("-" * 80)
        
        kbs = session.query(KnowledgeBase).all()
        print(f"총 지식 베이스: {len(kbs)}개")
        
        for kb in kbs:
            docs = session.query(Document).filter(Document.knowledge_base_id == kb.id).all()
            print(f"\n  📚 {kb.name} ({kb.category.value})")
            print(f"     문서 수: {len(docs)}개")
            
            for doc in docs[:3]:  # 처음 3개만 표시
                chunks = session.query(DocumentChunk).filter(
                    DocumentChunk.document_id == doc.id
                ).all()
                print(f"     - {doc.title}: {len(chunks)}개 청크")
                
                for chunk in chunks[:2]:  # 처음 2개 청크만
                    print(f"       Chunk {chunk.chunk_index}: {len(chunk.content)} 글자, "
                          f"{chunk.token_count} 토큰")
        
        # 2. RAG 서비스 테스트
        print("\n2️⃣ RAG 서비스 테스트")
        print("-" * 80)
        
        rag_service = RAGService()
        
        # 테스트 쿼리
        test_query = "워크플로우 생성"
        print(f"\n테스트 쿼리: '{test_query}'")
        
        # 하이브리드 검색 (context 확장 포함)
        try:
            results = await rag_service.hybrid_search(
                query=test_query,
                limit=5,
                include_context=True,
                context_radius=1
            )
            
            print(f"✅ 검색 결과: {len(results)}개")
            
            for i, result in enumerate(results):
                metadata = result.get("metadata", {})
                content_len = len(result.get("content", ""))
                
                print(f"\n  결과 #{i+1}")
                print(f"    제목: {metadata.get('title', 'N/A')}")
                print(f"    청크 인덱스: {metadata.get('chunk_index', 'N/A')}")
                print(f"    컨텐츠 길이: {content_len} 글자")
                print(f"    스코어: {result.get('final_score', 'N/A'):.3f}")
                print(f"    문맥 확장 여부: {'context_chunks_count' in result}")
                
                if 'context_chunks_count' in result:
                    print(f"    포함된 청크 수: {result.get('context_chunks_count')}")
                    print(f"    청크 범위: {result.get('context_range')}")
                
                # 컨텐츠 프리뷰
                content_preview = result.get("content", "")[:150]
                print(f"    컨텐츠 미리보기: {content_preview}...")
        
        except Exception as e:
            print(f"❌ 검색 오류: {e}")
            import traceback
            traceback.print_exc()
        
        # 3. build_context 테스트
        print("\n3️⃣ build_context 테스트")
        print("-" * 80)
        
        try:
            if results:
                # build_context 호출
                context = rag_service.build_context(results, max_tokens=30000)
                
                print(f"✅ 컨텍스트 생성 성공")
                print(f"  컨텍스트 길이: {len(context)} 글자")
                print(f"  토큰 수 (추정): {len(rag_service.tokenizer.encode(context))}")
                
                # 줄 수 세기
                lines = context.split('\n')
                print(f"  줄 수: {len(lines)}")
                
                # 청크 수 세기
                chunk_count = context.count('[Chunk')
                print(f"  포함된 청크 수: {chunk_count}")
                
                # 마지막 부분 미리보기
                print(f"\n  컨텍스트 마지막 500글자:")
                print("  " + "-" * 76)
                print("  " + context[-500:].replace('\n', '\n  '))
                print("  " + "-" * 76)
        
        except Exception as e:
            print(f"❌ build_context 오류: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("✅ 진단 완료")
    print("=" * 80)
    
    # 결론
    print("\n📋 결론:")
    print("1. 검색 결과에 context_chunks_count가 있는가?")
    print("2. build_context에서 여러 청크가 포함되는가?")
    print("3. 컨텍스트 길이가 충분한가?")

if __name__ == "__main__":
    asyncio.run(main())
