#!/usr/bin/env python3
"""
빠른 재임베딩 스크립트 - 간단한 버전
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("=" * 80)
print("🔄 RAG 문서 재임베딩 - 빠른 버전")
print("=" * 80)

try:
    print("\n1️⃣  모듈 임포트 중...")
    from database.session import get_session
    from database.models import Document, DocumentChunk
    print("   ✅ 데이터베이스 모듈 임포트됨")
    
    from services.rag_service import RAGService
    print("   ✅ RAG 서비스 임포트됨")
    
    from utils import get_logger
    logger = get_logger("quick_reprocess")
    print("   ✅ 로거 임포트됨")
    
    print("\n2️⃣  데이터베이스 정보 확인 중...")
    with get_session() as session:
        # 문서 수 확인
        doc_count = session.query(Document).filter(
            Document.is_processed == True
        ).count()
        print(f"   처리된 문서: {doc_count}개")
        
        # 청크 수 확인
        chunk_count = session.query(DocumentChunk).count()
        print(f"   기존 청크: {chunk_count}개")
    
    if doc_count == 0:
        print("\n⚠️  처리할 문서가 없습니다!")
        sys.exit(0)
    
    print(f"\n3️⃣  {doc_count}개 문서 재임베딩 준비...")
    print("   설정: chunk_size=1500, overlap=300")
    print("\n   💡 팁: 시간이 걸릴 수 있습니다. 중단하지 마세요!")
    
    # 실제 재임베딩은 별도 스크립트에서 진행
    print("\n✅ 준비 완료!")
    print("\n다음 단계:")
    print("   python reprocess_documents.py")
    
except Exception as e:
    print(f"\n❌ 오류: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
